import "server-only";

import type { AdminSession } from "@/lib/admin-auth";
import type { AdminDashboardPayload } from "@/lib/types";

export const backendUrl = process.env.BACKEND_URL ?? "http://127.0.0.1:8123";

function adminHeaders(session: AdminSession): HeadersInit {
  return {
    Authorization: `Bearer ${process.env.ADMIN_SERVICE_TOKEN ?? "change-me-admin-service-token"}`,
    "X-Actor-Id": session.actorId,
    "X-Actor-Role": session.role,
    "X-Tenant-Id": session.tenantId,
    "X-Space-Id": session.spaceId,
  };
}

export async function fetchAdmin<T>(
  session: AdminSession,
  path: string,
  init?: RequestInit,
): Promise<T> {
  const headers = new Headers(adminHeaders(session));
  if (!(init?.body instanceof FormData)) headers.set("Content-Type", "application/json");
  new Headers(init?.headers).forEach((value, key) => headers.set(key, value));
  const response = await fetch(`${backendUrl}${path}`, {
    ...init,
    cache: "no-store",
    headers,
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(`Backend request failed: ${response.status} ${message}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export async function getAdminDashboard(
  session: AdminSession,
): Promise<AdminDashboardPayload> {
  const [stats, candidates, knowledge, graph, trends, documents, imports, relations, views, audits, modelConfigs] =
    await Promise.all([
      fetchAdmin<AdminDashboardPayload["stats"]>(session, "/api/v1/admin/stats"),
      fetchAdmin<AdminDashboardPayload["candidates"]>(session, "/api/v1/admin/candidates"),
      fetchAdmin<AdminDashboardPayload["knowledge"]>(session, "/api/v1/admin/knowledge"),
      fetchAdmin<AdminDashboardPayload["graph"]>(session, "/api/v1/admin/knowledge/graph"),
      fetchAdmin<AdminDashboardPayload["trends"]>(session, "/api/v1/admin/trends"),
      fetchAdmin<AdminDashboardPayload["documents"]>(session, "/api/v1/admin/documents"),
      fetchAdmin<AdminDashboardPayload["imports"]>(session, "/api/v1/admin/imports"),
      fetchAdmin<AdminDashboardPayload["relations"]>(session, "/api/v1/admin/relations"),
      fetchAdmin<AdminDashboardPayload["views"]>(session, "/api/v1/admin/views"),
      fetchAdmin<AdminDashboardPayload["audits"]>(session, "/api/v1/admin/audits"),
      fetchAdmin<AdminDashboardPayload["modelConfigs"]>(session, "/api/v1/admin/model-configs"),
    ]);
  return { stats, candidates, knowledge, graph, trends, documents, imports, relations, views, audits, modelConfigs };
}
