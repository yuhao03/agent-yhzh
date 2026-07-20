import hashlib
import hmac
from contextvars import ContextVar, Token
from dataclasses import dataclass

from fastapi import Header, HTTPException, Request, status

from agent_yhzh.config import settings


@dataclass(frozen=True)
class CallerContext:
    actor_id: str
    role: str
    tenant_id: str
    space_id: str
    user_id: str | None = None
    session_id: str | None = None
    product_scope: str = "default"
    learning_consent: bool = False


_caller_context: ContextVar[CallerContext | None] = ContextVar(
    "agent_yhzh_caller_context", default=None
)


def set_caller_context(context: CallerContext) -> Token:
    return _caller_context.set(context)


def reset_caller_context(token: Token) -> None:
    _caller_context.reset(token)


def get_current_caller() -> CallerContext:
    context = _caller_context.get()
    if context is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return context


def _bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, value = authorization.partition(" ")
    return value.strip() if scheme.lower() == "bearer" and value.strip() else None


def _secure_equal(value: str | None, expected: str) -> bool:
    if value is None:
        return False
    return hmac.compare_digest(value, expected)


def _safe_scope(value: str | None, default: str) -> str:
    scope = (value or default).strip()
    if not scope or len(scope) > 80 or not all(
        character.isalnum() or character in {"-", "_", "."} for character in scope
    ):
        raise HTTPException(status_code=400, detail="Invalid scope")
    return scope


def _bool_header(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def require_admin(
    authorization: str | None = Header(default=None),
    x_admin_key: str | None = Header(default=None),
    x_actor_id: str | None = Header(default=None),
    x_actor_role: str | None = Header(default=None),
    x_tenant_id: str | None = Header(default=None),
    x_space_id: str | None = Header(default=None),
) -> CallerContext:
    token = _bearer_token(authorization)
    service_authenticated = _secure_equal(token, settings.admin_service_token)
    development_authenticated = (
        settings.environment != "production"
        and _secure_equal(x_admin_key, settings.admin_api_key)
    )
    if not service_authenticated and not development_authenticated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    role = (x_actor_role or "admin").strip().lower()
    if role not in {"admin", "reviewer"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return CallerContext(
        actor_id=(x_actor_id or "local-admin")[:120],
        role=role,
        tenant_id=_safe_scope(x_tenant_id, settings.default_tenant_id),
        space_id=_safe_scope(x_space_id, settings.default_space_id),
    )


def require_admin_write(context: CallerContext | None = None) -> CallerContext:
    context = context or get_current_caller()
    if context.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return context


def get_user_context(
    authorization: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
    x_session_id: str | None = Header(default=None),
    x_product_scope: str | None = Header(default=None),
    x_tenant_id: str | None = Header(default=None),
    x_space_id: str | None = Header(default=None),
    x_learning_consent: str | None = Header(default=None),
) -> CallerContext:
    if not _secure_equal(_bearer_token(authorization), settings.agent_service_token):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    user_id = (x_user_id or "").strip()
    session_id = (x_session_id or "").strip()
    if not user_id or len(user_id) > 120 or not session_id or len(session_id) > 160:
        raise HTTPException(status_code=400, detail="Invalid user context")
    return CallerContext(
        actor_id=user_id,
        role="user",
        tenant_id=_safe_scope(x_tenant_id, settings.default_tenant_id),
        space_id=_safe_scope(x_space_id, settings.default_space_id),
        user_id=user_id,
        session_id=session_id,
        product_scope=_safe_scope(x_product_scope, "default"),
        learning_consent=_bool_header(x_learning_consent),
    )


def caller_from_request_headers(request: Request) -> CallerContext:
    return get_user_context(
        authorization=request.headers.get("authorization"),
        x_user_id=request.headers.get("x-user-id"),
        x_session_id=request.headers.get("x-session-id"),
        x_product_scope=request.headers.get("x-product-scope"),
        x_tenant_id=request.headers.get("x-tenant-id"),
        x_space_id=request.headers.get("x-space-id"),
        x_learning_consent=request.headers.get("x-learning-consent"),
    )


def require_ops(
    authorization: str | None = Header(default=None),
    x_ops_key: str | None = Header(default=None),
) -> None:
    token = _bearer_token(authorization)
    if not _secure_equal(token, settings.ops_api_key) and not _secure_equal(
        x_ops_key, settings.ops_api_key
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


def hash_user_reference(user_id: str) -> str:
    return hmac.new(
        settings.user_hash_salt.encode(), user_id.encode(), hashlib.sha256
    ).hexdigest()
