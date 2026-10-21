// @ts-nocheck — static view; intentionally NOT connected to the backend.
import { useState } from "react";
import { ShieldCheck, KeyRound, Route, History } from "lucide-react";

// Mirrors backend security.py, routing.py and history.py. Local-only demo logic.
const INJECTION = [
  /ignore (all|previous) instructions/i,
  /system prompt/i,
  /you are now/i,
  /disregard/i,
];
const GREET = /^(hi|hello|hey|thanks|thank you|bye|ok|okay|cool)\b/i;
const GENERAL = /^(what is|who is|define|explain)\b/i;

function classify(q: string) {
  const t = q.trim();
  if (!t) return null;
  if (GREET.test(t)) return "conversational";
  if (/\b(document|according to|in the (text|file|report)|this (doc|paper))\b/i.test(t))
    return "document_grounded";
  if (GENERAL.test(t)) return "general_knowledge";
  return "ambiguous";
}

const Card = ({ icon: Icon, title, tag, children }) => (
  <div className="border border-[var(--bd)] bg-[var(--bg)] p-[0.75rem] flex flex-col gap-[0.5rem]">
    <div className="flex items-center justify-between border-b border-[var(--bd)] pb-[0.375rem]">
      <div className="flex items-center gap-[0.375rem]">
        <Icon size={14} strokeWidth={1.5} />
        <span className="font-bold text-[0.75rem] uppercase text-[var(--tx)]">{title}</span>
      </div>
      <span className="text-[0.6875rem] text-[var(--tx-3)]">{tag}</span>
    </div>
    {children}
  </div>
);

const sessions = [
  { id: "sess-7f2a", turns: 6, last: "2 min ago" },
  { id: "sess-91cd", turns: 3, last: "18 min ago" },
  { id: "sess-04be", turns: 11, last: "1 h ago" },
];

export const SecurityView = () => {
  const [token, setToken] = useState<string | null>(null);
  const [probe, setProbe] = useState("");
  const [query, setQuery] = useState("");
  const flagged = INJECTION.some((r) => r.test(probe));
  const intent = classify(query);

  const makeToken = () => {
    const rnd = () => Math.random().toString(36).slice(2, 12);
    setToken(`eyJhbGciOiJIUzI1NiJ9.${rnd()}${rnd()}.${rnd()}`);
  };

  const input =
    "w-full bg-[var(--bg-2)] border border-[var(--bd)] p-[0.5rem] text-[0.75rem] text-[var(--tx)] outline-none";

  return (
    <div className="flex-1 min-h-0 overflow-y-auto p-[1rem] font-mono">
      <div className="max-w-[72rem] mx-auto grid grid-cols-1 lg:grid-cols-2 gap-[0.75rem]">
        <Card icon={KeyRound} title="API Access Token" tag="JWT · HS256 · 24H">
          <p className="text-[0.6875rem] text-[var(--tx-3)]">
            Bearer tokens protect every API call through zero-trust middleware.
          </p>
          <button
            onClick={makeToken}
            className="self-start px-[0.625rem] py-[0.375rem] text-[0.6875rem] bg-[var(--inv-bg)] text-[var(--inv-tx)] font-semibold uppercase"
          >
            Generate token
          </button>
          {token && (
            <code className="break-all text-[0.6875rem] border border-[var(--bd)] bg-[var(--bg-2)] p-[0.5rem] text-[var(--tx)]">
              {token}
            </code>
          )}
        </Card>

        <Card icon={ShieldCheck} title="Prompt Injection Guard" tag="SANITIZER">
          <textarea
            rows={3}
            value={probe}
            onChange={(e) => setProbe(e.target.value)}
            placeholder="Paste text to test…"
            className={input}
          />
          <div className="flex justify-between text-[0.6875rem]">
            <span className="text-[var(--tx-3)]">RESULT</span>
            <span className="font-bold text-[var(--tx)]">
              {!probe ? "—" : flagged ? "REJECTED · suspicious content" : "PASSED"}
            </span>
          </div>
          <div className="flex justify-between text-[0.6875rem] border-t border-[var(--bd)] pt-[0.375rem]">
            <span className="text-[var(--tx-3)]">QUERY RATE LIMIT</span>
            <span className="font-bold text-[var(--tx)]">10 requests / min (sliding window)</span>
          </div>
        </Card>

        <Card icon={Route} title="Query Intent Routing" tag="CLASSIFIER">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type a question…"
            className={input}
          />
          <div className="grid grid-cols-2 gap-[0.375rem] text-[0.6875rem]">
            {["conversational", "general_knowledge", "document_grounded", "ambiguous"].map((k) => (
              <div
                key={k}
                className={`border border-[var(--bd)] p-[0.375rem] ${intent === k ? "bg-[var(--inv-bg)] text-[var(--inv-tx)]" : "bg-[var(--bg-2)] text-[var(--tx-3)]"}`}
              >
                {k.replace("_", " ").toUpperCase()}
              </div>
            ))}
          </div>
        </Card>

        <Card icon={History} title="Conversation Sessions" tag="SESSION MANAGER">
          <div className="flex flex-col text-[0.6875rem]">
            {sessions.map((s) => (
              <div
                key={s.id}
                className="grid grid-cols-3 border-b border-[var(--bd)] py-[0.375rem] text-[var(--tx)]"
              >
                <span>{s.id}</span>
                <span className="text-center">{s.turns} turns</span>
                <span className="text-right text-[var(--tx-3)]">{s.last}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
};
