import { describe, expect, it } from "vitest";
import { KNOWN_TABS, parsePath } from "./router";

describe("parsePath", () => {
  it("maps each known tab", () => {
    for (const tab of KNOWN_TABS) {
      expect(parsePath(`/${tab}`, "").activeTab).toBe(tab);
    }
  });

  it("extracts the conversation id from /chat/<id>", () => {
    expect(parsePath("/chat/conv-abc", "")).toMatchObject({
      activeTab: "chat",
      conversationId: "conv-abc",
    });
  });

  it("treats / and /chat as the chat tab without a conversation", () => {
    expect(parsePath("/", "").activeTab).toBe("chat");
    expect(parsePath("/chat", "").conversationId).toBeUndefined();
  });

  it("ignores a trailing slash", () => {
    expect(parsePath("/documents/", "").path).toBe("/documents");
  });

  it("prefers a legacy #/hash route over the pathname", () => {
    expect(parsePath("/", "#/settings").activeTab).toBe("settings");
  });

  it("falls back to chat for unknown paths", () => {
    expect(parsePath("/nope", "")).toMatchObject({ path: "/chat", activeTab: "chat" });
  });
});
