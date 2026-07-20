import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import {
  ADMIN_COOKIE,
  createAdminSessionToken,
  isValidAdminPassword,
} from "@/lib/admin-auth";

export async function POST(request: Request) {
  const payload = (await request.json()) as { password?: string };
  if (!isValidAdminPassword(payload.password)) {
    return NextResponse.json({ error: "认证失败" }, { status: 401 });
  }

  const cookieStore = await cookies();
    cookieStore.set(ADMIN_COOKIE, createAdminSessionToken("admin"), {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 8,
  });

  return NextResponse.json({ status: "ok" });
}

export async function DELETE() {
  const cookieStore = await cookies();
  cookieStore.delete(ADMIN_COOKIE);
  return NextResponse.json({ status: "ok" });
}
