import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from agent_yhzh.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(settings.database_url, pool_pre_ping=True)
session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


def run_migrations() -> None:
    api_root = Path(__file__).resolve().parents[1]
    config = Config(str(api_root / "alembic.ini"))
    config.set_main_option("script_location", str(api_root / "alembic"))
    config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))
    command.upgrade(config, "head")


async def seed_defaults() -> None:
    from agent_yhzh.models import (
        KnowledgeSpace,
        KnowledgeType,
        PromotionPolicy,
        Tenant,
    )

    async with session_factory() as session:
        tenant = await session.get(Tenant, settings.default_tenant_id)
        if tenant is None:
            session.add(
                Tenant(
                    id=settings.default_tenant_id,
                    name="默认租户",
                    properties={"bootstrap": True},
                )
            )
        space = await session.get(KnowledgeSpace, settings.default_space_id)
        if space is None:
            session.add(
                KnowledgeSpace(
                    id=settings.default_space_id,
                    tenant_id=settings.default_tenant_id,
                    slug=settings.default_space_id,
                    name="默认知识空间",
                    permissions={"admin": ["read", "write", "review"]},
                )
            )

        existing_types = set(
            await session.scalars(
                select(KnowledgeType.slug).where(
                    KnowledgeType.tenant_id == settings.default_tenant_id,
                    KnowledgeType.space_id == settings.default_space_id,
                )
            )
        )
        for slug, name, risk in [
            ("faq", "FAQ", "low"),
            ("process", "流程", "medium"),
            ("policy", "规则", "high"),
            ("case", "案例", "medium"),
            ("preference", "用户偏好", "private"),
        ]:
            if slug not in existing_types:
                session.add(
                    KnowledgeType(
                        tenant_id=settings.default_tenant_id,
                        space_id=settings.default_space_id,
                        slug=slug,
                        name=name,
                        risk_level=risk,
                    )
                )

        existing_policies = set(
            await session.scalars(
                select(PromotionPolicy.knowledge_type).where(
                    PromotionPolicy.tenant_id == settings.default_tenant_id,
                    PromotionPolicy.space_id == settings.default_space_id,
                )
            )
        )
        for knowledge_type, min_users in [
            ("faq", settings.candidate_min_distinct_users),
            ("process", settings.candidate_min_distinct_users),
            ("policy", settings.candidate_min_distinct_users),
            ("case", settings.candidate_min_distinct_users),
        ]:
            if knowledge_type not in existing_policies:
                session.add(
                    PromotionPolicy(
                        tenant_id=settings.default_tenant_id,
                        space_id=settings.default_space_id,
                        knowledge_type=knowledge_type,
                        occurrence_threshold=settings.candidate_review_threshold,
                        min_distinct_users=min_users,
                        review_required=True,
                        auto_promote=False,
                    )
                )
        await session.commit()


async def init_database() -> None:
    settings.validate_runtime_security()
    from agent_yhzh import models  # noqa: F401

    if settings.auto_migrate:
        await asyncio.to_thread(run_migrations)
    await seed_defaults()


async def close_database() -> None:
    await engine.dispose()
