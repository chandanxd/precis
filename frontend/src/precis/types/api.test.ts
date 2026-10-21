import { describe, expect, it } from "vitest";
import type { QueryResponse, HardwareProfile, Fact } from "../types/api";

describe("API Contract and Schema Validation", () => {
  it("uses canonical compression_rate and preserves response metadata", () => {
    const mockRes: QueryResponse = {
      answer: "The bill was approved.",
      facts_used: [],
      tokens_used: 120,
      naive_rag_tokens: 450,
      compression_rate: 0.733,
      avg_sdh_score: 0.812,
      latency_ms: 240,
      model: "qwen3.5:4b",
      inference_tokens: 28,
      session_id: "test-session-123",
    };

    expect(mockRes.compression_rate).toBe(0.733);
    expect(mockRes.model).toBe("qwen3.5:4b");
    expect(mockRes.session_id).toBe("test-session-123");
  });

  it("HardwareProfile models cpu_model and ml_accelerator correctly", () => {
    const hw: HardwareProfile = {
      cpu_cores: 8,
      cpu_model: "AMD Ryzen 7 7840HS",
      ram_gb: 16,
      has_gpu: true,
      gpu_name: "NVIDIA RTX 4060",
      vram_gb: 8,
      recommended_model: "qwen3.5:4b",
      recommended_mode: "gpu",
      token_ceiling: 4096,
      ml_accelerator: "cuda",
    };

    expect(hw.cpu_model).toBe("AMD Ryzen 7 7840HS");
    expect(hw.ml_accelerator).toBe("cuda");
  });

  it("Fact preserves array and string adjuncts without truncation", () => {
    const fact: Fact = {
      subject: "Council",
      verb: "approved",
      object: "bill",
      adjuncts: {
        time: ["on Friday", "in 2026"],
        location: "in parliament",
      },
      negated: false,
      modality: "asserted",
      attributed_to: null,
      disjunctive: false,
      sdh_score: 0.85,
      source_doc: "doc.txt",
      sentence_id: 1,
    };

    expect(Array.isArray(fact.adjuncts["time"])).toBe(true);
    expect(fact.adjuncts["time"]).toEqual(["on Friday", "in 2026"]);
    expect(fact.adjuncts["location"]).toBe("in parliament");
  });
});
