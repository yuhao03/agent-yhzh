import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    content: str = Field(min_length=1)
    knowledge_type: str = "faq"
    sensitivity: str = "internal"
    agent_scope: list[str] = Field(default_factory=lambda: ["default"])
    properties: dict = Field(default_factory=dict)


class KnowledgeItemRead(KnowledgeItemCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    source_kind: str
    source_candidate_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class CandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    content: str
    candidate_type: str
    status: str
    risk_level: str
    occurrence_count: int
    distinct_user_count: int
    score: float
    source_event_ids: list[str]
    created_at: datetime
    updated_at: datetime


class InteractionCreate(BaseModel):
    event_type: str = "question"
    content: str = Field(min_length=1, max_length=10000)
    consent: bool = True


class AdminStats(BaseModel):
    published_knowledge: int
    candidates: int
    pending_review: int
    interaction_events: int
    private_memories: int


class PromoteCandidateRequest(BaseModel):
    title: str | None = None
    content: str | None = None
    knowledge_type: str = "faq"
    agent_scope: list[str] = Field(default_factory=lambda: ["default"])


class PromoteCandidateResponse(BaseModel):
    candidate: CandidateRead
    knowledge: KnowledgeItemRead


class KnowledgeGraphNode(BaseModel):
    id: str
    label: str
    knowledge_type: str
    source_kind: str


class KnowledgeGraphEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str
    inferred: bool = False


class KnowledgeGraphRead(BaseModel):
    nodes: list[KnowledgeGraphNode]
    edges: list[KnowledgeGraphEdge]
