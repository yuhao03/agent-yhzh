import asyncio
import uuid
from datetime import UTC, datetime

from celery import Celery
from sqlalchemy import select

from agent_yhzh.config import settings
from agent_yhzh.database import session_factory
from agent_yhzh.models import OutboxEvent
from agent_yhzh.services.documents import process_document_import
from agent_yhzh.services.learning import (
    delete_expired_interactions,
    process_interaction_event,
)
from agent_yhzh.services.memory import expire_memories


celery_app = Celery(
    "agent_yhzh",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.conf.update(
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=270,
    task_always_eager=settings.celery_task_always_eager,
    task_eager_propagates=settings.celery_task_eager_propagates,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    beat_schedule={
        "cleanup-private-data-daily": {
            "task": "agent_yhzh.cleanup_private_data",
            "schedule": 86400.0,
        },
        "dispatch-outbox-every-minute": {
            "task": "agent_yhzh.dispatch_outbox",
            "schedule": 60.0,
        },
    },
)


def _run(coroutine):
    return asyncio.run(coroutine)


@celery_app.task(name="agent_yhzh.health")
def worker_health() -> dict[str, str]:
    return {"status": "ok"}


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
    name="agent_yhzh.process_interaction",
)
def process_interaction_task(self, event_id: str) -> dict[str, str]:
    async def process() -> dict[str, str]:
        async with session_factory() as session:
            candidate = await process_interaction_event(session, uuid.UUID(event_id))
            return {
                "status": "processed",
                "candidate_id": str(candidate.id) if candidate else "",
            }

    return _run(process())


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 4},
    name="agent_yhzh.process_document",
)
def process_document_task(self, job_id: str) -> dict[str, str]:
    async def process() -> dict[str, str]:
        async with session_factory() as session:
            await process_document_import(session, uuid.UUID(job_id))
            return {"status": "processed", "job_id": job_id}

    return _run(process())


@celery_app.task(name="agent_yhzh.cleanup_private_data")
def cleanup_private_data_task() -> dict[str, int]:
    async def cleanup() -> dict[str, int]:
        async with session_factory() as session:
            interactions = await delete_expired_interactions(session)
            memories = await expire_memories(session)
            return {"interactions": interactions, "memories": memories}

    return _run(cleanup())


@celery_app.task(name="agent_yhzh.dispatch_outbox")
def dispatch_outbox_task() -> dict[str, int]:
    async def dispatch() -> dict[str, int]:
        async with session_factory() as session:
            events = list(
                await session.scalars(
                    select(OutboxEvent)
                    .where(OutboxEvent.status == "pending")
                    .order_by(OutboxEvent.created_at)
                    .limit(100)
                    .with_for_update(skip_locked=True)
                )
            )
            for event in events:
                event.status = "processed"
                event.attempts += 1
                event.processed_at = datetime.now(UTC)
            await session.commit()
            return {"processed": len(events)}

    return _run(dispatch())


def enqueue_interaction(event_id: uuid.UUID) -> None:
    if settings.celery_task_always_eager:
        raise RuntimeError("local_async_fallback")
    process_interaction_task.delay(str(event_id))


def enqueue_document(job_id: uuid.UUID) -> None:
    if settings.celery_task_always_eager:
        raise RuntimeError("local_async_fallback")
    process_document_task.delay(str(job_id))
