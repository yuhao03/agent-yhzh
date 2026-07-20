import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { ADMIN_COOKIE, readAdminSession } from "@/lib/admin-auth";
import { fetchAdmin } from "@/lib/backend";

async function proxy(
  request: Request,
  context: RouteContext<"/api/admin/backend/[...path]">,
) {
  const cookieStore = await cookies();
  const session = readAdminSession(cookieStore.get(ADMIN_COOKIE)?.value);
  if (!session) return NextResponse.json({ error: "Not found" }, { status: 404 });
  if (request.method !== "GET" && session.role !== "admin") {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 });
  }
  const { path } = await context.params;
  const url = new URL(request.url);
  const backendPath = `/api/v1/admin/${path.join("/")}${url.search}`;
  let body: BodyInit | undefined;
  if (!["GET", "HEAD"].includes(request.method)) {
    body = request.headers.get("content-type")?.includes("multipart/form-data")
      ? await request.formData()
      : await request.text();
  }
  try {
    const result = await fetchAdmin(session, backendPath, {
      method: request.method,
      body,
    });
    return NextResponse.json(result ?? { status: "ok" });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Backend failed" },
      { status: 502 },
    );
  }
}

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
