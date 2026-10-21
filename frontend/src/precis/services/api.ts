// @ts-nocheck — ported code written for a less strict TS config
import type {
  Document,
  Fact,
  FactStoreStats,
  HardwareProfile,
  Message,
  PipelineEvent,
  QueryResponse,
} from "../types/api";
import {
  mockDocuments,
  mockFacts,
  mockHardware,
  mockPipelineEvents,
  mockQueryResponse,
  mockFactStoreStats,
} from "../mocks/data";
import { DEMO_MODE } from "./demo";
import { getQueryOptions } from "./settings";

/**
 * Backend location.
 * - VITE_API_URL / VITE_WS_URL win when set.
 * - Under the Vite dev server the backend is on port 8000 of the same host.
 * - In a built deployment the app is served behind the nginx proxy, which forwards
 *   /api and /ws, so the page's own origin is used (works over a LAN IP or HTTPS).
 */
function apiBase(): string {
  const configured = import.meta.env["VITE_API_URL"] as string | undefined;
  if (configured) return configured.replace(/\/$/, "");
  if (typeof window === "undefined") return "http://localhost:8000";
  if (import.meta.env.DEV) return `${window.location.protocol}//${window.location.hostname}:8000`;
  return window.location.origin;
}

function wsBase(): string {
  const configured = import.meta.env["VITE_WS_URL"] as string | undefined;
  if (configured) return configured;
  if (typeof window === "undefined") return "ws://localhost:8000/ws";
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  if (import.meta.env.DEV) return `${proto}//${window.location.hostname}:8000/ws`;
  return `${proto}//${window.location.host}/ws`;
}

// --- Client identity ---

export const CLIENT_ID_KEY = "precis_client_id";
const CLIENT_ID_PATTERN = /^client-[0-9a-f]{32}$/;

/**
 * Stable random ID for this browser. The backend keys each user's documents and
 * chat context by it, so reloads and token expiry keep the same data. Clearing
 * site data creates a new ID (and an empty workspace).
 */
export function getClientId(): string | null {
  try {
    let id = localStorage.getItem(CLIENT_ID_KEY);
    if (!id || !CLIENT_ID_PATTERN.test(id)) {
      id = `client-${crypto.randomUUID().replace(/-/g, "")}`;
      localStorage.setItem(CLIENT_ID_KEY, id);
    }
    return id;
  } catch {
    return null;
  }
}

// --- JWT Token Management ---

let cachedToken: string | null = null;
let tokenExpiresAt: number = 0;
let tokenPromise: Promise<string | null> | null = null;

/**
 * Acquire a JWT token from the backend. Caches and reuses until near expiry.
 * Returns null if the backend is unreachable.
 */
async function acquireToken(): Promise<string | null> {
  const now = Date.now();
  // Reuse cached token if still valid (with 60s safety margin)
  if (cachedToken && tokenExpiresAt > now + 60_000) {
    return cachedToken;
  }

  // Deduplicate concurrent requests
  if (tokenPromise) return tokenPromise;

  tokenPromise = (async () => {
    try {
      const clientId = getClientId();
      const res = await fetch(`${apiBase()}/api/auth/token`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ client_id: clientId }),
      });
      if (!res.ok) return null;
      const data = await res.json();
      cachedToken = data.access_token;
      tokenExpiresAt = now + (data.expires_in ?? 86400) * 1000;
      return cachedToken;
    } catch {
      return null;
    } finally {
      tokenPromise = null;
    }
  })();

  return tokenPromise;
}

/**
 * Return current cached token without fetching.
 */
function getCachedToken(): string | null {
  if (cachedToken && tokenExpiresAt > Date.now() + 60_000) {
    return cachedToken;
  }
  return null;
}

/**
 * Drop the cached token (e.g. after a 401) so the next call mints a fresh one.
 */
function invalidateToken(): void {
  cachedToken = null;
  tokenExpiresAt = 0;
}

/**
 * Make an authenticated fetch request. Acquires a token automatically and, if the
 * backend rejects it (expired, or the server restarted with a new secret), mints a
 * new one and retries once.
 */
async function authFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const attempt = async (): Promise<Response> => {
    const token = await acquireToken();
    const headers = new Headers(options.headers);
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
    return fetch(url, { ...options, headers });
  };

  const res = await attempt();
  if (res.status !== 401) return res;
  invalidateToken();
  return attempt();
}

// --- Backend Health ---

let isBackendAvailable: boolean | null = null;

/**
 * Check if the backend is reachable (health endpoint is public, no auth needed).
 */
export async function checkBackendHealth(): Promise<boolean> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 1500);
    const res = await fetch(`${apiBase()}/api/health`, {
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    isBackendAvailable = res.ok;
    if (res.ok) {
      // Pre-acquire token in background so it's ready for subsequent calls
      acquireToken();
    }
    return res.ok;
  } catch {
    isBackendAvailable = false;
    return false;
  }
}

export function getBackendStatus(): boolean | null {
  return isBackendAvailable;
}

/**
 * Fetch hardware profile with fallback.
 */
export async function fetchHardware(): Promise<HardwareProfile> {
  try {
    const res = await authFetch(`${apiBase()}/api/hardware`);
    if (!res.ok) throw new Error(`Hardware endpoint error (${res.status})`);
    isBackendAvailable = true;
    return await res.json();
  } catch (e) {
    if (DEMO_MODE) return mockHardware;
    throw e;
  }
}

/**
 * Fetch knowledge store stats with fallback.
 */
export async function fetchFactStats(): Promise<FactStoreStats> {
  try {
    const res = await authFetch(`${apiBase()}/api/facts/stats`);
    if (!res.ok) throw new Error(`Stats endpoint error (${res.status})`);
    isBackendAvailable = true;
    const data = await res.json();
    return {
      total_facts: data.total_facts ?? 0,
      negated_count: data.negated_count ?? 0,
      modality_breakdown: data.modality_breakdown ?? {},
      attributed_count: data.modality_breakdown?.attributed ?? 0,
      conditional_count: data.modality_breakdown?.conditional ?? 0,
      avg_sdh_score: data.avg_sdh_score ?? 0,
    };
  } catch (e) {
    if (DEMO_MODE) return mockFactStoreStats;
    throw e;
  }
}

/**
 * Fetch document list with fallback.
 */
export async function fetchDocuments(): Promise<Document[]> {
  try {
    const res = await authFetch(`${apiBase()}/api/documents`);
    if (!res.ok) throw new Error(`Documents endpoint error (${res.status})`);
    isBackendAvailable = true;
    const data = await res.json();
    // The backend reports only name and fact count; do not invent dates or sizes.
    return (data.documents || []).map((doc: { name: string; fact_count: number }) => ({
      id: doc.name,
      name: doc.name,
      fact_count: doc.fact_count,
    }));
  } catch (e) {
    if (DEMO_MODE) return mockDocuments;
    throw e;
  }
}

/**
 * Delete a specific document by name.
 */
export async function deleteDocument(name: string): Promise<boolean> {
  try {
    const res = await authFetch(`${apiBase()}/api/documents/${encodeURIComponent(name)}`, {
      method: "DELETE",
    });
    return res.ok;
  } catch {
    return false;
  }
}

/**
 * Clear all facts from the store.
 */
export async function clearAllFacts(): Promise<boolean> {
  try {
    const res = await authFetch(`${apiBase()}/api/facts`, {
      method: "DELETE",
    });
    return res.ok;
  } catch {
    return false;
  }
}

/**
 * Ingest document via REST.
 */
export async function ingestDocumentRest(
  text: string,
  documentName: string,
): Promise<{
  success: boolean;
  document_name: string;
  facts_stored: number;
  facts_extracted?: number;
  latency_ms?: number;
}> {
  try {
    const res = await authFetch(`${apiBase()}/api/ingest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, document_name: documentName }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Ingest failed" }));
      throw new Error(err.detail || "Ingest failed");
    }
    const data = await res.json();
    return {
      success: true,
      document_name: data.document_name,
      facts_stored: data.facts_stored,
      facts_extracted: data.facts_extracted,
      latency_ms: data.latency_ms,
    };
  } catch (e) {
    // Simulated result is only allowed in explicit demo mode
    if (DEMO_MODE && isBackendAvailable === false) {
      return {
        success: true,
        document_name: documentName || "document.txt",
        facts_stored: Math.max(12, Math.round(text.split(".").length * 2.5)),
      };
    }
    throw e;
  }
}

/**
 * Fetch all facts from backend for the FactExplorer.
 * Returns live data; mock data only in explicit demo mode, otherwise throws.
 */
export async function fetchAllFacts(
  documentName?: string,
): Promise<{ facts: Fact[]; isLive: boolean; total: number }> {
  try {
    const queryParams = new URLSearchParams();
    queryParams.set("limit", "1000");
    if (documentName) queryParams.set("source_doc", documentName);

    const res = await authFetch(`${apiBase()}/api/facts?${queryParams.toString()}`);
    if (!res.ok) throw new Error(`Facts endpoint error (${res.status})`);
    const data = await res.json();
    const facts = (data.facts || []) as Fact[];
    return {
      facts,
      isLive: true,
      total: typeof data.total === "number" ? data.total : facts.length,
    };
  } catch (e) {
    if (DEMO_MODE) return { facts: mockFacts, isLive: false, total: mockFacts.length };
    throw e;
  }
}

export interface HardwareTier {
  mode: string;
  label: string;
  model: string;
  token_ceiling: number;
  /** null when Ollama could not be reached. */
  installed: boolean | null;
}

export interface ModelsInfo {
  ollama_reachable: boolean;
  ollama_url: string;
  installed: string[];
  detected_mode: string;
  default_model: string;
  default_token_ceiling: number;
  list_extraction_enabled: boolean;
  tiers: HardwareTier[];
}

/** Installed Ollama models and the hardware tiers (null if the backend is unreachable). */
export async function fetchModels(): Promise<ModelsInfo | null> {
  try {
    const res = await authFetch(`${apiBase()}/api/models`);
    return res.ok ? await res.json() : null;
  } catch {
    return null;
  }
}

export interface SecurityCheckResult {
  accepted: boolean;
  reason: string | null;
  intent: string | null;
  answer_source: string | null;
  relevance?: number | null;
  has_documents?: boolean;
}

/** Run text through the backend's real sanitiser, injection filter and chat router. */
export async function checkSecurity(text: string): Promise<SecurityCheckResult | null> {
  try {
    const res = await authFetch(`${apiBase()}/api/security/check`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    return res.ok ? await res.json() : null;
  } catch {
    return null;
  }
}

/** This browser's access token state, without exposing the token itself. */
export function getTokenInfo(): { clientId: string | null; expiresAt: number | null } {
  return {
    clientId: getClientId(),
    expiresAt: cachedToken && tokenExpiresAt > Date.now() ? tokenExpiresAt : null,
  };
}

/** Make sure a token is held (minting one if needed); returns its expiry time. */
export async function ensureToken(): Promise<number | null> {
  const token = await acquireToken();
  return token ? tokenExpiresAt : null;
}

/**
 * Ask the backend's local model for a short title for a new chat.
 * Returns null on any failure, so callers keep their fallback title.
 */
export async function fetchChatTitle(question: string, answer: string): Promise<string | null> {
  try {
    const res = await authFetch(`${apiBase()}/api/chat/title`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, answer, options: getQueryOptions() }),
    });
    if (!res.ok) return null;
    const data = await res.json();
    return typeof data.title === "string" && data.title.trim() ? data.title.trim() : null;
  } catch {
    return null;
  }
}

/** One earlier turn of the conversation, sent with a query for follow-up context. */
export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
  /** True when the assistant answered from the documents. */
  grounded?: boolean;
}

/**
 * The last completed question/answer pairs of a conversation, oldest first.
 * Failed answers and questions left without an answer (stopped) are skipped,
 * since the backend never answered them.
 */
export function buildChatHistory(messages: Message[], maxTurns = 6): ChatTurn[] {
  const turns: ChatTurn[] = [];
  for (let i = 0; i + 1 < messages.length; i++) {
    const question = messages[i];
    const answer = messages[i + 1];
    // The prefix catches error messages saved before `failed` existed.
    const failed = answer.failed || answer.content.startsWith("Pipeline query failed:");
    if (question.role !== "user" || answer.role !== "ai" || failed) continue;
    const response = answer.query_response;
    turns.push(
      { role: "user", content: question.content },
      {
        role: "assistant",
        content: response?.answer || answer.content,
        grounded:
          response?.answer_source === "document" ||
          (response?.answer_source === undefined && (response?.facts_used?.length ?? 0) > 0),
      },
    );
    i++;
  }
  return turns.slice(-maxTurns);
}

/**
 * Run Query via WebSocket with progressive token & stage streaming.
 * Reports an error if the backend is unreachable or the connection drops
 * (simulated execution only in explicit demo mode).
 */
export function streamQueryPipeline(
  question: string,
  callbacks: {
    onStage: (event: PipelineEvent) => void;
    onToken: (token: string) => void;
    onDone: (response: QueryResponse) => void;
    onError: (err: string) => void;
  },
  sessionId?: string,
  history?: ChatTurn[],
): () => void {
  const CONNECT_TIMEOUT_MS = 10_000;

  let ws: WebSocket | null = null;
  let isCancelled = false;
  let settled = false;
  let connectTimer: ReturnType<typeof setTimeout> | undefined;

  const closeSocket = () => {
    clearTimeout(connectTimer);
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
      ws.close();
    }
  };

  const cleanup = () => {
    isCancelled = true;
    closeSocket();
  };

  const handleDone = (response: QueryResponse) => {
    if (settled || isCancelled) return;
    settled = true;
    closeSocket();
    callbacks.onDone(response);
  };

  const handleError = (err: string) => {
    if (settled || isCancelled) return;
    settled = true;
    closeSocket();
    callbacks.onError(err);
  };

  // Connection-level failure: simulated run in demo mode, otherwise a real error.
  const failConnection = (err: string) => {
    if (settled || isCancelled) return;
    if (DEMO_MODE) {
      settled = true;
      closeSocket();
      runMockQueryPipeline(question, callbacks, () => isCancelled, sessionId);
      return;
    }
    handleError(err);
  };

  // Ensure we have a valid token before connecting
  acquireToken()
    .then((token) => {
      if (isCancelled || settled) return;

      if (!token) {
        failConnection("Could not authenticate with the backend. Is it running?");
        return;
      }

      try {
        // The token is sent once, in the auth message, so it never appears in a URL or access log.
        ws = new WebSocket(wsBase());

        connectTimer = setTimeout(() => {
          if (ws && ws.readyState !== WebSocket.OPEN) {
            failConnection("Timed out connecting to the backend.");
          }
        }, CONNECT_TIMEOUT_MS);

        ws.onopen = () => {
          clearTimeout(connectTimer);
          if (settled || isCancelled) return;
          ws?.send(JSON.stringify({ type: "auth", token }));
        };

        ws.onmessage = (event) => {
          if (isCancelled || settled) return;
          try {
            const data = JSON.parse(event.data);
            if (data.type === "auth_ok") {
              ws?.send(
                JSON.stringify({
                  type: "query",
                  question,
                  session_id: sessionId || undefined,
                  options: getQueryOptions(),
                  // The conversation as shown, so cleared or regenerated turns never
                  // linger in the backend's follow-up context.
                  history,
                }),
              );
              return;
            }
            if (data.type === "pipeline:stage") {
              // Backend stage events may omit count/error; the UI expects both.
              callbacks.onStage({ count: 0, error: null, ...data.payload });
            } else if (data.type === "pipeline:token") {
              callbacks.onToken(data.payload.char);
            } else if (data.type === "pipeline:done") {
              const payload = data.payload;
              handleDone({
                ...payload,
                compression_rate: payload.compression_rate ?? 0,
              });
            } else if (data.type === "error") {
              // A rejected token is stale; mint a new one on the next attempt.
              if (/(invalid|expired).*token|authentication required/i.test(data.detail || ""))
                invalidateToken();
              handleError(data.detail || "Pipeline error");
            }
          } catch (e: unknown) {
            const msg = e instanceof Error ? e.message : "Parse error";
            handleError(msg);
          }
        };

        ws.onerror = () => {
          failConnection("Could not reach the backend.");
        };

        ws.onclose = () => {
          // A close before pipeline:done / error would otherwise leave the UI streaming forever.
          failConnection("Connection closed before the answer completed.");
        };
      } catch {
        failConnection("Could not open a connection to the backend.");
      }
    })
    .catch(() => {
      failConnection("Could not authenticate with the backend. Is it running?");
    });

  return cleanup;
}

/**
 * High-fidelity simulated pipeline for offline/demo mode.
 */
async function runMockQueryPipeline(
  _question: string,
  callbacks: {
    onStage: (event: PipelineEvent) => void;
    onToken: (token: string) => void;
    onDone: (response: QueryResponse) => void;
    onError: (err: string) => void;
  },
  isCancelled: () => boolean,
  sessionId?: string,
) {
  for (const stageEvent of mockPipelineEvents) {
    if (isCancelled()) return;
    callbacks.onStage({
      ...stageEvent,
      status: "running",
      detail: `Executing ${stageEvent.stage_name}...`,
    });
    await new Promise((r) => setTimeout(r, 180));

    if (isCancelled()) return;
    callbacks.onStage(stageEvent);
    await new Promise((r) => setTimeout(r, 120));
  }

  if (isCancelled()) return;

  // Filter relevant mock facts or use standard ones
  const relevantFacts: Fact[] = mockFacts.slice(0, 5);
  const words = mockQueryResponse.answer.split(" ");

  for (const word of words) {
    if (isCancelled()) return;
    callbacks.onToken(word + " ");
    await new Promise((r) => setTimeout(r, 25));
  }

  if (isCancelled()) return;

  callbacks.onDone({
    ...mockQueryResponse,
    facts_used: relevantFacts,
    session_id: sessionId || mockQueryResponse.session_id || null,
    latency_ms: 640 + Math.floor(Math.random() * 200),
  });
}
