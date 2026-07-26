import { NextRequest, NextResponse } from "next/server";

import {
  USER_COOKIE,
  createUserSession,
  encodeUserSession,
  isAuthTokenExpired,
  readUserSession,
  sessionCookieMaxAge,
  type UserSession,
} from "@/lib/user-session";

function setCookie(response: NextResponse, session: UserSession) {
  response.cookies.set(USER_COOKIE, encodeUserSession(session), {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: sessionCookieMaxAge(session),
  });
}

export async function GET(request: NextRequest) {
  const existing = readUserSession(request.cookies.get(USER_COOKIE)?.value);
  const memberExpired = existing ? isAuthTokenExpired(existing) : false;
  const session = existing && !memberExpired ? existing : createUserSession(false);
  const response = NextResponse.json({
    learningConsent: session.learningConsent,
    member: session.authToken
      ? { email: session.email ?? "", displayName: session.displayName ?? "" }
      : null,
    memberExpired,
  });
  if (!existing || memberExpired) setCookie(response, session);
  return response;
}

export async function POST(request: NextRequest) {
  const payload = (await request.json().catch(() => null)) as {
    learningConsent?: boolean;
  } | null;
  if (!payload || typeof payload !== "object") {
    return NextResponse.json({ error: "无效请求。" }, { status: 400 });
  }
  const existing = readUserSession(request.cookies.get(USER_COOKIE)?.value);
  const session =
    existing && !isAuthTokenExpired(existing) ? existing : createUserSession(false);
  session.learningConsent = payload.learningConsent === true;
  session.sessionId = crypto.randomUUID();
  const response = NextResponse.json({ learningConsent: session.learningConsent });
  setCookie(response, session);
  return response;
}
