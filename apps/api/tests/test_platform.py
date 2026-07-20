import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from agent_yhzh.app import app
from agent_yhzh.config import settings
from agent_yhzh.database import init_database, session_factory
from agent_yhzh.models import InteractionEvent, KnowledgeCandidate


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
