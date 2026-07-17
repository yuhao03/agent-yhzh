import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_yhzh.config import settings
from agent_yhzh.models import InteractionEvent, KnowledgeCandidate
from agent_yhzh.security import hash_user_reference


def normalize_learning_key(content: str) -> str:
    normalized = re.sub(r"\s+", " ", content.strip().lower())
    normalized = re.sub(r"[，。！？、,.!?;；:：\"'“”‘’()（）]", "", normalized)
    return normalized[:320]


async def capture_interaction(
    session: AsyncSession,
    *,
    user_id: str,
    session_id: str,
    event_type: str,
    content: str,
    consent: bool,
) -> KnowledgeCandidate | None:
    user_hash = hash_user_reference(user_id)
    event = InteractionEvent(
        user_ref_hash=user_hash,
        session_id=session_id,
        event_type=event_type,
        payload={"content": content},
        consent=consent,
    )
    session.add(event)
    await session.flush()

    if not consent or event_type not in {"question", "correction", "feedback"}:
        await session.commit()
        return None

    normalized_key = normalize_learning_key(content)
    if not normalized_key:
        await session.commit()
        return None

    candidate = await session.scalar(
        select(KnowledgeCandidate)
        .where(KnowledgeCandidate.normalized_key == normalized_key)
        .with_for_update()
    )

    if candidate is None:
        candidate = KnowledgeCandidate(
            normalized_key=normalized_key,
            title=content.strip()[:240],
            content=content.strip(),
            occurrence_count=1,
            distinct_user_count=1,
            score=0.2,
            source_event_ids=[str(event.id)],
            observed_user_hashes=[user_hash],
        )
        session.add(candidate)
    else:
        candidate.occurrence_count += 1
        candidate.source_event_ids = [*candidate.source_event_ids, str(event.id)][-50:]
        if user_hash not in candidate.observed_user_hashes:
            candidate.observed_user_hashes = [
                *candidate.observed_user_hashes,
                user_hash,
            ][-100:]
            candidate.distinct_user_count += 1

    candidate.score = min(0.95, 0.2 + candidate.occurrence_count * 0.15)
    if (
        candidate.status != "promoted"
        and candidate.occurrence_count >= settings.candidate_review_threshold
    ):
        candidate.status = "pending_review"

    await session.commit()
    await session.refresh(candidate)
    return candidate
