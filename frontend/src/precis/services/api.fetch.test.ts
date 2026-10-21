import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

type Reply = { status: number; body?: unknown };

/** Fetch stub: token requests always succeed; other calls pop scripted replies. */
function stubBackend(replies: Reply[]) {
  let tokens = 0;
  const calls: { url: string; auth: string | null }[] = [];
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    if (url.endsWith("/api/auth/token")) {
      tokens += 1;
      return {
        ok: true,
        status: 200,
        json: async () => ({ access_token: `tok${tokens}`, expires_in: 86400 }),
      };
    }
    calls.push({ url, auth: new Headers(init?.headers).get("Authorization") });
    const reply = replies.shift() ?? { status: 200, body: {} };
    return {
      ok: reply.status >= 200 && reply.status < 300,
      status: reply.status,
      json: async () => reply.body,
    };
  });
  vi.stubGlobal("fetch", fetchMock);
  return { calls, tokens: () => tokens };
}

async function freshApi() {
  vi.resetModules();
  return import("./api");
}

describe("backend fetch helpers", () => {
  beforeEach(() => vi.unstubAllGlobals());
  afterEach(() => vi.unstubAllGlobals());

  it("maps documents without inventing dates or sizes", async () => {
    stubBackend([{ status: 200, body: { documents: [{ name: "a.txt", fact_count: 3 }] } }]);
    const { fetchDocuments } = await freshApi();
    const docs = await fetchDocuments();
    expect(docs).toEqual([{ id: "a.txt", name: "a.txt", fact_count: 3 }]);
  });

  it("throws on a server error instead of returning mock data", async () => {
    stubBackend([{ status: 500 }]);
    const { fetchDocuments, fetchHardware } = await freshApi();
    await expect(fetchDocuments()).rejects.toThrow(/500/);
    stubBackend([{ status: 500 }]);
    await expect(fetchHardware()).rejects.toThrow();
  });

  it("throws when the backend is unreachable", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => Promise.reject(new TypeError("network"))),
    );
    const { fetchAllFacts } = await freshApi();
    await expect(fetchAllFacts()).rejects.toThrow();
  });

  it("retries once with a fresh token after a 401", async () => {
    const backend = stubBackend([{ status: 401 }, { status: 200, body: { documents: [] } }]);
    const { fetchDocuments } = await freshApi();
    await expect(fetchDocuments()).resolves.toEqual([]);
    expect(backend.calls.map((c) => c.auth)).toEqual(["Bearer tok1", "Bearer tok2"]);
  });

  it("gives up after a second 401", async () => {
    stubBackend([{ status: 401 }, { status: 401 }]);
    const { fetchDocuments } = await freshApi();
    await expect(fetchDocuments()).rejects.toThrow(/401/);
  });

  it("reports the real fact total, not the page size", async () => {
    stubBackend([{ status: 200, body: { facts: [{}, {}], total: 57 } }]);
    const { fetchAllFacts } = await freshApi();
    const result = await fetchAllFacts();
    expect(result.facts).toHaveLength(2);
    expect(result.total).toBe(57);
    expect(result.isLive).toBe(true);
  });

  it("surfaces the backend's message when ingest is rejected", async () => {
    stubBackend([{ status: 400, body: { detail: "Input rejected: suspicious content detected" } }]);
    const { ingestDocumentRest } = await freshApi();
    await expect(ingestDocumentRest("text", "doc")).rejects.toThrow(/suspicious/);
  });

  it("encodes document names with slashes when deleting", async () => {
    const backend = stubBackend([{ status: 200 }]);
    const { deleteDocument } = await freshApi();
    await deleteDocument("folder/a b.txt");
    expect(backend.calls[0]!.url).toContain("folder%2Fa%20b.txt");
  });
});
