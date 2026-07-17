import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from agent_yhzh.config import settings
from agent_yhzh.database import Base


JSON_TYPE = JSON().with_variant(JSONB, "postgresql")
EMBEDDING_TYPE = JSON().with_variant(Vector(1536), "postgresql")


def table_args(schema: str) -> dict[str, str]:
    return {"schema": schema} if settings.is_postgres else {}


def foreign_key(table: str) -> str:
    return f"knowledge.{table}" if settings.is_postgres else table


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class KnowledgeItem(TimestampMixin, Base):
    __tablename__ = "knowledge_items"
    __table_args__ = table_args("knowledge")

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    knowledge_type: Mapped[str] = mapped_column(
        String(80), default="faq", nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(32), default="published", nullable=False, index=True
    )
    sensitivity: Mapped[str] = mapped_column(
        String(32), default="internal", nullable=False
    )
    agent_scope: Mapped[list[str]] = mapped_column(
        JSON_TYPE, default=lambda: ["default"], nullable=False
    )
    source_kind: Mapped[str] = mapped_column(
        String(40), default="admin", nullable=False
    )
    source_candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True
    )
    properties: Mapped[dict] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(
        EMBEDDING_TYPE, nullable=True
    )


class KnowledgeRelation(TimestampMixin, Base):
    __tablename__ = "knowledge_relations"
    __table_args__ = table_args("knowledge")

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(foreign_key("knowledge_items.id"), ondelete="CASCADE"),
        nullable=False,
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(foreign_key("knowledge_items.id"), ondelete="CASCADE"),
        nullable=False,
    )
    relation_type: Mapped[str] = mapped_column(String(80), nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="published", nullable=False
    )
    evidence: Mapped[dict] = mapped_column(JSON_TYPE, default=dict, nullable=False)


class InteractionEvent(Base):
    __tablename__ = "interaction_events"
    __table_args__ = table_args("knowledge")

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_ref_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    consent: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class KnowledgeCandidate(TimestampMixin, Base):
    __tablename__ = "knowledge_candidates"
    __table_args__ = table_args("knowledge")

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    normalized_key: Mapped[str] = mapped_column(
        String(320), nullable=False, unique=True, index=True
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    candidate_type: Mapped[str] = mapped_column(
        String(80), default="faq", nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(32), default="observed", nullable=False, index=True
    )
    risk_level: Mapped[str] = mapped_column(
        String(24), default="medium", nullable=False
    )
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    distinct_user_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.2, nullable=False)
    source_event_ids: Mapped[list[str]] = mapped_column(
        JSON_TYPE, default=list, nullable=False
    )
    observed_user_hashes: Mapped[list[str]] = mapped_column(
        JSON_TYPE, default=list, nullable=False
    )


class UserMemory(TimestampMixin, Base):
    __tablename__ = "user_memories"
    __table_args__ = table_args("private_memory")

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[str] = mapped_column(
        String(80), default="default", nullable=False, index=True
    )
    user_ref_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    product_scope: Mapped[str] = mapped_column(
        String(80), default="default", nullable=False, index=True
    )
    memory_type: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    consent: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
