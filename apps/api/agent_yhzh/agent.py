"""Supervisor + 子 Agent 编排图。

supervisor 节点负责:捕获交互信号(学习管道)、意图路由;
每个专家节点按自身分类检索知识与私有记忆,经多协议网关生成回答。
路由结果写入图状态(active_agent/category),通过 AG-UI 同步给前端。
"""

import atexit
from collections.abc import Hashable
from functools import partial

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph

from agent_yhzh.config import settings
from agent_yhzh.database import session_factory
from agent_yhzh.security import get_current_caller
from agent_yhzh.services.knowledge import search_knowledge
from agent_yhzh.services.learning import capture_interaction, process_interaction_event
from agent_yhzh.services.memory import list_memories
from agent_yhzh.services.model_config import get_runtime_model_config
from agent_yhzh.services.subagents import (
    GENERALIST_SLUG,
    SUBAGENTS,
    SubAgentSpec,
    generate_agent_answer,
    get_subagent,
    route_question,
)
from agent_yhzh.services.taxonomy import classify_text
from agent_yhzh.worker import enqueue_interaction


class AgentState(MessagesState):
    active_agent: str
    active_agent_name: str
    category: str
    routed_by: str


def _build_checkpointer():
    if not settings.is_postgres:
        return MemorySaver()
    try:
        import psycopg
        from langgraph.checkpoint.postgres import PostgresSaver

        connection = psycopg.connect(
            settings.checkpoint_database_url,
            autocommit=True,
            prepare_threshold=0,
            connect_timeout=3,
        )
        saver = PostgresSaver(connection)
        saver.setup()
        atexit.register(connection.close)
        return saver
    except Exception:
        if settings.environment == "production":
            raise
        return MemorySaver()


def _latest_question(state: MessagesState) -> str | None:
    message = next(
        (
            message
            for message in reversed(state["messages"])
            if isinstance(message, HumanMessage)
        ),
        None,
    )
    return str(message.content) if message else None


async def supervisor_node(state: AgentState, config: RunnableConfig) -> dict:
    question = _latest_question(state)
    if question is None:
        return {
            "messages": [AIMessage(content="请告诉我你想解决的问题。")],
            "active_agent": "none",
            "active_agent_name": "",
            "category": "general",
            "routed_by": "none",
        }

    caller = get_current_caller()
    async with session_factory() as session:
        event = await capture_interaction(
            session,
            context=caller,
            event_type="question",
            content=question,
            consent=caller.learning_consent,
        )
        if event.processed_status == "queued":
            try:
                enqueue_interaction(event.id)
            except Exception:
                await process_interaction_event(session, event.id)
        runtime = await get_runtime_model_config(
            session, caller.tenant_id, caller.space_id
        )

    spec, routed_by = await route_question(question, runtime)
    return {
        "active_agent": spec.slug,
        "active_agent_name": spec.name,
        # 展示分类跟随路由到的专家,generalist 没有专属分类才退回关键词分类。
        "category": spec.categories[0] if spec.categories else classify_text(question),
        "routed_by": routed_by,
    }


async def specialist_node(
    state: AgentState, config: RunnableConfig, *, spec: SubAgentSpec
) -> dict:
    question = _latest_question(state)
    if question is None:
        return {"messages": [AIMessage(content="请告诉我你想解决的问题。")]}

    caller = get_current_caller()
    async with session_factory() as session:
        knowledge = await search_knowledge(
            session,
            question,
            tenant_id=caller.tenant_id,
            space_id=caller.space_id,
            product_scope=caller.product_scope,
            categories=list(spec.categories) or None,
        )
        memories = await list_memories(session, caller, limit=20)
        runtime = await get_runtime_model_config(
            session, caller.tenant_id, caller.space_id
        )

    answer = await generate_agent_answer(spec, question, knowledge, memories, runtime)
    return {
        "messages": [AIMessage(content=answer, name=spec.slug)],
        "active_agent": spec.slug,
        "active_agent_name": spec.name,
    }


def _route(state: AgentState) -> str:
    slug = state.get("active_agent") or GENERALIST_SLUG
    if slug == "none":
        return END
    return get_subagent(slug).slug


builder = StateGraph(AgentState)
builder.add_node("supervisor", supervisor_node)
for spec in SUBAGENTS:
    builder.add_node(spec.slug, partial(specialist_node, spec=spec))
    builder.add_edge(spec.slug, END)
builder.add_edge(START, "supervisor")
_route_targets: dict[Hashable, str] = {spec.slug: spec.slug for spec in SUBAGENTS}
_route_targets[END] = END
builder.add_conditional_edges("supervisor", _route, _route_targets)
graph = builder.compile(checkpointer=_build_checkpointer())
