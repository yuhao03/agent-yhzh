import { NextRequest, NextResponse } from "next/server";

import { backendUrl } from "@/lib/backend";
import {
  USER_COOKIE,
  backendUserHeaders,
  isAuthTokenExpired,
  readUserSession,
} from "@/lib/user-session";

async function forward(request: NextRequest, method: string) {
  const session = readUserSession(request.cookies.get(USER_COOKIE)?.value);
  if (!session) return NextResponse.json({ error: "Session required" }, { status: 401 });
  if (isAuthTokenExpired(session)) {
    return NextResponse.json({ error: "auth_expired" }, { status: 401 });
  }
  const response = await fetch(`${backendUrl}/api/v1/user/memories`, {
    method,
    headers: {
      ...backendUserHeaders(session),
      "Content-Type": "application/json",
    },
    body: method === "POST" ? await request.text() : undefined,
    cache: "no-store",
  });
  const text = await response.text();
  return new NextResponse(text || null, {
    status: response.status,
    headers: { "Content-Type": "application/json" },
  });
}

export async function GET(request: NextRequest) {
  return forward(request, "GET");
}

export async function POST(request: NextRequest) {
  return forward(request, "POST");
}

export async function DELETE(request: NextRequest) {
  return forward(request, "DELETE");
}
