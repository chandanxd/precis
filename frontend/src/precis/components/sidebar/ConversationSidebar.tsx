// @ts-nocheck — ported code written for a less strict TS config
import { useState } from "react";
import type { Conversation } from "../../types/api";
import {
  Plus,
  PanelLeftClose,
  PanelLeftOpen,
  Trash2,
  Edit2,
  FileText,
  Search,
  Check,
  X,
  MessageSquare,
} from "lucide-react";

interface ConversationSidebarProps {
  conversations: Conversation[];
  activeConvId: string;
  onSelectConversation: (id: string) => void;
  onCreateConversation: () => void;
  onDeleteConversation: (id: string) => void;
  onRenameConversation: (id: string, newTitle: string) => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

export const ConversationSidebar = ({
  conversations,
  activeConvId,
  onSelectConversation,
  onCreateConversation,
  onDeleteConversation,
  onRenameConversation,
  isCollapsed,
  onToggleCollapse,
}: ConversationSidebarProps) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const filtered = conversations.filter(
    (c) =>
      c.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.document.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  const startEditing = (conv: Conversation) => {
    setEditingId(conv.id);
    setEditTitle(conv.title);
  };

  const commitEditing = (id: string) => {
    if (editTitle.trim()) {
      onRenameConversation(id, editTitle.trim());
    }
    setEditingId(null);
  };

  if (isCollapsed) {
    return (
      <aside
        className="w-10 border-r border-[var(--bd)] bg-[var(--bg)] flex flex-col items-center py-2 shrink-0 h-full select-none transition-all duration-200"
        aria-label="Conversation Sidebar Collapsed"
      >
        <button
          type="button"
          onClick={onToggleCollapse}
          title="Expand conversations (Ctrl/Cmd + B)"
          className="p-1.5 text-[var(--tx-3)] hover:text-[var(--tx)] hover:bg-[var(--bg-3)] border border-transparent hover:border-[var(--bd)] transition-colors cursor-pointer mb-2"
        >
          <PanelLeftOpen size={14} strokeWidth={1.5} />
        </button>

        <button
          type="button"
          onClick={onCreateConversation}
          title="New query session"
          className="p-1.5 text-[var(--tx)] bg-[var(--bg-2)] hover:bg-[var(--inv-bg)] hover:text-[var(--inv-tx)] border border-[var(--bd)] transition-colors cursor-pointer mb-4"
        >
          <Plus size={14} strokeWidth={2} />
        </button>

        <div className="flex-1 flex items-center justify-center">
          <span className="text-[0.5625rem] font-mono text-[var(--tx-4)] uppercase tracking-widest [writing-mode:vertical-lr] rotate-180">
            SESSIONS ({conversations.length})
          </span>
        </div>
      </aside>
    );
  }

  return (
    <aside
      className="precis-dock w-64 border-r border-[var(--bd)] bg-[var(--bg)] flex flex-col shrink-0 h-full overflow-hidden select-none font-mono transition-all duration-200"
      aria-label="Conversation Sidebar"
    >
      {/* Header: Title + Collapse Toggle */}
      <div className="h-10 px-3 border-b border-[var(--bd)] flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs font-semibold text-[var(--tx-2)]">
          <MessageSquare size={13} strokeWidth={1.5} />
          <span className="tracking-wide uppercase text-[0.6875rem]">Sessions</span>
          <span className="text-[0.625rem] text-[var(--tx-4)] font-normal">
            ({conversations.length})
          </span>
        </div>

        <button
          type="button"
          onClick={onToggleCollapse}
          title="Collapse sidebar (Ctrl/Cmd + B)"
          className="p-1 text-[var(--tx-3)] hover:text-[var(--tx)] hover:bg-[var(--bg-2)] transition-colors cursor-pointer"
        >
          <PanelLeftClose size={13} strokeWidth={1.5} />
        </button>
      </div>

      {/* Actions: New Session Button & Filter */}
      <div className="p-2 border-b border-[var(--bd)] flex flex-col gap-1.5">
        <button
          type="button"
          onClick={onCreateConversation}
          className="w-full py-1.5 px-2.5 bg-[var(--bg-2)] hover:bg-[var(--inv-bg)] hover:text-[var(--inv-tx)] border border-[var(--bd-2)] text-[var(--tx)] text-xs font-medium flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
        >
          <Plus size={12} strokeWidth={2} />
          <span>New Session</span>
        </button>

        {/* Filter input */}
        {conversations.length > 2 && (
          <div className="flex items-center gap-1.5 bg-[var(--bg-2)] px-2 py-1 text-xs border border-[var(--bd)]">
            <Search size={11} className="text-[var(--tx-4)] shrink-0" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter..."
              className="bg-transparent border-0 outline-none w-full text-[var(--tx)] placeholder:text-[var(--tx-4)] text-[0.6875rem]"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery("")}
                className="text-[var(--tx-4)] hover:text-[var(--tx)]"
              >
                <X size={10} />
              </button>
            )}
          </div>
        )}
      </div>

      {/* Conversation List */}
      <div className="flex-1 overflow-y-auto p-1.5 flex flex-col gap-0.5">
        {filtered.map((conv) => {
          const isActive = conv.id === activeConvId;
          const isEditing = editingId === conv.id;
          const isConfirmingDelete = confirmDeleteId === conv.id;

          return (
            <div
              key={conv.id}
              onClick={() => {
                if (!isEditing) onSelectConversation(conv.id);
              }}
              className={`px-2.5 py-2 flex flex-col gap-1 transition-colors cursor-pointer group text-xs ${
                isActive
                  ? "bg-[var(--bg-3)] border-l-2 border-l-[var(--accent)] text-[var(--tx)] font-medium pl-2"
                  : "border-l-2 border-l-transparent text-[var(--tx-2)] hover:bg-[var(--bg-2)] hover:text-[var(--tx)]"
              }`}
            >
              {/* Title Row */}
              <div className="flex items-center justify-between gap-1">
                {isEditing ? (
                  <div
                    className="flex items-center gap-1 w-full"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <input
                      type="text"
                      value={editTitle}
                      autoFocus
                      onChange={(e) => setEditTitle(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") commitEditing(conv.id);
                        if (e.key === "Escape") setEditingId(null);
                      }}
                      onBlur={() => commitEditing(conv.id)}
                      className="w-full bg-[var(--bg)] border border-[var(--tx-3)] px-1 py-0.5 text-xs text-[var(--tx)] outline-none"
                    />
                    <button
                      type="button"
                      onClick={() => commitEditing(conv.id)}
                      className="text-[var(--tx)] hover:opacity-80 p-0.5"
                    >
                      <Check size={11} />
                    </button>
                  </div>
                ) : (
                  <>
                    <span className="truncate flex-1 font-sans text-xs">{conv.title}</span>

                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          startEditing(conv);
                        }}
                        title="Rename session"
                        className="text-[var(--tx-4)] hover:text-[var(--accent-strong)] p-0.5 transition-colors"
                      >
                        <Edit2 size={10} />
                      </button>

                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setConfirmDeleteId(conv.id);
                        }}
                        title="Delete session"
                        className="text-[var(--tx-4)] hover:text-[var(--accent-strong)] p-0.5 transition-colors"
                      >
                        <Trash2 size={10} />
                      </button>
                    </div>
                  </>
                )}
              </div>

              {/* Inline Delete Confirmation */}
              {isConfirmingDelete && (
                <div
                  onClick={(e) => e.stopPropagation()}
                  className="border border-[var(--bd-3)] bg-[var(--bg-2)] p-1 text-[0.5625rem] flex items-center justify-between mt-1 animate-in fade-in duration-100"
                >
                  <span className="text-[var(--tx-3)]">Delete session?</span>
                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={() => {
                        onDeleteConversation(conv.id);
                        setConfirmDeleteId(null);
                      }}
                      className="text-[var(--tx)] font-bold hover:underline"
                    >
                      YES
                    </button>
                    <span>·</span>
                    <button
                      type="button"
                      onClick={() => setConfirmDeleteId(null)}
                      className="text-[var(--tx-3)] hover:text-[var(--tx)]"
                    >
                      CANCEL
                    </button>
                  </div>
                </div>
              )}

              {/* Metadata Sub-row */}
              <div className="flex items-center justify-between text-[0.625rem] text-[var(--tx-4)] font-mono">
                <span className="flex items-center gap-1 truncate max-w-[10rem]">
                  <FileText size={9} />
                  <span className="truncate">{conv.document}</span>
                </span>
                <span>{conv.message_count}</span>
              </div>
            </div>
          );
        })}

        {filtered.length === 0 && (
          <div className="p-4 text-center text-xs text-[var(--tx-4)]">No sessions match</div>
        )}
      </div>

      {/* Clean, minimal footer hint */}
      <div className="px-3 py-1.5 border-t border-[var(--bd)] text-[0.5625rem] text-[var(--tx-4)] flex items-center justify-between">
        <span>LOCAL STORE</span>
        <span>Ctrl+B</span>
      </div>
    </aside>
  );
};
