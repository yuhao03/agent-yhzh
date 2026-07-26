import base64
import hashlib
import ipaddress
import socket
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlsplit

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from agent_yhzh.config import settings
from agent_yhzh.models import ModelProviderConfig
from agent_yhzh.schemas import ModelProviderConfigCreate, ModelProviderConfigUpdate
from agent_yhzh.security import CallerContext
from agent_yhzh.services.audit import add_audit, add_outbox


@dataclass(frozen=True)
class RuntimeModelConfig:
    provider: str
    api_protocol: str
    base_url: str | None
    chat_model: str
    embedding_model: str | None
    api_key: str | None
    temperature: float
    max_tokens: int
    timeout_seconds: int
    source: str


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.config_encryption_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(secret: str) -> str:
    return _fernet().encrypt(secret.encode("utf-8")).decode("ascii")


def decrypt_secret(ciphertext: str | None) -> str | None:
    if not ciphertext:
        return None
    try:
        return _fernet().decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except InvalidToken as error:
        raise RuntimeError("model_api_key_decryption_failed") from error


def secret_hint(secret: str) -> str:
    if len(secret) <= 6:
        return "••••••"
    return f"{secret[:2]}••••{secret[-4:]}"


def _literal_ip(
    hostname: str,
) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address(hostname)
    except ValueError:
        pass
    try:
        # glibc 会把 2130706433、127.1、0x7f000001 这类字面量解析成 IPv4,
        # 统一转成规范地址再做私网检查(不做 DNS 解析,保持离线确定)。
        return ipaddress.ip_address(socket.inet_aton(hostname))
    except OSError:
        return None


def validate_model_base_url(base_url: str | None) -> None:
    if not base_url:
        return
    parsed = urlsplit(base_url)
    if parsed.username or parsed.password or not parsed.hostname:
        raise ValueError("unsafe_model_base_url")
    hostname = parsed.hostname.lower()
    is_private = hostname == "localhost" or hostname.endswith(".local")
    address = _literal_ip(hostname)
    if address is not None:
        is_private = is_private or any(
            [
                address.is_private,
                address.is_loopback,
                address.is_link_local,
                address.is_multicast,
                address.is_reserved,
            ]
        )
    if is_private and not settings.allow_private_model_urls:
        raise ValueError("private_model_url_not_allowed")


def config_dto(config: ModelProviderConfig) -> dict:
    return {
        "id": config.id,
        "tenant_id": config.tenant_id,
        "space_id": config.space_id,
        "name": config.name,
        "provider": config.provider,
        "api_protocol": config.api_protocol,
        "base_url": config.base_url,
        "chat_model": config.chat_model,
        "embedding_model": config.embedding_model,
        "api_key_configured": bool(config.api_key_ciphertext),
        "api_key_hint": config.api_key_hint,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "timeout_seconds": config.timeout_seconds,
        "enabled": config.enabled,
        "is_default": config.is_default,
        "last_test_status": config.last_test_status,
        "last_test_message": config.last_test_message,
        "last_tested_at": config.last_tested_at,
        "created_at": config.created_at,
        "updated_at": config.updated_at,
    }


async def list_model_configs(
    session: AsyncSession, context: CallerContext
) -> list[dict]:
    configs = await session.scalars(
        select(ModelProviderConfig)
        .where(
            ModelProviderConfig.tenant_id == context.tenant_id,
            ModelProviderConfig.space_id == context.space_id,
        )
        .order_by(
            ModelProviderConfig.is_default.desc(),
            ModelProviderConfig.updated_at.desc(),
        )
    )
    return [config_dto(config) for config in configs]


async def _clear_other_defaults(
    session: AsyncSession, context: CallerContext, keep_id: uuid.UUID | None = None
) -> None:
    statement = update(ModelProviderConfig).where(
        ModelProviderConfig.tenant_id == context.tenant_id,
        ModelProviderConfig.space_id == context.space_id,
        ModelProviderConfig.is_default.is_(True),
    )
    if keep_id:
        statement = statement.where(ModelProviderConfig.id != keep_id)
    await session.execute(statement.values(is_default=False))


async def create_model_config(
    session: AsyncSession,
    context: CallerContext,
    payload: ModelProviderConfigCreate,
) -> dict:
    validate_model_base_url(payload.base_url)
    if payload.is_default:
        await _clear_other_defaults(session, context)
    api_key = (payload.api_key or "").strip()
    config = ModelProviderConfig(
        tenant_id=context.tenant_id,
        space_id=context.space_id,
        name=payload.name.strip(),
        provider=payload.provider,
        api_protocol=payload.api_protocol,
        base_url=payload.base_url,
        chat_model=payload.chat_model.strip(),
        embedding_model=(payload.embedding_model or "").strip() or None,
        api_key_ciphertext=encrypt_secret(api_key) if api_key else None,
        api_key_hint=secret_hint(api_key) if api_key else None,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
        timeout_seconds=payload.timeout_seconds,
        enabled=payload.enabled,
        is_default=payload.is_default,
    )
    session.add(config)
    await session.flush()
    add_audit(
        session,
        context,
        action="model_config.create",
        object_type="model_provider_config",
        object_id=str(config.id),
        details={
            "provider": config.provider,
            "base_url": config.base_url,
            "chat_model": config.chat_model,
            "api_key_configured": bool(api_key),
        },
    )
    add_outbox(
        session,
        tenant_id=context.tenant_id,
        event_type="model_config.changed",
        aggregate_type="model_provider_config",
        aggregate_id=str(config.id),
    )
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise ValueError("model_config_name_exists") from error
    await session.refresh(config)
    return config_dto(config)


async def update_model_config(
    session: AsyncSession,
    context: CallerContext,
    config_id: uuid.UUID,
    payload: ModelProviderConfigUpdate,
) -> dict | None:
    config = await session.scalar(
        select(ModelProviderConfig)
        .where(
            ModelProviderConfig.id == config_id,
            ModelProviderConfig.tenant_id == context.tenant_id,
            ModelProviderConfig.space_id == context.space_id,
        )
        .with_for_update()
    )
    if config is None:
        return None
    values = payload.model_dump(exclude_unset=True)
    api_key = values.pop("api_key", None)
    validate_model_base_url(values.get("base_url", config.base_url))
    if values.get("is_default") is True:
        await _clear_other_defaults(session, context, keep_id=config.id)
    for key, value in values.items():
        if key in {"name", "chat_model"} and isinstance(value, str):
            value = value.strip()
        if key == "embedding_model" and isinstance(value, str):
            value = value.strip() or None
        setattr(config, key, value)
    if isinstance(api_key, str) and api_key.strip():
        normalized_key = api_key.strip()
        config.api_key_ciphertext = encrypt_secret(normalized_key)
        config.api_key_hint = secret_hint(normalized_key)
    add_audit(
        session,
        context,
        action="model_config.update",
        object_type="model_provider_config",
        object_id=str(config.id),
        details={
            "fields": sorted(values),
            "api_key_rotated": bool(isinstance(api_key, str) and api_key.strip()),
        },
    )
    add_outbox(
        session,
        tenant_id=context.tenant_id,
        event_type="model_config.changed",
        aggregate_type="model_provider_config",
        aggregate_id=str(config.id),
    )
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise ValueError("model_config_name_exists") from error
    await session.refresh(config)
    return config_dto(config)


async def get_runtime_model_config(
    session: AsyncSession, tenant_id: str, space_id: str
) -> RuntimeModelConfig:
    config = await session.scalar(
        select(ModelProviderConfig)
        .where(
            ModelProviderConfig.tenant_id == tenant_id,
            ModelProviderConfig.space_id == space_id,
            ModelProviderConfig.enabled.is_(True),
        )
        .order_by(
            ModelProviderConfig.is_default.desc(),
            ModelProviderConfig.updated_at.desc(),
        )
        .limit(1)
    )
    if config:
        return RuntimeModelConfig(
            provider=config.provider,
            api_protocol=config.api_protocol,
            base_url=config.base_url,
            chat_model=config.chat_model,
            embedding_model=config.embedding_model,
            api_key=decrypt_secret(config.api_key_ciphertext),
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            timeout_seconds=config.timeout_seconds,
            source="database",
        )
    return RuntimeModelConfig(
        provider="openai",
        api_protocol=settings.model_protocol,
        base_url=settings.model_base_url or None,
        chat_model=settings.model_name,
        embedding_model=settings.embedding_model,
        api_key=settings.openai_api_key or None,
        temperature=0.2,
        max_tokens=4096,
        timeout_seconds=60,
        source="environment",
    )


def litellm_model_name(provider: str, model: str) -> str:
    if "/" in model:
        return model
    prefix = {
        "openai": "openai",
        "openai_compatible": "openai",
        "azure": "azure",
        "anthropic": "anthropic",
        "ollama": "ollama",
    }.get(provider, provider)
    return f"{prefix}/{model}"


async def test_model_connection(
    session: AsyncSession, context: CallerContext, config_id: uuid.UUID
) -> dict | None:
    config = await session.scalar(
        select(ModelProviderConfig).where(
            ModelProviderConfig.id == config_id,
            ModelProviderConfig.tenant_id == context.tenant_id,
            ModelProviderConfig.space_id == context.space_id,
        )
    )
    if config is None:
        return None
    validate_model_base_url(config.base_url)
    api_key = decrypt_secret(config.api_key_ciphertext)
    runtime = RuntimeModelConfig(
        provider=config.provider,
        api_protocol=config.api_protocol,
        base_url=config.base_url,
        chat_model=config.chat_model,
        embedding_model=config.embedding_model,
        api_key=api_key,
        temperature=0,
        max_tokens=16,
        timeout_seconds=config.timeout_seconds,
        source="database",
    )
    started = time.perf_counter()
    try:
        from agent_yhzh.services.llm_gateway import chat_complete

        await chat_complete(
            runtime,
            [{"role": "user", "content": "Reply with OK."}],
        )
        success = True
        message = "连接成功，模型已返回响应。"
        config.last_test_status = "success"
    except Exception as error:
        success = False
        raw_message = str(error)
        if api_key:
            raw_message = raw_message.replace(api_key, "[secret]")
        message = f"连接失败：{raw_message[:350]}"
        config.last_test_status = "failed"
    latency_ms = int((time.perf_counter() - started) * 1000)
    config.last_test_message = message[:500]
    config.last_tested_at = datetime.now(UTC)
    add_audit(
        session,
        context,
        action="model_config.test",
        object_type="model_provider_config",
        object_id=str(config.id),
        details={"success": success, "latency_ms": latency_ms},
    )
    await session.commit()
    return {"success": success, "latency_ms": latency_ms, "message": message}
