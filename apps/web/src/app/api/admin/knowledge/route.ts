import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { ADMIN_COOKIE, readAdminSession } from "@/lib/admin-auth";
import { fetchAdmin } from "@/lib/backend";

export async function POST(request: Request) {
  const cookieStore = await cookies();
  const session = readAdminSession(cookieStore.get(ADMIN_COOKIE)?.value);
  if (!session || session.role !== "admin") {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }

  try {
    const payload = (await request.json()) as Record<string, unknown>;
    const result = await fetchAdmin(session, "/api/v1/admin/knowledge", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    return NextResponse.json(result, { status: 201 });
  } catch {
    return NextResponse.json({ error: "创建失败" }, { status: 502 });
  }
}
