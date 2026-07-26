import "server-only";

import { createHmac, timingSafeEqual } from "node:crypto";

export const ADMIN_COOKIE = "agent_yhzh_admin";

export type AdminSession = {
  actorId: string;
  role: "admin" | "reviewer";
  tenantId: string;
  spaceId: string;
  expiresAt: number;
};

function sessionSecret(): string {
  const secret = process.env.ADMIN_SESSION_SECRET ?? "change-me-admin-session-secret";
  if (process.env.NODE_ENV === "production" && secret.startsWith("change-me")) {
    throw new Error("ADMIN_SESSION_SECRET must be configured in production");
  }
  return secret;
}

function sign(value: string): string {
  return createHmac("sha256", sessionSecret()).update(value).digest("base64url");
}

function safeEqual(left: string, right: string): boolean {
  const expected = Buffer.from(left);
  const received = Buffer.from(right);
  return expected.length === received.length && timingSafeEqual(expected, received);
}

export function createAdminSessionToken(
  role: AdminSession["role"] = "admin",
): string {
  const payload: AdminSession = {
    actorId: "local-admin",
    role,
    tenantId: process.env.DEFAULT_TENANT_ID ?? "default",
    spaceId: process.env.DEFAULT_SPACE_ID ?? "default",
    expiresAt: Date.now() + 8 * 60 * 60 * 1000,
  };
  const encoded = Buffer.from(JSON.stringify(payload)).toString("base64url");
  return `${encoded}.${sign(encoded)}`;
}

export function readAdminSession(token: string | undefined): AdminSession | null {
  if (!token) return null;
  const [encoded, signature] = token.split(".");
  if (!encoded || !signature || !safeEqual(sign(encoded), signature)) return null;
  try {
    const session = JSON.parse(
      Buffer.from(encoded, "base64url").toString("utf8"),
    ) as AdminSession;
    if (
      session.expiresAt <= Date.now() ||
      !["admin", "reviewer"].includes(session.role) ||
      !session.actorId ||
      !session.tenantId ||
      !session.spaceId
    ) return null;
    return session;
  } catch {
    return null;
  }
}

export function isValidAdminSession(token: string | undefined): boolean {
  return readAdminSession(token) !== null;
}

export function isValidAdminPassword(password: string | undefined): boolean {
  if (!password) return false;
  const configured = process.env.ADMIN_API_KEY ?? "change-me-admin-key";
  if (process.env.NODE_ENV === "production" && configured.startsWith("change-me")) {
    throw new Error("ADMIN_API_KEY must be configured in production");
  }
  return safeEqual(configured, password);
}
