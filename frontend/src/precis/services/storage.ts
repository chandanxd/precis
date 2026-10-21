// @ts-nocheck — ported code written for a less strict TS config
import type { Conversation, Message } from "../types/api";
import { mockConversations, mockMessages } from "../mocks/data";
import { DEMO_MODE } from "./demo";

const CONVERSATIONS_KEY = "precis_conversations";
const MESSAGES_PREFIX = "precis_messages_";
const ACTIVE_CONV_KEY = "precis_active_conv_id";
const SIDEBAR_COLLAPSED_KEY = "precis_sidebar_collapsed";

/**
 * Initializes and retrieves conversation list from localStorage.
 * Seeds with mockConversations if localStorage is empty.
 */
export function loadConversations(): Conversation[] {
  try {
    const stored = localStorage.getItem(CONVERSATIONS_KEY);
    if (stored) {
      const parsed = JSON.parse(stored) as Conversation[];
      if (Array.isArray(parsed) && parsed.length > 0) {
        return parsed;
      }
    }
  } catch {
    // fallback to seed
  }

  if (DEMO_MODE) {
    // Seed mock conversations and conv-001 messages
    saveConversations(mockConversations);
    saveMessages("conv-001", mockMessages);
    return mockConversations;
  }

  // Real mode: start with a single empty conversation
  const blank: Conversation = {
    id: `conv-${crypto.randomUUID()}`,
    title: "New Query Session",
    document: "",
    created_at: new Date().toISOString(),
    message_count: 0,
  };
  saveConversations([blank]);
  saveMessages(blank.id, []);
  return [blank];
}

/**
 * Persists conversations array to localStorage.
 */
export function saveConversations(conversations: Conversation[]): void {
  try {
    localStorage.setItem(CONVERSATIONS_KEY, JSON.stringify(conversations));
  } catch {
    // ignore storage errors
  }
}

/**
 * Loads messages for a given conversation.
 */
export function loadMessages(convId: string): Message[] {
  try {
    const stored = localStorage.getItem(`${MESSAGES_PREFIX}${convId}`);
    if (stored) {
      const parsed = JSON.parse(stored) as Message[];
      if (Array.isArray(parsed)) {
        return parsed;
      }
    }
  } catch {
    // fallback
  }

  // If it's the primary demo conversation and has no stored data, seed it
  if (DEMO_MODE && convId === "conv-001") {
    saveMessages("conv-001", mockMessages);
    return mockMessages;
  }

  return [];
}

/**
 * Persists messages for a given conversation.
 */
export function saveMessages(convId: string, messages: Message[]): void {
  try {
    localStorage.setItem(`${MESSAGES_PREFIX}${convId}`, JSON.stringify(messages));
  } catch {
    // ignore storage errors
  }
}

/**
 * Creates a brand new conversation thread.
 */
export function createConversation(title = "New Query Session", document = ""): Conversation {
  const conversations = loadConversations();
  const newId = `conv-${crypto.randomUUID()}`;
  const newConv: Conversation = {
    id: newId,
    title,
    document,
    created_at: new Date().toISOString(),
    message_count: 0,
  };

  const updated = [newConv, ...conversations];
  saveConversations(updated);
  saveMessages(newId, []);
  setActiveConversationId(newId);
  return newConv;
}

/**
 * Deletes a conversation and its messages.
 */
export function deleteConversation(id: string): Conversation[] {
  const conversations = loadConversations();
  const updated = conversations.filter((c) => c.id !== id);
  saveConversations(updated);

  try {
    localStorage.removeItem(`${MESSAGES_PREFIX}${id}`);
  } catch {
    // ignore
  }

  return updated;
}

/**
 * Renames an existing conversation.
 */
export function renameConversation(id: string, newTitle: string): Conversation | undefined {
  const trimmed = newTitle.trim();
  if (!trimmed) return undefined;

  const conversations = loadConversations();
  const target = conversations.find((c) => c.id === id);
  if (!target) return undefined;

  target.title = trimmed;
  saveConversations(conversations);
  return target;
}

/**
 * Gets currently active conversation ID from storage.
 */
export function getActiveConversationId(): string {
  try {
    const stored = localStorage.getItem(ACTIVE_CONV_KEY);
    if (stored) return stored;
  } catch {
    // ignore
  }
  const convs = loadConversations();
  const first = convs[0]?.id || "conv-001";
  setActiveConversationId(first);
  return first;
}

/**
 * Sets active conversation ID in storage.
 */
export function setActiveConversationId(id: string): void {
  try {
    localStorage.setItem(ACTIVE_CONV_KEY, id);
  } catch {
    // ignore
  }
}

/**
 * Gets sidebar collapsed state.
 */
export function getSidebarCollapsed(): boolean {
  try {
    const stored = localStorage.getItem(SIDEBAR_COLLAPSED_KEY);
    return stored === "true";
  } catch {
    return false;
  }
}

/**
 * Sets sidebar collapsed state.
 */
export function setSidebarCollapsed(collapsed: boolean): void {
  try {
    localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(collapsed));
  } catch {
    // ignore
  }
}
