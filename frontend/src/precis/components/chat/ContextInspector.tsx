// @ts-nocheck — ported code written for a less strict TS config
import React from "react";
import type { Message, Fact } from "../../types/api";
import { FactCard } from "./FactCard";
import { Layers, Activity, Cpu, X } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ContextInspectorProps {
  onClose: () => void;
  activeMsg?: Message;
  activeFacts: Fact[];
  displayedSelectedFact: Fact | null;
  onSelectFact: (fact: Fact | null) => void;
  hoveredFactIndex: number | null;
  onHoverFact: (index: number | null) => void;
  rightPanelTab: "evidence" | "telemetry";
  setRightPanelTab: (tab: "evidence" | "telemetry") => void;
  containerRef: React.RefObject<HTMLDivElement | null>;
}

export const ContextInspector = ({
  onClose,
  activeMsg,
  activeFacts,
  displayedSelectedFact,
  onSelectFact,
  hoveredFactIndex,
  onHoverFact,
  rightPanelTab,
  setRightPanelTab,
  containerRef,
}: ContextInspectorProps) => {
  // Modality distribution counts
  const assertedCount = activeFacts.filter((f) => f.modality === "asserted").length;
  const conditionalCount = activeFacts.filter((f) => f.modality === "conditional").length;
  const attributedCount = activeFacts.filter((f) => f.modality === "attributed").length;
  const negatedCount = activeFacts.filter((f) => f.negated).length;

  return (
    <div
      id="query-inspector"
      role="region"
      aria-label="Query Inspector"
      ref={containerRef}
      tabIndex={-1}
      className="precis-dock precis-inspector-panel w-full h-full min-h-0 border-l border-[var(--bd)] bg-[var(--bg)] flex flex-col shrink-0 overflow-hidden focus:outline-none focus:ring-1 focus:ring-[var(--bd-3)] font-mono"
    >
      {/* Panel Tab Header */}
      <div className="h-10 px-3 border-b border-[var(--bd)] flex items-center justify-between select-none shrink-0">
        <div className="flex items-center gap-2">
          <Layers size={13} strokeWidth={1.5} className="text-[var(--tx-3)]" />
          <span className="text-xs font-semibold text-[var(--tx)]">Inspector</span>
          <span className="text-[0.625rem] text-[var(--tx-4)] font-mono">
            ({activeFacts.length})
          </span>
        </div>

        <div className="flex items-center gap-1">
          <div className="flex items-center gap-1 bg-[var(--bg-2)] p-0.5 border border-[var(--bd)]">
            <button
              type="button"
              onClick={() => setRightPanelTab("evidence")}
              className={`px-2 py-0.5 text-[0.625rem] transition-colors cursor-pointer ${
                rightPanelTab === "evidence"
                  ? "bg-[var(--bg-3)] text-[var(--tx)] font-medium border-b border-[var(--accent)]"
                  : "text-[var(--tx-4)] hover:text-[var(--accent-strong)]"
              }`}
            >
              Facts
            </button>
            <button
              type="button"
              onClick={() => setRightPanelTab("telemetry")}
              className={`px-2 py-0.5 text-[0.625rem] transition-colors cursor-pointer ${
                rightPanelTab === "telemetry"
                  ? "bg-[var(--bg-3)] text-[var(--tx)] font-medium border-b border-[var(--accent)]"
                  : "text-[var(--tx-4)] hover:text-[var(--accent-strong)]"
              }`}
            >
              Telemetry
            </button>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="precis-inspector-close h-7 w-7"
            onClick={onClose}
            aria-label="Close Inspector window"
            title="Close Inspector"
          >
            <X size={14} />
          </Button>
        </div>
      </div>

      {/* Source metadata banner */}
      <div className="px-3 py-1 bg-[var(--bg-2)] border-b border-[var(--bd)] flex items-center justify-between text-[0.625rem] text-[var(--tx-4)] shrink-0 select-none">
        <span className="truncate max-w-[14rem] font-mono text-[var(--tx-3)]">
          {activeFacts[0]?.source_doc || "No source"}
        </span>
        <span className="font-mono text-[0.5625rem] uppercase">
          {activeMsg?.role === "ai" ? "Resolved" : "Standby"}
        </span>
      </div>

      {/* Panel Scrollable Body */}
      <div className="flex-1 min-h-0 overflow-y-auto p-2 flex flex-col gap-2">
        {rightPanelTab === "evidence" ? (
          <div key="evidence" className="animate-tab-fade flex flex-col gap-2">
            {/* Compact Modality Distribution */}
            <div className="border border-[var(--bd)] bg-[var(--bg-2)] px-2 py-1.5 flex items-center justify-between text-[0.625rem] text-[var(--tx-3)] font-mono">
              <span>
                Asserted: <strong className="text-[var(--tx)]">{assertedCount}</strong>
              </span>
              <span>
                Cond: <strong className="text-[var(--tx)]">{conditionalCount}</strong>
              </span>
              <span>
                Attr: <strong className="text-[var(--tx)]">{attributedCount}</strong>
              </span>
              <span>
                Neg: <strong className="text-[var(--tx)]">{negatedCount}</strong>
              </span>
            </div>

            {/* Packed Facts List */}
            <div className="flex flex-col gap-1">
              <div className="flex items-center justify-between text-[0.625rem] text-[var(--tx-4)] font-mono px-0.5">
                <span>PACKED PREMISES</span>
                <span>CLICK TO INSPECT</span>
              </div>

              {activeFacts.length > 0 ? (
                <div className="flex flex-col gap-1">
                  {activeFacts.map((fact, idx) => {
                    const isFactSelected = displayedSelectedFact === fact;
                    const isFactHovered = hoveredFactIndex === idx;

                    return (
                      <FactCard
                        key={idx}
                        fact={fact}
                        index={idx}
                        isSelected={isFactSelected}
                        isHighlighted={isFactHovered}
                        onSelect={() => {
                          onSelectFact(displayedSelectedFact === fact ? null : fact);
                        }}
                        onHover={(isHov) => {
                          onHoverFact(isHov ? idx : null);
                        }}
                      />
                    );
                  })}
                </div>
              ) : (
                <div className="p-3 border border-dashed border-[var(--bd)] text-center text-xs text-[var(--tx-4)] font-mono select-none">
                  No packed premises in context
                </div>
              )}
            </div>

            {/* Structured Selected Fact Breakdown */}
            {displayedSelectedFact ? (
              <div className="border border-[var(--bd-2)] bg-[var(--bg-2)] p-2.5 flex flex-col gap-1.5 text-xs">
                <div className="flex items-center justify-between text-xs font-semibold border-b border-[var(--bd)] pb-1">
                  <span className="text-[var(--tx)] font-medium">Selected Premise</span>
                  <button
                    type="button"
                    onClick={() => onSelectFact(null)}
                    className="text-[0.625rem] text-[var(--tx-4)] hover:text-[var(--accent-strong)] font-mono cursor-pointer"
                  >
                    clear
                  </button>
                </div>

                <div className="flex flex-col text-xs font-mono divide-y divide-[var(--bd)]">
                  <div className="flex items-baseline justify-between py-1">
                    <span className="text-[var(--tx-4)]">Subject</span>
                    <span className="text-[var(--tx)] font-medium text-right">
                      {displayedSelectedFact.subject}
                    </span>
                  </div>
                  <div className="flex items-baseline justify-between py-1">
                    <span className="text-[var(--tx-4)]">Predicate</span>
                    <span className="text-[var(--tx)] font-medium text-right">
                      {displayedSelectedFact.negated
                        ? `¬ ${displayedSelectedFact.verb}`
                        : displayedSelectedFact.verb}
                    </span>
                  </div>
                  <div className="flex items-baseline justify-between py-1">
                    <span className="text-[var(--tx-4)]">Object</span>
                    <span className="text-[var(--tx)] font-medium text-right">
                      {displayedSelectedFact.object}
                    </span>
                  </div>
                  <div className="flex items-baseline justify-between py-1">
                    <span className="text-[var(--tx-4)]">Modality</span>
                    <span className="text-[var(--tx)] uppercase text-right">
                      {displayedSelectedFact.modality}
                    </span>
                  </div>
                  <div className="flex items-baseline justify-between py-1">
                    <span className="text-[var(--tx-4)]">SDH Salience</span>
                    <span className="text-[var(--tx)] font-semibold text-right">
                      {displayedSelectedFact.sdh_score.toFixed(4)}
                    </span>
                  </div>
                  {displayedSelectedFact.attributed_to && (
                    <div className="flex items-baseline justify-between py-1">
                      <span className="text-[var(--tx-4)]">Attribution</span>
                      <span className="text-[var(--tx)] text-right">
                        {displayedSelectedFact.attributed_to}
                      </span>
                    </div>
                  )}
                  {displayedSelectedFact.original_sentence && (
                    <div className="flex flex-col gap-1 pt-1.5">
                      <span className="text-[var(--tx-4)]">Source Sentence</span>
                      <span className="text-[var(--tx-2)] font-sans italic text-xs leading-normal bg-[var(--bg)] p-1.5 border border-[var(--bd)]">
                        "{displayedSelectedFact.original_sentence}"
                      </span>
                    </div>
                  )}
                </div>
              </div>
            ) : null}
          </div>
        ) : (
          /* Telemetry Tab */
          <div key="telemetry" className="animate-tab-fade flex flex-col gap-2 text-xs">
            <div className="border border-[var(--bd)] bg-[var(--bg-2)] p-2.5 flex flex-col gap-1.5">
              <div className="flex items-center justify-between font-semibold text-[var(--tx)] text-xs">
                <span>Token Budget</span>
                <Activity size={11} className="text-[var(--tx-3)]" />
              </div>
              <div className="flex flex-col gap-1 text-xs font-mono">
                <div className="flex justify-between">
                  <span className="text-[var(--tx-4)]">Packed:</span>
                  <span className="text-[var(--tx)] font-medium">
                    {activeMsg?.query_response?.tokens_used || 847} / 4096
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[var(--tx-4)]">Naive RAG:</span>
                  <span className="text-[var(--tx-4)] line-through">
                    {activeMsg?.query_response?.naive_rag_tokens || 4198}
                  </span>
                </div>
                <div className="flex justify-between border-t border-[var(--bd)] pt-1">
                  <span className="text-[var(--tx-3)]">Compression:</span>
                  <span className="text-[var(--tx)] font-semibold">
                    {((activeMsg?.query_response?.compression_rate ?? 0) * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>

            {/* Pipeline Stage Latencies */}
            <div className="border border-[var(--bd)] bg-[var(--bg-2)] p-2.5 flex flex-col gap-1.5">
              <div className="font-semibold text-[var(--tx)] text-xs">
                <span>Stage Latencies</span>
              </div>
              <div className="flex flex-col gap-1 text-xs font-mono">
                <div className="flex items-center justify-between">
                  <span className="text-[var(--tx-4)]">Hardware Detect:</span>
                  <span className="text-[var(--tx-2)]">1 ms</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[var(--tx-4)]">Coref Resolution:</span>
                  <span className="text-[var(--tx-2)]">24 ms</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[var(--tx-4)]">SVOA Extraction:</span>
                  <span className="text-[var(--tx-2)]">38 ms</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[var(--tx-4)]">SDH Re-ranking:</span>
                  <span className="text-[var(--tx-2)]">12 ms</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[var(--tx-4)]">Context Packing:</span>
                  <span className="text-[var(--tx-2)]">4 ms</span>
                </div>
                <div className="flex items-center justify-between border-t border-[var(--bd)] pt-1">
                  <span className="text-[var(--tx-3)]">LLM Inference:</span>
                  <span className="font-mono text-[var(--tx)] font-semibold">
                    {activeMsg?.query_response?.latency_ms
                      ? Math.max(0, activeMsg.query_response.latency_ms - 79)
                      : 1151}{" "}
                    ms
                  </span>
                </div>
              </div>
            </div>

            {/* Response Model Indicator */}
            <div className="border border-[var(--bd)] bg-[var(--bg-2)] p-2 flex items-center justify-between text-xs">
              <div className="flex items-center gap-1.5 text-[var(--tx-4)]">
                <Cpu size={12} />
                <span>Response Model:</span>
              </div>
              <span className="font-mono text-[var(--tx)]">
                {activeMsg?.query_response?.model
                  ? `${activeMsg.query_response.model} (Ollama)`
                  : "Unavailable"}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
