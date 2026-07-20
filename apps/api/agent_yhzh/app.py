import time
import uuid
from contextlib import asynccontextmanager

import uvicorn
from ag_ui_langgraph import add_langgraph_fastapi_endpoint
from copilotkit import LangGraphAGUIAgent
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from agent_yhzh.agent import graph
from agent_yhzh.config import settings
from agent_yhzh.database import close_database, engine, init_database
from agent_yhzh.observability import (
    HTTP_LATENCY,
    HTTP_REQUESTS,
    configure_logging,
    configure_tracing,
    logger,
)
from agent_yhzh.rate_limit import rate_limiter
from agent_yhzh.routers import admin, user
from agent_yhzh.security import (
    caller_from_request_headers,
    hash_user_reference,
    require_admin,
    require_ops,
    reset_caller_context,
    set_caller_context,
)


configure_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_database()
    yield
    await close_database()


class RequestBoundaryMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request = Request(scope, receive=receive)
        path = scope.get("path", "")
        method = scope.get("method", "GET")
        started = time.perf_counter()
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        context_token = None
        status_code = 500
        try:
            if path.startswith("/ag-ui"):
                context = caller_from_request_headers(request)
                allowed = await rate_limiter.allow(
                    f"{context.tenant_id}:{hash_user_reference(context.user_id or '')}"
                )
                if not allowed:
                    response = JSONResponse(
                        {"detail": "Too many requests"}, status_code=429
                    )
                    await response(scope, receive, send)
                    status_code = 429
                    return
                context_token = set_caller_context(context)

            async def send_with_metrics(message):
                nonlocal status_code
                if message["type"] == "http.response.start":
                    status_code = message["status"]
                    headers = list(message.get("headers", []))
                    headers.append((b"x-request-id", request_id.encode()))
                    message["headers"] = headers
                await send(message)

            await self.app(scope, receive, send_with_metrics)
        except Exception as error:
            if hasattr(error, "status_code"):
                status_code = int(error.status_code)
                response = JSONResponse(
                    {"detail": getattr(error, "detail", "Request failed")},
                    status_code=status_code,
                )
                await response(scope, receive, send)
            else:
                logger.exception("unhandled_request_error", path=path, request_id=request_id)
                raise
        finally:
            if context_token is not None:
                reset_caller_context(context_token)
            HTTP_REQUESTS.labels(method=method, path=path, status=str(status_code)).inc()
            HTTP_LATENCY.labels(method=method, path=path).observe(
                time.perf_counter() - started
            )


app = FastAPI(
    title="agent-yhzh API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.add_middleware(RequestBoundaryMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Admin-Key",
        "X-Actor-Id",
        "X-Actor-Role",
        "X-Tenant-Id",
        "X-Space-Id",
        "X-User-Id",
        "X-Session-Id",
        "X-Product-Scope",
        "X-Learning-Consent",
        "X-Request-Id",
    ],
)
app.include_router(admin.router)
app.include_router(user.router)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@app.get("/metrics", include_in_schema=False, dependencies=[Depends(require_ops)])
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get(
    "/api/v1/admin/openapi.json",
    include_in_schema=False,
    dependencies=[Depends(require_admin)],
)
async def protected_openapi():
    return app.openapi()


@app.get(
    "/api/v1/admin/docs",
    include_in_schema=False,
    dependencies=[Depends(require_admin)],
)
async def protected_docs():
    return get_swagger_ui_html(
        openapi_url="/api/v1/admin/openapi.json", title="agent-yhzh Admin API"
    )


add_langgraph_fastapi_endpoint(
    app=app,
    agent=LangGraphAGUIAgent(
        name="knowledge_agent",
        description="A user-facing agent backed by validated, admin-managed knowledge.",
        graph=graph,
    ),
    path="/ag-ui",
)
configure_tracing(app, engine)


def run() -> None:
    uvicorn.run(
        "agent_yhzh.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development",
    )
