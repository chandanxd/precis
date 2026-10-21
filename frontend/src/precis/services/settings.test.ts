import { describe, expect, it } from "vitest";
import {
  DEFAULT_SETTINGS,
  getQueryOptions,
  loadSettings,
  normalizeSettings,
  resetToDemoBaseline,
  saveSettings,
} from "./settings";
import { createConversation, loadConversations, saveMessages } from "./storage";

describe("getQueryOptions", () => {
  it("sends nothing when settings are untouched", () => {
    expect(getQueryOptions()).toEqual({});
  });

  it("sends only the values that were changed", () => {
    saveSettings({ ...DEFAULT_SETTINGS, ollamaModel: "qwen3.5:4b", temperature: 0.8 });
    expect(getQueryOptions()).toEqual({ model: "qwen3.5:4b", temperature: 0.8 });
  });

  it("sends the enabled modalities when the selection changed", () => {
    saveSettings({
      ...DEFAULT_SETTINGS,
      allowedModalities: {
        ...DEFAULT_SETTINGS.allowedModalities,
        hypothetical: true,
        attributed: false,
      },
    });
    const options = getQueryOptions();
    expect(options["allowed_modalities"]).toEqual(["asserted", "conditional", "hypothetical"]);
  });
});

describe("getQueryOptions with a chosen model and ceiling", () => {
  it("sends a chosen ceiling even when it equals the old default", () => {
    saveSettings({ ...DEFAULT_SETTINGS, tokenCeiling: 4096 });
    expect(getQueryOptions()).toEqual({ token_ceiling: 4096 });
  });

  it("sends nothing for auto", () => {
    saveSettings({ ...DEFAULT_SETTINGS, ollamaModel: "", tokenCeiling: null });
    expect(getQueryOptions()).toEqual({});
  });
});

describe("normalizeSettings", () => {
  it("turns stored version-1 defaults into auto, so behaviour does not change", () => {
    const s = normalizeSettings({
      ollamaModel: "llama3:8b-q4_K_M",
      tokenCeiling: 4096,
      ollamaBaseUrl: "http://x",
      minSdhScore: 0.5,
      strictNegation: true,
    });
    expect(s.ollamaModel).toBe("");
    expect(s.tokenCeiling).toBeNull();
    expect(s.devicePreset).toBe("auto");
    expect(s).not.toHaveProperty("minSdhScore");
    expect(s).not.toHaveProperty("ollamaBaseUrl");
  });

  it("keeps version-1 values the user had changed, as a custom preset", () => {
    const s = normalizeSettings({ ollamaModel: "qwen3.5:9b", tokenCeiling: 2048 });
    expect(s).toMatchObject({
      ollamaModel: "qwen3.5:9b",
      tokenCeiling: 2048,
      devicePreset: "custom",
    });
  });

  it("keeps a version-2 4096 ceiling as chosen", () => {
    expect(normalizeSettings({ version: 2, tokenCeiling: 4096 }).tokenCeiling).toBe(4096);
  });
});

describe("loadSettings", () => {
  it("merges stored partial settings over the defaults", () => {
    localStorage.setItem("precis_settings", JSON.stringify({ temperature: 0.9 }));
    const s = loadSettings();
    expect(s.temperature).toBe(0.9);
    expect(s.tokenCeiling).toBe(DEFAULT_SETTINGS.tokenCeiling);
    expect(s.allowedModalities).toEqual(DEFAULT_SETTINGS.allowedModalities);
  });
});

describe("resetToDemoBaseline", () => {
  it("clears stored sessions but keeps the client id", () => {
    const conv = createConversation("Old");
    saveMessages(conv.id, [{ id: "m" } as never]);
    localStorage.setItem("precis_client_id", "client-" + "a".repeat(32));
    saveSettings({ ...DEFAULT_SETTINGS, temperature: 1.5 });

    resetToDemoBaseline();

    expect(localStorage.getItem("precis_client_id")).toBe("client-" + "a".repeat(32));
    expect(loadSettings().temperature).toBe(DEFAULT_SETTINGS.temperature);
    expect(loadConversations()).toEqual([]);
  });
});
