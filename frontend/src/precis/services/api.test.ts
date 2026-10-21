import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { streamQueryPipeline } from "./api";
import { CLIENT_ID_KEY } from "./api";

class FakeWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;
  static last: FakeWebSocket | null = null;

  readyState = FakeWebSocket.CONNECTING;
  sent: string[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  onclose: (() => void) | null = null;

  constructor(public url: string) {
    FakeWebSocket.last = this;
  }
  send(data: string) {
    this.sent.push(data);
  }
  close() {
    this.readyState = FakeWebSocket.CLOSED;
    this.onclose?.();
  }
  open() {
    this.readyState = FakeWebSocket.OPEN;
    this.onopen?.();
  }
  emit(msg: unknown) {
    this.onmessage?.({ data: JSON.stringify(msg) });
  }
}

const flush = () => new Promise((r) => setTimeout(r, 0));

function makeCallbacks() {
  return { onStage: vi.fn(), onToken: vi.fn(), onDone: vi.fn(), onError: vi.fn() };
}

describe("streamQueryPipeline", () => {
  beforeEach(() => {
    FakeWebSocket.last = null;
    vi.stubGlobal("WebSocket", FakeWebSocket);
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        json: async () => ({ access_token: "tok", expires_in: 86400 }),
      })),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("reports an error when the socket closes before completion", async () => {
    const cb = makeCallbacks();
    streamQueryPipeline("q", cb);
    await flush();
    FakeWebSocket.last!.open();
    FakeWebSocket.last!.readyState = FakeWebSocket.CLOSED;
    FakeWebSocket.last!.onclose?.();
    expect(cb.onError).toHaveBeenCalledTimes(1);
    expect(cb.onDone).not.toHaveBeenCalled();
  });

  it("reports connection errors instead of simulating an answer", async () => {
    const cb = makeCallbacks();
    streamQueryPipeline("q", cb);
    await flush();
    FakeWebSocket.last!.onerror?.();
    expect(cb.onError).toHaveBeenCalledTimes(1);
    expect(cb.onToken).not.toHaveBeenCalled();
    expect(cb.onDone).not.toHaveBeenCalled();
  });

  it("completes once and ignores the close that follows", async () => {
    const cb = makeCallbacks();
    streamQueryPipeline("q", cb);
    await flush();
    const ws = FakeWebSocket.last!;
    ws.open();
    ws.emit({ type: "pipeline:done", payload: { answer: "a", facts_used: [] } });
    expect(cb.onDone).toHaveBeenCalledTimes(1);
    expect(cb.onError).not.toHaveBeenCalled();
  });

  it("surfaces a server error message once", async () => {
    const cb = makeCallbacks();
    streamQueryPipeline("q", cb);
    await flush();
    const ws = FakeWebSocket.last!;
    ws.open();
    ws.emit({ type: "error", detail: "boom" });
    expect(cb.onError).toHaveBeenCalledWith("boom");
    expect(cb.onError).toHaveBeenCalledTimes(1);
  });

  it("stays silent after cancel", async () => {
    const cb = makeCallbacks();
    const cancel = streamQueryPipeline("q", cb);
    await flush();
    FakeWebSocket.last!.open();
    cancel();
    FakeWebSocket.last!.emit({ type: "pipeline:done", payload: { answer: "a" } });
    expect(cb.onDone).not.toHaveBeenCalled();
    expect(cb.onError).not.toHaveBeenCalled();
  });

  it("errors when no token can be obtained", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: false, json: async () => ({}) })),
    );
    // Fresh module: the token cache is module-level state.
    vi.resetModules();
    const fresh = await import("./api");
    const cb = makeCallbacks();
    fresh.streamQueryPipeline("q", cb);
    await flush();
    expect(cb.onError).toHaveBeenCalledTimes(1);
  });

  it("sends the token once in an auth message, then the query after auth_ok", async () => {
    const cb = makeCallbacks();
    streamQueryPipeline("what?", cb, "sess");
    await flush();
    const ws = FakeWebSocket.last!;
    expect(ws.url).not.toContain("token");
    ws.open();
    expect(ws.sent.map((m) => JSON.parse(m).type)).toEqual(["auth"]);
    ws.emit({ type: "auth_ok" });
    const query = JSON.parse(ws.sent[1]!);
    expect(query).toMatchObject({ type: "query", question: "what?", session_id: "sess" });
    expect(query.token).toBeUndefined();
  });

  it("refreshes the token after the backend rejects it", async () => {
    vi.resetModules();
    const fresh = await import("./api");
    const cb = makeCallbacks();
    fresh.streamQueryPipeline("q", cb);
    await flush();
    FakeWebSocket.last!.open();
    FakeWebSocket.last!.emit({ type: "error", detail: "Invalid or expired token." });
    expect(cb.onError).toHaveBeenCalledTimes(1);
    const mint = vi.mocked(fetch);
    const callsBefore = mint.mock.calls.length;
    fresh.streamQueryPipeline("q2", makeCallbacks());
    await flush();
    expect(mint.mock.calls.length).toBe(callsBefore + 1);
  });

  it("requests the token with a stable client id", async () => {
    const store = new Map<string, string>();
    vi.stubGlobal("localStorage", {
      getItem: (k: string) => store.get(k) ?? null,
      setItem: (k: string, v: string) => void store.set(k, v),
      removeItem: (k: string) => void store.delete(k),
    });
    vi.resetModules();
    const { streamQueryPipeline: stream, CLIENT_ID_KEY: key } = await import("./api");
    stream("q", makeCallbacks());
    await flush();
    const first = localStorage.getItem(key);
    expect(first).toMatch(/^client-[0-9a-f]{32}$/);
    vi.resetModules();
    const fresh = await import("./api");
    fresh.streamQueryPipeline("q", makeCallbacks());
    await flush();
    expect(localStorage.getItem(key)).toBe(first);
    const body = JSON.parse(vi.mocked(fetch).mock.calls.at(-1)![1]!.body as string);
    expect(body.client_id).toBe(first);
  });
});
