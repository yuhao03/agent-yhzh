"""注册/登录/登出/当前用户。

这些端点由 Next 服务端以 AGENT_SERVICE_TOKEN 服务间调用,
浏览器永远不直接携带后端会话 token。
"""

import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from agent_yhzh.config import settings
from agent_yhzh.database import get_session
from agent_yhzh.rate_limit import rate_limiter
from agent_yhzh.schemas import (
    AuthSessionResponse,
    LoginRequest,
    RegisterRequest,
    UserAccountRead,
)
from agent_yhzh.services.accounts import (
    AccountError,
    authenticate_user,
    create_auth_session,
    register_user,
    resolve_auth_token,
    revoke_auth_token,
)


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_ERROR_STATUS = {
    "invalid_email": 422,
    "weak_password": 422,
    "email_exists": 409,
    "invalid_credentials": 401,
    "account_disabled": 403,
}


def require_service(authorization: str | None = Header(default=None)) -> None:
    scheme, _, value = (authorization or "").partition(" ")
    # 统一转字节比较:compare_digest 遇到非 ASCII str 会抛 TypeError 变成 500。
    if scheme.lower() != "bearer" or not hmac.compare_digest(
        value.strip().encode("utf-8"), settings.agent_service_token.encode("utf-8")
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


async def _enforce_rate_limit(request: Request, action: str, limit: int) -> None:
    client_host = request.client.host if request.client else "unknown"
    if not await rate_limiter.allow(f"auth:{action}:{client_host}", limit):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests"
        )


def _account_error(error: AccountError) -> HTTPException:
    code = str(error)
    return HTTPException(
        status_code=_ERROR_STATUS.get(code, 400), detail=code
    )


def _tenant(x_tenant_id: str | None) -> str:
    return (x_tenant_id or settings.default_tenant_id).strip() or settings.default_tenant_id


@router.post(
    "/register",
    response_model=AuthSessionResponse,
    status_code=201,
    dependencies=[Depends(require_service)],
)
async def post_register(
    payload: RegisterRequest,
    request: Request,
    x_tenant_id: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
):
    await _enforce_rate_limit(
        request, "register", settings.auth_register_rate_limit_per_minute
    )
    try:
        account = await register_user(
            session,
            tenant_id=_tenant(x_tenant_id),
            email=payload.email,
            password=payload.password,
            display_name=payload.display_name,
        )
    except AccountError as error:
        raise _account_error(error) from error
    token, auth_session = await create_auth_session(
        session, account, user_agent=request.headers.get("user-agent")
    )
    return {"user": account, "token": token, "expires_at": auth_session.expires_at}


@router.post(
    "/login",
    response_model=AuthSessionResponse,
    dependencies=[Depends(require_service)],
)
async def post_login(
    payload: LoginRequest,
    request: Request,
    x_tenant_id: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
):
    await _enforce_rate_limit(
        request, "login", settings.auth_login_rate_limit_per_minute
    )
    try:
        account = await authenticate_user(
            session,
            tenant_id=_tenant(x_tenant_id),
            email=payload.email,
            password=payload.password,
        )
    except AccountError as error:
        raise _account_error(error) from error
    token, auth_session = await create_auth_session(
        session, account, user_agent=request.headers.get("user-agent")
    )
    return {"user": account, "token": token, "expires_at": auth_session.expires_at}


@router.post("/logout", status_code=204, dependencies=[Depends(require_service)])
async def post_logout(
    x_auth_token: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> None:
    if x_auth_token:
        await revoke_auth_token(session, x_auth_token)


@router.get(
    "/me",
    response_model=UserAccountRead,
    dependencies=[Depends(require_service)],
)
async def get_me(
    x_auth_token: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
):
    account = await resolve_auth_token(session, x_auth_token or "")
    if account is None:
        raise HTTPException(status_code=401, detail="Invalid session")
    return account
