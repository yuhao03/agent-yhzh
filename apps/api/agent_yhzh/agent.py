import atexit

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph

from agent_yhzh.config import settings
from agent_yhzh.database import session_factory
from agent_yhzh.security import get_current_caller
from agent_yhzh.services.knowledge import generate_user_answer, search_knowledge
from agent_yhzh.services.learning import capture_interaction, process_interaction_event
from agent_yhzh.services.memory import list_memories
from agent_yhzh.services.model_config import get_runtime_model_config
from agent_yhzh.worker import enqueue_interaction


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


async def assistant_node(
    state: MessagesState,
    config: RunnableConfig,
) -> dict[str, list[AIMessage]]:
    user_message = next(
        (
            message
            for message in reversed(state["messages"])
            if isinstance(message, HumanMessage)
        ),
        None,
    )
    if user_message is None:
        return {"messages": [AIMessage(content="请告诉我你想解决的问题。")]}

    caller = get_current_caller()
    question = str(user_message.content)
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
        knowledge = await search_knowledge(
            session,
            question,
            tenant_id=caller.tenant_id,
            space_id=caller.space_id,
            product_scope=caller.product_scope,
        )
        memories = await list_memories(session, caller, limit=20)
        runtime = await get_runtime_model_config(
            session, caller.tenant_id, caller.space_id
        )

    answer = await generate_user_answer(question, knowledge, memories, runtime)
    return {"messages": [AIMessage(content=answer)]}


builder = StateGraph(MessagesState)
builder.add_node("assistant", assistant_node)
builder.add_edge(START, "assistant")
builder.add_edge("assistant", END)
graph = builder.compile(checkpointer=_build_checkpointer())
