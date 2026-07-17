import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { AdminDashboard } from "@/components/admin-dashboard";
import { ADMIN_COOKIE, isValidAdminSession } from "@/lib/admin-auth";
import { getAdminDashboard } from "@/lib/backend";
import type { AdminDashboardPayload } from "@/lib/types";

export default async function AdminPage() {
  const cookieStore = await cookies();
  if (!isValidAdminSession(cookieStore.get(ADMIN_COOKIE)?.value)) {
    redirect("/admin/login");
  }

  let data: AdminDashboardPayload | null = null;
  let error = "";
  try {
    data = await getAdminDashboard();
  } catch {
    error = "后端服务暂时不可用，请确认 API 与 PostgreSQL 已启动。";
  }

  return <AdminDashboard data={data} error={error} />;
}
