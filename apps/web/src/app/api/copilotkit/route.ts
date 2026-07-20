import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { LangGraphHttpAgent } from "@copilotkit/runtime/langgraph";
import { NextRequest } from "next/server";

import {
  USER_COOKIE,
  backendUserHeaders,
  createUserSession,
  encodeUserSession,
  readUserSession,
} from "@/lib/user-session";

const serviceAdapter = new ExperimentalEmptyAdapter();

export async function POST(request: NextRequest) {
  const existing = readUserSession(request.cookies.get(USER_COOKIE)?.value);
  const session = existing ?? createUserSession(false);
  const runtime = new CopilotRuntime({
    agents: {
      knowledge_agent: new LangGraphHttpAgent({
        url: process.env.LANGGRAPH_DEPLOYMENT_URL ?? "http://127.0.0.1:8123/ag-ui",
        headers: Object.fromEntries(new Headers(backendUserHeaders(session))),
      }),
    },
  });
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });
  const response = await handleRequest(request);
  if (!existing) {
    response.headers.append(
      "Set-Cookie",
      `${USER_COOKIE}=${encodeUserSession(session)}; Path=/; HttpOnly; SameSite=Lax; Max-Age=31536000${process.env.NODE_ENV === "production" ? "; Secure" : ""}`,
    );
  }
  return response;
}
