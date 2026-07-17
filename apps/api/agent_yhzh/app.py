from contextlib import asynccontextmanager

import uvicorn
from ag_ui_langgraph import add_langgraph_fastapi_endpoint
from copilotkit import LangGraphAGUIAgent
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent_yhzh.agent import graph
from agent_yhzh.config import settings
from agent_yhzh.database import close_database, init_database
from agent_yhzh.routers import admin, user


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_database()
    yield
    await close_database()


app = FastAPI(
    title="agent-yhzh API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin.router)
app.include_router(user.router)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


add_langgraph_fastapi_endpoint(
    app=app,
    agent=LangGraphAGUIAgent(
        name="knowledge_agent",
        description="A user-facing agent backed by validated, admin-managed knowledge.",
        graph=graph,
    ),
    path="/ag-ui",
)


def run() -> None:
    uvicorn.run(
        "agent_yhzh.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development",
    )
