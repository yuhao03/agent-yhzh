import atexit

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph

from agent_yhzh.config import settings
from agent_yhzh.database import session_factory
from agent_yhzh.services.knowledge import generate_user_answer, search_knowledge
from agent_yhzh.services.learning import capture_interaction


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
            connect_timeout=2,
        )
        saver = PostgresSaver(connection)
        saver.setup()
        atexit.register(connection.close)
        return saver
    except Exception:
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

    configurable = config.get("configurable", {})
    user_id = str(configurable.get("user_id", "demo-user"))
    session_id = str(configurable.get("thread_id", "demo-session"))
    product_scope = str(configurable.get("product_scope", "default"))
    question = str(user_message.content)

    async with session_factory() as session:
        await capture_interaction(
            session,
            user_id=user_id,
            session_id=session_id,
            event_type="question",
            content=question,
            consent=True,
        )
        knowledge = await search_knowledge(
            session,
            question,
            product_scope=product_scope,
        )

    answer = await generate_user_answer(question, knowledge)
    return {"messages": [AIMessage(content=answer)]}


builder = StateGraph(MessagesState)
builder.add_node("assistant", assistant_node)
builder.add_edge(START, "assistant")
builder.add_edge("assistant", END)
graph = builder.compile(checkpointer=_build_checkpointer())
