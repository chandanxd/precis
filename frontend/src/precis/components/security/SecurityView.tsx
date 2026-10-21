// @ts-nocheck — ported code written for a less strict TS config
import { useEffect, useState } from "react";
import { ShieldCheck, KeyRound, History } from "lucide-react";
import {
  checkSecurity,
  ensureToken,
  getTokenInfo,
  type SecurityCheckResult,
} from "../../services/api";
import { loadConversations } from "../../services/storage";

// Every value on this page comes from the backend or this browser's storage:
// the checks run through the real sanitiser, injection filter and chat router.

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

const Row = ({ label, value }) => (
  <div className="flex justify-between gap-2 text-[0.6875rem] border-t border-[var(--bd)] pt-[0.375rem]">
    <span className="text-[var(--tx-3)]">{label}</span>
    <span className="font-bold text-[var(--tx)] text-right">{value}</span>
  </div>
);

const SOURCE_LABELS = {
  document: "Answered from your documents",
  general: "Answered from the model's general knowledge",
  conversation: "Conversational reply",
};

const LIMITS = [
  ["Chat questions", "10 per minute, 2,000 characters"],
  ["Chat titles", "10 per minute"],
  ["Documents", "100,000 characters after sanitising"],
  ["Access token", "HS256 JWT, valid 24 hours"],
];

export const SecurityView = () => {
  const [token, setToken] = useState(() => getTokenInfo());
  const [text, setText] = useState("");
  const [result, setResult] = useState<SecurityCheckResult | null>(null);
  const [checkError, setCheckError] = useState(false);
  const conversations = loadConversations();

  useEffect(() => {
    let active = true;
    ensureToken().then(() => {
      if (active) setToken(getTokenInfo());
    });
    return () => {
      active = false;
    };
  }, []);

  // Check the text shortly after typing stops, so the backend is not called per keystroke.
  useEffect(() => {
    if (!text.trim()) {
      setResult(null);
      setCheckError(false);
      return;
    }
    let active = true;
    const timer = setTimeout(() => {
      checkSecurity(text).then((r) => {
        if (!active) return;
        setResult(r);
        setCheckError(r === null);
      });
    }, 400);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [text]);

  const input =
    "w-full bg-[var(--bg-2)] border border-[var(--bd)] p-[0.5rem] text-[0.75rem] text-[var(--tx)] outline-none";

  return (
    <div className="flex-1 min-h-0 overflow-y-auto p-[1rem] font-mono">
      <div className="max-w-[72rem] mx-auto grid grid-cols-1 lg:grid-cols-2 gap-[0.75rem]">
        <Card icon={ShieldCheck} title="Input Checks" tag="SANITISER · INJECTION FILTER · ROUTER">
          <p className="text-[0.6875rem] text-[var(--tx-3)]">
            Type a chat message to see what the backend would do with it. No model is called.
          </p>
          <textarea
            rows={3}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="e.g. What does the report say about revenue?"
            aria-label="Text to check"
            className={input}
          />
          <Row
            label="RESULT"
            value={
              !text.trim()
                ? "—"
                : checkError
                  ? "Backend unreachable"
                  : !result
                    ? "Checking…"
                    : result.accepted
                      ? "ACCEPTED"
                      : `REJECTED · ${result.reason}`
            }
          />
          {result?.accepted && (
            <>
              <Row label="INTENT" value={result.intent?.replace(/_/g, " ").toUpperCase()} />
              <Row
                label="ROUTE"
                value={SOURCE_LABELS[result.answer_source] ?? result.answer_source}
              />
              {typeof result.relevance === "number" && (
                <Row label="BEST DOCUMENT MATCH" value={result.relevance.toFixed(2)} />
              )}
              <Row label="DOCUMENTS LOADED" value={result.has_documents ? "Yes" : "No"} />
            </>
          )}
        </Card>

        <Card icon={KeyRound} title="Access" tag="JWT · PER-BROWSER CLIENT ID">
          <p className="text-[0.6875rem] text-[var(--tx-3)]">
            This browser keeps a random client ID; the backend keys your documents and chat context
            by it. Every API call carries a token minted for that ID. Minting is open unless the
            server sets PRECIS_TOKEN_MINT_KEY.
          </p>
          <Row
            label="CLIENT ID"
            value={token.clientId ? `${token.clientId.slice(0, 15)}…` : "Unavailable"}
          />
          <Row
            label="TOKEN"
            value={
              token.expiresAt
                ? `Valid until ${new Date(token.expiresAt).toLocaleString()}`
                : "None (backend unreachable?)"
            }
          />
          {LIMITS.map(([label, value]) => (
            <Row key={label} label={label.toUpperCase()} value={value} />
          ))}
        </Card>

        <Card icon={History} title="Conversations" tag="STORED IN THIS BROWSER">
          <p className="text-[0.6875rem] text-[var(--tx-3)]">
            Chats live in this browser&apos;s storage. The server keeps only recent turns of each
            chat in memory for follow-up questions, for up to 4 hours.
          </p>
          {conversations.length === 0 ? (
            <span className="text-[0.6875rem] text-[var(--tx-3)]">No saved conversations.</span>
          ) : (
            <div className="flex flex-col text-[0.6875rem]">
              {conversations.map((c) => (
                <div
                  key={c.id}
                  className="grid grid-cols-[1fr_auto_auto] gap-[0.75rem] border-b border-[var(--bd)] py-[0.375rem] text-[var(--tx)]"
                >
                  <span className="truncate">{c.title}</span>
                  <span className="text-[var(--tx-3)]">{c.message_count} msgs</span>
                  <span className="text-right text-[var(--tx-3)]">
                    {new Date(c.created_at).toLocaleDateString()}
                  </span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};
