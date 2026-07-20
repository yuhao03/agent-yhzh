import re
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_yhzh.config import settings
from agent_yhzh.models import (
    FeedbackSignal,
    InteractionEvent,
    KnowledgeCandidate,
    PromotionPolicy,
)
from agent_yhzh.observability import LEARNING_EVENTS
from agent_yhzh.security import CallerContext, hash_user_reference


REDACTION_PATTERNS = [
    (re.compile(r"(?<!\w)[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?!\w)"), "[邮箱]"),
    (re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"), "[手机号]"),
    (re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"), "[身份证号]"),
    (re.compile(r"(?<!\d)\d{16,19}(?!\d)"), "[银行卡号]"),
]


def redact_text(content: str) -> tuple[str, int]:
    redacted = content
    count = 0
    for pattern, replacement in REDACTION_PATTERNS:
        redacted, replacements = pattern.subn(replacement, redacted)
        count += replacements
    return redacted, count


def normalize_learning_key(content: str) -> str:
    normalized = re.sub(r"\s+", " ", content.strip().lower())
    normalized = re.sub(r"[，。！？、,.!?;；:：\"'“”‘’()（）]", "", normalized)
    return normalized[:320]


async def capture_interaction(
    session: AsyncSession,
    *,
    context: CallerContext,
    event_type: str,
    content: str,
    consent: bool,
    target: str | None = None,
) -> InteractionEvent:
    if not context.user_id or not context.session_id:
        raise ValueError("user_context_required")
    redacted, redaction_count = redact_text(content)
    effective_consent = bool(context.learning_consent and consent)
    event = InteractionEvent(
        tenant_id=context.tenant_id,
        space_id=context.space_id,
        user_ref_hash=hash_user_reference(context.user_id),
        session_id=context.session_id,
        product_scope=context.product_scope,
        event_type=event_type,
        payload={"content": redacted, "target": target},
        consent=effective_consent,
        sensitivity="redacted" if redaction_count else "normal",
        redaction_count=redaction_count,
        processed_status="queued" if effective_consent else "ignored_no_consent",
        retention_expires_at=datetime.now(UTC)
        + timedelta(days=settings.interaction_retention_days),
    )
    session.add(event)
    await session.flush()
    if event_type in {"accepted", "rejected", "task_success", "task_failure"}:
        session.add(
            FeedbackSignal(
                tenant_id=context.tenant_id,
                space_id=context.space_id,
                event_id=event.id,
                signal_type=event_type,
                value={"content": redacted},
                target=target,
            )
        )
    await session.commit()
    await session.refresh(event)
    LEARNING_EVENTS.labels(status=event.processed_status, event_type=event_type).inc()
    return event


async def process_interaction_event(
    session: AsyncSession, event_id: uuid.UUID
) -> KnowledgeCandidate | None:
    event = await session.scalar(
        select(InteractionEvent)
        .where(InteractionEvent.id == event_id)
        .with_for_update()
    )
    if event is None or event.processed_status not in {"queued", "failed"}:
        return None
    if not event.consent or event.event_type not in {"question", "correction", "feedback"}:
        event.processed_status = "ignored"
        await session.commit()
        return None

    content = str(event.payload.get("content", "")).strip()
    normalized_key = normalize_learning_key(content)
    if not normalized_key:
        event.processed_status = "ignored_empty"
        await session.commit()
        return None

    candidate = await session.scalar(
        select(KnowledgeCandidate)
        .where(
            KnowledgeCandidate.tenant_id == event.tenant_id,
            KnowledgeCandidate.space_id == event.space_id,
            KnowledgeCandidate.normalized_key == normalized_key,
        )
        .with_for_update()
    )
    if candidate is None:
        candidate = KnowledgeCandidate(
            tenant_id=event.tenant_id,
            space_id=event.space_id,
            normalized_key=normalized_key,
            title=content[:240],
            content=content,
            occurrence_count=1,
            distinct_user_count=1,
            score=0.2,
            source_event_ids=[str(event.id)],
            observed_user_hashes=[event.user_ref_hash],
            evidence_summary="来自已同意学习且已脱敏的用户互动。",
        )
        session.add(candidate)
    else:
        candidate.occurrence_count += 1
        candidate.source_event_ids = [*candidate.source_event_ids, str(event.id)][-100:]
        if event.user_ref_hash not in candidate.observed_user_hashes:
            candidate.observed_user_hashes = [
                *candidate.observed_user_hashes,
                event.user_ref_hash,
            ][-500:]
            candidate.distinct_user_count += 1

    policy = await session.scalar(
        select(PromotionPolicy).where(
            PromotionPolicy.tenant_id == event.tenant_id,
            PromotionPolicy.space_id == event.space_id,
            PromotionPolicy.knowledge_type == candidate.candidate_type,
        )
    )
    occurrence_threshold = (
        policy.occurrence_threshold if policy else settings.candidate_review_threshold
    )
    distinct_threshold = (
        policy.min_distinct_users if policy else settings.candidate_min_distinct_users
    )
    candidate.score = min(
        0.98,
        0.15
        + min(candidate.occurrence_count, 10) * 0.05
        + min(candidate.distinct_user_count, 10) * 0.08,
    )
    if (
        candidate.status not in {"promoted", "rejected"}
        and candidate.occurrence_count >= occurrence_threshold
        and candidate.distinct_user_count >= distinct_threshold
    ):
        candidate.status = "pending_review"
    event.processed_status = "processed"
    await session.commit()
    await session.refresh(candidate)
    LEARNING_EVENTS.labels(status="processed", event_type=event.event_type).inc()
    return candidate


async def delete_expired_interactions(session: AsyncSession) -> int:
    result = await session.execute(
        delete(InteractionEvent).where(
            InteractionEvent.retention_expires_at.is_not(None),
            InteractionEvent.retention_expires_at <= datetime.now(UTC),
        )
    )
    await session.commit()
    return int(getattr(result, "rowcount", 0) or 0)
