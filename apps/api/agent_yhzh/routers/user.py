import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from agent_yhzh.database import get_session, session_factory
from agent_yhzh.schemas import (
    InteractionAccepted,
    InteractionCreate,
    UserMemoryCreate,
    UserMemoryRead,
)
from agent_yhzh.security import CallerContext, get_user_context
from agent_yhzh.services.learning import capture_interaction, process_interaction_event
from agent_yhzh.services.memory import (
    create_memory,
    delete_memory,
    list_memories,
    reset_memories,
)
from agent_yhzh.worker import enqueue_interaction


router = APIRouter(prefix="/api/v1/user", tags=["user"])


async def _local_process(event_id: uuid.UUID) -> None:
    async with session_factory() as session:
        await process_interaction_event(session, event_id)


@router.post("/interaction", status_code=202, response_model=InteractionAccepted)
async def post_interaction(
    payload: InteractionCreate,
    background_tasks: BackgroundTasks,
    context: CallerContext = Depends(get_user_context),
    session: AsyncSession = Depends(get_session),
) -> dict:
    event = await capture_interaction(
        session,
        context=context,
        event_type=payload.event_type,
        content=payload.content,
        consent=payload.consent,
        target=payload.target,
    )
    queued = event.processed_status == "queued"
    if queued:
        try:
            enqueue_interaction(event.id)
        except Exception:
            background_tasks.add_task(_local_process, event.id)
    return {
        "status": "accepted",
        "event_id": event.id,
        "learning_queued": queued,
        "redaction_count": event.redaction_count,
    }


@router.get("/memories", response_model=list[UserMemoryRead])
async def get_memories(
    limit: int = Query(default=100, ge=1, le=200),
    context: CallerContext = Depends(get_user_context),
    session: AsyncSession = Depends(get_session),
):
    return await list_memories(session, context, limit)


@router.post("/memories", response_model=UserMemoryRead, status_code=201)
async def post_memory(
    payload: UserMemoryCreate,
    context: CallerContext = Depends(get_user_context),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await create_memory(session, context, payload)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail="Consent required") from error


@router.delete("/memories/{memory_id}", status_code=204)
async def remove_memory(
    memory_id: uuid.UUID,
    context: CallerContext = Depends(get_user_context),
    session: AsyncSession = Depends(get_session),
):
    if not await delete_memory(session, context, memory_id):
        raise HTTPException(status_code=404, detail="Not found")


@router.delete("/memories", status_code=200)
async def remove_all_memories(
    context: CallerContext = Depends(get_user_context),
    session: AsyncSession = Depends(get_session),
) -> dict[str, int]:
    return {"deleted": await reset_memories(session, context)}


@router.get("/experience")
async def get_experience(
    context: CallerContext = Depends(get_user_context),
) -> dict[str, object]:
    return {
        "status": "ready",
        "learning_consent": context.learning_consent,
        "message": (
            "助手只会从已同意、已脱敏且通过管理员审核的使用信号中改进；"
            "知识库本身对普通用户不可见。"
        ),
    }
