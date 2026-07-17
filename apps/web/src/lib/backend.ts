import "server-only";

import type { AdminDashboardPayload } from "@/lib/types";

const backendUrl = process.env.BACKEND_URL ?? "http://127.0.0.1:8123";

async function fetchAdmin<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${backendUrl}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Key": process.env.ADMIN_API_KEY ?? "change-me-admin-key",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`Backend request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function getAdminDashboard(): Promise<AdminDashboardPayload> {
  const [stats, candidates, knowledge, graph] = await Promise.all([
    fetchAdmin<AdminDashboardPayload["stats"]>("/api/v1/admin/stats"),
    fetchAdmin<AdminDashboardPayload["candidates"]>("/api/v1/admin/candidates"),
    fetchAdmin<AdminDashboardPayload["knowledge"]>("/api/v1/admin/knowledge"),
    fetchAdmin<AdminDashboardPayload["graph"]>("/api/v1/admin/knowledge/graph"),
  ]);

  return { stats, candidates, knowledge, graph };
}

export async function promoteCandidate(
  candidateId: string,
  payload: Record<string, unknown>,
): Promise<unknown> {
  return fetchAdmin(`/api/v1/admin/candidates/${candidateId}/promote`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function createKnowledge(
  payload: Record<string, unknown>,
): Promise<unknown> {
  return fetchAdmin("/api/v1/admin/knowledge", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
