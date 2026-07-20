import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


KnowledgeStatus = Literal["draft", "pending_review", "published", "deprecated"]


class KnowledgeItemCreate(BaseModel):
    title: str = Field(min_length=2, max_length=240)
    content: str = Field(min_length=10, max_length=100_000)
    summary: str | None = Field(default=None, max_length=2000)
    knowledge_type: str = Field(default="faq", min_length=1, max_length=80)
    sensitivity: str = Field(default="internal", max_length=32)
    agent_scope: list[str] = Field(default_factory=lambda: ["default"])
    properties: dict[str, Any] = Field(default_factory=dict)
    publish: bool = True

    @field_validator("agent_scope")
    @classmethod
    def validate_agent_scope(cls, value: list[str]) -> list[str]:
        normalized = sorted({scope.strip() for scope in value if scope.strip()})
        if not normalized or any(len(scope) > 80 for scope in normalized):
            raise ValueError("agent_scope must contain valid scopes")
        return normalized


class KnowledgeItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=240)
    content: str | None = Field(default=None, min_length=10, max_length=100_000)
    summary: str | None = Field(default=None, max_length=2000)
    knowledge_type: str | None = Field(default=None, min_length=1, max_length=80)
    sensitivity: str | None = Field(default=None, max_length=32)
    agent_scope: list[str] | None = None
    properties: dict[str, Any] | None = None
    status: KnowledgeStatus | None = None
    change_reason: str = Field(default="管理员编辑", min_length=2, max_length=1000)


class KnowledgeItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: str
    space_id: str
    title: str
    summary: str | None
    content: str
    knowledge_type: str
    sensitivity: str
    agent_scope: list[str]
    properties: dict[str, Any]
    status: str
    version: int
    source_kind: str
    source_candidate_id: uuid.UUID | None
    published_at: datetime | None
    deprecated_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: str
    space_id: str
    title: str
    content: str
    candidate_type: str
    status: str
    risk_level: str
    sensitivity: str
    occurrence_count: int
    distinct_user_count: int
    score: float
    source_event_ids: list[str]
    source_chunk_ids: list[str]
    evidence_summary: str | None
    conflict_status: str
    created_at: datetime
    updated_at: datetime


class InteractionCreate(BaseModel):
    event_type: Literal[
        "question",
        "correction",
        "feedback",
        "accepted",
        "rejected",
        "task_success",
        "task_failure",
    ] = "question"
    content: str = Field(min_length=1, max_length=10_000)
    consent: bool = False
    target: str | None = Field(default=None, max_length=240)


class InteractionAccepted(BaseModel):
    status: Literal["accepted"] = "accepted"
    event_id: uuid.UUID
    learning_queued: bool
    redaction_count: int


class AdminStats(BaseModel):
    published_knowledge: int
    draft_knowledge: int
    candidates: int
    pending_review: int
    interaction_events: int
    private_memories: int
    documents: int
    failed_imports: int
    relations: int
    reviews: int


class QualityTrendPoint(BaseModel):
    date: str
    interactions: int
    candidates: int
    published: int


class PromoteCandidateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=240)
    content: str = Field(min_length=10, max_length=100_000)
    knowledge_type: str = Field(default="faq", min_length=1, max_length=80)
    agent_scope: list[str] = Field(default_factory=lambda: ["default"])
    review_reason: str = Field(min_length=3, max_length=2000)


class RejectCandidateRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)


class PromoteCandidateResponse(BaseModel):
    candidate: CandidateRead
    knowledge: KnowledgeItemRead


class KnowledgeRelationCreate(BaseModel):
    source_id: uuid.UUID
    target_id: uuid.UUID
    relation_type: str = Field(min_length=1, max_length=80)
    direction: Literal["directed", "bidirectional"] = "directed"
    weight: float = Field(default=1.0, ge=0, le=10)
    confidence: float = Field(default=1.0, ge=0, le=1)
    evidence_quote: str = Field(min_length=3, max_length=5000)
    publish: bool = True

    @field_validator("target_id")
    @classmethod
    def target_is_present(cls, value: uuid.UUID) -> uuid.UUID:
        return value


class KnowledgeRelationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: str
    space_id: str
    source_id: uuid.UUID
    target_id: uuid.UUID
    relation_type: str
    direction: str
    weight: float
    confidence: float
    status: str
    source_kind: str
    version: int
    evidence: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class KnowledgeEvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_kind: str
    quote: str
    confidence: float
    chunk_id: uuid.UUID | None
    event_id: uuid.UUID | None
    properties: dict[str, Any]
    created_at: datetime


class KnowledgeVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version: int
    snapshot: dict[str, Any]
    change_kind: str
    actor_ref: str
    created_at: datetime


class KnowledgeReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    object_type: str
    object_id: uuid.UUID
    proposal: dict[str, Any]
    reviewer_ref: str | None
    decision: str | None
    reason: str | None
    status: str
    decided_at: datetime | None
    created_at: datetime


class KnowledgeDetail(BaseModel):
    item: KnowledgeItemRead
    evidence: list[KnowledgeEvidenceRead]
    versions: list[KnowledgeVersionRead]
    reviews: list[KnowledgeReviewRead]
    relations: list[KnowledgeRelationRead]


class KnowledgeGraphNode(BaseModel):
    id: str
    label: str
    knowledge_type: str
    source_kind: str
    status: str


class KnowledgeGraphEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str
    inferred: bool = False
    confidence: float = 1.0


class KnowledgeGraphRead(BaseModel):
    nodes: list[KnowledgeGraphNode]
    edges: list[KnowledgeGraphEdge]


class KnowledgeViewCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    view_type: Literal["grid", "graph", "dashboard"] = "grid"
    is_shared: bool = False
    configuration: dict[str, Any] = Field(default_factory=dict)


class KnowledgeViewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    view_type: str
    owner_ref: str
    is_shared: bool
    configuration: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    checksum: str
    mime_type: str
    byte_size: int
    parser_status: str
    version: int
    created_at: datetime
    updated_at: datetime


class ImportJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    status: str
    progress: int
    error: str | None
    created_at: datetime
    updated_at: datetime


class DocumentUploadResponse(BaseModel):
    document: DocumentRead
    import_job: ImportJobRead


class UserMemoryCreate(BaseModel):
    memory_type: Literal["preference", "profile", "workflow", "fact"] = "preference"
    content: str = Field(min_length=2, max_length=5000)
    consent: bool
    expires_in_days: int | None = Field(default=180, ge=1, le=730)


class UserMemoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    memory_type: str
    content: str
    consent: bool
    status: str
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AuditEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor_ref: str
    actor_role: str
    action: str
    object_type: str
    object_id: str | None
    details: dict[str, Any]
    request_id: str | None
    created_at: datetime


class RetrievalDebugItem(BaseModel):
    item: KnowledgeItemRead
    score: float
    lexical_score: float
    vector_score: float
    relation_score: float


ModelProvider = Literal[
    "openai", "openai_compatible", "azure", "anthropic", "ollama"
]


class ModelProviderConfigCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    provider: ModelProvider = "openai_compatible"
    base_url: str | None = Field(default=None, max_length=1000)
    chat_model: str = Field(min_length=1, max_length=240)
    embedding_model: str | None = Field(default=None, max_length=240)
    api_key: str | None = Field(default=None, max_length=2000)
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_tokens: int = Field(default=4096, ge=1, le=200_000)
    timeout_seconds: int = Field(default=60, ge=1, le=600)
    enabled: bool = True
    is_default: bool = True

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str | None) -> str | None:
        normalized = (value or "").strip().rstrip("/")
        if normalized and not normalized.startswith(("http://", "https://")):
            raise ValueError("base_url must start with http:// or https://")
        return normalized or None


class ModelProviderConfigUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    provider: ModelProvider | None = None
    base_url: str | None = Field(default=None, max_length=1000)
    chat_model: str | None = Field(default=None, min_length=1, max_length=240)
    embedding_model: str | None = Field(default=None, max_length=240)
    api_key: str | None = Field(default=None, max_length=2000)
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1, le=200_000)
    timeout_seconds: int | None = Field(default=None, ge=1, le=600)
    enabled: bool | None = None
    is_default: bool | None = None

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str | None) -> str | None:
        normalized = (value or "").strip().rstrip("/")
        if normalized and not normalized.startswith(("http://", "https://")):
            raise ValueError("base_url must start with http:// or https://")
        return normalized or None


class ModelProviderConfigRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: str
    space_id: str
    name: str
    provider: str
    base_url: str | None
    chat_model: str
    embedding_model: str | None
    api_key_configured: bool
    api_key_hint: str | None
    temperature: float
    max_tokens: int
    timeout_seconds: int
    enabled: bool
    is_default: bool
    last_test_status: str | None
    last_test_message: str | None
    last_tested_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ModelConnectionTestResponse(BaseModel):
    success: bool
    latency_ms: int
    message: str
