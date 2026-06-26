export interface Fact {
    subject: string;
    verb: string;
    object: string;
    adjuncts: Record<string, string>;
    negated: boolean;
    modality: Modality;
    attributed_to: string | null;
    disjunctive: boolean;
    sdh_score: number;
    source_doc: string;
    sentence_id: number;
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
    5: "LLM inference"
} as const;

export interface QueryResponse {
    answer: string;
    facts_used: Fact[];
    tokens_used: number;
    naive_rag_tokens: number;
    compression_ratio: number;
    avg_sdh_score: number;
    latency_ms: number;
}

export type HardwareMode = "gpu" | "gpu-partial" | "cpu" | "cpu-light"
export interface HardwareProfile {
    cpu_cores: number;
    ram_gb: number;
    has_gpu: boolean;
    gpu_name: string | null;
    vram_gb: number | null;
    recommended_model: string;
    recommended_mode: HardwareMode;
    token_ceiling: number;
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
}

export interface Document {
    id: string;
    name: string;
    ingested_at: string;
    fact_count: number
    size_bytes: number;
}

export interface FactStoreStats {
    total_facts: number;
    negated_count: number;
    with_adjuncts: number;
    attributed_count: number;
    conditional_count: number;
    avg_sdh_score: number;
}

export type Theme = "dark" | "light"
