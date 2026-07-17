import hashlib
import hmac
from dataclasses import dataclass

from fastapi import Header, HTTPException, status

from agent_yhzh.config import settings


def require_admin(x_admin_key: str | None = Header(default=None)) -> None:
    if not x_admin_key or not hmac.compare_digest(x_admin_key, settings.admin_api_key):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found",
        )


@dataclass(frozen=True)
class UserContext:
    user_id: str
    session_id: str
    product_scope: str


def get_user_context(
    x_user_id: str | None = Header(default=None),
    x_session_id: str | None = Header(default=None),
    x_product_scope: str | None = Header(default=None),
) -> UserContext:
    return UserContext(
        user_id=x_user_id or "demo-user",
        session_id=x_session_id or "demo-session",
        product_scope=x_product_scope or "default",
    )


def hash_user_reference(user_id: str) -> str:
    material = f"{settings.user_hash_salt}:{user_id}".encode()
    return hashlib.sha256(material).hexdigest()
