"""Create governed knowledge platform baseline.

Revision ID: 0001_platform_baseline
Revises:
Create Date: 2026-07-20
"""

from alembic import op
from sqlalchemy import text


revision = "0001_platform_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        bind.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        bind.execute(text("CREATE SCHEMA IF NOT EXISTS knowledge"))
        bind.execute(text("CREATE SCHEMA IF NOT EXISTS agent_runtime"))
        bind.execute(text("CREATE SCHEMA IF NOT EXISTS private_memory"))

    from agent_yhzh import models  # noqa: F401
    from agent_yhzh.database import Base

    Base.metadata.create_all(bind=bind)
    if bind.dialect.name == "postgresql":
        bind.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_knowledge_items_fts "
                "ON knowledge.knowledge_items USING gin "
                "(to_tsvector('simple', coalesce(title, '') || ' ' || "
                "coalesce(summary, '') || ' ' || coalesce(content, '')))"
            )
        )
        bind.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_embeddings_vector_hnsw "
                "ON knowledge.embeddings USING hnsw (vector vector_cosine_ops)"
            )
        )


def downgrade() -> None:
    from agent_yhzh import models  # noqa: F401
    from agent_yhzh.database import Base

    Base.metadata.drop_all(bind=op.get_bind())
