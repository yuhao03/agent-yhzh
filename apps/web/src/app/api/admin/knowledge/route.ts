import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { ADMIN_COOKIE, isValidAdminSession } from "@/lib/admin-auth";
import { createKnowledge } from "@/lib/backend";

export async function POST(request: Request) {
  const cookieStore = await cookies();
  if (!isValidAdminSession(cookieStore.get(ADMIN_COOKIE)?.value)) {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }

  try {
    const payload = (await request.json()) as Record<string, unknown>;
    const result = await createKnowledge(payload);
    return NextResponse.json(result, { status: 201 });
  } catch {
    return NextResponse.json({ error: "创建失败" }, { status: 502 });
  }
}
