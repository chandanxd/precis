// @ts-nocheck — ported code written for a less strict TS config
import { useState } from "react";
import type { PipelineEvent, StageIndex } from "../../types/api";
import { STAGE_NAMES } from "../../types/api";
import {
  Check,
  Loader2,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Cpu,
  GitBranch,
  FileSpreadsheet,
  Scale,
  PackageCheck,
  Bot,
} from "lucide-react";

interface PipelineTrackerProps {
  events: PipelineEvent[];
  isStreaming?: boolean;
}

const STAGE_ICONS: Record<StageIndex, React.ReactNode> = {
  0: <Cpu size={12} strokeWidth={1.5} />,
  1: <GitBranch size={12} strokeWidth={1.5} />,
  2: <FileSpreadsheet size={12} strokeWidth={1.5} />,
  3: <Scale size={12} strokeWidth={1.5} />,
  4: <PackageCheck size={12} strokeWidth={1.5} />,
  5: <Bot size={12} strokeWidth={1.5} />,
};

export const PipelineTracker = ({ events, isStreaming = false }: PipelineTrackerProps) => {
  const [expanded, setExpanded] = useState<boolean>(true);

  const stages: StageIndex[] = [0, 1, 2, 3, 4, 5];

  // Find the latest event for each stage
  const eventMap = new Map<StageIndex, PipelineEvent>();
  events.forEach((ev) => {
    eventMap.set(ev.stage, ev);
  });

  const activeStage = events.length > 0 ? events[events.length - 1] : null;

  return (
    <div className="border border-[var(--bd)] bg-[var(--bg-2)] font-mono text-xs mb-2">
      {/* Header summary bar */}
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-[var(--bd)] select-none">
        <div className="flex items-center gap-2">
          <span className="text-[var(--tx)] font-medium text-xs">Pipeline</span>
          {isStreaming && (
            <span className="flex items-center gap-1.5 text-[0.625rem] text-[var(--tx-3)]">
              <Loader2 size={10} className="animate-spin" />
              <span>Stage 0{activeStage?.stage ?? 0} active</span>
            </span>
          )}
        </div>

        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1 text-[0.625rem] text-[var(--tx-4)] hover:text-[var(--tx-2)] transition-colors cursor-pointer"
        >
          <span>{expanded ? "Hide" : "Show"}</span>
          {expanded ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
        </button>
      </div>

      {/* Stepper Flow Bar */}
      <div className="grid grid-cols-2 md:grid-cols-6 divide-x divide-y md:divide-y-0 divide-[var(--bd)] border-b border-[var(--bd)]">
        {stages.map((stIdx) => {
          const event = eventMap.get(stIdx);
          const isComplete = event?.status === "complete";
          const isRunning = event?.status === "running";
          const isError = event?.status === "error";

          return (
            <div
              key={stIdx}
              className={`p-[0.5rem] flex flex-col gap-[0.25rem] transition-colors ${
                isRunning
                  ? "bg-[var(--bg-3)] border-b-2 border-b-[var(--tx)]"
                  : isComplete
                    ? "bg-[var(--bg-2)]"
                    : "bg-[var(--bg)] opacity-50"
              }`}
            >
              <div className="flex items-center justify-between text-[0.6875rem]">
                <span className="flex items-center gap-[0.25rem] text-[var(--tx-3)]">
                  {STAGE_ICONS[stIdx]}
                  STAGE 0{stIdx}
                </span>

                <span className="shrink-0">
                  {isComplete && <Check size={12} strokeWidth={2} className="text-[var(--tx)]" />}
                  {isRunning && <Loader2 size={12} className="animate-spin text-[var(--tx)]" />}
                  {isError && (
                    <AlertCircle size={12} strokeWidth={2} className="text-[var(--tx)]" />
                  )}
                  {!event && <span className="text-[var(--tx-4)]">--</span>}
                </span>
              </div>

              <div className="text-[0.6875rem] font-semibold text-[var(--tx)] truncate">
                {STAGE_NAMES[stIdx]}
              </div>

              {event?.count !== undefined && event.count > 0 && (
                <div className="text-[0.625rem] text-[var(--tx-2)]">
                  {event.count.toLocaleString()} ITEMS
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Detailed Log Console when expanded */}
      {expanded && (
        <div className="p-[0.75rem] bg-[var(--bg)] flex flex-col gap-[0.375rem] max-h-[12rem] overflow-y-auto border-t border-[var(--bd)] text-[0.6875rem]">
          {events.length === 0 ? (
            <div className="text-[var(--tx-3)] py-[0.25rem] italic">
              Pipeline awaiting query input.
            </div>
          ) : (
            events.map((ev, i) => (
              <div key={i} className="flex items-start gap-[0.5rem] leading-relaxed">
                <span className="text-[var(--tx-3)] shrink-0 font-mono">[S{ev.stage}]</span>
                <span className="text-[var(--tx-2)] uppercase shrink-0 w-[9rem]">
                  {ev.stage_name}:
                </span>
                <span className="text-[var(--tx)] flex-1 break-words">{ev.detail}</span>
                {ev.error && (
                  <span className="text-[var(--inv-tx)] bg-[var(--inv-bg)] px-[0.25rem] py-[0.0625rem] shrink-0">
                    [ERROR: {ev.error}]
                  </span>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};
