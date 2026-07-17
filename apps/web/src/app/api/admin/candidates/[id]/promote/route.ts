import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { ADMIN_COOKIE, isValidAdminSession } from "@/lib/admin-auth";
import { promoteCandidate } from "@/lib/backend";

export async function POST(
  request: Request,
  context: RouteContext<"/api/admin/candidates/[id]/promote">,
) {
  const cookieStore = await cookies();
  if (!isValidAdminSession(cookieStore.get(ADMIN_COOKIE)?.value)) {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }

  const { id } = await context.params;
  try {
    const payload = (await request.json()) as Record<string, unknown>;
    const result = await promoteCandidate(id, payload);
    return NextResponse.json(result);
  } catch {
    return NextResponse.json({ error: "发布失败" }, { status: 502 });
  }
}
