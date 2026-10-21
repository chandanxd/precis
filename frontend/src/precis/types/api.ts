// @ts-nocheck — ported code written for a less strict TS config
export interface Fact {
  subject: string;
  verb: string;
  object: string;
  adjuncts: Record<string, string | string[]>;
  negated: boolean;
  modality: Modality;
  attributed_to: string | null;
  disjunctive: boolean;
  sdh_score: number;
  source_doc: string;
  sentence_id: number;
  original_sentence?: string;
}
export type Modality = "asserted" | "conditional" | "attributed" | "hypothetical";

export type StageIndex = 0 | 1 | 2 | 3 | 4 | 5;
export type StageStatus = "running" | "complete" | "error";
export interface PipelineEvent {
  stage: StageIndex;
  stage_name: string;
  status: StageStatus;
  detail: string;
  count: number;
  error: string | null;
}

export const STAGE_NAMES: Record<StageIndex, string> = {
  0: "Hardware detection",
  1: "Coreference resolution",
  2: "SVOA extraction",
  3: "SDH scoring",
  4: "Re-rank + pack",
  5: "LLM inference",
} as const;

export interface QueryResponse {
  answer: string;
  facts_used: Fact[];
  tokens_used: number;
  naive_rag_tokens: number;
  compression_rate: number;
  avg_sdh_score: number;
  latency_ms: number;
  model?: string;
  inference_tokens?: number;
  session_id?: string | null;
  stage_latencies?: Record<string, number>;
  /** Where the answer came from: casual chat, the model's own knowledge, or the documents. */
  answer_source?: "conversation" | "general" | "document";
}

export type HardwareMode = "gpu" | "gpu-partial" | "cpu" | "cpu-light";
export interface HardwareProfile {
  cpu_cores: number;
  cpu_model?: string;
  ram_gb: number;
  has_gpu: boolean;
  gpu_name: string | null;
  vram_gb: number | null;
  recommended_model: string;
  recommended_mode: HardwareMode;
  token_ceiling: number;
  ml_accelerator?: string | null;
}

export type WSMessage =
  | { type: "pipeline:stage"; payload: PipelineEvent }
  | { type: "pipeline:token"; payload: { char: string } }
  | { type: "pipeline:done"; payload: QueryResponse }
  | { type: "pipeline:error"; payload: { stage: StageIndex; error: string } };

export interface Conversation {
  id: string;
  title: string;
  document: string;
  created_at: string;
  message_count: number;
}

export interface Message {
  id: string;
  role: "user" | "ai";
  content: string;
  timestamp: string;
  pipeline_events: PipelineEvent[];
  query_response: QueryResponse;
  /** Set on the error message shown when a query fails. */
  failed?: boolean;
}

export interface Document {
  id: string;
  name: string;
  /** Not reported by the backend; present only on demo fixtures. */
  ingested_at?: string;
  fact_count: number;
  /** Not reported by the backend; present only on demo fixtures. */
  size_bytes?: number;
}

export interface FactStoreStats {
  total_facts: number;
  negated_count: number;
  modality_breakdown: Record<string, number>;
  attributed_count: number;
  conditional_count: number;
  avg_sdh_score: number;
}

export type Theme = "dark" | "light";

export type ActiveTab =
  "chat" | "facts" | "documents" | "system" | "evaluation" | "security" | "settings";

export interface UserSettings {
  ollamaModel: string;
  tokenCeiling: number;
  temperature: number;
  ollamaBaseUrl: string;
  minSdhScore: number;
  allowedModalities: Record<Modality, boolean>;
  strictNegation: boolean;
  defaultEvidenceExpanded: boolean;
  defaultSidebarCollapsed: boolean;
  theme: Theme;
}

export interface GraphNode {
  id: string;
  name: string;
  type: "subject" | "object";
  degree?: number;
}

export interface GraphLink {
  source: string;
  target: string;
  label: string;
  modality: Modality;
  negated: boolean;
  sdh_score: number;
}

export interface FactFilter {
  search: string;
  modality: Modality | "all";
  negatedOnly: boolean;
  minSdh: number;
}
