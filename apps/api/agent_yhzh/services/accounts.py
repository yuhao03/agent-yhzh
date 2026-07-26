"""多用户账号与会话:scrypt 密码哈希,会话 token 只存 SHA-256 哈希。

账号 ID 作为用户身份进入既有 user_ref_hash 加盐哈希管道,
公共知识域仍然只保存哈希,隐私边界不变。
"""

import hashlib
import hmac
import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from agent_yhzh.models import AuthSession, UserAccount
from agent_yhzh.security import CallerContext
from agent_yhzh.services.audit import add_audit


SESSION_TTL_DAYS = 30
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1

_EMAIL_PATTERN = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")


class AccountError(ValueError):
    """账号操作失败,message 是稳定的错误码。"""


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, n, r, p, salt_hex, digest_hex = encoded.split("$")
        if scheme != "scrypt":
            return False
        candidate = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt_hex),
            n=int(n),
            r=int(r),
            p=int(p),
        )
        return hmac.compare_digest(candidate.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# 账号不存在时也校验一次此占位哈希,对齐 scrypt 耗时,防止用响应时间枚举邮箱。
_DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(32))


def normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if not _EMAIL_PATTERN.match(normalized) or len(normalized) > 320:
        raise AccountError("invalid_email")
    return normalized


def validate_password(password: str) -> None:
    if len(password) < 8 or len(password) > 128:
        raise AccountError("weak_password")
    if not any(character.isdigit() for character in password) or not any(
        character.isalpha() for character in password
    ):
        raise AccountError("weak_password")


async def register_user(
    session: AsyncSession,
    *,
    tenant_id: str,
    email: str,
    password: str,
    display_name: str,
) -> UserAccount:
    normalized = normalize_email(email)
    validate_password(password)
    account = UserAccount(
        tenant_id=tenant_id,
        email=normalized,
        display_name=display_name.strip()[:160] or normalized.split("@")[0],
        password_hash=hash_password(password),
    )
    session.add(account)
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise AccountError("email_exists") from error
    await session.refresh(account)
    return account


async def authenticate_user(
    session: AsyncSession, *, tenant_id: str, email: str, password: str
) -> UserAccount:
    try:
        normalized = normalize_email(email)
    except AccountError:
        raise AccountError("invalid_credentials") from None
    account = await session.scalar(
        select(UserAccount).where(
            UserAccount.tenant_id == tenant_id,
            UserAccount.email == normalized,
        )
    )
    if account is None:
        verify_password(password, _DUMMY_PASSWORD_HASH)
        raise AccountError("invalid_credentials")
    if not verify_password(password, account.password_hash):
        raise AccountError("invalid_credentials")
    if account.status != "active":
        raise AccountError("account_disabled")
    account.last_login_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(account)
    return account


async def create_auth_session(
    session: AsyncSession,
    account: UserAccount,
    *,
    user_agent: str | None = None,
) -> tuple[str, AuthSession]:
    token = secrets.token_urlsafe(48)
    auth_session = AuthSession(
        user_id=account.id,
        token_hash=_hash_token(token),
        expires_at=datetime.now(UTC) + timedelta(days=SESSION_TTL_DAYS),
        user_agent=(user_agent or "")[:320] or None,
    )
    session.add(auth_session)
    await session.commit()
    await session.refresh(auth_session)
    return token, auth_session


async def resolve_auth_token(
    session: AsyncSession, token: str
) -> UserAccount | None:
    if not token or len(token) > 256:
        return None
    now = datetime.now(UTC)
    result = await session.execute(
        select(UserAccount, AuthSession)
        .join(AuthSession, AuthSession.user_id == UserAccount.id)
        .where(
            AuthSession.token_hash == _hash_token(token),
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > now,
        )
    )
    row = result.first()
    if row is None:
        return None
    account, _ = row
    if account.status != "active":
        return None
    return account


async def revoke_auth_token(session: AsyncSession, token: str) -> bool:
    auth_session = await session.scalar(
        select(AuthSession).where(AuthSession.token_hash == _hash_token(token))
    )
    if auth_session is None or auth_session.revoked_at is not None:
        return False
    auth_session.revoked_at = datetime.now(UTC)
    await session.commit()
    return True


async def list_user_accounts(
    session: AsyncSession,
    context: CallerContext,
    *,
    limit: int = 200,
    query: str | None = None,
) -> list[UserAccount]:
    statement = select(UserAccount).where(UserAccount.tenant_id == context.tenant_id)
    if query:
        pattern = f"%{query.strip().lower()}%"
        statement = statement.where(
            UserAccount.email.ilike(pattern)
            | UserAccount.display_name.ilike(pattern)
        )
    return list(
        await session.scalars(
            statement.order_by(UserAccount.created_at.desc()).limit(limit)
        )
    )


async def count_user_accounts(
    session: AsyncSession, context: CallerContext
) -> int:
    return int(
        (
            await session.scalar(
                select(func.count())
                .select_from(UserAccount)
                .where(UserAccount.tenant_id == context.tenant_id)
            )
        )
        or 0
    )


async def set_account_status(
    session: AsyncSession,
    context: CallerContext,
    account_id: uuid.UUID,
    status: str,
) -> UserAccount | None:
    account = await session.scalar(
        select(UserAccount).where(
            UserAccount.id == account_id,
            UserAccount.tenant_id == context.tenant_id,
        )
    )
    if account is None:
        return None
    account.status = status
    if status == "disabled":
        # 禁用即刻生效:撤销该账号的全部活跃会话。
        sessions = await session.scalars(
            select(AuthSession).where(
                AuthSession.user_id == account.id,
                AuthSession.revoked_at.is_(None),
            )
        )
        now = datetime.now(UTC)
        for auth_session in sessions:
            auth_session.revoked_at = now
    add_audit(
        session,
        context,
        action="user_account.status",
        object_type="user_account",
        object_id=str(account.id),
        details={"status": status},
    )
    await session.commit()
    await session.refresh(account)
    return account
