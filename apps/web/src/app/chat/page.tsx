import type { Metadata } from "next";
import { cookies } from "next/headers";

import { ChatWorkspace } from "@/components/chat-workspace";
import { USER_COOKIE, isAuthTokenExpired, readUserSession } from "@/lib/user-session";

export const metadata: Metadata = { title: "工作台 · 砺知智能" };

export default async function ChatPage() {
  const cookieStore = await cookies();
  const session = readUserSession(cookieStore.get(USER_COOKIE)?.value);
  const memberExpired = session ? isAuthTokenExpired(session) : false;
  const member =
    session?.authToken && !memberExpired
      ? {
          email: session.email ?? "",
          displayName: session.displayName ?? session.email ?? "",
        }
      : null;
  return <ChatWorkspace member={member} memberExpired={memberExpired} />;
}
