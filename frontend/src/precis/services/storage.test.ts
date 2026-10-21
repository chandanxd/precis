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
  it("starts with no conversations and no demo data", () => {
    expect(loadConversations()).toEqual([]);
    expect(localStorage.getItem("precis_conversations")).toBeNull();
  });

  it("gives an unsaved draft ID when there is no conversation yet", () => {
    const id = getActiveConversationId();
    expect(id).toMatch(/^conv-/);
    expect(loadConversations()).toEqual([]);
  });

  it("creates a conversation under a given ID", () => {
    const created = createConversation("Draft", "", "conv-draft");
    expect(created.id).toBe("conv-draft");
    expect(loadConversations().map((c) => c.id)).toEqual(["conv-draft"]);
  });

  it("returns the same conversations on subsequent loads", () => {
    createConversation("A");
    const first = loadConversations();
    expect(loadConversations()).toEqual(first);
  });

  it("creates a conversation, makes it active and puts it first", () => {
    createConversation("First");
    const created = createConversation("Second");
    expect(loadConversations()[0]!.id).toBe(created.id);
    expect(getActiveConversationId()).toBe(created.id);
  });

  it("round-trips messages per conversation", () => {
    const a = createConversation("A");
    const b = createConversation("B");
    saveMessages(a.id, [message("1")]);
    saveMessages(b.id, [message("2"), message("3")]);
    expect(loadMessages(a.id).map((m) => m.id)).toEqual(["1"]);
    expect(loadMessages(b.id).map((m) => m.id)).toEqual(["2", "3"]);
  });

  it("deletes a conversation together with its messages", () => {
    const a = createConversation("A");
    const b = createConversation("B");
    saveMessages(b.id, [message("x")]);
    const remaining = deleteConversation(b.id);
    expect(remaining.map((c) => c.id)).toEqual([a.id]);
    expect(loadMessages(b.id)).toEqual([]);
  });

  it("renames, ignoring blank titles", () => {
    const a = createConversation("A");
    expect(renameConversation(a.id, "  Revenue  ")?.title).toBe("Revenue");
    expect(renameConversation(a.id, "   ")).toBeUndefined();
    expect(loadConversations()[0]!.title).toBe("Revenue");
  });

  it("survives corrupt stored JSON", () => {
    localStorage.setItem("precis_conversations", "{not json");
    expect(loadConversations()).toEqual([]);
  });
});
