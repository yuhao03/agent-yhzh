import { NextRequest, NextResponse } from "next/server";

import { backendUrl } from "@/lib/backend";
import {
  USER_COOKIE,
  createUserSession,
  encodeUserSession,
  memberSessionFrom,
  readUserSession,
  sessionCookieMaxAge,
  type UserSession,
} from "@/lib/user-session";

type AuthAction = "register" | "login" | "logout";

type BackendAuthResponse = {
  user: { id: string; email: string; display_name: string };
  token: string;
  expires_at: string;
};

const ERROR_MESSAGES: Record<string, string> = {
  invalid_email: "邮箱格式不正确。",
  weak_password: "密码至少 8 位，且需同时包含字母和数字。",
  email_exists: "该邮箱已注册，请直接登录。",
  invalid_credentials: "邮箱或密码不正确。",
  account_disabled: "账号已被禁用，请联系管理员。",
};

function serviceHeaders(session: UserSession): Record<string, string> {
  return {
    Authorization: `Bearer ${process.env.AGENT_SERVICE_TOKEN ?? "change-me-agent-service-token"}`,
    "X-Tenant-Id": session.tenantId,
    "Content-Type": "application/json",
  };
}

function withSessionCookie(response: NextResponse, session: UserSession) {
  response.cookies.set(USER_COOKIE, encodeUserSession(session), {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: sessionCookieMaxAge(session),
  });
  return response;
}

export async function POST(request: NextRequest) {
  const payload = (await request.json().catch(() => null)) as {
    action?: AuthAction;
    email?: string;
    password?: string;
    displayName?: string;
  } | null;
  if (!payload?.action) {
    return NextResponse.json({ error: "无效请求。" }, { status: 400 });
  }
  const existing = readUserSession(request.cookies.get(USER_COOKIE)?.value);
  const session = existing ?? createUserSession(false);

  if (payload.action === "logout") {
    if (session.authToken) {
      await fetch(`${backendUrl}/api/v1/auth/logout`, {
        method: "POST",
        headers: {
          ...serviceHeaders(session),
          "X-Auth-Token": session.authToken,
        },
        cache: "no-store",
      }).catch(() => null);
    }
    const guest = createUserSession(false);
    return withSessionCookie(NextResponse.json({ member: null }), guest);
  }

  const email = (payload.email ?? "").trim();
  const password = payload.password ?? "";
  if (!email || !password) {
    return NextResponse.json({ error: "请输入邮箱和密码。" }, { status: 400 });
  }
  const endpoint = payload.action === "register" ? "register" : "login";
  const body =
    endpoint === "register"
      ? {
          email,
          password,
          display_name: (payload.displayName ?? "").trim() || email.split("@")[0],
        }
      : { email, password };
  const response = await fetch(`${backendUrl}/api/v1/auth/${endpoint}`, {
    method: "POST",
    headers: serviceHeaders(session),
    body: JSON.stringify(body),
    cache: "no-store",
  }).catch(() => null);
  if (!response) {
    return NextResponse.json({ error: "服务暂时不可用,请稍后再试。" }, { status: 502 });
  }
  if (!response.ok) {
    const detail = (await response.json().catch(() => null)) as {
      detail?: string;
    } | null;
    return NextResponse.json(
      { error: ERROR_MESSAGES[detail?.detail ?? ""] ?? "操作失败,请稍后再试。" },
      { status: response.status },
    );
  }
  const data = (await response.json()) as BackendAuthResponse;
  const member = memberSessionFrom(session, data.user, data.token, data.expires_at);
  return withSessionCookie(
    NextResponse.json({
      member: { email: data.user.email, displayName: data.user.display_name },
    }),
    member,
  );
}
