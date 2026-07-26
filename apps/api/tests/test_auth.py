import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from agent_yhzh.app import app
from agent_yhzh.config import settings
from agent_yhzh.database import init_database


@pytest.fixture(scope="session", autouse=True)
async def database_ready():
    await init_database()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as instance:
        yield instance


def service_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.agent_service_token}",
        "X-Tenant-Id": settings.default_tenant_id,
    }


def admin_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.admin_service_token}",
        "X-Actor-Id": "test-admin",
        "X-Actor-Role": "admin",
        "X-Tenant-Id": settings.default_tenant_id,
        "X-Space-Id": settings.default_space_id,
    }


def user_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.agent_service_token}",
        "X-Session-Id": f"session-{uuid.uuid4()}",
        "X-Auth-Token": token,
        "X-Learning-Consent": "true",
        "X-Tenant-Id": settings.default_tenant_id,
        "X-Space-Id": settings.default_space_id,
        "X-Product-Scope": "default",
    }


async def register(client: AsyncClient, email: str, password: str = "Passw0rd123"):
    return await client.post(
        "/api/v1/auth/register",
        headers=service_headers(),
        json={"email": email, "password": password, "display_name": "测试用户"},
    )


async def test_register_login_me_logout_flow(client: AsyncClient):
    email = f"user-{uuid.uuid4().hex[:10]}@example.com"

    unauthorized = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Passw0rd123", "display_name": "x"},
    )
    assert unauthorized.status_code == 404

    created = await register(client, email)
    assert created.status_code == 201
    body = created.json()
    assert body["user"]["email"] == email
    assert body["token"]

    duplicated = await register(client, email)
    assert duplicated.status_code == 409

    weak = await register(client, f"weak-{uuid.uuid4().hex[:8]}@example.com", "short")
    assert weak.status_code == 422

    bad_login = await client.post(
        "/api/v1/auth/login",
        headers=service_headers(),
        json={"email": email, "password": "WrongPass123"},
    )
    assert bad_login.status_code == 401

    login = await client.post(
        "/api/v1/auth/login",
        headers=service_headers(),
        json={"email": email, "password": "Passw0rd123"},
    )
    assert login.status_code == 200
    token = login.json()["token"]

    me = await client.get(
        "/api/v1/auth/me", headers={**service_headers(), "X-Auth-Token": token}
    )
    assert me.status_code == 200
    assert me.json()["email"] == email

    logout = await client.post(
        "/api/v1/auth/logout", headers={**service_headers(), "X-Auth-Token": token}
    )
    assert logout.status_code == 204

    me_after = await client.get(
        "/api/v1/auth/me", headers={**service_headers(), "X-Auth-Token": token}
    )
    assert me_after.status_code == 401


async def test_authenticated_identity_flows_into_private_memory(client: AsyncClient):
    email = f"memo-{uuid.uuid4().hex[:10]}@example.com"
    created = await register(client, email)
    token = created.json()["token"]

    saved = await client.post(
        "/api/v1/user/memories",
        headers=user_headers(token),
        json={
            "memory_type": "preference",
            "content": "回复保持简洁",
            "consent": True,
            "expires_in_days": 30,
        },
    )
    assert saved.status_code == 201

    listing = await client.get("/api/v1/user/memories", headers=user_headers(token))
    assert listing.status_code == 200
    assert any(memory["content"] == "回复保持简洁" for memory in listing.json())

    other = await register(client, f"other-{uuid.uuid4().hex[:10]}@example.com")
    other_token = other.json()["token"]
    other_listing = await client.get(
        "/api/v1/user/memories", headers=user_headers(other_token)
    )
    assert other_listing.status_code == 200
    assert all(
        memory["content"] != "回复保持简洁" for memory in other_listing.json()
    )

    forged = await client.get(
        "/api/v1/user/memories", headers=user_headers("forged-token")
    )
    assert forged.status_code == 401


async def test_admin_can_list_and_disable_users(client: AsyncClient):
    email = f"gov-{uuid.uuid4().hex[:10]}@example.com"
    created = await register(client, email)
    token = created.json()["token"]
    account_id = created.json()["user"]["id"]

    users = await client.get("/api/v1/admin/users", headers=admin_headers())
    assert users.status_code == 200
    assert any(user["email"] == email for user in users.json())

    disabled = await client.patch(
        f"/api/v1/admin/users/{account_id}",
        headers=admin_headers(),
        json={"status": "disabled"},
    )
    assert disabled.status_code == 200
    assert disabled.json()["status"] == "disabled"

    me = await client.get(
        "/api/v1/auth/me", headers={**service_headers(), "X-Auth-Token": token}
    )
    assert me.status_code == 401

    login = await client.post(
        "/api/v1/auth/login",
        headers=service_headers(),
        json={"email": email, "password": "Passw0rd123"},
    )
    assert login.status_code == 403

    restored = await client.patch(
        f"/api/v1/admin/users/{account_id}",
        headers=admin_headers(),
        json={"status": "active"},
    )
    assert restored.status_code == 200


async def test_admin_categories_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/admin/categories", headers=admin_headers())
    assert response.status_code == 200
    slugs = {category["slug"] for category in response.json()}
    assert {"ecommerce_product_copy", "ecommerce_service", "general"} <= slugs


async def test_non_ascii_auth_headers_return_not_found(client: AsyncClient):
    login = await client.post(
        "/api/v1/auth/login",
        headers={b"Authorization": "Bearer 非ASCII令牌".encode()},
        json={"email": "someone@example.com", "password": "Passw0rd123"},
    )
    assert login.status_code == 404

    stats = await client.get(
        "/api/v1/admin/stats",
        headers={b"X-Admin-Key": "非ASCII管理密钥".encode()},
    )
    assert stats.status_code == 404


async def test_login_rate_limit_returns_429():
    previous = settings.auth_login_rate_limit_per_minute
    settings.auth_login_rate_limit_per_minute = 3
    transport = ASGITransport(
        app=app, client=(f"limit-{uuid.uuid4().hex}", 12345)
    )
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as instance:
            statuses = [
                (
                    await instance.post(
                        "/api/v1/auth/login",
                        headers=service_headers(),
                        json={
                            "email": "rate-limit@example.com",
                            "password": "WrongPass123",
                        },
                    )
                ).status_code
                for _ in range(5)
            ]
        assert statuses[:3] == [401, 401, 401]
        assert statuses[3:] == [429, 429]
    finally:
        settings.auth_login_rate_limit_per_minute = previous
