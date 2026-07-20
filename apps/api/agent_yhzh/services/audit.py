from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from agent_yhzh.models import AuditEvent, OutboxEvent
from agent_yhzh.security import CallerContext


def add_audit(
    session: AsyncSession,
    context: CallerContext,
    *,
    action: str,
    object_type: str,
    object_id: str | None = None,
    details: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> AuditEvent:
    event = AuditEvent(
        tenant_id=context.tenant_id,
        space_id=context.space_id,
        actor_ref=context.actor_id,
        actor_role=context.role,
        action=action,
        object_type=object_type,
        object_id=object_id,
        details=details or {},
        request_id=request_id,
    )
    session.add(event)
    return event


def add_outbox(
    session: AsyncSession,
    *,
    tenant_id: str,
    event_type: str,
    aggregate_type: str,
    aggregate_id: str,
    payload: dict[str, Any] | None = None,
) -> OutboxEvent:
    event = OutboxEvent(
        tenant_id=tenant_id,
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        payload=payload or {},
    )
    session.add(event)
    return event
