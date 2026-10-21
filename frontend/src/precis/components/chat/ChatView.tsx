// @ts-nocheck — ported code written for a less strict TS config
import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import type { Message, PipelineEvent, QueryResponse, Fact, Conversation } from "../../types/api";
import { buildChatHistory, fetchChatTitle, streamQueryPipeline } from "../../services/api";
import { loadSettings } from "../../services/settings";
import {
  loadConversations,
  saveConversations,
  loadMessages,
  saveMessages,
  createConversation,
  deleteConversation,
  renameConversation,
  getPageConversationId,
  newConversationId,
  setPageConversationId,
  setActiveConversationId,
  getSidebarCollapsed,
  setSidebarCollapsed,
} from "../../services/storage";
import { ConversationSidebar } from "../sidebar/ConversationSidebar";
import { MessageTurn } from "./MessageTurn";
import { QueryComposer } from "./QueryComposer";
import { ContextInspector } from "./ContextInspector";
import { KeyboardShortcutsModal } from "./KeyboardShortcutsModal";
import { useRouter } from "../../services/router";
import { Check, Bot, PanelRightOpen } from "lucide-react";
import { Button } from "@/components/ui/button";

const newMsgId = () => `msg-${crypto.randomUUID()}`;

export const ChatView = () => {
  const { conversationId: routeConvId, navigate } = useRouter();

  // Conversation sessions & persistence
  const [conversations, setConversations] = useState<Conversation[]>(() => loadConversations());
  // First mount of this page load: start a new, unsaved session whatever the URL
  // (a restored tab or autocompleted address still points at the old chat).
  const [isFreshStart] = useState(() => getPageConversationId() === null);
  const [activeConvId, setActiveConvId] = useState<string>(() =>
    isFreshStart ? newConversationId() : routeConvId || getPageConversationId()!,
  );
  useEffect(() => {
    setPageConversationId(activeConvId);
  }, [activeConvId]);
  useEffect(() => {
    if (isFreshStart && routeConvId) navigate("/chat", { replace: true });
    // Only on mount: later route changes are handled below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const [messages, setMessages] = useState<Message[]>(() => loadMessages(activeConvId));
  // A new session is a draft until its first message is sent: it has an ID but is
  // not stored or listed yet.
  const isDraft = !conversations.some((c) => c.id === activeConvId);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState<boolean>(() =>
    getSidebarCollapsed(),
  );

  // Query & Streaming state
  const [inputValue, setInputValue] = useState<string>("");
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [currentPipelineEvents, setCurrentPipelineEvents] = useState<PipelineEvent[]>([]);
  const [streamingText, setStreamingText] = useState<string>("");

  // Turn selection & Correspondence state
  const [selectedMsgId, setSelectedMsgId] = useState<string>("");
  const [selectedFact, setSelectedFact] = useState<Fact | null>(null);
  const [rightPanelTab, setRightPanelTab] = useState<"evidence" | "telemetry">("evidence");
  const [isInspectorOpen, setIsInspectorOpen] = useState(true);
  const [expandedEvidenceMap, setExpandedEvidenceMap] = useState<Record<string, boolean>>({});
  // Settings → "Supporting evidence default state"; a click on a list overrides it.
  const [evidenceOpenByDefault] = useState(() => loadSettings().defaultEvidenceExpanded);
  const [hoveredFactIndex, setHoveredFactIndex] = useState<number | null>(null);
  const [hoveredSentenceIndex, setHoveredSentenceIndex] = useState<number | null>(null);
  const [copiedMsgId, setCopiedMsgId] = useState<string | null>(null);

  // Modals & transient HUD state
  const [isShortcutsModalOpen, setIsShortcutsModalOpen] = useState<boolean>(false);
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);

  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortStreamRef = useRef<(() => void) | null>(null);
  // Mirrors currentPipelineEvents so stream callbacks (which close over a stale
  // render) can read the latest events when saving the finished message.
  const pipelineEventsRef = useRef<PipelineEvent[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const contextInspectorRef = useRef<HTMLDivElement>(null);
  const inspectorToggleRef = useRef<HTMLButtonElement>(null);
  const premiseRowRefs = useRef<Record<string, HTMLButtonElement | null>>({});
  const evidenceHeaderRefs = useRef<Record<string, HTMLButtonElement | null>>({});

  // Platform detection
  const isMac = useMemo(() => {
    if (typeof navigator === "undefined") return false;
    return (
      /Mac|iPhone|iPod|iPad/i.test(navigator.platform || "") ||
      /Mac|iPhone|iPod|iPad/i.test(navigator.userAgent || "")
    );
  }, []);
  const modKeyLabel = isMac ? "⌘" : "Ctrl";

  // Auto-scroll
  const scrollToBottom = useCallback((smooth = true) => {
    messagesEndRef.current?.scrollIntoView({ behavior: smooth ? "smooth" : "auto" });
  }, []);

  useEffect(() => {
    scrollToBottom(false);
  }, [streamingText, currentPipelineEvents, scrollToBottom]);

  useEffect(() => {
    scrollToBottom(true);
  }, [messages, scrollToBottom]);

  // Active message & facts for Context Inspector
  const activeMsg = useMemo(() => {
    return messages.find((m) => m.id === selectedMsgId) || messages[messages.length - 1];
  }, [messages, selectedMsgId]);

  const activeFacts = useMemo(() => {
    return activeMsg?.query_response?.facts_used || [];
  }, [activeMsg]);

  const displayedSelectedFact = useMemo(() => {
    return selectedFact && activeFacts.includes(selectedFact) ? selectedFact : null;
  }, [selectedFact, activeFacts]);

  // Switch active message and cleanly reset selection
  const handleSelectMessage = useCallback((msgId: string) => {
    setSelectedMsgId(msgId);
    setSelectedFact(null);
    setHoveredFactIndex(null);
    setHoveredSentenceIndex(null);
  }, []);

  // Toggle supporting evidence collapse state per message
  const toggleEvidence = useCallback(
    (msgId: string) => {
      setExpandedEvidenceMap((prev) => ({
        ...prev,
        [msgId]: !(prev[msgId] ?? evidenceOpenByDefault),
      }));
    },
    [evidenceOpenByDefault],
  );

  // Abort any in-flight stream when the active conversation changes (switch, route
  // change, delete) or the view unmounts, so late callbacks can't write into the
  // wrong conversation's history.
  useEffect(() => {
    return () => {
      abortStreamRef.current?.();
      abortStreamRef.current = null;
    };
  }, [activeConvId]);

  const [prevRouteConvId, setPrevRouteConvId] = useState(routeConvId);

  // Adjust state during render when route conversation changes (React 19 recommended pattern)
  if (routeConvId !== prevRouteConvId) {
    setPrevRouteConvId(routeConvId);
    if (routeConvId && routeConvId !== activeConvId) {
      const exists = conversations.some((c) => c.id === routeConvId);
      if (exists) {
        setActiveConvId(routeConvId);
        setActiveConversationId(routeConvId);
        setMessages(loadMessages(routeConvId));
        setSelectedMsgId("");
        setSelectedFact(null);
        setStreamingText("");
        setIsStreaming(false);
        setCurrentPipelineEvents([]);
      }
    }
  }

  // Unknown conversation ID in the URL: fall back to the active conversation
  // (a draft has no URL of its own).
  useEffect(() => {
    if (routeConvId && !conversations.some((c) => c.id === routeConvId)) {
      navigate(isDraft ? "/chat" : `/chat/${activeConvId}`, { replace: true });
    }
  }, [routeConvId, conversations, activeConvId, isDraft, navigate]);

  // Normalize URL when at /chat without ID
  useEffect(() => {
    if (!routeConvId && activeConvId && !isDraft) {
      navigate(`/chat/${activeConvId}`, { replace: true });
    }
  }, [routeConvId, activeConvId, isDraft, navigate]);

  // Conversation Management
  const handleSelectConversation = useCallback(
    (id: string) => {
      abortStreamRef.current?.();
      abortStreamRef.current = null;
      setActiveConvId(id);
      setActiveConversationId(id);
      const loaded = loadMessages(id);
      setMessages(loaded);
      setSelectedMsgId("");
      setSelectedFact(null);
      setStreamingText("");
      setIsStreaming(false);
      setCurrentPipelineEvents([]);
      navigate(`/chat/${id}`);
    },
    [navigate],
  );

  const focusComposer = useCallback(() => {
    requestAnimationFrame(() => textareaRef.current?.focus());
  }, []);

  // Opens an empty draft; the conversation is created when its first message is sent.
  const handleCreateConversation = useCallback(() => {
    if (isDraft && messages.length === 0) {
      focusComposer();
      return;
    }
    abortStreamRef.current?.();
    abortStreamRef.current = null;
    setActiveConvId(newConversationId());
    setMessages([]);
    setSelectedMsgId("");
    setSelectedFact(null);
    setStreamingText("");
    setIsStreaming(false);
    setCurrentPipelineEvents([]);
    navigate("/chat");
    focusComposer();
  }, [isDraft, messages.length, navigate, focusComposer]);

  const handleDeleteConversation = useCallback(
    (id: string) => {
      const updated = deleteConversation(id);
      setConversations(updated);
      if (activeConvId === id) {
        const nextId = updated[0]?.id;
        if (nextId) {
          handleSelectConversation(nextId);
        } else {
          handleCreateConversation();
        }
      }
    },
    [activeConvId, handleSelectConversation, handleCreateConversation],
  );

  const handleRenameConversation = useCallback((id: string, newTitle: string) => {
    renameConversation(id, newTitle);
    setConversations(loadConversations());
  }, []);

  const handleToggleSidebar = useCallback(() => {
    setIsSidebarCollapsed((prev) => {
      const next = !prev;
      setSidebarCollapsed(next);
      return next;
    });
  }, []);

  // Sending & Streaming Query
  const handleSend = useCallback(
    (textToSend?: string, baseMessages?: Message[]) => {
      const queryText = (textToSend || inputValue).trim();
      if (!queryText || isStreaming) return;

      const userMsgId = newMsgId();
      const userMsg: Message = {
        id: userMsgId,
        role: "user",
        content: queryText,
        timestamp: new Date().toISOString(),
        pipeline_events: [],
        query_response: {
          answer: "",
          facts_used: [],
          tokens_used: 0,
          naive_rag_tokens: 0,
          compression_rate: 0,
          avg_sdh_score: 0,
          latency_ms: 0,
        },
      };

      // Name the session after its first query: create a draft, or rename a
      // session that still has the default title.
      const words = queryText.split(" ").slice(0, 5).join(" ");
      const newTitle = words.length > 30 ? `${words.slice(0, 30)}...` : words;
      const currentConv = conversations.find((c) => c.id === activeConvId);
      // Set when this message names the session; the model's title replaces it
      // once the first answer arrives.
      let placeholderTitle: string | null = null;
      if (!currentConv) {
        createConversation(newTitle, "", activeConvId);
        setConversations(loadConversations());
        navigate(`/chat/${activeConvId}`, { replace: true });
        placeholderTitle = newTitle;
      } else if (currentConv.title === "New Query Session") {
        renameConversation(activeConvId, newTitle);
        setConversations(loadConversations());
        placeholderTitle = newTitle;
      }
      const convId = activeConvId;

      const priorMessages = baseMessages ?? messages;
      const updatedWithUser = [...priorMessages, userMsg];
      setMessages(updatedWithUser);
      saveMessages(activeConvId, updatedWithUser);
      setInputValue("");
      setIsStreaming(true);
      pipelineEventsRef.current = [];
      setCurrentPipelineEvents([]);
      setStreamingText("");

      const abortFn = streamQueryPipeline(
        queryText,
        {
          onStage: (event: PipelineEvent) => {
            const next = [
              ...pipelineEventsRef.current.filter((p) => p.stage !== event.stage),
              event,
            ].sort((a, b) => a.stage - b.stage);
            pipelineEventsRef.current = next;
            setCurrentPipelineEvents(next);
          },
          onToken: (token: string) => {
            setStreamingText((prev) => prev + token);
          },
          onDone: (response: QueryResponse) => {
            const aiMsgId = newMsgId();
            // Storage already holds the user message saved at send time.
            const messageCount = loadMessages(activeConvId).length + 1;
            const aiMsg: Message = {
              id: aiMsgId,
              role: "ai",
              content: response.answer,
              timestamp: new Date().toISOString(),
              pipeline_events: pipelineEventsRef.current,
              query_response: response,
            };

            setMessages((prev) => {
              const finalMsgs = [...prev, aiMsg];
              saveMessages(activeConvId, finalMsgs);
              return finalMsgs;
            });

            // Update message count in conversation header. Read from storage, not
            // React state, so a rename made meanwhile is not overwritten.
            const updatedConvs = loadConversations().map((c) =>
              c.id === activeConvId ? { ...c, message_count: messageCount } : c,
            );
            saveConversations(updatedConvs);
            setConversations(updatedConvs);

            if (placeholderTitle && response.answer) {
              void fetchChatTitle(queryText, response.answer).then((title) => {
                // Keep a name the user chose while the title was being made.
                const conv = loadConversations().find((c) => c.id === convId);
                if (!title || !conv || conv.title !== placeholderTitle) return;
                renameConversation(convId, title);
                setConversations(loadConversations());
              });
            }

            handleSelectMessage(aiMsgId);
            setSelectedFact(null);
            setIsStreaming(false);
            setStreamingText("");
            setCurrentPipelineEvents([]);
            abortStreamRef.current = null;
          },
          onError: (err: string) => {
            const errorAiMsg: Message = {
              id: newMsgId(),
              role: "ai",
              content: `Pipeline query failed: ${err}`,
              timestamp: new Date().toISOString(),
              failed: true,
              pipeline_events: pipelineEventsRef.current,
              query_response: {
                answer: `Pipeline query failed: ${err}`,
                facts_used: [],
                tokens_used: 0,
                naive_rag_tokens: 0,
                compression_rate: 0,
                avg_sdh_score: 0,
                latency_ms: 0,
              },
            };
            setMessages((prev) => {
              const finalMsgs = [...prev, errorAiMsg];
              saveMessages(activeConvId, finalMsgs);
              return finalMsgs;
            });
            setIsStreaming(false);
            setStreamingText("");
            setCurrentPipelineEvents([]);
            abortStreamRef.current = null;
          },
        },
        activeConvId,
        buildChatHistory(priorMessages),
      );

      abortStreamRef.current = abortFn;
    },
    [inputValue, isStreaming, messages, activeConvId, conversations, handleSelectMessage, navigate],
  );

  // Put the cursor back in the chat bar when an answer finishes (or fails or is
  // stopped), unless the user has moved on to typing somewhere else.
  const wasStreamingRef = useRef(false);
  useEffect(() => {
    if (wasStreamingRef.current && !isStreaming) {
      const el = document.activeElement as HTMLElement | null;
      const typingElsewhere =
        !!el &&
        el !== textareaRef.current &&
        (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.isContentEditable);
      if (!typingElsewhere) textareaRef.current?.focus();
    }
    wasStreamingRef.current = isStreaming;
  }, [isStreaming]);

  const handleStop = () => {
    if (abortStreamRef.current) {
      abortStreamRef.current();
      abortStreamRef.current = null;
    }
    setIsStreaming(false);
    setStreamingText("");
    pipelineEventsRef.current = [];
    setCurrentPipelineEvents([]);
  };

  const handleClearMessages = () => {
    setMessages([]);
    if (!isDraft) saveMessages(activeConvId, []);
    setSelectedMsgId("");
    setSelectedFact(null);
  };

  const handleCopyAnswer = async (
    text: string,
    msgId: string,
    kind: "answer" | "question" = "answer",
  ) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedMsgId(msgId);
      setCopyFeedback(
        kind === "question" ? "COPIED MESSAGE TO CLIPBOARD" : "COPIED ANSWER TO CLIPBOARD",
      );
      setTimeout(() => {
        setCopiedMsgId(null);
        setCopyFeedback(null);
      }, 1500);
    } catch {
      // fallback
    }
  };

  const copyActiveAnswer = useCallback(() => {
    const targetMsg =
      activeMsg?.role === "ai" ? activeMsg : [...messages].reverse().find((m) => m.role === "ai");
    if (!targetMsg) return;
    const answerText = targetMsg.query_response?.answer || targetMsg.content;
    if (!answerText) return;
    navigator.clipboard
      .writeText(answerText)
      .then(() => {
        setCopiedMsgId(targetMsg.id);
        setCopyFeedback("COPIED ACTIVE ANSWER TO CLIPBOARD");
        setTimeout(() => {
          setCopiedMsgId(null);
          setCopyFeedback(null);
        }, 1500);
      })
      .catch(() => {});
  }, [activeMsg, messages]);

  // Edit a question: drop it and everything after it, then ask the new text.
  const handleEditMessage = (msgId: string, text: string) => {
    const msgIndex = messages.findIndex((m) => m.id === msgId);
    if (msgIndex < 0 || messages[msgIndex]!.role !== "user") return;
    handleSend(text, messages.slice(0, msgIndex));
  };

  const handleRegenerate = (msgId: string) => {
    const msgIndex = messages.findIndex((m) => m.id === msgId);
    if (msgIndex > 0) {
      const prevUserMsg = messages[msgIndex - 1];
      if (prevUserMsg && prevUserMsg.role === "user") {
        // Replace the old question/answer pair instead of appending a duplicate question.
        handleSend(
          prevUserMsg.content,
          messages.filter((_, i) => i !== msgIndex - 1 && i !== msgIndex),
        );
      }
    }
  };

  const focusContextInspector = useCallback(() => {
    setRightPanelTab("evidence");
    setIsInspectorOpen(true);
    requestAnimationFrame(() => contextInspectorRef.current?.focus());
  }, []);

  const closeInspector = useCallback(() => {
    setIsInspectorOpen(false);
    inspectorToggleRef.current?.focus();
  }, []);

  // Global keyboard shortcuts
  useEffect(() => {
    const onGlobalKeyDown = (e: KeyboardEvent) => {
      const isMod = e.ctrlKey || e.metaKey;
      const activeElement = document.activeElement;
      const activeTag = (activeElement?.tagName || "").toLowerCase();
      const isInput =
        activeTag === "input" ||
        activeTag === "textarea" ||
        (activeElement as HTMLElement)?.isContentEditable;

      // Toggle sidebar: Ctrl/Cmd + B
      if (isMod && (e.key === "b" || e.key === "B")) {
        e.preventDefault();
        handleToggleSidebar();
        return;
      }

      // Reference overlay: Ctrl/Cmd + / or ?
      if (isMod && (e.key === "/" || e.key === "?")) {
        e.preventDefault();
        setIsShortcutsModalOpen((prev) => !prev);
        return;
      }

      // Focus query input: Ctrl/Cmd + K
      if (isMod && (e.key === "k" || e.key === "K")) {
        e.preventDefault();
        textareaRef.current?.focus();
        const len = textareaRef.current?.value.length || 0;
        textareaRef.current?.setSelectionRange(len, len);
        return;
      }

      // Copy active answer: Ctrl/Cmd + Shift + C
      if (isMod && e.shiftKey && (e.key === "c" || e.key === "C")) {
        e.preventDefault();
        copyActiveAnswer();
        return;
      }

      // Focus Context Inspector: Ctrl/Cmd + Shift + I
      if (isMod && e.shiftKey && (e.key === "i" || e.key === "I")) {
        e.preventDefault();
        focusContextInspector();
        return;
      }

      // Escape hierarchy
      if (e.key === "Escape") {
        if (isShortcutsModalOpen) {
          e.preventDefault();
          setIsShortcutsModalOpen(false);
          return;
        }
        if (selectedFact) {
          e.preventDefault();
          setSelectedFact(null);
          return;
        }
        if (isInspectorOpen && contextInspectorRef.current?.contains(activeElement)) {
          e.preventDefault();
          closeInspector();
          return;
        }
        if (isInput) {
          e.preventDefault();
          (activeElement as HTMLElement)?.blur();
          return;
        }
      }
    };

    window.addEventListener("keydown", onGlobalKeyDown);
    return () => window.removeEventListener("keydown", onGlobalKeyDown);
  }, [
    isShortcutsModalOpen,
    selectedFact,
    copyActiveAnswer,
    focusContextInspector,
    handleToggleSidebar,
    isInspectorOpen,
    closeInspector,
  ]);

  // Group messages into question-answer turns
  const turns = useMemo(() => {
    const result: { userMsg?: Message; aiMsg?: Message }[] = [];
    for (let i = 0; i < messages.length; i++) {
      const m = messages[i];
      if (m.role === "user") {
        const next = messages[i + 1];
        if (next && next.role === "ai") {
          result.push({ userMsg: m, aiMsg: next });
          i++;
        } else {
          result.push({ userMsg: m });
        }
      } else {
        result.push({ aiMsg: m });
      }
    }
    return result;
  }, [messages]);

  return (
    <div className="precis-stage relative flex-1 min-h-0 w-full flex flex-row overflow-hidden">
      {/* Left: Collapsible Session Sidebar */}
      <ConversationSidebar
        conversations={conversations}
        activeConvId={activeConvId}
        onSelectConversation={handleSelectConversation}
        onCreateConversation={handleCreateConversation}
        onDeleteConversation={handleDeleteConversation}
        onRenameConversation={handleRenameConversation}
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={handleToggleSidebar}
      />

      {/* Middle Stage: Chat Stream & Composer */}
      <div className="flex-1 min-w-0 h-full flex flex-col overflow-hidden p-3 lg:p-4 gap-2.5">
        <div className="flex justify-end shrink-0">
          <Button
            ref={inspectorToggleRef}
            variant="ghost"
            size="sm"
            className="precis-inspector-toggle"
            aria-label={isInspectorOpen ? "Close Inspector" : "Open Inspector"}
            aria-expanded={isInspectorOpen}
            aria-controls="query-inspector"
            title={isInspectorOpen ? "Close Inspector" : "Open Inspector"}
            onClick={() => (isInspectorOpen ? closeInspector() : focusContextInspector())}
          >
            <PanelRightOpen size={14} />
            Inspector
          </Button>
        </div>
        {/* Scrollable Conversation Stream */}
        <div className="flex-1 min-h-0 overflow-y-auto flex flex-col pr-1">
          {turns.length === 0 && !isStreaming && (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-8 select-none">
              <div className="precis-orb-icon mb-5">
                <Bot size={16} strokeWidth={1.5} />
              </div>
              <span className="precis-hero-title mb-3">Ask Précis</span>
              <span className="text-xs text-[var(--tx-4)] max-w-sm leading-relaxed font-sans">
                Ask questions grounded in SVOA premises. Answers are verified with epistemic scores
                and direct claim citations.
              </span>
            </div>
          )}

          {turns.map((turn, tIdx) => {
            const turnMsgId = turn.aiMsg?.id || turn.userMsg?.id || `turn-${tIdx}`;
            const isSelected = selectedMsgId
              ? selectedMsgId === turn.aiMsg?.id || selectedMsgId === turn.userMsg?.id
              : turn.aiMsg?.id === activeMsg?.id;
            const isEvidenceExpanded = turn.aiMsg
              ? (expandedEvidenceMap[turn.aiMsg.id] ?? evidenceOpenByDefault)
              : false;

            return (
              <MessageTurn
                key={turnMsgId}
                userMsg={turn.userMsg}
                aiMsg={turn.aiMsg}
                isSelected={isSelected}
                onSelectMessage={() =>
                  handleSelectMessage(turn.aiMsg?.id || turn.userMsg?.id || "")
                }
                displayedSelectedFact={displayedSelectedFact}
                onSelectFact={(fact) => {
                  setSelectedFact(fact);
                  if (fact) focusContextInspector();
                }}
                hoveredFactIndex={hoveredFactIndex}
                onHoverFact={setHoveredFactIndex}
                hoveredSentenceIndex={hoveredSentenceIndex}
                onHoverSentence={setHoveredSentenceIndex}
                copiedMsgId={copiedMsgId}
                onCopyAnswer={handleCopyAnswer}
                onRegenerate={handleRegenerate}
                onEditMessage={handleEditMessage}
                isBusy={isStreaming}
                isEvidenceExpanded={isEvidenceExpanded}
                onToggleEvidence={() => {
                  if (turn.aiMsg) toggleEvidence(turn.aiMsg.id);
                }}
                premiseRowRefs={premiseRowRefs}
                evidenceHeaderRef={(el) => {
                  if (turn.aiMsg) evidenceHeaderRefs.current[turn.aiMsg.id] = el;
                }}
              />
            );
          })}

          {/* Active streaming block if pipeline is running */}
          {isStreaming && (
            <MessageTurn
              isStreamingTurn={true}
              streamingText={streamingText}
              currentPipelineEvents={currentPipelineEvents}
              isSelected={true}
              onSelectMessage={() => {}}
              displayedSelectedFact={null}
              onSelectFact={() => {}}
              hoveredFactIndex={null}
              onHoverFact={() => {}}
              hoveredSentenceIndex={null}
              onHoverSentence={() => {}}
              copiedMsgId={null}
              onCopyAnswer={() => {}}
              onRegenerate={() => {}}
              isEvidenceExpanded={false}
              onToggleEvidence={() => {}}
              premiseRowRefs={premiseRowRefs}
              evidenceHeaderRef={() => {}}
            />
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Query Composer */}
        <QueryComposer
          inputValue={inputValue}
          setInputValue={setInputValue}
          isStreaming={isStreaming}
          onSend={handleSend}
          onStop={handleStop}
          onClear={handleClearMessages}
          onOpenShortcuts={() => setIsShortcutsModalOpen(true)}
          selectedFact={selectedFact}
          onClearSelectedFact={() => setSelectedFact(null)}
          textareaRef={textareaRef}
          modKeyLabel={modKeyLabel}
        />
      </div>

      {/* Right Stage: Context Inspector */}
      <div
        className={`precis-inspector-window ${isInspectorOpen ? "is-open" : ""}`}
        inert={!isInspectorOpen}
        aria-hidden={!isInspectorOpen}
      >
        <ContextInspector
          onClose={closeInspector}
          activeMsg={activeMsg}
          activeFacts={activeFacts}
          displayedSelectedFact={displayedSelectedFact}
          onSelectFact={(fact) => setSelectedFact(fact)}
          hoveredFactIndex={hoveredFactIndex}
          onHoverFact={setHoveredFactIndex}
          rightPanelTab={rightPanelTab}
          setRightPanelTab={setRightPanelTab}
          containerRef={contextInspectorRef}
        />
      </div>

      {/* Transient HUD Notification for Clipboard Copy */}
      {copyFeedback && (
        <div className="fixed bottom-14 right-6 z-50 border border-[var(--bd-3)] bg-[var(--inv-bg)] text-[var(--inv-tx)] px-3 py-1.5 text-[0.6875rem] font-mono font-bold shadow-xl flex items-center gap-2 select-none pointer-events-none animate-toast-in">
          <Check size={12} strokeWidth={2.5} />
          <span>{copyFeedback}</span>
        </div>
      )}

      {/* Compact Monochrome Keyboard Shortcuts Overlay */}
      <KeyboardShortcutsModal
        isOpen={isShortcutsModalOpen}
        onClose={() => setIsShortcutsModalOpen(false)}
        isMac={isMac}
      />
    </div>
  );
};
