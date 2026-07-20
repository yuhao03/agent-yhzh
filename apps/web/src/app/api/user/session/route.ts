import { NextRequest, NextResponse } from "next/server";

import {
  USER_COOKIE,
  createUserSession,
  encodeUserSession,
  readUserSession,
} from "@/lib/user-session";

function setCookie(response: NextResponse, session: ReturnType<typeof createUserSession>) {
  response.cookies.set(USER_COOKIE, encodeUserSession(session), {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 365 * 24 * 60 * 60,
  });
}

export async function GET(request: NextRequest) {
  const existing = readUserSession(request.cookies.get(USER_COOKIE)?.value);
  const session = existing ?? createUserSession(false);
  const response = NextResponse.json({ learningConsent: session.learningConsent });
  if (!existing) setCookie(response, session);
  return response;
}

export async function POST(request: NextRequest) {
  const payload = (await request.json()) as { learningConsent?: boolean };
  const session =
    readUserSession(request.cookies.get(USER_COOKIE)?.value) ?? createUserSession(false);
  session.learningConsent = payload.learningConsent === true;
  session.sessionId = crypto.randomUUID();
  const response = NextResponse.json({ learningConsent: session.learningConsent });
  setCookie(response, session);
  return response;
}
