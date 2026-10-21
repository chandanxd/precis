// @ts-nocheck — ported code written for a less strict TS config
import { useState } from "react";
import type { Fact, Modality } from "../../types/api";
import { ChevronDown, ChevronUp, FileText, Tag } from "lucide-react";

interface FactCardProps {
  fact: Fact;
  index?: number;
  isSelected?: boolean;
  isHighlighted?: boolean;
  compact?: boolean;
  onSelect?: () => void;
  onHover?: (hovering: boolean) => void;
}

export const FactCard = ({
  fact,
  index,
  isSelected = false,
  isHighlighted = false,
  compact = false,
  onSelect,
  onHover,
}: FactCardProps) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(false);
  const [showOriginalSentence, setShowOriginalSentence] = useState<boolean>(false);

  // Details are collapsed by default; click toggles expansion
  const expanded = isExpanded;

  const renderModalityBadge = (modality: Modality) => {
    switch (modality) {
      case "asserted":
        return (
          <span className="px-[0.3125rem] py-[0.0625rem] text-[0.5625rem] font-mono uppercase bg-[var(--inv-bg)] text-[var(--inv-tx)] font-bold tracking-wider">
            ASSERTED
          </span>
        );
      case "conditional":
        return (
          <span className="px-[0.3125rem] py-[0.0625rem] text-[0.5625rem] font-mono uppercase border border-[var(--tx-2)] text-[var(--tx)] font-medium">
            CONDITIONAL
          </span>
        );
      case "attributed":
        return (
          <span className="px-[0.3125rem] py-[0.0625rem] text-[0.5625rem] font-mono uppercase border border-[var(--bd-3)] text-[var(--tx-2)] font-normal">
            ATTRIBUTED
          </span>
        );
      case "hypothetical":
        return (
          <span className="px-[0.3125rem] py-[0.0625rem] text-[0.5625rem] font-mono uppercase border border-dashed border-[var(--tx-3)] text-[var(--tx-3)] italic">
            HYPOTHETICAL
          </span>
        );
    }
  };

  const adjunctEntries = Object.entries(fact.adjuncts || {});

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => {
        if (onSelect) onSelect();
        setIsExpanded((prev) => !prev);
      }}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          if (onSelect) onSelect();
          setIsExpanded((prev) => !prev);
        }
      }}
      onMouseEnter={() => onHover?.(true)}
      onMouseLeave={() => onHover?.(false)}
      onFocus={() => onHover?.(true)}
      onBlur={() => onHover?.(false)}
      className={`border p-2.5 font-mono text-xs flex flex-col gap-1.5 transition-colors cursor-pointer ${
        isSelected
          ? "border-[var(--accent)] bg-[var(--bg-3)]"
          : isHighlighted
            ? "border-[var(--accent)]/60 bg-[var(--accent-soft)]"
            : "border-[var(--bd)] bg-[var(--bg-2)] hover:border-[var(--bd-2)] hover:bg-[var(--bg-3)]"
      }`}
    >
      {/* Header: Index + Modality Badge + Negation + SDH Score + Expand Icon */}
      <div className="flex items-center justify-between gap-1.5 border-b border-[var(--bd)] pb-1 select-none">
        <div className="flex items-center gap-1.5 flex-wrap">
          {index !== undefined && (
            <span className="text-[0.625rem] text-[var(--tx-4)] font-mono">
              {index < 9 ? `0${index + 1}` : index + 1}
            </span>
          )}
          {renderModalityBadge(fact.modality)}
          {fact.negated && (
            <span className="px-1 text-[0.5625rem] font-mono uppercase bg-[var(--inv-bg)] text-[var(--inv-tx)] font-semibold">
              ¬NEG
            </span>
          )}
          {fact.disjunctive && (
            <span className="px-1 text-[0.5625rem] font-mono uppercase text-[var(--tx-4)]">OR</span>
          )}
        </div>

        <div className="flex items-center gap-1 text-[0.625rem] text-[var(--tx-4)] shrink-0">
          <span>{fact.sdh_score.toFixed(2)}</span>
          <span>{expanded ? <ChevronUp size={11} /> : <ChevronDown size={11} />}</span>
        </div>
      </div>

      {/* SVOA Core Triplet: SUBJECT → PREDICATE → OBJECT */}
      <div className="flex items-baseline gap-1.5 flex-wrap text-xs leading-snug">
        <span className="font-medium text-[var(--tx)]">{fact.subject}</span>

        <span className="text-[var(--tx-4)] text-[0.625rem]">
          {fact.negated ? `¬ ${fact.verb}` : fact.verb}
        </span>

        <span className="text-[var(--tx-2)]">{fact.object}</span>
      </div>

      {/* Expanded Details State */}
      {expanded && !compact && (
        <div className="flex flex-col gap-1.5 pt-1.5 border-t border-[var(--bd)] text-xs">
          {/* Attribution */}
          {fact.attributed_to && (
            <div className="flex items-center gap-1.5 text-[0.6875rem]">
              <span className="text-[var(--tx-4)] text-[0.625rem]">Source:</span>
              <span className="text-[var(--tx-2)]">{fact.attributed_to}</span>
            </div>
          )}
          {/* Adjuncts */}
          {adjunctEntries.length > 0 && (
            <div className="flex items-center gap-1.5 flex-wrap text-[0.625rem]">
              <Tag size={10} className="text-[var(--tx-4)] shrink-0" />
              {adjunctEntries.map(([k, v]) => (
                <span
                  key={k}
                  className="bg-[var(--bg)] px-1.5 py-0.5 border border-[var(--bd)] text-[var(--tx-3)]"
                >
                  {k}: {Array.isArray(v) ? v.join(", ") : v}
                </span>
              ))}
            </div>
          )}

          {/* Source Information */}
          {fact.source_doc && (
            <div className="flex flex-col gap-1 pt-1">
              <div className="flex items-center justify-between text-[0.625rem] text-[var(--tx-4)]">
                <span className="flex items-center gap-1 truncate max-w-[12rem]">
                  <FileText size={9} />
                  <span>{fact.source_doc}</span>
                </span>

                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowOriginalSentence((prev) => !prev);
                  }}
                  className="text-[var(--accent-strong)] hover:underline cursor-pointer"
                >
                  {showOriginalSentence ? "Hide sentence" : "View sentence"}
                </button>
              </div>

              {showOriginalSentence && (
                <div className="bg-[var(--bg)] p-1.5 text-xs text-[var(--tx-2)] italic font-sans border border-[var(--bd)]">
                  "{fact.original_sentence || `${fact.subject} ${fact.verb} ${fact.object}.`}"
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
