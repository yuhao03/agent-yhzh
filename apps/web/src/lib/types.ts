export type AdminStats = {
  published_knowledge: number;
  draft_knowledge: number;
  candidates: number;
  pending_review: number;
  interaction_events: number;
  private_memories: number;
  documents: number;
  failed_imports: number;
  relations: number;
  reviews: number;
};

export type KnowledgeItem = {
  id: string;
  tenant_id: string;
  space_id: string;
  title: string;
  summary: string | null;
  content: string;
  knowledge_type: string;
  sensitivity: string;
  agent_scope: string[];
  properties: Record<string, unknown>;
  status: string;
  version: number;
  source_kind: string;
  source_candidate_id: string | null;
  published_at: string | null;
  deprecated_at: string | null;
  created_at: string;
  updated_at: string;
};

export type KnowledgeCandidate = {
  id: string;
  tenant_id: string;
  space_id: string;
  title: string;
  content: string;
  candidate_type: string;
  status: string;
  risk_level: string;
  sensitivity: string;
  occurrence_count: number;
  distinct_user_count: number;
  score: number;
  source_event_ids: string[];
  source_chunk_ids: string[];
  evidence_summary: string | null;
  conflict_status: string;
  created_at: string;
  updated_at: string;
};

export type KnowledgeGraph = {
  nodes: Array<{
    id: string;
    label: string;
    knowledge_type: string;
    source_kind: string;
    status: string;
  }>;
  edges: Array<{
    id: string;
    source: string;
    target: string;
    label: string;
    inferred: boolean;
    confidence: number;
  }>;
};

export type QualityTrend = {
  date: string;
  interactions: number;
  candidates: number;
  published: number;
};

export type KnowledgeDocument = {
  id: string;
  filename: string;
  checksum: string;
  mime_type: string;
  byte_size: number;
  parser_status: string;
  version: number;
  created_at: string;
  updated_at: string;
};

export type ImportJob = {
  id: string;
  document_id: string;
  status: string;
  progress: number;
  error: string | null;
  created_at: string;
  updated_at: string;
};

export type KnowledgeRelation = {
  id: string;
  source_id: string;
  target_id: string;
  relation_type: string;
  direction: string;
  weight: number;
  confidence: number;
  status: string;
  evidence: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type KnowledgeView = {
  id: string;
  name: string;
  view_type: string;
  owner_ref: string;
  is_shared: boolean;
  configuration: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type AuditEvent = {
  id: string;
  actor_ref: string;
  actor_role: string;
  action: string;
  object_type: string;
  object_id: string | null;
  details: Record<string, unknown>;
  request_id: string | null;
  created_at: string;
};

export type ModelProviderConfig = {
  id: string;
  tenant_id: string;
  space_id: string;
  name: string;
  provider: "openai" | "openai_compatible" | "azure" | "anthropic" | "ollama";
  base_url: string | null;
  chat_model: string;
  embedding_model: string | null;
  api_key_configured: boolean;
  api_key_hint: string | null;
  temperature: number;
  max_tokens: number;
  timeout_seconds: number;
  enabled: boolean;
  is_default: boolean;
  last_test_status: string | null;
  last_test_message: string | null;
  last_tested_at: string | null;
  created_at: string;
  updated_at: string;
};

export type AdminDashboardPayload = {
  stats: AdminStats;
  candidates: KnowledgeCandidate[];
  knowledge: KnowledgeItem[];
  graph: KnowledgeGraph;
  trends: QualityTrend[];
  documents: KnowledgeDocument[];
  imports: ImportJob[];
  relations: KnowledgeRelation[];
  views: KnowledgeView[];
  audits: AuditEvent[];
  modelConfigs: ModelProviderConfig[];
};
