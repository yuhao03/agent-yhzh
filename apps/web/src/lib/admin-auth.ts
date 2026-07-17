import "server-only";

import { createHmac, timingSafeEqual } from "node:crypto";

export const ADMIN_COOKIE = "agent_yhzh_admin";

function sessionSecret(): string {
  return process.env.ADMIN_SESSION_SECRET ?? "development-only-session-secret";
}

export function createAdminSessionToken(): string {
  return createHmac("sha256", sessionSecret())
    .update("agent-yhzh:admin-session:v1")
    .digest("hex");
}

export function isValidAdminSession(token: string | undefined): boolean {
  if (!token) return false;
  const expected = Buffer.from(createAdminSessionToken());
  const received = Buffer.from(token);
  return expected.length === received.length && timingSafeEqual(expected, received);
}

export function isValidAdminPassword(password: string | undefined): boolean {
  if (!password) return false;
  const expected = Buffer.from(
    process.env.ADMIN_API_KEY ?? "change-me-admin-key",
  );
  const received = Buffer.from(password);
  return expected.length === received.length && timingSafeEqual(expected, received);
}
