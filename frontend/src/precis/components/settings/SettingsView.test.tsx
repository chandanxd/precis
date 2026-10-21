import { act, fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { getQueryOptions, loadSettings } from "../../services/settings";

vi.mock("../../services/api", () => ({
  clearAllFacts: async () => true,
  fetchModels: async () => ({
    ollama_reachable: true,
    ollama_url: "http://localhost:11434",
    installed: ["qwen3.5:4b", "qwen3.5:9b"],
    detected_mode: "gpu",
    default_model: "qwen3.5:4b",
    default_token_ceiling: 4096,
    list_extraction_enabled: false,
    tiers: [
      {
        mode: "gpu",
        label: "GPU with 6 GB+ VRAM (and 8 GB+ RAM)",
        model: "qwen3.5:4b",
        token_ceiling: 4096,
        installed: true,
      },
      {
        mode: "cpu-light",
        label: "Under 16 GB RAM, no usable GPU",
        model: "qwen3.5:2b",
        token_ceiling: 1024,
        installed: false,
      },
    ],
  }),
}));

const { SettingsView } = await import("./SettingsView");

const renderSettings = async () => {
  render(<SettingsView theme="dark" onThemeChange={() => {}} />);
  await act(async () => {});
};

describe("SettingsView device presets", () => {
  it("applies a preset's model and ceiling and flags a model that is not pulled", async () => {
    await renderSettings();
    expect(screen.getByText("not installed: ollama pull qwen3.5:2b")).toBeTruthy();
    fireEvent.click(screen.getByText("Under 16 GB RAM, no usable GPU"));
    expect(loadSettings()).toMatchObject({
      devicePreset: "cpu-light",
      ollamaModel: "qwen3.5:2b",
      tokenCeiling: 1024,
    });
    expect(getQueryOptions()).toEqual({ model: "qwen3.5:2b", token_ceiling: 1024 });

    fireEvent.click(screen.getByText(/^Auto: this machine/));
    expect(getQueryOptions()).toEqual({});
  });

  it("offers only installed models", async () => {
    await renderSettings();
    const options = [...(screen.getByLabelText("Model (Ollama)") as HTMLSelectElement).options].map(
      (o) => o.value,
    );
    expect(options).toEqual(["", "qwen3.5:4b", "qwen3.5:9b"]);
  });

  it("reports Ollama as the backend sees it", async () => {
    await renderSettings();
    expect(
      screen.getByText(/Reachable at http:\/\/localhost:11434 · 2 models installed/),
    ).toBeTruthy();
  });
});
