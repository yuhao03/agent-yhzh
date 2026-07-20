import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from agent_yhzh.database import get_session
from agent_yhzh.schemas import (
    AdminStats,
    AuditEventRead,
    CandidateRead,
    DocumentRead,
    DocumentUploadResponse,
    ImportJobRead,
    KnowledgeDetail,
    KnowledgeGraphRead,
    KnowledgeItemCreate,
    KnowledgeItemRead,
    KnowledgeItemUpdate,
    KnowledgeRelationCreate,
    KnowledgeRelationRead,
    KnowledgeViewCreate,
    KnowledgeViewRead,
    ModelConnectionTestResponse,
    ModelProviderConfigCreate,
    ModelProviderConfigRead,
    ModelProviderConfigUpdate,
    PromoteCandidateRequest,
    PromoteCandidateResponse,
    QualityTrendPoint,
    RejectCandidateRequest,
    RetrievalDebugItem,
)
from agent_yhzh.security import CallerContext, require_admin, require_admin_write
from agent_yhzh.services.documents import (
    create_document_upload,
    list_documents,
    list_import_jobs,
    process_document_import,
)
from agent_yhzh.services.knowledge import (
    admin_stats,
    build_knowledge_graph,
    create_knowledge,
    create_relation,
    create_view,
    get_knowledge_detail,
    list_audits,
    list_candidates,
    list_knowledge,
    list_relations,
    list_views,
    promote_candidate,
    quality_trend,
    reject_candidate,
    update_knowledge,
)
from agent_yhzh.services.retrieval import hybrid_search
from agent_yhzh.services.model_config import (
    create_model_config,
    list_model_configs,
    test_model_connection,
    update_model_config,
)
from agent_yhzh.worker import enqueue_document


router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def ensure_write(context: CallerContext) -> CallerContext:
    return require_admin_write(context)


def model_config_error(error: ValueError) -> HTTPException:
    if str(error) == "model_config_name_exists":
        return HTTPException(status_code=409, detail="Config name already exists")
    return HTTPException(status_code=422, detail="Model Base URL is not allowed")


@router.get("/stats", response_model=AdminStats)
async def get_stats(
    context: CallerContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    return await admin_stats(session, context)


@router.get("/trends", response_model=list[QualityTrendPoint])
async def get_trends(
    days: int = Query(default=14, ge=7, le=90),
    context: CallerContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    return await quality_trend(session, context, days)


@router.get("/knowledge", response_model=list[KnowledgeItemRead])
async def get_knowledge(
    limit: int = Query(default=100, ge=1, le=500),
    status: str | None = Query(default=None),
    query: str | None = Query(default=None, max_length=240),
    context: CallerContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    return await list_knowledge(session, context, limit, status=status, query=query)


@router.get("/knowledge/graph", response_model=KnowledgeGraphRead)
async def get_knowledge_graph(
    context: CallerContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    return await build_knowledge_graph(session, context)


@router.get("/knowledge/{item_id}", response_model=KnowledgeDetail)
async def get_knowledge_item(
    item_id: uuid.UUID,
    context: CallerContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    detail = await get_knowledge_detail(session, context, item_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Not found")
    return detail


@router.post("/knowledge", response_model=KnowledgeItemRead, status_code=201)
async def post_knowledge(
    payload: KnowledgeItemCreate,
    context: CallerContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    return await create_knowledge(session, ensure_write(context), payload)


@router.patch("/knowledge/{item_id}", response_model=KnowledgeItemRead)
async def patch_knowledge(
    item_id: uuid.UUID,
    payload: KnowledgeItemUpdate,
    context: CallerContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    item = await update_knowledge(session, ensure_write(context), item_id, payload)
    if item is None:
        raise HTTPException(status_code=404, detail="Not found")
    return item


@router.get("/candidates", response_model=list[CandidateRead])
async def get_candidates(
    limit: int = Query(default=100, ge=1, le=500),
    context: CallerContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    return await list_candidates(session, context, limit)


@router.post(
    "/candidates/{candidate_id}/promote", response_model=PromoteCandidateResponse
)
async def post_promote_candidate(
    candidate_id: uuid.UUID,
    payload: PromoteCandidateRequest,
    context: CallerContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    try:
        candidate, knowledge = await promote_candidate(
            session, ensure_write(context), candidate_id, payload
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail="Not found") from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail="Already promoted") from error
    return {"candidate": candidate, "knowledge": knowledge}


@router.post("/candidates/{candidate_id}/reject", response_model=CandidateRead)
async def post_reject_candidate(
    candidate_id: uuid.UUID,
    payload: RejectCandidateRequest,
    context: CallerContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    candidate = await reject_candidate(
        session, ensure_write(context), candidate_id, payload.reason
    )
    if candidate is None:
        raise HTTPException(status_code=404, detail="Not found")
    return candidate


@router.get("/relations", response_model=list[KnowledgeRelationRead])
async def get_relations(
    context: CallerContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    return await list_relations(session, context)


@router.post("/relations", response_model=KnowledgeRelationRead, status_code=201)
async def post_relation(
    payload: KnowledgeRelationCreate,
    context: CallerContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await create_relation(session, ensure_write(context), payload)
    except LookupError as error:
        raise HTTPException(status_code=404, detail="Not found") from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/views", response_model=list[KnowledgeViewRead])
async def get_views(
    context: CallerContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    return await list_views(session, context)


@router.post("/views", response_model=KnowledgeViewRead, status_code=201)
async def post_view(
    payload: KnowledgeViewCreate,
    context: CallerContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    return await create_view(session, context, payload)


@router.get("/documents", response_model=list[DocumentRead])
async def get_documents(
    context: CallerContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    return await list_documents(session, context.tenant_id, context.space_id)


@router.get("/imports", response_model=list[ImportJobRead])
async def get_imports(
    context: CallerContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    return await list_import_jobs(session, context.tenant_id, context.space_id)


@router.post("/documents", response_model=DocumentUploadResponse, status_code=202)
async def post_document(
    file: UploadFile = File(...),
    context: CallerContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    ensure_write(context)
    try:
        document, job = await create_document_upload(
            session,
            context,
            filename=file.filename or "upload.txt",
            mime_type=file.content_type,
            data=await file.read(),
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if job.status == "queued":
        try:
            enqueue_document(job.id)
        except Exception:
            await process_document_import(session, job.id)
            await session.refresh(document)
            await session.refresh(job)
    return {"document": document, "import_job": job}


@router.get("/audits", response_model=list[AuditEventRead])
async def get_audits(
    limit: int = Query(default=100, ge=1, le=500),
    context: CallerContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    return await list_audits(session, context, limit)


@router.get("/retrieval/debug", response_model=list[RetrievalDebugItem])
async def debug_retrieval(
    query: str = Query(min_length=1, max_length=500),
    limit: int = Query(default=10, ge=1, le=50),
    context: CallerContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    results = await hybrid_search(
        session,
        query,
        tenant_id=context.tenant_id,
        space_id=context.space_id,
        limit=limit,
    )
    return [
        {
            "item": result.item,
            "score": result.score,
            "lexical_score": result.lexical_score,
            "vector_score": result.vector_score,
            "relation_score": result.relation_score,
        }
        for result in results
    ]


@router.get("/model-configs", response_model=list[ModelProviderConfigRead])
async def get_model_configs(
    context: CallerContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    return await list_model_configs(session, context)


@router.post(
    "/model-configs", response_model=ModelProviderConfigRead, status_code=201
)
async def post_model_config(
    payload: ModelProviderConfigCreate,
    context: CallerContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await create_model_config(session, ensure_write(context), payload)
    except ValueError as error:
        raise model_config_error(error) from error


@router.patch(
    "/model-configs/{config_id}", response_model=ModelProviderConfigRead
)
async def patch_model_config(
    config_id: uuid.UUID,
    payload: ModelProviderConfigUpdate,
    context: CallerContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    try:
        config = await update_model_config(
            session, ensure_write(context), config_id, payload
        )
    except ValueError as error:
        raise model_config_error(error) from error
    if config is None:
        raise HTTPException(status_code=404, detail="Not found")
    return config


@router.post(
    "/model-configs/{config_id}/test", response_model=ModelConnectionTestResponse
)
async def post_model_connection_test(
    config_id: uuid.UUID,
    context: CallerContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    try:
        result = await test_model_connection(
            session, ensure_write(context), config_id
        )
    except ValueError as error:
        raise model_config_error(error) from error
    if result is None:
        raise HTTPException(status_code=404, detail="Not found")
    return result
