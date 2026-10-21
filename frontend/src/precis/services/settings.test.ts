import { describe, expect, it } from "vitest";
import {
  DEFAULT_SETTINGS,
  getQueryOptions,
  loadSettings,
  resetToDemoBaseline,
  saveSettings,
} from "./settings";
import { loadConversations, saveMessages } from "./storage";

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
    const [conv] = loadConversations();
    saveMessages(conv!.id, [{ id: "m" } as never]);
    localStorage.setItem("precis_client_id", "client-" + "a".repeat(32));
    saveSettings({ ...DEFAULT_SETTINGS, temperature: 1.5 });

    resetToDemoBaseline();

    expect(localStorage.getItem("precis_client_id")).toBe("client-" + "a".repeat(32));
    expect(loadSettings().temperature).toBe(DEFAULT_SETTINGS.temperature);
    const after = loadConversations();
    expect(after).toHaveLength(1);
    expect(after[0]!.id).not.toBe(conv!.id);
  });
});
