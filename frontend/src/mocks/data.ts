import type {
    Fact,
    PipelineEvent,
    QueryResponse,
    HardwareProfile,
    Conversation,
    Message,
    Document,
    FactStoreStats,
} from "../types/api";

// Mock facts for developing and initial testing

export const mockFacts: Fact[] = [
    {
        subject: "government",
        verb: "approved",
        object: "climate bill",
        adjuncts: { time: "on Friday", location: "in parliament" },
        negated: false,
        modality: "asserted",
        attributed_to: null,
        disjunctive: false,
        sdh_score: 0.921,
        source_doc: "climate_policy_2026.txt",
        sentence_id: 0,
    },
    {
        subject: "bill",
        verb: "include",
        object: "nuclear subsidies",
        adjuncts: {},
        negated: true,
        modality: "asserted",
        attributed_to: null,
        disjunctive: false,
        sdh_score: 0.887,
        source_doc: "climate_policy_2026.txt",
        sentence_id: 1,
    },
    {
        subject: "minister",
        verb: "claimed",
        object: "renewable targets will be met",
        adjuncts: { time: "during press conference" },
        negated: false,
        modality: "attributed",
        attributed_to: "Environment Minister",
        disjunctive: false,
        sdh_score: 0.812,
        source_doc: "climate_policy_2026.txt",
        sentence_id: 3,
    },
    {
        subject: "carbon tax",
        verb: "reduce",
        object: "emissions",
        adjuncts: { condition: "if implemented by 2028" },
        negated: false,
        modality: "conditional",
        attributed_to: null,
        disjunctive: false,
        sdh_score: 0.776,
        source_doc: "climate_policy_2026.txt",
        sentence_id: 5,
    },
    {
        subject: "policy",
        verb: "lead",
        object: "economic disruption",
        adjuncts: {},
        negated: false,
        modality: "hypothetical",
        attributed_to: null,
        disjunctive: false,
        sdh_score: 0.654,
        source_doc: "climate_policy_2026.txt",
        sentence_id: 7,
    },
    {
        subject: "senate",
        verb: "ratified",
        object: "amendment",
        adjuncts: { time: "on Thursday", manner: "unanimously" },
        negated: false,
        modality: "asserted",
        attributed_to: null,
        disjunctive: false,
        sdh_score: 0.903,
        source_doc: "climate_policy_2026.txt",
        sentence_id: 9,
    },
    {
        subject: "opposition",
        verb: "support",
        object: "carbon tax provisions",
        adjuncts: {},
        negated: true,
        modality: "asserted",
        attributed_to: null,
        disjunctive: false,
        sdh_score: 0.845,
        source_doc: "climate_policy_2026.txt",
        sentence_id: 11,
    },
    {
        subject: "researchers",
        verb: "estimated",
        object: "15% reduction in industrial output",
        adjuncts: { time: "by 2030" },
        negated: false,
        modality: "attributed",
        attributed_to: "IISc research team",
        disjunctive: false,
        sdh_score: 0.791,
        source_doc: "climate_policy_2026.txt",
        sentence_id: 14,
    },
];

// Mock Pipeline Events─

/** A complete sequence of pipeline events for one query. */
export const mockPipelineEvents: PipelineEvent[] = [
    {
        stage: 0,
        stage_name: "Hardware detection",
        status: "complete",
        detail: "Ryzen 9 8945HS · 16 GB · RTX 4060 8 GB · gpu mode",
        count: 1,
        error: null
    },
    {
        stage: 1,
        stage_name: "Coreference resolution",
        status: "complete",
        detail: "47 references resolved across 312 sentences",
        count: 47,
        error: null
    },
    {
        stage: 2,
        stage_name: "SVOA extraction",
        status: "complete",
        detail: "2,847 facts extracted · 312 negated · 89 attributed",
        count: 2847,
        error: null,
    },
    {
        stage: 3,
        stage_name: "SDH scoring",
        status: "complete",
        detail: "avg score 0.714 · range 0.23 to 0.97 · 4 terms weighted",
        count: 2847,
        error: null,
    },
    {
        stage: 4,
        stage_name: "Re-rank + pack",
        status: "complete",
        detail: "847 tokens packed · 79.8% compression · 42 facts selected",
        count: 42,
        error: null,
    },
    {
        stage: 5,
        stage_name: "LLM inference",
        status: "complete",
        detail: "llama3:8b-q4_K_M · 1.2s · 142 tokens generated",
        count: 142,
        error: null
    },
];

/** A sequence showing pipeline in progress (stages 0-2 done, 3 running). */
export const mockPipelineInProgress: PipelineEvent[] = [
    {
        stage: 0,
        stage_name: "Hardware detection",
        status: "complete",
        detail: "Ryzen 9 8945HS · 16 GB · RTX 4060 8 GB · gpu mode",
        count: 0,
        error: null
    },
    {
        stage: 1,
        stage_name: "Coreference resolution",
        status: "complete",
        detail: "47 references resolved across 312 sentences",
        count: 0,
        error: null
    },
    {
        stage: 2,
        stage_name: "SVOA extraction",
        status: "complete",
        detail: "2,847 facts extracted · 312 negated · 89 attributed",
        count: 2847,
        error: null
    },
    {
        stage: 3,
        stage_name: "SDH scoring",
        status: "running",
        detail: "Scoring facts…",
        count: 0,
        error: null
    },
];

/** A pipeline event showing an error state. */
export const mockPipelineError: PipelineEvent = {
    stage: 5,
    stage_name: "LLM inference",
    status: "error",
    detail: "Ollama connection refused. Is the service running?",
    count: 0,
    error: "ConnectionRefusedError: localhost:11434",
};

// Mock Query Response

export const mockQueryResponse: QueryResponse = {
    answer:
        "The government approved the climate bill on Friday in parliament. The bill specifically does not include nuclear subsidies. The senate ratified an amendment unanimously on Thursday. According to the Environment Minister, renewable targets will be met. However, the opposition does not support the carbon tax provisions.",
    facts_used: mockFacts.slice(0, 6),
    tokens_used: 847,
    naive_rag_tokens: 4198,
    compression_ratio: 0.798,
    avg_sdh_score: 0.857,
    latency_ms: 1247,
};

// Mock Hardware Profile

export const mockHardware: HardwareProfile = {
    cpu_cores: 16,
    ram_gb: 16,
    has_gpu: true,
    gpu_name: "NVIDIA GeForce RTX 4060",
    vram_gb: 8,
    recommended_model: "llama3:8b-q4_K_M",
    recommended_mode: "gpu",
    token_ceiling: 4096,
};

/** A hardware profile for a lower-end machine (CPU-only mode). */
export const mockHardwareCPU: HardwareProfile = {
    cpu_cores: 8,
    ram_gb: 8,
    has_gpu: false,
    gpu_name: null,
    vram_gb: null,
    recommended_model: "phi3:3.8b-q4_K_M",
    recommended_mode: "cpu-light",
    token_ceiling: 1024,
};

// Mock Conversations

export const mockConversations: Conversation[] = [
    {
        id: "conv-001",
        title: "Climate bill analysis",
        document: "climate_policy_2026.txt",
        created_at: "2026-06-15T10:30:00Z",
        message_count: 4,
    },
    {
        id: "conv-002",
        title: "Neural network architecture",
        document: "transformer_survey.pdf",
        created_at: "2026-06-14T14:15:00Z",
        message_count: 8,
    },
    {
        id: "conv-003",
        title: "Contract clause review",
        document: "service_agreement.docx",
        created_at: "2026-06-13T09:00:00Z",
        message_count: 3,
    },
];

// Mock Messages

export const mockMessages: Message[] = [
    {
        id: "msg-001",
        role: "user",
        content: "What did the government approve and what was excluded from the bill?",
        timestamp: "2026-06-15T10:30:12Z",
        pipeline_events: mockPipelineEvents,
        query_response: mockQueryResponse
    },
    {
        id: "msg-002",
        role: "ai",
        content: mockQueryResponse.answer,
        timestamp: "2026-06-15T10:30:14Z",
        pipeline_events: mockPipelineEvents,
        query_response: mockQueryResponse,
    },
    {
        id: "msg-003",
        role: "user",
        content: "Does the opposition support any part of the bill?",
        timestamp: "2026-06-15T10:31:45Z",
        pipeline_events: mockPipelineEvents,
        query_response: mockQueryResponse
    },
    {
        id: "msg-004",
        role: "ai",
        content:
            "No. The opposition does not support the carbon tax provisions in the bill. This is stated as a direct assertion in the document, not speculation or attribution.",
        timestamp: "2026-06-15T10:31:47Z",
        pipeline_events: mockPipelineEvents,
        query_response: {
            ...mockQueryResponse,
            answer:
                "No. The opposition does not support the carbon tax provisions in the bill. This is stated as a direct assertion in the document, not speculation or attribution.",
            facts_used: [mockFacts[6]],
            tokens_used: 312,
            compression_ratio: 0.926,
            avg_sdh_score: 0.845,
            latency_ms: 890,
        },
    },
];

// Mock Documents

export const mockDocuments: Document[] = [
    {
        id: "doc-001",
        name: "climate_policy_2026.txt",
        ingested_at: "2026-06-15T10:29:00Z",
        fact_count: 2847,
        size_bytes: 48_200,
    },
    {
        id: "doc-002",
        name: "transformer_survey.pdf",
        ingested_at: "2026-06-14T14:10:00Z",
        fact_count: 5103,
        size_bytes: 2_340_000,
    },
];

// Mock Fact Store Stats

export const mockFactStoreStats: FactStoreStats = {
    total_facts: 7950,
    negated_count: 624,
    with_adjuncts: 3812,
    attributed_count: 891,
    conditional_count: 413,
    avg_sdh_score: 0.714,
};
