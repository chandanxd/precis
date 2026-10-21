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
  ollamaModel: "llama3:8b-q4_K_M",
  tokenCeiling: 4096,
  temperature: 0.3,
  ollamaBaseUrl: "http://localhost:11434",
  minSdhScore: 0.5,
  allowedModalities: {
    asserted: true,
    attributed: true,
    conditional: true,
    hypothetical: false,
  },
  strictNegation: true,
  defaultEvidenceExpanded: false,
  defaultSidebarCollapsed: false,
  theme: "dark",
};

/**
 * Per-query options sent to the backend. Only values the user changed from the
 * defaults are sent, so untouched defaults never override the backend's
 * hardware-calibrated model and token ceiling.
 */
export function getQueryOptions(): Record<string, unknown> {
  const s = loadSettings();
  const d = DEFAULT_SETTINGS;
  const options: Record<string, unknown> = {};
  if (s.ollamaModel && s.ollamaModel !== d.ollamaModel) options.model = s.ollamaModel;
  if (s.tokenCeiling !== d.tokenCeiling) options.token_ceiling = s.tokenCeiling;
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
      const parsed = JSON.parse(stored) as Partial<UserSettings>;
      return {
        ...DEFAULT_SETTINGS,
        ...parsed,
        allowedModalities: {
          ...DEFAULT_SETTINGS.allowedModalities,
          ...(parsed.allowedModalities || {}),
        },
      };
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
 * Test connectivity to an Ollama endpoint.
 */
export async function testOllamaConnection(
  baseUrl: string,
): Promise<{ success: boolean; latencyMs: number; message: string; models?: string[] }> {
  const cleanUrl = baseUrl.trim().replace(/\/+$/, "");
  const t0 = performance.now();

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2500);

    const res = await fetch(`${cleanUrl}/api/tags`, {
      signal: controller.signal,
      method: "GET",
    });
    clearTimeout(timeoutId);

    const latencyMs = Math.round(performance.now() - t0);

    if (res.ok) {
      const data = (await res.json()) as { models?: { name: string }[] };
      const modelNames = data.models ? data.models.map((m) => m.name) : [];
      return {
        success: true,
        latencyMs,
        message: `Ollama reachable (${latencyMs}ms). Found ${modelNames.length} models.`,
        models: modelNames,
      };
    }

    return {
      success: false,
      latencyMs,
      message: `Ollama responded with HTTP ${res.status}: ${res.statusText}`,
    };
  } catch (err: unknown) {
    const latencyMs = Math.round(performance.now() - t0);
    const msg =
      err instanceof Error && err.name === "AbortError"
        ? "Connection timed out (2.5s ceiling exceeded)"
        : "Could not reach Ollama daemon (check if `ollama serve` is running)";
    return {
      success: false,
      latencyMs,
      message: msg,
    };
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
      saveSettings({
        ...DEFAULT_SETTINGS,
        ...parsed.settings,
      });
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
    } else {
      // loadConversations() creates a fresh empty conversation when none exist
      const [first] = loadConversations();
      if (first) setActiveConversationId(first.id);
    }
  } catch {
    // ignore
  }
}
