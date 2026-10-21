// @ts-nocheck — ported code written for a less strict TS config
import type { UserSettings } from "../types/api";
import {
  loadConversations,
  saveConversations,
  loadMessages,
  saveMessages,
  setActiveConversationId,
} from "./storage";
import { mockConversations, mockMessages } from "../mocks/data";
import { DEMO_MODE } from "./demo";

const SETTINGS_KEY = "precis_settings";

export const DEFAULT_SETTINGS: UserSettings = {
  ollamaModel: "",
  tokenCeiling: null,
  devicePreset: "auto",
  temperature: 0.3,
  allowedModalities: {
    asserted: true,
    attributed: true,
    conditional: true,
    hypothetical: false,
  },
  defaultEvidenceExpanded: false,
  theme: "dark",
  version: 2,
};

// Version-1 defaults. They were never sent to the backend (only changed values
// were), so a stored copy of them means "let the backend decide".
const V1_DEFAULT_MODEL = "llama3:8b-q4_K_M";
const V1_DEFAULT_CEILING = 4096;

/** Bring stored or imported settings to the current format, dropping unknown keys. */
export function normalizeSettings(
  raw: Partial<UserSettings> & Record<string, unknown>,
): UserSettings {
  const s = { ...DEFAULT_SETTINGS };
  const legacy = raw.version !== 2;
  if (typeof raw.ollamaModel === "string") {
    s.ollamaModel = legacy && raw.ollamaModel === V1_DEFAULT_MODEL ? "" : raw.ollamaModel.trim();
  }
  if (typeof raw.tokenCeiling === "number") {
    s.tokenCeiling = legacy && raw.tokenCeiling === V1_DEFAULT_CEILING ? null : raw.tokenCeiling;
  }
  if (typeof raw.devicePreset === "string") s.devicePreset = raw.devicePreset;
  else if (s.ollamaModel || s.tokenCeiling !== null) s.devicePreset = "custom";
  if (typeof raw.temperature === "number") s.temperature = raw.temperature;
  if (raw.allowedModalities && typeof raw.allowedModalities === "object") {
    s.allowedModalities = { ...DEFAULT_SETTINGS.allowedModalities, ...raw.allowedModalities };
  }
  if (typeof raw.defaultEvidenceExpanded === "boolean") {
    s.defaultEvidenceExpanded = raw.defaultEvidenceExpanded;
  }
  if (raw.theme === "light" || raw.theme === "dark") s.theme = raw.theme;
  return s;
}

/**
 * Per-query options sent to the backend. The model and token ceiling are sent
 * only when chosen (not "auto"), so otherwise the backend's hardware-calibrated
 * values apply; the other options only when changed from their defaults.
 */
export function getQueryOptions(): Record<string, unknown> {
  const s = loadSettings();
  const d = DEFAULT_SETTINGS;
  const options: Record<string, unknown> = {};
  if (s.ollamaModel) options.model = s.ollamaModel;
  if (s.tokenCeiling !== null) options.token_ceiling = s.tokenCeiling;
  if (s.temperature !== d.temperature) options.temperature = s.temperature;
  const modalities = Object.keys(s.allowedModalities) as (keyof typeof s.allowedModalities)[];
  if (modalities.some((m) => s.allowedModalities[m] !== d.allowedModalities[m])) {
    options.allowed_modalities = modalities.filter((m) => s.allowedModalities[m]);
  }
  return options;
}

/**
 * Loads user settings from localStorage or returns defaults.
 */
export function loadSettings(): UserSettings {
  try {
    const stored = localStorage.getItem(SETTINGS_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      if (parsed && typeof parsed === "object") return normalizeSettings(parsed);
    }
  } catch {
    // fallback
  }
  return { ...DEFAULT_SETTINGS };
}

/**
 * Persists user settings to localStorage.
 */
export function saveSettings(settings: UserSettings): void {
  try {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
  } catch {
    // ignore
  }
}

/**
 * Exports all research conversations, messages, and settings into a JSON bundle.
 */
export function exportAllData(): string {
  const convs = loadConversations();
  const allMessages: Record<string, unknown> = {};

  for (const c of convs) {
    allMessages[c.id] = loadMessages(c.id);
  }

  const bundle = {
    app: "PRÉCIS",
    version: "0.1.0",
    exported_at: new Date().toISOString(),
    settings: loadSettings(),
    conversations: convs,
    messages: allMessages,
  };

  return JSON.stringify(bundle, null, 2);
}

/**
 * Imports research conversations, messages, and settings from a JSON bundle.
 */
export function importAllData(jsonStr: string): {
  success: boolean;
  conversationCount: number;
  error?: string;
} {
  try {
    const parsed = JSON.parse(jsonStr);
    if (!parsed || !Array.isArray(parsed.conversations)) {
      return {
        success: false,
        conversationCount: 0,
        error: "Invalid backup format: missing conversations array",
      };
    }

    // Save conversations
    saveConversations(parsed.conversations);

    // Save messages
    if (parsed.messages && typeof parsed.messages === "object") {
      for (const [convId, msgs] of Object.entries(parsed.messages)) {
        if (Array.isArray(msgs)) {
          saveMessages(convId, msgs);
        }
      }
    }

    // Save settings if present
    if (parsed.settings && typeof parsed.settings === "object") {
      saveSettings(normalizeSettings(parsed.settings));
    }

    if (parsed.conversations.length > 0) {
      setActiveConversationId(parsed.conversations[0].id);
    }

    return {
      success: true,
      conversationCount: parsed.conversations.length,
    };
  } catch (e) {
    return {
      success: false,
      conversationCount: 0,
      error: e instanceof Error ? e.message : "Failed to parse JSON file",
    };
  }
}

/**
 * Resets all stored data back to the demo baseline.
 */
export function resetToDemoBaseline(): void {
  try {
    // Clear all precis_* keys
    const keysToRemove: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      // Keep the client ID: it is what ties this browser to its backend documents.
      if (key && key.startsWith("precis_") && key !== "precis_client_id") {
        keysToRemove.push(key);
      }
    }
    for (const k of keysToRemove) {
      localStorage.removeItem(k);
    }

    saveSettings(DEFAULT_SETTINGS);
    if (DEMO_MODE) {
      saveConversations(mockConversations);
      saveMessages("conv-001", mockMessages);
      setActiveConversationId("conv-001");
    }
    // Otherwise no conversations remain; the next message starts a new one.
  } catch {
    // ignore
  }
}
