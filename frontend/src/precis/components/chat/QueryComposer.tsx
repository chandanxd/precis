// @ts-nocheck — ported code written for a less strict TS config
import React from "react";
import { ArrowUp, Square, RotateCcw } from "lucide-react";
import type { Fact } from "../../types/api";

interface QueryComposerProps {
  inputValue: string;
  setInputValue: (val: string) => void;
  isStreaming: boolean;
  onSend: (text?: string) => void;
  onStop: () => void;
  onClear: () => void;
  onOpenShortcuts: () => void;
  selectedFact: Fact | null;
  onClearSelectedFact: () => void;
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
  modKeyLabel: string;
}

export const QueryComposer = ({
  inputValue,
  setInputValue,
  isStreaming,
  onSend,
  onStop,
  onClear,
  onOpenShortcuts,
  selectedFact,
  onClearSelectedFact,
  textareaRef,
  modKeyLabel,
}: QueryComposerProps) => {
  const sampleQueries = [
    "What did the government approve and what was excluded?",
    "Does the opposition support any part of the bill?",
    "What are the economic disruption risks mentioned?",
  ];

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter") {
      if (e.ctrlKey || e.metaKey) {
        e.preventDefault();
        onSend();
      } else if (e.shiftKey) {
        // Shift + Enter inserts newline (browser native)
        return;
      } else {
        e.preventDefault();
        onSend();
      }
    } else if (e.key === "Escape") {
      if (selectedFact) {
        e.preventDefault();
        onClearSelectedFact();
      } else {
        e.preventDefault();
        textareaRef.current?.blur();
      }
    }
  };

  return (
    <div className="flex flex-col gap-1.5 shrink-0">
      {/* Subtle Sample Queries (only if input is empty) */}
      {!inputValue && (
        <div className="flex items-center gap-1 overflow-x-auto text-xs text-[var(--tx-4)] shrink-0 select-none font-mono py-0.5">
          <span className="shrink-0 text-[0.625rem] uppercase text-[var(--tx-4)] mr-1">Try:</span>
          {sampleQueries.map((q, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => onSend(q)}
              disabled={isStreaming}
              className="text-[0.6875rem] text-[var(--tx-3)] hover:text-[var(--accent-strong)] hover:bg-[var(--accent-soft)] px-2 py-0.5 transition-colors disabled:opacity-50 whitespace-nowrap cursor-pointer truncate max-w-[18rem]"
            >
              "{q}"
            </button>
          ))}
        </div>
      )}

      {/* Clean Query Composer Box */}
      <div className="precis-composer p-3 flex flex-col gap-1.5 shrink-0">
        <div className="flex items-end gap-2">
          <textarea
            ref={textareaRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`Ask a question... (${modKeyLabel}+K to focus)`}
            rows={2}
            disabled={isStreaming}
            className="flex-1 bg-transparent border-0 outline-none resize-none font-sans text-sm leading-relaxed text-[var(--tx)] placeholder:text-[var(--tx-4)] p-0 min-h-[3rem]"
          />

          <div className="flex items-center gap-1.5 shrink-0 pb-0.5 font-mono">
            {isStreaming ? (
              <button
                type="button"
                onClick={onStop}
                title="Stop generating"
                className="px-3 py-1.5 bg-[var(--inv-bg)] text-[var(--inv-tx)] hover:opacity-85 text-xs font-semibold flex items-center gap-1.5 transition-opacity cursor-pointer"
              >
                <Square size={10} strokeWidth={2} />
                <span>STOP</span>
              </button>
            ) : (
              <button
                type="button"
                onClick={() => onSend()}
                disabled={!inputValue.trim()}
                title="Execute query (Enter)"
                className="px-3 py-1.5 bg-[var(--inv-bg)] text-[var(--inv-tx)] disabled:opacity-30 disabled:hover:opacity-30 text-xs font-semibold flex items-center gap-1.5 transition-opacity cursor-pointer"
              >
                <ArrowUp size={12} strokeWidth={2.5} />
                <span>Query</span>
              </button>
            )}

            <button
              type="button"
              onClick={onClear}
              title="Clear conversation"
              className="p-1.5 text-[var(--tx-4)] hover:text-[var(--accent-strong)] hover:bg-[var(--bg-3)] transition-colors cursor-pointer"
            >
              <RotateCcw size={12} strokeWidth={1.5} />
            </button>
          </div>
        </div>

        <div className="flex items-center justify-between text-[0.625rem] text-[var(--tx-4)] pt-1 border-t border-[var(--bd)] select-none font-mono">
          <span>Enter to send · Shift+Enter for newline</span>
          <button
            type="button"
            onClick={onOpenShortcuts}
            className="hover:text-[var(--accent-strong)] transition-colors cursor-pointer"
          >
            Shortcuts ({modKeyLabel}+/)
          </button>
        </div>
      </div>
    </div>
  );
};
