import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from agent_yhzh.config import settings
from agent_yhzh.database import Base


JSON_TYPE = JSON().with_variant(JSONB, "postgresql")
VECTOR_TYPE = JSON().with_variant(
    Vector(settings.embedding_dimensions), "postgresql"
)


def table_args(schema: str, *constraints):
    options = {"schema": schema} if settings.is_postgres else {}
    return (*constraints, options) if constraints else options


def foreign_key(schema: str, table: str) -> str:
    return f"{schema}.{table}" if settings.is_postgres else table


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


class TenantSpaceMixin:
    tenant_id: Mapped[str] = mapped_column(
        String(80), default=settings.default_tenant_id, nullable=False, index=True
    )
    space_id: Mapped[str] = mapped_column(
        String(80), default=settings.default_space_id, nullable=False, index=True
    )


class Tenant(TimestampMixin, Base):
    __tablename__ = "tenants"
    __table_args__ = table_args("knowledge")

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    properties: Mapped[dict] = mapped_column(JSON_TYPE, default=dict, nullable=False)


class KnowledgeSpace(TimestampMixin, Base):
    __tablename__ = "knowledge_spaces"
    __table_args__ = table_args(
        "knowledge",
        UniqueConstraint("tenant_id", "slug", name="uq_knowledge_space_slug"),
    )

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    permissions: Mapped[dict] = mapped_column(JSON_TYPE, default=dict, nullable=False)


class KnowledgeType(TimestampMixin, TenantSpaceMixin, Base):
    __tablename__ = "knowledge_types"
    __table_args__ = table_args(
        "knowledge",
        UniqueConstraint(
            "tenant_id", "space_id", "slug", name="uq_knowledge_type_slug"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    slug: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    field_schema: Mapped[dict] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    relation_rules: Mapped[dict] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    risk_level: Mapped[str] = mapped_column(
        String(24), default="medium", nullable=False
    )


class Document(TimestampMixin, TenantSpaceMixin, Base):
    __tablename__ = "documents"
    __table_args__ = table_args(
        "knowledge",
        UniqueConstraint(
            "tenant_id", "space_id", "checksum", name="uq_document_checksum"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    filename: Mapped[str] = mapped_column(String(320), nullable=False)
    object_key: Mapped[str] = mapped_column(String(640), nullable=False)
    source_uri: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    mime_type: Mapped[str] = mapped_column(String(160), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    parser_status: Mapped[str] = mapped_column(
        String(32), default="queued", nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    properties: Mapped[dict] = mapped_column(JSON_TYPE, default=dict, nullable=False)


class DocumentChunk(TimestampMixin, TenantSpaceMixin, Base):
    __tablename__ = "document_chunks"
    __table_args__ = table_args(
        "knowledge",
        UniqueConstraint(
            "document_id", "content_hash", name="uq_document_chunk_hash"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(foreign_key("knowledge", "documents.id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[dict] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class KnowledgeItem(TimestampMixin, TenantSpaceMixin, Base):
    __tablename__ = "knowledge_items"
    __table_args__ = table_args(
        "knowledge",
        Index("ix_knowledge_scope_status", "tenant_id", "space_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False, index=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    knowledge_type: Mapped[str] = mapped_column(
        String(80), default="faq", nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(32), default="draft", nullable=False, index=True
    )
    sensitivity: Mapped[str] = mapped_column(
        String(32), default="internal", nullable=False
    )
    agent_scope: Mapped[list[str]] = mapped_column(
        JSON_TYPE, default=lambda: ["default"], nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    source_kind: Mapped[str] = mapped_column(
        String(40), default="admin", nullable=False
    )
    source_candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True
    )
    properties: Mapped[dict] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deprecated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class KnowledgeRelation(TimestampMixin, TenantSpaceMixin, Base):
    __tablename__ = "knowledge_relations"
    __table_args__ = table_args(
        "knowledge",
        UniqueConstraint(
            "tenant_id",
            "space_id",
            "source_id",
            "target_id",
            "relation_type",
            name="uq_knowledge_relation",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            foreign_key("knowledge", "knowledge_items.id"), ondelete="CASCADE"
        ),
        nullable=False,
        index=True,
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            foreign_key("knowledge", "knowledge_items.id"), ondelete="CASCADE"
        ),
        nullable=False,
        index=True,
    )
    relation_type: Mapped[str] = mapped_column(String(80), nullable=False)
    direction: Mapped[str] = mapped_column(
        String(20), default="directed", nullable=False
    )
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="pending_review", nullable=False
    )
    source_kind: Mapped[str] = mapped_column(
        String(40), default="admin", nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSON_TYPE, default=dict, nullable=False)


class InteractionEvent(Base):
    __tablename__ = "interaction_events"
    __table_args__ = table_args(
        "knowledge",
        Index(
            "ix_interaction_scope_time",
            "tenant_id",
            "space_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    space_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    user_ref_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    product_scope: Mapped[str] = mapped_column(
        String(80), default="default", nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    consent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sensitivity: Mapped[str] = mapped_column(
        String(24), default="normal", nullable=False
    )
    redaction_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processed_status: Mapped[str] = mapped_column(
        String(32), default="queued", nullable=False, index=True
    )
    retention_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class FeedbackSignal(TimestampMixin, TenantSpaceMixin, Base):
    __tablename__ = "feedback_signals"
    __table_args__ = table_args("knowledge")

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            foreign_key("knowledge", "interaction_events.id"), ondelete="CASCADE"
        ),
        nullable=False,
        index=True,
    )
    signal_type: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[dict] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    target: Mapped[str | None] = mapped_column(String(240), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)


class KnowledgeCandidate(TimestampMixin, TenantSpaceMixin, Base):
    __tablename__ = "knowledge_candidates"
    __table_args__ = table_args(
        "knowledge",
        UniqueConstraint(
            "tenant_id",
            "space_id",
            "normalized_key",
            name="uq_candidate_normalized_key",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    normalized_key: Mapped[str] = mapped_column(String(320), nullable=False)
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
    sensitivity: Mapped[str] = mapped_column(
        String(24), default="normal", nullable=False
    )
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    distinct_user_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.2, nullable=False)
    source_event_ids: Mapped[list[str]] = mapped_column(
        JSON_TYPE, default=list, nullable=False
    )
    source_chunk_ids: Mapped[list[str]] = mapped_column(
        JSON_TYPE, default=list, nullable=False
    )
    observed_user_hashes: Mapped[list[str]] = mapped_column(
        JSON_TYPE, default=list, nullable=False
    )
    evidence_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    conflict_status: Mapped[str] = mapped_column(
        String(32), default="unchecked", nullable=False
    )
    promoted_item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True
    )


class UserMemory(TimestampMixin, Base):
    __tablename__ = "user_memories"
    __table_args__ = table_args(
        "private_memory",
        Index(
            "ix_user_memory_scope",
            "tenant_id",
            "user_ref_hash",
            "product_scope",
            "status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    user_ref_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    product_scope: Mapped[str] = mapped_column(
        String(80), default="default", nullable=False, index=True
    )
    memory_type: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    consent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(
        String(24), default="active", nullable=False, index=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class KnowledgeEvidence(TimestampMixin, TenantSpaceMixin, Base):
    __tablename__ = "knowledge_evidence"
    __table_args__ = table_args("knowledge")

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True, index=True
    )
    relation_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True, index=True
    )
    candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True, index=True
    )
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True, index=True
    )
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True, index=True
    )
    source_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    properties: Mapped[dict] = mapped_column(JSON_TYPE, default=dict, nullable=False)


class KnowledgeView(TimestampMixin, TenantSpaceMixin, Base):
    __tablename__ = "knowledge_views"
    __table_args__ = table_args(
        "knowledge",
        UniqueConstraint(
            "tenant_id", "space_id", "name", "owner_ref", name="uq_knowledge_view"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    view_type: Mapped[str] = mapped_column(String(40), default="grid", nullable=False)
    owner_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    is_shared: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    configuration: Mapped[dict] = mapped_column(JSON_TYPE, default=dict, nullable=False)


class KnowledgeReview(TimestampMixin, TenantSpaceMixin, Base):
    __tablename__ = "knowledge_reviews"
    __table_args__ = table_args("knowledge")

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    object_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    object_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )
    proposal: Mapped[dict] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    reviewer_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    decision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), default="pending", nullable=False, index=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class KnowledgeVersion(Base):
    __tablename__ = "knowledge_versions"
    __table_args__ = table_args(
        "knowledge",
        UniqueConstraint("item_id", "version", name="uq_knowledge_item_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    space_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            foreign_key("knowledge", "knowledge_items.id"), ondelete="CASCADE"
        ),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSON_TYPE, nullable=False)
    change_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    actor_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class KnowledgeEmbedding(Base):
    __tablename__ = "embeddings"
    __table_args__ = table_args(
        "knowledge",
        UniqueConstraint(
            "object_type", "object_id", "model", name="uq_embedding_object_model"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    space_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    object_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    object_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )
    model: Mapped[str] = mapped_column(String(160), nullable=False)
    vector: Mapped[list[float]] = mapped_column(VECTOR_TYPE, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PromotionPolicy(TimestampMixin, TenantSpaceMixin, Base):
    __tablename__ = "promotion_policies"
    __table_args__ = table_args(
        "knowledge",
        UniqueConstraint(
            "tenant_id",
            "space_id",
            "knowledge_type",
            name="uq_promotion_policy_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    knowledge_type: Mapped[str] = mapped_column(String(80), nullable=False)
    occurrence_threshold: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    min_distinct_users: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_promote: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    max_risk_level: Mapped[str] = mapped_column(
        String(24), default="low", nullable=False
    )


class ModelProviderConfig(TimestampMixin, TenantSpaceMixin, Base):
    __tablename__ = "model_provider_configs"
    __table_args__ = table_args(
        "knowledge",
        UniqueConstraint(
            "tenant_id", "space_id", "name", name="uq_model_provider_config_name"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    provider: Mapped[str] = mapped_column(
        String(40), default="openai_compatible", nullable=False
    )
    base_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    chat_model: Mapped[str] = mapped_column(String(240), nullable=False)
    embedding_model: Mapped[str | None] = mapped_column(String(240), nullable=True)
    api_key_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    api_key_hint: Mapped[str | None] = mapped_column(String(32), nullable=True)
    temperature: Mapped[float] = mapped_column(Float, default=0.2, nullable=False)
    max_tokens: Mapped[int] = mapped_column(Integer, default=4096, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_test_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_test_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    last_tested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class OutboxEvent(TimestampMixin, Base):
    __tablename__ = "outbox_events"
    __table_args__ = table_args("knowledge")

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    aggregate_type: Mapped[str] = mapped_column(String(80), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="pending", nullable=False, index=True
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    available_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = table_args("knowledge")

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    space_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    actor_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(40), nullable=False)
    action: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    object_type: Mapped[str] = mapped_column(String(80), nullable=False)
    object_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    details: Mapped[dict] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class ImportJob(TimestampMixin, TenantSpaceMixin, Base):
    __tablename__ = "import_jobs"
    __table_args__ = table_args("knowledge")

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(foreign_key("knowledge", "documents.id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32), default="queued", nullable=False, index=True
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
