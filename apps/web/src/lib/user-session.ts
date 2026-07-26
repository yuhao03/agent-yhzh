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
  /** 登录态:后端会话 token,逐请求由后端校验。 */
  authToken?: string;
  /** 登录态:后端会话过期时间(毫秒时间戳,来自 /api/v1/auth/* 的 expires_at)。 */
  authTokenExpiresAt?: number;
  email?: string;
  displayName?: string;
};

const GUEST_COOKIE_MAX_AGE = 365 * 24 * 60 * 60;
const AUTH_TOKEN_FALLBACK_TTL_MS = 30 * 24 * 60 * 60 * 1000;

export function isMemberSession(session: UserSession): boolean {
  return Boolean(session.authToken);
}

export function isAuthTokenExpired(session: UserSession): boolean {
  if (!session.authToken) return false;
  return !session.authTokenExpiresAt || session.authTokenExpiresAt <= Date.now();
}

export function sessionCookieMaxAge(session: UserSession): number {
  if (!session.authToken || !session.authTokenExpiresAt) return GUEST_COOKIE_MAX_AGE;
  return Math.max(60, Math.floor((session.authTokenExpiresAt - Date.now()) / 1000));
}

function secret(): string {
  const value = process.env.USER_SESSION_SECRET ?? "change-me-user-session-secret";
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
  const headers: Record<string, string> = {
    Authorization: `Bearer ${process.env.AGENT_SERVICE_TOKEN ?? "change-me-agent-service-token"}`,
    "X-User-Id": session.userId,
    "X-Session-Id": session.sessionId,
    "X-Learning-Consent": String(session.learningConsent),
    "X-Tenant-Id": session.tenantId,
    "X-Space-Id": session.spaceId,
    "X-Product-Scope": session.productScope,
  };
  if (session.authToken) headers["X-Auth-Token"] = session.authToken;
  return headers;
}

export function memberSessionFrom(
  base: UserSession | null,
  account: { id: string; email: string; display_name: string },
  authToken: string,
  authTokenExpiresAt: string,
): UserSession {
  const guest = base ?? createUserSession(false);
  const parsed = Date.parse(authTokenExpiresAt);
  return {
    ...guest,
    userId: account.id,
    sessionId: randomUUID(),
    authToken,
    authTokenExpiresAt: Number.isNaN(parsed)
      ? Date.now() + AUTH_TOKEN_FALLBACK_TTL_MS
      : parsed,
    email: account.email,
    displayName: account.display_name,
  };
}
