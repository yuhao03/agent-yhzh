from collections.abc import AsyncIterator

from sqlalchemy import text
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


async def init_database() -> None:
    from agent_yhzh import models  # noqa: F401

    async with engine.begin() as connection:
        if settings.is_postgres:
            await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await connection.execute(text("CREATE SCHEMA IF NOT EXISTS knowledge"))
            await connection.execute(text("CREATE SCHEMA IF NOT EXISTS agent_runtime"))
            await connection.execute(text("CREATE SCHEMA IF NOT EXISTS private_memory"))
        await connection.run_sync(Base.metadata.create_all)


async def close_database() -> None:
    await engine.dispose()
