import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from agent_yhzh.database import get_session
from agent_yhzh.schemas import (
    AdminStats,
    CandidateRead,
    KnowledgeItemCreate,
    KnowledgeItemRead,
    KnowledgeGraphRead,
    PromoteCandidateRequest,
    PromoteCandidateResponse,
)
from agent_yhzh.security import require_admin
from agent_yhzh.services.knowledge import (
    admin_stats,
    build_knowledge_graph,
    create_knowledge,
    list_candidates,
    list_knowledge,
    promote_candidate,
)


router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


@router.get("/stats", response_model=AdminStats)
async def get_stats(session: AsyncSession = Depends(get_session)) -> dict[str, int]:
    return await admin_stats(session)


@router.get("/knowledge", response_model=list[KnowledgeItemRead])
async def get_knowledge(
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
) -> list:
    return await list_knowledge(session, limit)


@router.get("/knowledge/graph", response_model=KnowledgeGraphRead)
async def get_knowledge_graph(
    session: AsyncSession = Depends(get_session),
) -> dict[str, list[dict]]:
    return await build_knowledge_graph(session)


@router.post("/knowledge", response_model=KnowledgeItemRead, status_code=201)
async def post_knowledge(
    payload: KnowledgeItemCreate,
    session: AsyncSession = Depends(get_session),
):
    return await create_knowledge(session, payload)


@router.get("/candidates", response_model=list[CandidateRead])
async def get_candidates(
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
) -> list:
    return await list_candidates(session, limit)


@router.post(
    "/candidates/{candidate_id}/promote",
    response_model=PromoteCandidateResponse,
)
async def post_promote_candidate(
    candidate_id: uuid.UUID,
    payload: PromoteCandidateRequest,
    session: AsyncSession = Depends(get_session),
):
    try:
        candidate, knowledge = await promote_candidate(session, candidate_id, payload)
    except LookupError as error:
        raise HTTPException(status_code=404, detail="Not found") from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail="Already promoted") from error
    return {"candidate": candidate, "knowledge": knowledge}
