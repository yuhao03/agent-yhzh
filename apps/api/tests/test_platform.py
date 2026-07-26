import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from agent_yhzh.app import app
from agent_yhzh.config import settings
from agent_yhzh.database import init_database, session_factory
from agent_yhzh.models import InteractionEvent, KnowledgeCandidate, ModelProviderConfig
from agent_yhzh.services.model_config import (
    get_runtime_model_config,
    validate_model_base_url,
)


def admin_headers(role: str = "admin") -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.admin_service_token}",
        "X-Actor-Id": "pytest-admin",
        "X-Actor-Role": role,
        "X-Tenant-Id": settings.default_tenant_id,
        "X-Space-Id": settings.default_space_id,
    }


def user_headers(user_id: str, *, consent: bool) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.agent_service_token}",
        "X-User-Id": user_id,
        "X-Session-Id": f"session-{user_id}",
        "X-Learning-Consent": str(consent).lower(),
        "X-Tenant-Id": settings.default_tenant_id,
        "X-Space-Id": settings.default_space_id,
        "X-Product-Scope": "default",
    }


@pytest.fixture(autouse=True, scope="session")
async def database_ready():
    await init_database()


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as http:
        yield http


async def test_admin_boundary_and_protected_openapi(client: AsyncClient):
    assert (await client.get("/api/v1/admin/stats")).status_code == 404
    assert (await client.get("/openapi.json")).status_code == 404
    protected = await client.get(
        "/api/v1/admin/openapi.json", headers=admin_headers()
    )
    assert protected.status_code == 200
    assert "/api/v1/admin/knowledge" in protected.json()["paths"]


async def test_consent_is_server_enforced_and_pii_is_redacted(client: AsyncClient):
    marker = uuid.uuid4().hex[:8]
    response = await client.post(
        "/api/v1/user/interaction",
        headers=user_headers(f"no-consent-{marker}", consent=False),
        json={
            "event_type": "question",
            "content": f"联系我 13800138000 test-{marker}@example.com",
            "consent": True,
        },
    )
    assert response.status_code == 202
    body = response.json()
    assert body["learning_queued"] is False
    assert body["redaction_count"] == 2
    async with session_factory() as session:
        event = await session.get(InteractionEvent, uuid.UUID(body["event_id"]))
        assert event is not None
        assert event.consent is False
        assert "13800138000" not in event.payload["content"]
        assert "example.com" not in event.payload["content"]


async def test_candidate_requires_distinct_users(client: AsyncClient):
    marker = uuid.uuid4().hex
    content = f"如何办理专项流程 {marker}"
    for user_id in [f"first-{marker}", f"second-{marker}"]:
        response = await client.post(
            "/api/v1/user/interaction",
            headers=user_headers(user_id, consent=True),
            json={"event_type": "question", "content": content, "consent": True},
        )
        assert response.status_code == 202
    async with session_factory() as session:
        candidate = await session.scalar(
            select(KnowledgeCandidate).where(KnowledgeCandidate.content == content)
        )
        assert candidate is not None
        assert candidate.occurrence_count == 2
        assert candidate.distinct_user_count == 2
        assert candidate.status == "pending_review"


async def test_private_memory_is_isolated_and_deletable(client: AsyncClient):
    marker = uuid.uuid4().hex
    first_headers = user_headers(f"memory-a-{marker}", consent=True)
    second_headers = user_headers(f"memory-b-{marker}", consent=True)
    created = await client.post(
        "/api/v1/user/memories",
        headers=first_headers,
        json={
            "memory_type": "preference",
            "content": "先给结论再解释",
            "consent": True,
            "expires_in_days": 30,
        },
    )
    assert created.status_code == 201
    memory_id = created.json()["id"]
    assert len((await client.get("/api/v1/user/memories", headers=first_headers)).json()) == 1
    assert (await client.get("/api/v1/user/memories", headers=second_headers)).json() == []
    assert (
        await client.delete(
            f"/api/v1/user/memories/{memory_id}", headers=second_headers
        )
    ).status_code == 404
    assert (
        await client.delete(
            f"/api/v1/user/memories/{memory_id}", headers=first_headers
        )
    ).status_code == 204


async def test_document_import_and_hybrid_retrieval(client: AsyncClient):
    marker = uuid.uuid4().hex
    uploaded = await client.post(
        "/api/v1/admin/documents",
        headers=admin_headers(),
        files={
            "file": (
                f"guide-{marker}.md",
                f"# 专项办理说明\n办理口令是 knowledge-{marker}，提交后等待审核。",
                "text/markdown",
            )
        },
    )
    assert uploaded.status_code == 202
    assert uploaded.json()["import_job"]["status"] == "completed"

    knowledge = await client.post(
        "/api/v1/admin/knowledge",
        headers=admin_headers(),
        json={
            "title": f"专项办理 {marker}",
            "content": f"办理口令 knowledge-{marker}，提交后等待审核确认。",
            "knowledge_type": "process",
            "publish": True,
        },
    )
    assert knowledge.status_code == 201
    debug = await client.get(
        "/api/v1/admin/retrieval/debug",
        params={"query": f"knowledge-{marker}"},
        headers=admin_headers(),
    )
    assert debug.status_code == 200
    assert debug.json()[0]["item"]["id"] == knowledge.json()["id"]


async def test_unknown_category_is_rejected(client: AsyncClient):
    response = await client.post(
        "/api/v1/admin/knowledge",
        headers=admin_headers(),
        json={
            "title": "非法分类条目",
            "content": "这是一段用于验证分类校验的知识内容。",
            "knowledge_type": "faq",
            "category": "not_a_real_category",
            "publish": True,
        },
    )
    assert response.status_code == 422


async def test_knowledge_graph_nodes_expose_category(client: AsyncClient):
    marker = uuid.uuid4().hex
    created = await client.post(
        "/api/v1/admin/knowledge",
        headers=admin_headers(),
        json={
            "title": f"售后分类 {marker}",
            "content": f"退款退货处理流程说明 {marker}，用于验证图谱节点分类。",
            "knowledge_type": "faq",
            "category": "ecommerce_service",
            "publish": True,
        },
    )
    assert created.status_code == 201
    graph = await client.get(
        "/api/v1/admin/knowledge/graph", headers=admin_headers()
    )
    assert graph.status_code == 200
    nodes = {node["id"]: node for node in graph.json()["nodes"]}
    assert nodes[created.json()["id"]]["category"] == "ecommerce_service"


async def test_promotion_cannot_bypass_review_reason(client: AsyncClient):
    candidate_id = uuid.uuid4()
    response = await client.post(
        f"/api/v1/admin/candidates/{candidate_id}/promote",
        headers=admin_headers(),
        json={
            "title": "已核验标题",
            "content": "这是长度足够且已经核验的正式知识内容。",
            "knowledge_type": "faq",
            "agent_scope": ["default"],
        },
    )
    assert response.status_code == 422


async def test_model_config_secret_is_encrypted_and_hot_loaded(client: AsyncClient):
    marker = uuid.uuid4().hex
    api_key = f"sk-secret-{marker}"
    created = await client.post(
        "/api/v1/admin/model-configs",
        headers=admin_headers(),
        json={
            "name": f"provider-{marker}",
            "provider": "openai_compatible",
            "base_url": "https://llm.example.test/v1",
            "chat_model": "test-chat-model",
            "embedding_model": "local/hash-1536",
            "api_key": api_key,
            "temperature": 0.3,
            "max_tokens": 2048,
            "timeout_seconds": 30,
            "enabled": True,
            "is_default": True,
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert "api_key" not in body
    assert body["api_key_configured"] is True
    assert api_key not in str(body)

    config_id = uuid.UUID(body["id"])
    async with session_factory() as session:
        stored = await session.get(ModelProviderConfig, config_id)
        assert stored is not None
        assert stored.api_key_ciphertext != api_key
        assert api_key not in (stored.api_key_ciphertext or "")
        runtime = await get_runtime_model_config(
            session, settings.default_tenant_id, settings.default_space_id
        )
        assert runtime.source == "database"
        assert runtime.api_key == api_key
        assert runtime.base_url == "https://llm.example.test/v1"
        await session.execute(
            delete(ModelProviderConfig).where(ModelProviderConfig.id == config_id)
        )
        await session.commit()

    forbidden = await client.post(
        "/api/v1/admin/model-configs",
        headers=admin_headers("reviewer"),
        json={
            "name": "reviewer-cannot-create",
            "provider": "ollama",
            "base_url": "http://127.0.0.1:11434",
            "chat_model": "qwen3",
        },
    )
    assert forbidden.status_code == 403


def test_private_model_urls_are_blocked_when_not_explicitly_allowed():
    previous = settings.allow_private_model_urls
    settings.allow_private_model_urls = False
    try:
        for url in (
            "http://127.0.0.1:11434/v1",
            "http://2130706433/v1",
            "http://127.1/v1",
            "http://0x7f000001/v1",
        ):
            with pytest.raises(ValueError, match="private_model_url_not_allowed"):
                validate_model_base_url(url)
        validate_model_base_url("https://api.example.com/v1")
    finally:
        settings.allow_private_model_urls = previous
