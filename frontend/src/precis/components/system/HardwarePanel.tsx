// @ts-nocheck — ported code written for a less strict TS config
import { useState, useEffect } from "react";
import type { HardwareProfile, FactStoreStats } from "../../types/api";
import { fetchHardware, fetchFactStats, fetchModels } from "../../services/api";
import { Cpu, Activity, Workflow } from "lucide-react";

export const HardwarePanel = () => {
  const [hardware, setHardware] = useState<HardwareProfile | null>(null);
  const [stats, setStats] = useState<FactStoreStats | null>(null);
  const [selectedStage, setSelectedStage] = useState<number>(2);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [listExtraction, setListExtraction] = useState<boolean | null>(null);

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
    fetchModels()
      .then((m) => {
        if (isMounted && m) setListExtraction(m.list_extraction_enabled);
      })
      .catch(() => {});
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

  // Descriptions follow the code and the paper (Section 4); no latency figures are
  // shown because none were measured per stage for this page.
  const stageDetails = [
    {
      stage: 0,
      title: "Hardware Detection & Calibration",
      short: "Hardware",
      tech: "psutil · nvidia-smi / rocm-smi · PyTorch",
      role: "Reads CPU cores, RAM and GPU memory and picks one of five modes, each with a default model and a token ceiling between 1,024 and 4,096 (Settings → Device preset). These rules were not evaluated in the paper.",
      inputs: "Host CPU, RAM and GPU",
      outputs: "Hardware profile: mode, default model, token ceiling",
    },
    {
      stage: 1,
      title: "Coreference Resolution",
      short: "Coreference",
      tech: "fastcoref · biu-nlp/f-coref",
      role: "Replaces pronouns and other references with the entities they refer to, so that each extracted fact stands on its own.",
      inputs: "Sanitised document prose",
      outputs: "Coreference-resolved text",
    },
    {
      stage: 2,
      title: "SVOA Extraction & Structural Retention",
      short: "Extraction",
      tech: "spaCy en_core_web_lg dependency parse · HTML table/list parser",
      role: `Extracts subject–verb–object–adjunct facts with negation and a modality (asserted, attributed, conditional or hypothetical). With structural retention on, HTML tables and lists are kept in native form instead of being rewritten as sentences. Structural retention is ${
        listExtraction === null ? "unknown" : listExtraction ? "ON" : "OFF"
      } on this server (PRECIS_ENABLE_LIST_EXTRACTION).`,
      inputs: "Resolved prose (and the raw HTML for tables and lists)",
      outputs: "Typed facts; structural evidence",
    },
    {
      stage: 3,
      title: "SDH Scoring & Indexing",
      short: "Scoring",
      tech: "all-MiniLM-L6-v2 · ChromaDB (cosine HNSW)",
      role: "Scores each fact with SDH, an equally weighted sum of entity relatedness, verb informativeness, uniqueness against stored facts and adjunct density (hand-set constants, not tuned), then stores facts and structural evidence with their embeddings.",
      inputs: "Typed facts; structural evidence",
      outputs: "Persistent fact and structural stores",
    },
    {
      stage: 4,
      title: "Query-Adaptive Packing",
      short: "Packing",
      tech: "Greedy budget packer · guarded structural priority (Candidate G)",
      role: "Retrieves up to 100 facts per question part, drops hypothetical facts by default, ranks the rest by SDH × query similarity and adds them greedily while the estimated tokens stay within the ceiling. With structural retention on, matching tables and lists are packed first under a guard.",
      inputs: "Question; token ceiling",
      outputs: "Packed context and the facts used",
    },
    {
      stage: 5,
      title: "Local Generation",
      short: "Generation",
      tech: `Ollama · ${hardware.recommended_model}`,
      role: "A locally served model answers from the packed context. The grounding prompt asks it to preserve negation and not to present attributed, conditional or hypothetical claims as established; the chat app also uses the conversation and may answer from general knowledge, saying so.",
      inputs: "Packed context; question; conversation",
      outputs: "Streamed answer",
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
              <span className="text-[var(--tx-3)] text-[0.625rem]">USABLE RAM</span>
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
              <span className="text-[var(--tx-3)]">DEFAULT MODEL FOR THIS MODE:</span>
              <span className="font-bold text-[var(--tx)]">{hardware.recommended_model}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[var(--tx-3)]">TOKEN BUDGET CEILING:</span>
              <span className="font-bold text-[var(--tx)]">{hardware.token_ceiling} tokens</span>
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
            <span>PIPELINE STAGES</span>
          </div>
          <span className="text-[0.6875rem] text-[var(--tx-3)] hidden sm:inline">
            OFFLINE · LOCAL MODELS ONLY
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
                {st.short}
              </span>
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
              WHAT IT DOES
            </span>
            <p className="text-[var(--tx-2)] leading-relaxed text-[0.75rem]">{currentStage.role}</p>
          </div>
        </div>
      </div>
    </div>
  );
};
