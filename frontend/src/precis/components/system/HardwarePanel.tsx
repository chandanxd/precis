// @ts-nocheck — ported code written for a less strict TS config
import { useState, useEffect } from "react";
import type { HardwareProfile, FactStoreStats } from "../../types/api";
import { fetchHardware, fetchFactStats } from "../../services/api";
import { Cpu, Activity, Workflow } from "lucide-react";

export const HardwarePanel = () => {
  const [hardware, setHardware] = useState<HardwareProfile | null>(null);
  const [stats, setStats] = useState<FactStoreStats | null>(null);
  const [selectedStage, setSelectedStage] = useState<number>(2);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    const onFail = () => {
      if (isMounted) setLoadError("Could not load telemetry from the backend.");
    };
    fetchHardware()
      .then((hw) => {
        if (isMounted) setHardware(hw);
      })
      .catch(onFail);
    fetchFactStats()
      .then((st) => {
        if (isMounted) setStats(st);
      })
      .catch(onFail);
    return () => {
      isMounted = false;
    };
  }, []);

  if (!hardware || !stats) {
    return (
      <div className="flex-1 min-h-0 flex items-center justify-center p-[2rem] font-mono text-[0.75rem] text-[var(--tx-3)]">
        {loadError ?? "Reading edge hardware sensors and ChromaDB telemetry..."}
      </div>
    );
  }

  const stageDetails = [
    {
      stage: 0,
      title: "Hardware Detection & Calibration",
      tech: "psutil · PyTorch CUDA · Sysinfo",
      targetLatency: "< 50 ms",
      role: "Calibrates host system cores, RAM, and GPU VRAM to set dynamic token budget ceilings (1024 - 4096 tokens) avoiding out-of-memory crashes on consumer devices.",
      inputs: "Host system hardware sensors",
      outputs: "Calibrated HardwareProfile + Token Ceiling",
    },
    {
      stage: 1,
      title: "Neural Coreference Resolution",
      tech: "FastCoref (F-Core) · DistilBERT",
      targetLatency: "~ 120 ms",
      role: "Resolves ambiguous pronouns and noun phrases across document sentences into concrete antecedent entities prior to syntactic predicate extraction.",
      inputs: "Raw sanitized document text",
      outputs: "Co-reference resolved document string",
    },
    {
      stage: 2,
      title: "SVOA Extraction & Modality Typing",
      tech: "spaCy en_core_web_sm · Dependency Matcher",
      targetLatency: "~ 180 ms",
      role: "Extracts Subject-Verb-Object-Adjunct quadruples. Classifies epistemics into Asserted, Conditional, Attributed, or Hypothetical, and sets explicit negation flags.",
      inputs: "Coreference-resolved sentence stream",
      outputs: "Epistemically-typed Fact[] tuples",
    },
    {
      stage: 3,
      title: "SDH Salience Scoring & Vector Indexing",
      tech: "ChromaDB · all-MiniLM-L6-v2 · 4-Term SDH Heuristic",
      targetLatency: "~ 90 ms",
      role: "Computes 4-term SDH score combining linguistic salience, semantic diversity, certainty weight, and term frequency. Persists vector embeddings into local ChromaDB.",
      inputs: "SVOA facts + Epistemic modalities",
      outputs: "Persisted vector index + SDH ranked store",
    },
    {
      stage: 4,
      title: "Query-Adaptive Re-Ranking & Modality Packing",
      tech: "Knapsack Budget Packer · BM25 + Cosine Fusion",
      targetLatency: "~ 40 ms",
      role: "Re-ranks stored facts against the query. Applies knapsack packing to fit the highest-salience facts into the hardware-calibrated token ceiling, pruning redundant tokens by 70-85%.",
      inputs: "User query + Token budget limit",
      outputs: "Densely packed context string + Used Fact[]",
    },
    {
      stage: 5,
      title: "Quantized Edge LLM Inference",
      tech: "Ollama · LLaMA-3 (8B) / Phi-3 (3.8B) 4-bit Quant",
      targetLatency: "~ 800 - 1500 ms",
      role: "Executes local generation over the compressed SVOA facts without cloud telemetry. Delivers hallucination-resistant answers with verifiable fact citations.",
      inputs: "SVOA prompt context + User question",
      outputs: "Streaming natural language answer",
    },
  ];

  const currentStage = stageDetails[selectedStage];

  return (
    <div className="flex-1 min-h-0 w-full flex flex-col font-mono gap-[0.75rem] overflow-y-auto p-2 lg:p-3">
      {/* Top Half: Sensor Readout & Knowledge Store Gauges */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-[0.75rem] shrink-0">
        {/* Edge Hardware Sensor Card */}
        <div className="border border-[var(--bd)] bg-[var(--bg)] p-[0.75rem] flex flex-col gap-[0.5rem]">
          <div className="flex items-center justify-between border-b border-[var(--bd)] pb-[0.375rem]">
            <div className="flex items-center gap-[0.375rem]">
              <Cpu size={14} strokeWidth={1.5} />
              <span className="font-bold text-[0.75rem] uppercase text-[var(--tx)]">
                Calibrated Hardware Sensor
              </span>
            </div>
            <span className="px-[0.375rem] py-[0.125rem] text-[0.625rem] bg-[var(--inv-bg)] text-[var(--inv-tx)] font-semibold uppercase">
              MODE: {hardware.recommended_mode}
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-[0.375rem] text-[0.75rem]">
            <div className="border border-[var(--bd)] bg-[var(--bg-2)] p-[0.5rem] flex flex-col gap-[0.125rem]">
              <span className="text-[var(--tx-3)] text-[0.625rem]">CPU PROCESSOR</span>
              <span
                className="text-[var(--tx)] font-bold truncate"
                title={hardware.cpu_model || `${hardware.cpu_cores} Cores`}
              >
                {hardware.cpu_model || `${hardware.cpu_cores} Cores`}
              </span>
            </div>

            <div className="border border-[var(--bd)] bg-[var(--bg-2)] p-[0.5rem] flex flex-col gap-[0.125rem]">
              <span className="text-[var(--tx-3)] text-[0.625rem]">PHYSICAL RAM</span>
              <span className="text-[var(--tx)] font-bold">{hardware.ram_gb} GB</span>
            </div>

            <div className="border border-[var(--bd)] bg-[var(--bg-2)] p-[0.5rem] flex flex-col gap-[0.125rem]">
              <span className="text-[var(--tx-3)] text-[0.625rem]">ACCELERATOR</span>
              <span className="text-[var(--tx)] font-bold truncate">
                {hardware.has_gpu
                  ? hardware.gpu_name || "Active GPU"
                  : hardware.ml_accelerator?.toUpperCase() || "CPU-Only"}
              </span>
            </div>

            <div className="border border-[var(--bd)] bg-[var(--bg-2)] p-[0.5rem] flex flex-col gap-[0.125rem]">
              <span className="text-[var(--tx-3)] text-[0.625rem]">DEDICATED VRAM</span>
              <span className="text-[var(--tx)] font-bold">
                {hardware.vram_gb ? `${hardware.vram_gb} GB` : "Shared Host"}
              </span>
            </div>
          </div>

          {/* Token budget allocation bar */}
          <div className="border border-[var(--bd)] bg-[var(--bg-2)] p-[0.5rem] flex flex-col gap-[0.25rem] text-[0.6875rem]">
            <div className="flex items-center justify-between">
              <span className="text-[var(--tx-3)]">TARGET QUANTIZED MODEL:</span>
              <span className="font-bold text-[var(--tx)]">{hardware.recommended_model}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[var(--tx-3)]">TOKEN BUDGET CEILING:</span>
              <span className="font-bold text-[var(--tx)]">{hardware.token_ceiling} tokens</span>
            </div>
            <div className="w-full h-[0.375rem] bg-[var(--bd)] border border-[var(--bd-2)] mt-[0.125rem] overflow-hidden">
              <div className="h-full bg-[var(--tx)]" style={{ width: "100%" }} />
            </div>
          </div>
        </div>

        {/* Fact Store Metrics Card */}
        <div className="border border-[var(--bd)] bg-[var(--bg)] p-[0.75rem] flex flex-col gap-[0.5rem]">
          <div className="flex items-center justify-between border-b border-[var(--bd)] pb-[0.375rem]">
            <div className="flex items-center gap-[0.375rem]">
              <Activity size={14} strokeWidth={1.5} />
              <span className="font-bold text-[0.75rem] uppercase text-[var(--tx)]">
                Epistemic Fact Store Metrics
              </span>
            </div>
            <span className="text-[0.6875rem] text-[var(--tx-3)]">CHROMADB LOCAL</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-[0.375rem] text-[0.75rem]">
            <div className="border border-[var(--bd)] bg-[var(--bg-2)] p-[0.5rem] flex flex-col gap-[0.125rem]">
              <span className="text-[var(--tx-3)] text-[0.625rem]">STORED FACTS</span>
              <span className="text-[var(--tx)] font-bold text-[0.875rem]">
                {stats.total_facts.toLocaleString()}
              </span>
            </div>

            <div className="border border-[var(--bd)] bg-[var(--bg-2)] p-[0.5rem] flex flex-col gap-[0.125rem]">
              <span className="text-[var(--tx-3)] text-[0.625rem]">NEGATED</span>
              <span className="text-[var(--tx)] font-bold text-[0.875rem]">
                {stats.negated_count.toLocaleString()}
              </span>
            </div>

            <div className="border border-[var(--bd)] bg-[var(--bg-2)] p-[0.5rem] flex flex-col gap-[0.125rem]">
              <span className="text-[var(--tx-3)] text-[0.625rem]">ATTRIBUTED</span>
              <span className="text-[var(--tx)] font-bold text-[0.875rem]">
                {stats.attributed_count.toLocaleString()}
              </span>
            </div>

            <div className="border border-[var(--bd)] bg-[var(--bg-2)] p-[0.5rem] flex flex-col gap-[0.125rem]">
              <span className="text-[var(--tx-3)] text-[0.625rem]">CONDITIONAL</span>
              <span className="text-[var(--tx)] font-bold text-[0.875rem]">
                {stats.conditional_count.toLocaleString()}
              </span>
            </div>
          </div>

          <div className="border border-[var(--bd)] bg-[var(--bg-2)] p-[0.5rem] flex items-center justify-between text-[0.6875rem]">
            <span className="text-[var(--tx-3)]">AVERAGE SDH SALIENCE HEURISTIC:</span>
            <span className="font-bold text-[var(--tx)]">{stats.avg_sdh_score.toFixed(3)}</span>
          </div>
        </div>
      </div>

      {/* Bottom Half: Full-Height 6-Stage Pipeline Architecture Cockpit */}
      <div className="flex-1 min-h-0 border border-[var(--bd)] bg-[var(--bg)] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="h-[2.5rem] border-b border-[var(--bd)] px-[0.75rem] flex items-center justify-between select-none shrink-0 bg-[var(--bg-2)]">
          <div className="flex items-center gap-[0.375rem] text-[0.75rem] font-bold text-[var(--tx)]">
            <Workflow size={13} strokeWidth={1.5} />
            <span>6-STAGE NLP PIPELINE ARCHITECTURE & EDGE LATENCY PROFILER</span>
          </div>
          <span className="text-[0.6875rem] text-[var(--tx-3)] hidden sm:inline">
            ZERO-TRUST LATENCY OPTIMIZED
          </span>
        </div>

        {/* Pipeline Stage Selector Grid */}
        <div className="grid grid-cols-2 md:grid-cols-6 border-b border-[var(--bd)] bg-[var(--bg-2)] shrink-0 divide-x divide-y md:divide-y-0 divide-[var(--bd)]">
          {stageDetails.map((st) => (
            <button
              key={st.stage}
              type="button"
              onClick={() => setSelectedStage(st.stage)}
              className={`p-[0.5rem] text-left transition-colors flex flex-col gap-[0.125rem] ${
                selectedStage === st.stage
                  ? "bg-[var(--bg)] border-b-2 border-b-[var(--tx)]"
                  : "hover:bg-[var(--bg-3)]"
              }`}
            >
              <span className="text-[0.625rem] text-[var(--tx-3)] font-bold">
                STAGE 0{st.stage}
              </span>
              <span className="text-[0.6875rem] font-semibold text-[var(--tx)] truncate">
                {st.title.split(" ")[0]}
              </span>
              <span className="text-[0.625rem] text-[var(--tx-2)]">{st.targetLatency}</span>
            </button>
          ))}
        </div>

        {/* Stage Deep-Dive Inspector (Fills Remaining Height) */}
        <div className="flex-1 min-h-0 overflow-y-auto p-[0.75rem] flex flex-col gap-[0.625rem] bg-[var(--bg)]">
          <div className="flex items-center justify-between border-b border-[var(--bd)] pb-[0.375rem]">
            <div className="flex items-center gap-[0.5rem]">
              <span className="px-[0.375rem] py-[0.125rem] bg-[var(--inv-bg)] text-[var(--inv-tx)] text-[0.625rem] font-bold">
                STAGE 0{currentStage.stage}
              </span>
              <span className="font-bold text-[0.875rem] text-[var(--tx)]">
                {currentStage.title}
              </span>
            </div>
            <span className="text-[0.6875rem] text-[var(--tx-2)] font-mono">
              BUDGET: {currentStage.targetLatency}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-[0.5rem] text-[0.75rem]">
            <div className="border border-[var(--bd)] bg-[var(--bg-2)] p-[0.625rem] flex flex-col gap-[0.25rem]">
              <span className="text-[0.625rem] text-[var(--tx-3)] font-bold uppercase">
                TECHNOLOGY STACK
              </span>
              <span className="text-[var(--tx)] font-semibold">{currentStage.tech}</span>
            </div>

            <div className="border border-[var(--bd)] bg-[var(--bg-2)] p-[0.625rem] flex flex-col gap-[0.25rem]">
              <span className="text-[0.625rem] text-[var(--tx-3)] font-bold uppercase">
                INPUT CONTRACT
              </span>
              <span className="text-[var(--tx)]">{currentStage.inputs}</span>
            </div>

            <div className="border border-[var(--bd)] bg-[var(--bg-2)] p-[0.625rem] flex flex-col gap-[0.25rem]">
              <span className="text-[0.625rem] text-[var(--tx-3)] font-bold uppercase">
                OUTPUT CONTRACT
              </span>
              <span className="text-[var(--tx)]">{currentStage.outputs}</span>
            </div>
          </div>

          <div className="border border-[var(--bd)] bg-[var(--bg-2)] p-[0.75rem] flex flex-col gap-[0.25rem] text-[0.75rem]">
            <span className="text-[0.625rem] text-[var(--tx-3)] font-bold uppercase">
              ALGORITHMIC ROLE & EDGE VIABILITY
            </span>
            <p className="text-[var(--tx-2)] leading-relaxed text-[0.75rem]">{currentStage.role}</p>
          </div>
        </div>
      </div>
    </div>
  );
};
