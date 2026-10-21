import { describe, expect, it } from "vitest";
import {
  createConversation,
  deleteConversation,
  getActiveConversationId,
  loadConversations,
  loadMessages,
  renameConversation,
  saveMessages,
} from "./storage";
import type { Message } from "../types/api";

const message = (id: string): Message =>
  ({ id, role: "user", content: id, timestamp: "", pipeline_events: [] }) as unknown as Message;

describe("conversation storage", () => {
  it("starts with one empty conversation and no demo data", () => {
    const convs = loadConversations();
    expect(convs).toHaveLength(1);
    expect(convs[0]).toMatchObject({ title: "New Query Session", document: "", message_count: 0 });
    expect(loadMessages(convs[0]!.id)).toEqual([]);
    expect(JSON.stringify(convs)).not.toContain("climate");
  });

  it("returns the same conversations on subsequent loads", () => {
    const first = loadConversations();
    expect(loadConversations()).toEqual(first);
  });

  it("creates a conversation, makes it active and puts it first", () => {
    loadConversations();
    const created = createConversation("Second");
    expect(loadConversations()[0]!.id).toBe(created.id);
    expect(getActiveConversationId()).toBe(created.id);
  });

  it("round-trips messages per conversation", () => {
    const [a] = loadConversations();
    const b = createConversation("B");
    saveMessages(a!.id, [message("1")]);
    saveMessages(b.id, [message("2"), message("3")]);
    expect(loadMessages(a!.id).map((m) => m.id)).toEqual(["1"]);
    expect(loadMessages(b.id).map((m) => m.id)).toEqual(["2", "3"]);
  });

  it("deletes a conversation together with its messages", () => {
    const [a] = loadConversations();
    const b = createConversation("B");
    saveMessages(b.id, [message("x")]);
    const remaining = deleteConversation(b.id);
    expect(remaining.map((c) => c.id)).toEqual([a!.id]);
    expect(loadMessages(b.id)).toEqual([]);
  });

  it("renames, ignoring blank titles", () => {
    const [a] = loadConversations();
    expect(renameConversation(a!.id, "  Revenue  ")?.title).toBe("Revenue");
    expect(renameConversation(a!.id, "   ")).toBeUndefined();
    expect(loadConversations()[0]!.title).toBe("Revenue");
  });

  it("survives corrupt stored JSON", () => {
    localStorage.setItem("precis_conversations", "{not json");
    expect(loadConversations()).toHaveLength(1);
  });
});
