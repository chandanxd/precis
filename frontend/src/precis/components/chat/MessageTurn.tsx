// @ts-nocheck — ported code written for a less strict TS config
import type { Message, PipelineEvent, Fact } from "../../types/api";
import { EvidencePanel } from "./EvidencePanel";
import { PipelineTracker } from "./PipelineTracker";
import { MarkdownContent } from "./MarkdownContent";
import { User, Bot, Clock, Zap, Copy, Check, RefreshCw, Activity } from "lucide-react";

function splitIntoSentences(text: string): string[] {
  if (!text) return [];
  const matches = text.match(/[^.!?]+[.!?]+(\s|$)|[^.!?]+$/g);
  return matches ? matches.map((s) => s.trim()).filter(Boolean) : [text];
}

function matchSentenceToFact(
  sentence: string,
  facts: Fact[],
): { fact: Fact; factIndex: number } | null {
  if (!facts || facts.length === 0) return null;
  const lower = sentence.toLowerCase();

  for (let i = 0; i < facts.length; i++) {
    const f = facts[i];
    const sMatch = lower.includes(f.subject.toLowerCase());
    const oMatch = lower.includes(f.object.toLowerCase());
    const vMatch = lower.includes(f.verb.toLowerCase());
    const attrMatch = f.attributed_to && lower.includes(f.attributed_to.toLowerCase());

    if ((sMatch && oMatch) || (sMatch && vMatch) || (oMatch && vMatch) || attrMatch) {
      return { fact: f, factIndex: i };
    }
  }

  for (let i = 0; i < facts.length; i++) {
    const f = facts[i];
    if (lower.includes(f.subject.toLowerCase()) || lower.includes(f.object.toLowerCase())) {
      return { fact: f, factIndex: i };
    }
  }
  return null;
}

interface MessageTurnProps {
  userMsg?: Message;
  aiMsg?: Message;
  isStreamingTurn?: boolean;
  streamingText?: string;
  currentPipelineEvents?: PipelineEvent[];
  isSelected: boolean;
  onSelectMessage: () => void;
  displayedSelectedFact: Fact | null;
  onSelectFact: (fact: Fact | null) => void;
  hoveredFactIndex: number | null;
  onHoverFact: (index: number | null) => void;
  hoveredSentenceIndex: number | null;
  onHoverSentence: (index: number | null) => void;
  copiedMsgId: string | null;
  onCopyAnswer: (text: string, msgId: string) => void;
  onRegenerate: (msgId: string) => void;
  isEvidenceExpanded: boolean;
  onToggleEvidence: () => void;
  premiseRowRefs: React.MutableRefObject<Record<string, HTMLButtonElement | null>>;
  evidenceHeaderRef: (el: HTMLButtonElement | null) => void;
}

export const MessageTurn = ({
  userMsg,
  aiMsg,
  isStreamingTurn = false,
  streamingText = "",
  currentPipelineEvents = [],
  isSelected,
  onSelectMessage,
  displayedSelectedFact,
  onSelectFact,
  hoveredFactIndex,
  onHoverFact,
  hoveredSentenceIndex,
  onHoverSentence,
  copiedMsgId,
  onCopyAnswer,
  onRegenerate,
  isEvidenceExpanded,
  onToggleEvidence,
  premiseRowRefs,
  evidenceHeaderRef,
}: MessageTurnProps) => {
  return (
    <section
      onClick={onSelectMessage}
      className={`precis-turn flex flex-col gap-4 cursor-pointer select-text animate-turn-entrance ${isSelected ? "is-selected" : ""}`}
    >
      {/* User Message Block */}
      {userMsg && (
        <div className="precis-user-bubble flex flex-col gap-1">
          <div className="flex items-center justify-between text-xs text-[var(--tx-3)] font-mono">
            <div className="flex items-center gap-1.5 font-medium text-[var(--tx-2)]">
              <User size={12} strokeWidth={1.5} />
              <span>You</span>
            </div>
            <span className="text-[0.625rem] text-[var(--tx-4)] font-mono">
              {new Date(userMsg.timestamp).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
          </div>

          {/* User Prompt: Prose in font-sans */}
          <div className="font-sans text-[0.9375rem] leading-relaxed text-[var(--tx)] font-normal">
            {userMsg.content}
          </div>
        </div>
      )}

      {/* AI Answer Block */}
      {aiMsg ? (
        (() => {
          const facts = aiMsg.query_response?.facts_used || [];
          const answerSentences = splitIntoSentences(aiMsg.query_response?.answer || aiMsg.content);

          return (
            <article className="precis-ai-card flex flex-col gap-2">
              {/* Answer Header Bar */}
              <div className="flex items-center justify-between text-xs text-[var(--tx-3)] font-mono">
                <div className="flex items-center gap-1.5 font-semibold text-[var(--tx)]">
                  <Bot size={13} strokeWidth={2} />
                  <span>Précis</span>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onCopyAnswer(aiMsg.query_response?.answer || aiMsg.content, aiMsg.id);
                    }}
                    title="Copy response (Ctrl/Cmd + Shift + C)"
                    className="text-[var(--tx-4)] hover:text-[var(--accent-strong)] p-0.5 transition-colors cursor-pointer"
                  >
                    {copiedMsgId === aiMsg.id ? (
                      <Check size={12} className="text-[var(--tx)]" />
                    ) : (
                      <Copy size={12} strokeWidth={1.5} />
                    )}
                  </button>

                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onRegenerate(aiMsg.id);
                    }}
                    title="Regenerate response from active store"
                    className="text-[var(--tx-4)] hover:text-[var(--accent-strong)] p-0.5 transition-colors cursor-pointer"
                  >
                    <RefreshCw size={12} strokeWidth={1.5} />
                  </button>

                  <span className="text-[0.625rem] text-[var(--tx-4)] font-mono">
                    {new Date(aiMsg.timestamp).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </div>
              </div>

              {/* Answer Prose Content: Markdown-rendered typography */}
              <MarkdownContent
                content={aiMsg.query_response?.answer || aiMsg.content}
                className="font-sans text-[0.9375rem] sm:text-[1rem]"
              />

              {/* Response Telemetry Metrics Bar (Decluttered Minimal Line) */}
              {aiMsg.query_response && (
                <div className="flex items-center gap-2 text-[0.625rem] text-[var(--tx-4)] font-mono pt-1">
                  {aiMsg.query_response.answer_source === "general" && (
                    <>
                      <span className="text-[var(--tx-3)]">general knowledge</span>
                      <span>·</span>
                    </>
                  )}
                  {aiMsg.query_response.answer_source === "document" && (
                    <>
                      <span className="text-[var(--tx-3)]">from documents</span>
                      <span>·</span>
                    </>
                  )}
                  <span className="text-[var(--tx-3)]">
                    {aiMsg.query_response.inference_tokens ?? aiMsg.query_response.tokens_used} tok
                  </span>
                  {aiMsg.query_response.compression_rate > 0 && (
                    <>
                      <span>·</span>
                      <span className="flex items-center gap-1">
                        <Zap size={9} />
                        {(aiMsg.query_response.compression_rate * 100).toFixed(1)}% comp
                      </span>
                    </>
                  )}
                  <span>·</span>
                  <span className="flex items-center gap-1">
                    <Clock size={9} />
                    {aiMsg.query_response.latency_ms}ms
                  </span>
                </div>
              )}

              {/* Supporting Evidence Panel */}
              {facts.length > 0 && (
                <EvidencePanel
                  messageId={aiMsg.id}
                  facts={facts}
                  isExpanded={isEvidenceExpanded}
                  onToggle={onToggleEvidence}
                  isSelected={isSelected}
                  displayedSelectedFact={displayedSelectedFact}
                  onSelectFact={onSelectFact}
                  hoveredFactIndex={hoveredFactIndex}
                  onHoverFact={onHoverFact}
                  premiseRowRefs={premiseRowRefs}
                  evidenceHeaderRef={evidenceHeaderRef}
                />
              )}

              {/* Collapsible Pipeline Execution Footnote */}
              {aiMsg.pipeline_events && aiMsg.pipeline_events.length > 0 && (
                <details className="text-[0.625rem] text-[var(--tx-4)] font-mono pt-0.5">
                  <summary className="cursor-pointer hover:text-[var(--tx-2)] select-none flex items-center gap-1.5">
                    <Activity size={10} strokeWidth={1.5} />
                    <span>
                      Pipeline trace (6 stages · {aiMsg.query_response?.latency_ms || 0}ms)
                    </span>
                  </summary>
                  <div className="mt-1.5 pl-3 border-l border-[var(--bd)] flex flex-col gap-1 py-1 text-[var(--tx-3)]">
                    {aiMsg.pipeline_events.map((ev, i) => (
                      <div key={i} className="flex items-center justify-between text-[0.625rem]">
                        <span className="font-mono text-[var(--tx-4)]">
                          [0{ev.stage}] {ev.stage_name}
                        </span>
                        <span className="text-[var(--tx-2)]">{ev.detail}</span>
                      </div>
                    ))}
                  </div>
                </details>
              )}
            </article>
          );
        })()
      ) : isStreamingTurn ? (
        /* Active streaming block right inside this pending turn */
        <div className="flex flex-col gap-2 items-start w-full pt-1">
          <PipelineTracker events={currentPipelineEvents} isStreaming={true} />

          <div className="w-full flex flex-col gap-1.5">
            <div className="flex items-center justify-between text-xs text-[var(--tx-3)] font-mono">
              <div className="flex items-center gap-1.5">
                <Bot size={13} strokeWidth={1.5} />
                <span className="font-semibold text-[var(--tx)]">Précis generating answer...</span>
              </div>
              <span className="animate-pulse text-[var(--tx-3)] text-[0.625rem] font-mono">
                STREAMING
              </span>
            </div>
            <div
              style={{ maxWidth: "min(90%, 68rem)" }}
              className="font-sans text-[0.9375rem] sm:text-[1rem] min-h-[2rem]"
            >
              {streamingText ? (
                <>
                  <MarkdownContent content={streamingText} />
                  <span className="inline-block w-2 h-4 bg-[var(--tx)] ml-0.5 align-middle animate-pulse" />
                </>
              ) : (
                <span className="text-[var(--tx-4)] italic text-sm">
                  Evaluating SVOA salience, pruning context, and synthesizing output...
                </span>
              )}
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
};
