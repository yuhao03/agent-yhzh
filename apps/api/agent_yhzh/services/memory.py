import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from agent_yhzh.models import UserMemory
from agent_yhzh.schemas import UserMemoryCreate
from agent_yhzh.security import CallerContext, hash_user_reference


def _scope(context: CallerContext):
    if not context.user_id:
        raise ValueError("user_context_required")
    return (
        UserMemory.tenant_id == context.tenant_id,
        UserMemory.user_ref_hash == hash_user_reference(context.user_id),
        UserMemory.product_scope == context.product_scope,
    )


async def create_memory(
    session: AsyncSession, context: CallerContext, payload: UserMemoryCreate
) -> UserMemory:
    if not context.learning_consent or not payload.consent:
        raise PermissionError("memory_consent_required")
    expires_at = (
        datetime.now(UTC) + timedelta(days=payload.expires_in_days)
        if payload.expires_in_days
        else None
    )
    memory = UserMemory(
        tenant_id=context.tenant_id,
        user_ref_hash=hash_user_reference(context.user_id or ""),
        product_scope=context.product_scope,
        memory_type=payload.memory_type,
        content=payload.content.strip(),
        evidence={"source": "explicit_user_input"},
        consent=True,
        expires_at=expires_at,
    )
    session.add(memory)
    await session.commit()
    await session.refresh(memory)
    return memory


async def list_memories(
    session: AsyncSession, context: CallerContext, limit: int = 100
) -> list[UserMemory]:
    now = datetime.now(UTC)
    result = await session.scalars(
        select(UserMemory)
        .where(*_scope(context), UserMemory.status == "active")
        .where((UserMemory.expires_at.is_(None)) | (UserMemory.expires_at > now))
        .order_by(UserMemory.updated_at.desc())
        .limit(limit)
    )
    return list(result)


async def delete_memory(
    session: AsyncSession, context: CallerContext, memory_id: uuid.UUID
) -> bool:
    memory = await session.scalar(
        select(UserMemory).where(UserMemory.id == memory_id, *_scope(context))
    )
    if memory is None:
        return False
    memory.status = "deleted"
    memory.deleted_at = datetime.now(UTC)
    memory.content = "[deleted]"
    memory.evidence = {}
    await session.commit()
    return True


async def reset_memories(session: AsyncSession, context: CallerContext) -> int:
    result = await session.execute(delete(UserMemory).where(*_scope(context)))
    await session.commit()
    return int(getattr(result, "rowcount", 0) or 0)


async def expire_memories(session: AsyncSession) -> int:
    now = datetime.now(UTC)
    result = await session.execute(
        update(UserMemory)
        .where(
            UserMemory.status == "active",
            UserMemory.expires_at.is_not(None),
            UserMemory.expires_at <= now,
        )
        .values(status="expired", content="[expired]", evidence={})
    )
    await session.commit()
    return int(getattr(result, "rowcount", 0) or 0)
