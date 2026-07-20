import "server-only";

import { createHmac, randomUUID, timingSafeEqual } from "node:crypto";

export const USER_COOKIE = "agent_yhzh_user";

export type UserSession = {
  userId: string;
  sessionId: string;
  learningConsent: boolean;
  tenantId: string;
  spaceId: string;
  productScope: string;
  expiresAt: number;
};

function secret(): string {
  const value = process.env.USER_SESSION_SECRET ?? "development-user-session-secret";
  if (process.env.NODE_ENV === "production" && value.startsWith("change-me")) {
    throw new Error("USER_SESSION_SECRET must be configured in production");
  }
  return value;
}

function signature(value: string): string {
  return createHmac("sha256", secret()).update(value).digest("base64url");
}

export function createUserSession(consent = false): UserSession {
  return {
    userId: randomUUID(),
    sessionId: randomUUID(),
    learningConsent: consent,
    tenantId: process.env.DEFAULT_TENANT_ID ?? "default",
    spaceId: process.env.DEFAULT_SPACE_ID ?? "default",
    productScope: process.env.DEFAULT_PRODUCT_SCOPE ?? "default",
    expiresAt: Date.now() + 365 * 24 * 60 * 60 * 1000,
  };
}

export function encodeUserSession(session: UserSession): string {
  const encoded = Buffer.from(JSON.stringify(session)).toString("base64url");
  return `${encoded}.${signature(encoded)}`;
}

export function readUserSession(token: string | undefined): UserSession | null {
  if (!token) return null;
  const [encoded, signed] = token.split(".");
  if (!encoded || !signed) return null;
  const left = Buffer.from(signature(encoded));
  const right = Buffer.from(signed);
  if (left.length !== right.length || !timingSafeEqual(left, right)) return null;
  try {
    const session = JSON.parse(
      Buffer.from(encoded, "base64url").toString("utf8"),
    ) as UserSession;
    return session.expiresAt > Date.now() ? session : null;
  } catch {
    return null;
  }
}

export function backendUserHeaders(session: UserSession): HeadersInit {
  return {
    Authorization: `Bearer ${process.env.AGENT_SERVICE_TOKEN ?? "change-me-agent-service-token"}`,
    "X-User-Id": session.userId,
    "X-Session-Id": session.sessionId,
    "X-Learning-Consent": String(session.learningConsent),
    "X-Tenant-Id": session.tenantId,
    "X-Space-Id": session.spaceId,
    "X-Product-Scope": session.productScope,
  };
}
