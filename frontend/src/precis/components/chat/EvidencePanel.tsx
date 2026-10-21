// @ts-nocheck — ported code written for a less strict TS config
import type { Fact } from "../../types/api";
import { Layers, ChevronDown, ArrowRight } from "lucide-react";

interface EvidencePanelProps {
  messageId: string;
  facts: Fact[];
  isExpanded: boolean;
  onToggle: () => void;
  isSelected: boolean;
  displayedSelectedFact: Fact | null;
  onSelectFact: (fact: Fact | null) => void;
  hoveredFactIndex: number | null;
  onHoverFact: (index: number | null) => void;
  premiseRowRefs: React.MutableRefObject<Record<string, HTMLButtonElement | null>>;
  evidenceHeaderRef: (el: HTMLButtonElement | null) => void;
}

export const EvidencePanel = ({
  messageId,
  facts,
  isExpanded,
  onToggle,
  isSelected,
  displayedSelectedFact,
  onSelectFact,
  hoveredFactIndex,
  onHoverFact,
  premiseRowRefs,
  evidenceHeaderRef,
}: EvidencePanelProps) => {
  if (!facts || facts.length === 0) return null;

  return (
    <div className="flex flex-col gap-[0.375rem] pt-[0.25rem]">
      {/* Collapsible Header */}
      <button
        ref={evidenceHeaderRef}
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          onToggle();
        }}
        onKeyDown={(e) => {
          if (e.key === " " || e.key === "Enter") {
            e.preventDefault();
            onToggle();
          } else if (e.key === "ArrowDown" && isExpanded && facts.length > 0) {
            e.preventDefault();
            premiseRowRefs.current[`${messageId}-0`]?.focus();
          }
        }}
        aria-expanded={isExpanded}
        className="w-full flex items-center justify-between text-xs text-[var(--tx-3)] hover:text-[var(--tx)] select-none pb-0.5 cursor-pointer group transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--tx)] font-mono"
      >
        <span className="flex items-center gap-1.5">
          <Layers
            size={11}
            strokeWidth={1.5}
            className="text-[var(--tx-3)] group-hover:text-[var(--tx)]"
          />
          <span>Supporting Evidence ({facts.length})</span>
          <span className="text-[var(--tx-4)] group-hover:text-[var(--tx-2)] inline-flex items-center">
            <ChevronDown
              size={11}
              className={`transition-transform duration-200 ${isExpanded ? "rotate-180" : ""}`}
            />
          </span>
        </span>

        <div className="flex items-center gap-2">
          {displayedSelectedFact && isSelected && (
            <span
              role="button"
              tabIndex={0}
              onClick={(e) => {
                e.stopPropagation();
                onSelectFact(null);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.stopPropagation();
                  e.preventDefault();
                  onSelectFact(null);
                }
              }}
              className="text-[0.625rem] text-[var(--tx-4)] hover:text-[var(--tx)] font-mono transition-colors cursor-pointer"
            >
              clear selection
            </span>
          )}
          <span className="text-[0.625rem] text-[var(--tx-4)] group-hover:text-[var(--tx-3)] font-mono">
            {isExpanded ? "collapse" : "expand"}
          </span>
        </div>
      </button>

      {/* Premise Rows with Smooth CSS Grid Accordion Transition */}
      <div
        className={`grid transition-[grid-template-rows,opacity] duration-200 ease-out ${
          isExpanded
            ? "grid-rows-[1fr] opacity-100"
            : "grid-rows-[0fr] opacity-0 pointer-events-none"
        }`}
      >
        <div className="overflow-hidden">
          <div className="flex flex-col gap-0.5 bg-[var(--bg-2)] p-1 border border-[var(--bd)]">
            {facts.map((fact, idx) => {
              const isFactSelected = displayedSelectedFact === fact && isSelected;
              const isFactHovered = isSelected && hoveredFactIndex === idx;

              return (
                <button
                  key={idx}
                  ref={(el) => {
                    premiseRowRefs.current[`${messageId}-${idx}`] = el;
                  }}
                  type="button"
                  onMouseEnter={() => {
                    if (isSelected) onHoverFact(idx);
                  }}
                  onMouseLeave={() => {
                    onHoverFact(null);
                  }}
                  onFocus={() => {
                    onHoverFact(idx);
                  }}
                  onBlur={() => {
                    onHoverFact(null);
                  }}
                  onClick={(e) => {
                    e.stopPropagation();
                    if (displayedSelectedFact === fact) {
                      onSelectFact(null);
                    } else {
                      onSelectFact(fact);
                    }
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      if (displayedSelectedFact === fact) {
                        onSelectFact(null);
                      } else {
                        onSelectFact(fact);
                      }
                    } else if (e.key === "ArrowDown") {
                      e.preventDefault();
                      if (idx < facts.length - 1) {
                        premiseRowRefs.current[`${messageId}-${idx + 1}`]?.focus();
                      }
                    } else if (e.key === "ArrowUp") {
                      e.preventDefault();
                      if (idx > 0) {
                        premiseRowRefs.current[`${messageId}-${idx - 1}`]?.focus();
                      }
                    } else if (e.key === "Escape") {
                      e.preventDefault();
                      onSelectFact(null);
                    }
                  }}
                  className={`w-full text-left py-1.5 px-2 flex items-center justify-between gap-2 text-xs font-mono transition-colors group cursor-pointer focus-visible:outline-none ${
                    isFactSelected
                      ? "bg-[var(--bg-3)] border-l-2 border-l-[var(--accent)] text-[var(--tx)] font-medium pl-1.5"
                      : isFactHovered
                        ? "bg-[var(--bg-3)]/80 border-l-2 border-l-[var(--accent)]/50 text-[var(--tx)] pl-1.5"
                        : "border-l-2 border-l-transparent text-[var(--tx-2)] hover:bg-[var(--bg-3)]/40 hover:text-[var(--tx)]"
                  }`}
                >
                  {/* Format: [01] modality subject → verb → object */}
                  <div className="flex items-center gap-2 truncate flex-1">
                    <span className="text-[0.625rem] text-[var(--tx-4)] shrink-0">{idx + 1}</span>

                    <span
                      className={`px-1 py-0.2 text-[0.5625rem] uppercase shrink-0 ${
                        fact.modality === "asserted"
                          ? "bg-[var(--inv-bg)] text-[var(--inv-tx)] font-medium"
                          : fact.modality === "conditional"
                            ? "border border-[var(--tx-3)] text-[var(--tx-2)]"
                            : "text-[var(--tx-4)] border border-[var(--bd)]"
                      }`}
                    >
                      {fact.modality}
                    </span>

                    {fact.negated && (
                      <span className="text-[0.5625rem] text-[var(--tx-2)] uppercase font-semibold shrink-0">
                        ¬NEG
                      </span>
                    )}

                    <span className="font-medium text-[var(--tx)] shrink-0">{fact.subject}</span>
                    <span className="text-[var(--tx-4)] text-[0.625rem] shrink-0">
                      {fact.negated ? `¬ ${fact.verb}` : fact.verb}
                    </span>
                    <span className="text-[var(--tx-2)] truncate">{fact.object}</span>
                  </div>

                  {/* SDH Score */}
                  <div className="flex items-center gap-1 shrink-0 text-[0.625rem] text-[var(--tx-4)] group-hover:text-[var(--accent-strong)] font-mono">
                    <span>{fact.sdh_score.toFixed(2)}</span>
                    <ArrowRight
                      size={9}
                      strokeWidth={1.5}
                      className="opacity-0 group-hover:opacity-100 transition-opacity"
                    />
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
