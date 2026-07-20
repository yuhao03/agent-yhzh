import { NextRequest, NextResponse } from "next/server";

import { backendUrl } from "@/lib/backend";
import {
  USER_COOKIE,
  backendUserHeaders,
  readUserSession,
} from "@/lib/user-session";

export async function DELETE(
  request: NextRequest,
  context: RouteContext<"/api/user/memories/[id]">,
) {
  const session = readUserSession(request.cookies.get(USER_COOKIE)?.value);
  if (!session) return NextResponse.json({ error: "Session required" }, { status: 401 });
  const { id } = await context.params;
  const response = await fetch(`${backendUrl}/api/v1/user/memories/${id}`, {
    method: "DELETE",
    headers: backendUserHeaders(session),
  });
  return new NextResponse(null, { status: response.status });
}
