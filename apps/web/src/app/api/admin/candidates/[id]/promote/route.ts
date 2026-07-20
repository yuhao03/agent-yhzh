import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { ADMIN_COOKIE, readAdminSession } from "@/lib/admin-auth";
import { fetchAdmin } from "@/lib/backend";

export async function POST(
  request: Request,
  context: RouteContext<"/api/admin/candidates/[id]/promote">,
) {
  const cookieStore = await cookies();
  const session = readAdminSession(cookieStore.get(ADMIN_COOKIE)?.value);
  if (!session || session.role !== "admin") {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }

  const { id } = await context.params;
  try {
    const payload = (await request.json()) as Record<string, unknown>;
    const result = await fetchAdmin(
      session,
      `/api/v1/admin/candidates/${id}/promote`,
      { method: "POST", body: JSON.stringify(payload) },
    );
    return NextResponse.json(result);
  } catch {
    return NextResponse.json({ error: "发布失败" }, { status: 502 });
  }
}
