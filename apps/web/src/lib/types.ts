export type AdminStats = {
  published_knowledge: number;
  candidates: number;
  pending_review: number;
  interaction_events: number;
  private_memories: number;
};

export type KnowledgeItem = {
  id: string;
  title: string;
  content: string;
  knowledge_type: string;
  sensitivity: string;
  agent_scope: string[];
  properties: Record<string, unknown>;
  status: string;
  source_kind: string;
  source_candidate_id: string | null;
  created_at: string;
  updated_at: string;
};

export type KnowledgeCandidate = {
  id: string;
  title: string;
  content: string;
  candidate_type: string;
  status: string;
  risk_level: string;
  occurrence_count: number;
  distinct_user_count: number;
  score: number;
  source_event_ids: string[];
  created_at: string;
  updated_at: string;
};

export type KnowledgeGraph = {
  nodes: Array<{
    id: string;
    label: string;
    knowledge_type: string;
    source_kind: string;
  }>;
  edges: Array<{
    id: string;
    source: string;
    target: string;
    label: string;
    inferred: boolean;
  }>;
};

export type AdminDashboardPayload = {
  stats: AdminStats;
  candidates: KnowledgeCandidate[];
  knowledge: KnowledgeItem[];
  graph: KnowledgeGraph;
};
