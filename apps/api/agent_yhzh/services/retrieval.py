from collections.abc import Sequence
from dataclasses import dataclass
import re

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_yhzh.config import settings
from agent_yhzh.models import KnowledgeEmbedding, KnowledgeItem, KnowledgeRelation
from agent_yhzh.observability import RETRIEVAL_REQUESTS
from agent_yhzh.services.embeddings import cosine_similarity, embed_text
from agent_yhzh.services.model_config import get_runtime_model_config


@dataclass
class RetrievalResult:
    item: KnowledgeItem
    score: float
    lexical_score: float
    vector_score: float
    relation_score: float = 0.0


def _in_scope(item: KnowledgeItem, product_scope: str) -> bool:
    return product_scope in item.agent_scope or "default" in item.agent_scope


async def hybrid_search(
    session: AsyncSession,
    query: str,
    *,
    tenant_id: str,
    space_id: str,
    product_scope: str = "default",
    limit: int = 5,
    categories: Sequence[str] | None = None,
) -> list[RetrievalResult]:
    items = list(
        await session.scalars(
            select(KnowledgeItem)
            .where(
                KnowledgeItem.tenant_id == tenant_id,
                KnowledgeItem.space_id == space_id,
                KnowledgeItem.status == "published",
            )
            .order_by(KnowledgeItem.updated_at.desc())
            .limit(500)
        )
    )
    items = [item for item in items if _in_scope(item, product_scope)]
    preferred_categories = set(categories or [])
    if preferred_categories:
        # 子 Agent 优先检索本域分类;本域为空时回退全域,避免跨域问题无解。
        scoped_items = [
            item for item in items if item.category in preferred_categories
        ]
        if scoped_items:
            items = scoped_items
    if not items:
        RETRIEVAL_REQUESTS.labels(result="empty").inc()
        return []

    runtime = await get_runtime_model_config(session, tenant_id, space_id)
    query_vector = await embed_text(query, runtime)
    query_identifiers = {
        value.lower()
        for value in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{7,}", query)
    }
    embeddings = {
        embedding.object_id: embedding.vector
        for embedding in await session.scalars(
            select(KnowledgeEmbedding).where(
                KnowledgeEmbedding.tenant_id == tenant_id,
                KnowledgeEmbedding.space_id == space_id,
                KnowledgeEmbedding.object_type == "knowledge_item",
                KnowledgeEmbedding.object_id.in_([item.id for item in items]),
            )
        )
    }
    query_words = {word.lower() for word in query.split() if word}
    ranked: list[RetrievalResult] = []
    for item in items:
        haystack = f"{item.title}\n{item.summary or ''}\n{item.content}"
        fuzzy = fuzz.WRatio(query, haystack[:5000]) / 100
        item_words = {word.lower() for word in haystack.split() if word}
        overlap = len(query_words & item_words) / max(1, len(query_words))
        lexical = min(1.0, fuzzy * 0.65 + overlap * 0.35)
        if query_identifiers:
            identifier_matches = sum(
                identifier in haystack.lower() for identifier in query_identifiers
            )
            if identifier_matches:
                lexical = min(1.0, lexical + 0.25 * identifier_matches)
            else:
                lexical *= 0.2
        vector = cosine_similarity(query_vector, embeddings.get(item.id, []))
        vector = max(0.0, vector)
        score = lexical * 0.68 + vector * 0.32
        if preferred_categories and item.category in preferred_categories:
            score += 0.06
        ranked.append(
            RetrievalResult(
                item=item,
                score=score,
                lexical_score=lexical,
                vector_score=vector,
            )
        )
    ranked.sort(key=lambda result: result.score, reverse=True)
    seeds = ranked[: max(limit * 2, 8)]
    seed_ids = [result.item.id for result in seeds]
    if seed_ids:
        relations = list(
            await session.scalars(
                select(KnowledgeRelation).where(
                    KnowledgeRelation.tenant_id == tenant_id,
                    KnowledgeRelation.space_id == space_id,
                    KnowledgeRelation.status == "published",
                    KnowledgeRelation.source_id.in_(seed_ids),
                )
            )
        )
        relation_targets = {relation.target_id: relation for relation in relations}
        for result in ranked:
            relation = relation_targets.get(result.item.id)
            if relation:
                result.relation_score = min(1.0, relation.weight / 10) * relation.confidence
                result.score += result.relation_score * 0.12
    ranked.sort(key=lambda result: result.score, reverse=True)
    relative_floor = max(0.08, ranked[0].score * 0.45) if ranked else 0.08
    matches = [entry for entry in ranked[:limit] if entry.score >= relative_floor]
    RETRIEVAL_REQUESTS.labels(result="hit" if matches else "miss").inc()
    return matches


async def upsert_item_embedding(session: AsyncSession, item: KnowledgeItem) -> None:
    content = f"{item.title}\n{item.summary or ''}\n{item.content}"
    from agent_yhzh.services.embeddings import content_hash

    digest = content_hash(content)
    runtime = await get_runtime_model_config(session, item.tenant_id, item.space_id)
    embedding_model = runtime.embedding_model or settings.embedding_model
    embedding = await session.scalar(
        select(KnowledgeEmbedding).where(
            KnowledgeEmbedding.object_type == "knowledge_item",
            KnowledgeEmbedding.object_id == item.id,
            KnowledgeEmbedding.model == embedding_model,
        )
    )
    vector = await embed_text(content, runtime)
    if embedding is None:
        session.add(
            KnowledgeEmbedding(
                tenant_id=item.tenant_id,
                space_id=item.space_id,
                object_type="knowledge_item",
                object_id=item.id,
                model=embedding_model,
                vector=vector,
                content_hash=digest,
            )
        )
    else:
        embedding.vector = vector
        embedding.content_hash = digest
