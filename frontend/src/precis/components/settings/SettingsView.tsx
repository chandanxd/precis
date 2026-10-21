// @ts-nocheck — ported code written for a less strict TS config
import { useEffect, useState, useRef } from "react";
import type { UserSettings, Modality, Theme } from "../../types/api";
import {
  loadSettings,
  saveSettings,
  exportAllData,
  importAllData,
  resetToDemoBaseline,
  DEFAULT_SETTINGS,
} from "../../services/settings";
import { clearAllFacts, fetchModels, type ModelsInfo } from "../../services/api";
import {
  Cpu,
  Filter,
  Sliders,
  HardDrive,
  Check,
  AlertCircle,
  Download,
  Upload,
  RotateCcw,
  Trash2,
  Sun,
  Moon,
  Activity,
  Server,
  RefreshCw,
} from "lucide-react";

interface SettingsViewProps {
  theme: Theme;
  onThemeChange: (theme: Theme) => void;
}

export const SettingsView = ({ theme, onThemeChange }: SettingsViewProps) => {
  const [settings, setSettings] = useState<UserSettings>(() => loadSettings());
  const [savedNotice, setSavedNotice] = useState<boolean>(false);

  // Installed models and hardware tiers, as the backend sees them
  const [models, setModels] = useState<ModelsInfo | null>(null);
  const [modelsState, setModelsState] = useState<"loading" | "ready" | "error">("loading");

  // Data operations
  const [importStatus, setImportStatus] = useState<string | null>(null);
  const [purgeStatus, setPurgeStatus] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const updateSettings = (partial: Partial<UserSettings>) => {
    const next = { ...settings, ...partial };
    setSettings(next);
    saveSettings(next);
    setSavedNotice(true);
    setTimeout(() => setSavedNotice(false), 1500);
  };

  const refreshModels = async () => {
    setModelsState("loading");
    const info = await fetchModels();
    setModels(info);
    setModelsState(info ? "ready" : "error");
  };

  useEffect(() => {
    void refreshModels();
  }, []);

  const isInstalled = (model: string) =>
    !!models && (models.installed.includes(model) || models.installed.includes(`${model}:latest`));

  const detectedTier = models?.tiers.find((t) => t.mode === models.detected_mode);

  const applyPreset = (mode: string) => {
    if (mode === "auto") {
      updateSettings({ devicePreset: "auto", ollamaModel: "", tokenCeiling: null });
      return;
    }
    const tier = models?.tiers.find((t) => t.mode === mode);
    if (tier) {
      updateSettings({
        devicePreset: mode,
        ollamaModel: tier.model,
        tokenCeiling: tier.token_ceiling,
      });
    }
  };

  const handleExport = () => {
    const json = exportAllData();
    const blob = new Blob([json], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `precis-research-backup-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleFileImport = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result;
      if (typeof text === "string") {
        const res = importAllData(text);
        if (res.success) {
          setImportStatus(`Successfully restored ${res.conversationCount} sessions!`);
          setSettings(loadSettings());
        } else {
          setImportStatus(`Import failed: ${res.error || "Unknown error"}`);
        }
        setTimeout(() => setImportStatus(null), 4000);
      }
    };
    reader.readAsText(file);
  };

  const handleResetBaseline = () => {
    if (window.confirm("Clear all stored sessions and restore default settings?")) {
      resetToDemoBaseline();
      setSettings(loadSettings());
      setSavedNotice(true);
      setTimeout(() => setSavedNotice(false), 2000);
    }
  };

  const handlePurgeStore = async () => {
    if (window.confirm("Purge all extracted facts from ChromaDB knowledge store?")) {
      const ok = await clearAllFacts();
      setPurgeStatus(ok ? "ChromaDB fact store purged." : "Purge failed / backend offline.");
      setTimeout(() => setPurgeStatus(null), 3000);
    }
  };

  const toggleModality = (mod: Modality) => {
    updateSettings({
      allowedModalities: {
        ...settings.allowedModalities,
        [mod]: !settings.allowedModalities[mod],
      },
    });
  };

  const popularModels = [
    "llama3:8b-q4_K_M",
    "phi3:3.8b-q4_K_M",
    "mistral:7b-instruct",
    "gemma2:2b",
    "qwen2.5:7b",
  ];

  return (
    <div className="flex-1 min-h-0 w-full flex flex-col bg-[var(--bg)] overflow-hidden font-mono select-text">
      {/* Header Title Bar */}
      <div className="p-3 border-b border-[var(--bd)] bg-[var(--bg-2)] flex items-center justify-between shrink-0 select-none">
        <div className="flex flex-col gap-0.5">
          <div className="flex items-center gap-2 text-xs font-bold text-[var(--tx)] uppercase tracking-wider">
            <Sliders size={13} strokeWidth={1.5} className="text-[var(--tx-2)]" />
            <span>SYSTEM CONFIGURATION & WORKBENCH PREFERENCES</span>
          </div>
          <span className="text-[0.625rem] text-[var(--tx-3)] font-sans">
            Model and context limits, evidence modalities, display and backups
          </span>
        </div>

        <div className="flex items-center gap-3">
          {savedNotice && (
            <span className="text-[0.625rem] text-[var(--tx)] bg-[var(--bg)] border border-[var(--bd-3)] px-2 py-0.5 font-bold flex items-center gap-1 animate-in fade-in duration-100">
              <Check size={10} strokeWidth={2.5} /> SAVED
            </span>
          )}
          <button
            type="button"
            onClick={() => updateSettings(DEFAULT_SETTINGS)}
            className="text-[0.625rem] text-[var(--tx-3)] hover:text-[var(--tx)] hover:underline flex items-center gap-1"
            title="Restore system defaults"
          >
            <RotateCcw size={10} />
            <span>DEFAULTS</span>
          </button>
        </div>
      </div>

      {/* Scrollable Settings Grid */}
      <div className="flex-1 min-h-0 overflow-y-auto p-3 lg:p-4 grid grid-cols-1 lg:grid-cols-2 gap-3 lg:gap-4">
        {/* Panel 1: Local LLM & Inference Parameters */}
        <div className="border border-[var(--bd)] bg-[var(--bg-2)] p-3 flex flex-col gap-3">
          <div className="flex items-center justify-between border-b border-[var(--bd)] pb-2">
            <div className="flex items-center gap-1.5 text-[0.6875rem] font-bold text-[var(--tx)] uppercase">
              <Cpu size={12} strokeWidth={1.5} />
              <span>1. LOCAL LLM INFERENCE ENGINE</span>
            </div>
            <span className="text-[0.5625rem] text-[var(--tx-4)] uppercase">STAGE 5 SYNTHESIS</span>
          </div>

          {/* Device preset: the backend's hardware tiers */}
          <div className="flex flex-col gap-1">
            <label className="text-[0.625rem] text-[var(--tx-3)] uppercase font-semibold">
              Device Preset
            </label>
            <span className="text-[0.5625rem] text-[var(--tx-4)] font-sans">
              Sets the model and context ceiling the backend would choose on that kind of machine.
              It does not make the rest of the pipeline lighter.
            </span>
            <div className="flex flex-col gap-1 pt-0.5">
              {[
                {
                  mode: "auto",
                  label: detectedTier
                    ? `Auto: this machine (${detectedTier.label})`
                    : "Auto: the backend decides for this machine",
                  detail: models
                    ? `${models.default_model} · ${models.default_token_ceiling} tokens`
                    : "",
                  missing: false,
                  model: "",
                },
                ...(models?.tiers ?? []).map((t) => ({
                  mode: t.mode,
                  label: t.label,
                  detail: `${t.model} · ${t.token_ceiling} tokens`,
                  missing: t.installed === false,
                  model: t.model,
                })),
              ].map((p) => (
                <button
                  key={p.mode}
                  type="button"
                  onClick={() => applyPreset(p.mode)}
                  className={`px-2 py-1.5 border text-left flex items-center justify-between gap-2 transition-colors cursor-pointer ${
                    settings.devicePreset === p.mode
                      ? "border-[var(--tx)] bg-[var(--bg)] text-[var(--tx)]"
                      : "border-[var(--bd)] bg-[var(--bg)] text-[var(--tx-3)] hover:text-[var(--tx)]"
                  }`}
                >
                  <span className="text-[0.625rem] font-bold">{p.label}</span>
                  <span className="text-[0.5625rem] text-right">
                    {p.detail}
                    {p.missing && (
                      <span className="block text-[var(--tx-4)]">
                        not installed: ollama pull {p.model}
                      </span>
                    )}
                  </span>
                </button>
              ))}
              {settings.devicePreset === "custom" && (
                <span className="text-[0.5625rem] text-[var(--tx-4)]">
                  Custom: model and ceiling set individually below.
                </span>
              )}
            </div>
          </div>

          {/* Model: installed models only */}
          <div className="flex flex-col gap-1">
            <label
              htmlFor="settings-model"
              className="text-[0.625rem] text-[var(--tx-3)] uppercase font-semibold"
            >
              Model (Ollama)
            </label>
            <select
              id="settings-model"
              value={settings.ollamaModel}
              onChange={(e) =>
                updateSettings({ ollamaModel: e.target.value, devicePreset: "custom" })
              }
              className="bg-[var(--bg)] border border-[var(--bd-3)] px-2 py-1 text-[0.6875rem] text-[var(--tx)] outline-none focus:border-[var(--tx)] font-mono"
            >
              <option value="">Auto{models ? ` (${models.default_model})` : ""}</option>
              {(models?.installed ?? []).map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
              {settings.ollamaModel && models && !isInstalled(settings.ollamaModel) && (
                <option value={settings.ollamaModel}>{settings.ollamaModel} (not installed)</option>
              )}
            </select>
          </div>

          {/* Token Ceiling Budget */}
          <div className="flex flex-col gap-1">
            <div className="flex items-center justify-between">
              <label className="text-[0.625rem] text-[var(--tx-3)] uppercase font-semibold">
                Context Token Ceiling
              </label>
              <span className="text-[0.6875rem] text-[var(--tx)] font-bold">
                {settings.tokenCeiling === null
                  ? `AUTO${models ? ` (${models.default_token_ceiling})` : ""}`
                  : `${settings.tokenCeiling} TOKENS`}
              </span>
            </div>
            <div className="grid grid-cols-7 gap-1">
              {[null, 512, 1024, 2048, 3072, 4096, 8192].map((ceil) => (
                <button
                  key={ceil ?? "auto"}
                  type="button"
                  onClick={() => updateSettings({ tokenCeiling: ceil, devicePreset: "custom" })}
                  className={`py-1 text-[0.625rem] border text-center transition-colors cursor-pointer ${
                    settings.tokenCeiling === ceil
                      ? "border-[var(--tx)] bg-[var(--inv-bg)] text-[var(--inv-tx)] font-bold"
                      : "border-[var(--bd)] bg-[var(--bg)] text-[var(--tx-3)] hover:text-[var(--tx)]"
                  }`}
                >
                  {ceil ?? "AUTO"}
                </button>
              ))}
            </div>
          </div>

          {/* Sampling Temperature Slider */}
          <div className="flex flex-col gap-1">
            <div className="flex items-center justify-between">
              <label className="text-[0.625rem] text-[var(--tx-3)] uppercase font-semibold">
                Sampling Temperature
              </label>
              <span className="text-[0.6875rem] text-[var(--tx)] font-bold">
                {settings.temperature.toFixed(2)}
              </span>
            </div>
            <input
              type="range"
              min="0.0"
              max="1.0"
              step="0.05"
              value={settings.temperature}
              onChange={(e) => updateSettings({ temperature: parseFloat(e.target.value) })}
              className="w-full accent-[var(--accent)] cursor-pointer"
            />
            <div className="flex items-center justify-between text-[0.5625rem] text-[var(--tx-4)] font-sans">
              <span>0.0 (Strict / Deterministic)</span>
              <span>0.3 (Grounded QA)</span>
              <span>1.0 (Creative)</span>
            </div>
          </div>

          {/* Ollama status, as the backend sees it */}
          <div className="flex flex-col gap-1 pt-1 border-t border-[var(--bd)]">
            <div className="flex items-center justify-between">
              <label className="text-[0.625rem] text-[var(--tx-3)] uppercase font-semibold">
                Ollama (used by the backend)
              </label>
              <button
                type="button"
                onClick={refreshModels}
                disabled={modelsState === "loading"}
                className="px-2 py-0.5 border border-[var(--bd)] text-[var(--tx-3)] hover:text-[var(--tx)] text-[0.5625rem] font-bold disabled:opacity-50 flex items-center gap-1 cursor-pointer"
              >
                <RefreshCw size={9} />
                <span>{modelsState === "loading" ? "CHECKING..." : "RECHECK"}</span>
              </button>
            </div>
            <div className="text-[0.625rem] p-1.5 border border-[var(--bd-3)] bg-[var(--bg)] flex items-center gap-1.5">
              {modelsState === "ready" && models?.ollama_reachable ? (
                <Check size={11} className="text-[var(--tx)] shrink-0" />
              ) : modelsState === "loading" ? (
                <Server size={11} className="text-[var(--tx-3)] shrink-0" />
              ) : (
                <AlertCircle size={11} className="text-[var(--tx-3)] shrink-0" />
              )}
              <span className="text-[var(--tx-2)]">
                {modelsState === "loading"
                  ? "Checking…"
                  : modelsState === "error"
                    ? "Backend unreachable."
                    : models!.ollama_reachable
                      ? `Reachable at ${models!.ollama_url} · ${models!.installed.length} models installed`
                      : `Not reachable at ${models!.ollama_url}. Start it with: ollama serve`}
              </span>
            </div>
            <span className="text-[0.5625rem] text-[var(--tx-4)] font-sans">
              The address is set on the server (PRECIS_OLLAMA_BASE_URL).
            </span>
          </div>
        </div>

        {/* Panel 2: SVOA Epistemic Retrieval & Modality Filters */}
        <div className="border border-[var(--bd)] bg-[var(--bg-2)] p-3 flex flex-col gap-3">
          <div className="flex items-center justify-between border-b border-[var(--bd)] pb-2">
            <div className="flex items-center gap-1.5 text-[0.6875rem] font-bold text-[var(--tx)] uppercase">
              <Filter size={12} strokeWidth={1.5} />
              <span>2. EVIDENCE MODALITIES</span>
            </div>
            <span className="text-[0.5625rem] text-[var(--tx-4)] uppercase">STAGE 4 PACKING</span>
          </div>

          {/* Modality Filter Selection */}
          <div className="flex flex-col gap-1.5">
            <label className="text-[0.625rem] text-[var(--tx-3)] uppercase font-semibold">
              Facts the packer may use
            </label>
            <span className="text-[0.5625rem] text-[var(--tx-4)] font-sans">
              Hypothetical facts are left out by default, as in the paper.
            </span>
            <div className="grid grid-cols-2 gap-1.5">
              {(["asserted", "attributed", "conditional", "hypothetical"] as Modality[]).map(
                (mod) => {
                  const isAllowed = settings.allowedModalities[mod];
                  return (
                    <button
                      key={mod}
                      type="button"
                      onClick={() => toggleModality(mod)}
                      className={`p-2 border text-left flex items-center justify-between transition-colors cursor-pointer ${
                        isAllowed
                          ? "border-[var(--accent)] bg-[var(--bg)] text-[var(--tx)]"
                          : "border-[var(--bd)] bg-[var(--bg-3)] text-[var(--tx-4)] opacity-60"
                      }`}
                    >
                      <div className="flex flex-col">
                        <span className="text-[0.625rem] font-bold uppercase">{mod}</span>
                        <span className="text-[0.5rem] text-[var(--tx-3)] font-sans">
                          {mod === "asserted" && "Direct factual statements"}
                          {mod === "attributed" && "Source-quoted claims"}
                          {mod === "conditional" && "If / then clauses"}
                          {mod === "hypothetical" && "Speculative scenarios"}
                        </span>
                      </div>
                      <span className="text-[0.5625rem] font-mono">
                        {isAllowed ? "[ALLOW]" : "[BLOCK]"}
                      </span>
                    </button>
                  );
                },
              )}
            </div>
          </div>
        </div>

        {/* Panel 3: Workbench & Reading Preferences */}
        <div className="border border-[var(--bd)] bg-[var(--bg-2)] p-3 flex flex-col gap-3">
          <div className="flex items-center justify-between border-b border-[var(--bd)] pb-2">
            <div className="flex items-center gap-1.5 text-[0.6875rem] font-bold text-[var(--tx)] uppercase">
              <Activity size={12} strokeWidth={1.5} />
              <span>3. WORKBENCH & DISPLAY PREFERENCES</span>
            </div>
            <span className="text-[0.5625rem] text-[var(--tx-4)] uppercase">UI BEHAVIOR</span>
          </div>

          {/* Theme Choice */}
          <div className="flex items-center justify-between">
            <div className="flex flex-col">
              <span className="text-[0.625rem] font-bold text-[var(--tx)] uppercase">
                Workbench Theme
              </span>
              <span className="text-[0.5625rem] text-[var(--tx-3)] font-sans">
                Strict monochrome high-contrast dark or clean daylight mode
              </span>
            </div>
            <div className="flex border border-[var(--bd)] bg-[var(--bg)] p-0.5">
              <button
                type="button"
                onClick={() => {
                  updateSettings({ theme: "dark" });
                  onThemeChange("dark");
                }}
                className={`px-2 py-0.5 text-[0.625rem] flex items-center gap-1 transition-colors cursor-pointer ${
                  theme === "dark"
                    ? "bg-[var(--inv-bg)] text-[var(--inv-tx)] font-bold"
                    : "text-[var(--tx-3)] hover:text-[var(--tx)]"
                }`}
              >
                <Moon size={10} />
                <span>DARK</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  updateSettings({ theme: "light" });
                  onThemeChange("light");
                }}
                className={`px-2 py-0.5 text-[0.625rem] flex items-center gap-1 transition-colors cursor-pointer ${
                  theme === "light"
                    ? "bg-[var(--inv-bg)] text-[var(--inv-tx)] font-bold"
                    : "text-[var(--tx-3)] hover:text-[var(--tx)]"
                }`}
              >
                <Sun size={10} />
                <span>LIGHT</span>
              </button>
            </div>
          </div>

          {/* Default Supporting Evidence Accordion State */}
          <div className="flex items-center justify-between border-t border-[var(--bd)] pt-2">
            <div className="flex flex-col">
              <span className="text-[0.625rem] font-bold text-[var(--tx)] uppercase">
                Supporting Evidence Default State
              </span>
              <span className="text-[0.5625rem] text-[var(--tx-3)] font-sans">
                Whether the supporting-evidence list under each answer starts open
              </span>
            </div>
            <button
              type="button"
              onClick={() =>
                updateSettings({
                  defaultEvidenceExpanded: !settings.defaultEvidenceExpanded,
                })
              }
              className={`px-2.5 py-1 text-[0.625rem] border font-bold transition-colors cursor-pointer ${
                settings.defaultEvidenceExpanded
                  ? "border-[var(--tx)] bg-[var(--inv-bg)] text-[var(--inv-tx)]"
                  : "border-[var(--bd)] bg-[var(--bg)] text-[var(--tx-3)]"
              }`}
            >
              {settings.defaultEvidenceExpanded ? "EXPANDED" : "COLLAPSED"}
            </button>
          </div>
        </div>

        {/* Panel 4: Data Management, Backup & Export */}
        <div className="border border-[var(--bd)] bg-[var(--bg-2)] p-3 flex flex-col gap-3">
          <div className="flex items-center justify-between border-b border-[var(--bd)] pb-2">
            <div className="flex items-center gap-1.5 text-[0.6875rem] font-bold text-[var(--tx)] uppercase">
              <HardDrive size={12} strokeWidth={1.5} />
              <span>4. DATA PERSISTENCE & EXPORT</span>
            </div>
            <span className="text-[0.5625rem] text-[var(--tx-4)] uppercase">BACKUP / RESTORE</span>
          </div>

          {/* Export and Import Buttons */}
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <span className="text-[0.625rem] font-bold text-[var(--tx)] uppercase">
                Backup Research Sessions
              </span>
              <span className="text-[0.5625rem] text-[var(--tx-4)]">JSON FORMAT</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={handleExport}
                className="py-1.5 px-2 border border-[var(--tx)] bg-[var(--bg)] hover:bg-[var(--inv-bg)] hover:text-[var(--inv-tx)] text-[var(--tx)] text-[0.625rem] font-semibold flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
              >
                <Download size={11} />
                <span>EXPORT BACKUP</span>
              </button>

              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="py-1.5 px-2 border border-[var(--bd)] bg-[var(--bg)] hover:border-[var(--tx)] hover:text-[var(--tx)] text-[var(--tx-2)] text-[0.625rem] font-semibold flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
              >
                <Upload size={11} />
                <span>IMPORT BACKUP</span>
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".json,application/json"
                onChange={handleFileImport}
                className="hidden"
              />
            </div>
            {importStatus && (
              <span className="text-[0.5625rem] text-[var(--tx)] bg-[var(--bg)] p-1 border border-[var(--bd-3)] mt-1">
                {importStatus}
              </span>
            )}
          </div>

          {/* Reset Baseline Demo */}
          <div className="flex items-center justify-between border-t border-[var(--bd)] pt-2">
            <div className="flex flex-col">
              <span className="text-[0.625rem] font-bold text-[var(--tx)] uppercase">
                Restore Baseline Benchmark
              </span>
              <span className="text-[0.5625rem] text-[var(--tx-3)] font-sans">
                Clear stored sessions and restore default settings
              </span>
            </div>
            <button
              type="button"
              onClick={handleResetBaseline}
              className="px-2.5 py-1 text-[0.625rem] border border-[var(--bd)] bg-[var(--bg)] hover:border-[var(--tx)] hover:text-[var(--tx)] text-[var(--tx-2)] font-mono transition-colors cursor-pointer"
            >
              RESTORE
            </button>
          </div>

          {/* Purge ChromaDB Facts */}
          <div className="flex items-center justify-between border-t border-[var(--bd)] pt-2">
            <div className="flex flex-col">
              <span className="text-[0.625rem] font-bold text-[var(--tx)] uppercase">
                Purge ChromaDB Store
              </span>
              <span className="text-[0.5625rem] text-[var(--tx-3)] font-sans">
                Flushes all epistemic propositions and embeddings from active vector store
              </span>
            </div>
            <button
              type="button"
              onClick={handlePurgeStore}
              className="px-2.5 py-1 text-[0.625rem] border border-[var(--bd)] bg-[var(--bg)] hover:bg-[var(--inv-bg)] hover:text-[var(--inv-tx)] text-[var(--tx-3)] hover:border-[var(--tx)] flex items-center gap-1 transition-colors cursor-pointer"
            >
              <Trash2 size={10} />
              <span>PURGE</span>
            </button>
          </div>
          {purgeStatus && (
            <span className="text-[0.5625rem] text-[var(--tx)] bg-[var(--bg)] p-1 border border-[var(--bd-3)]">
              {purgeStatus}
            </span>
          )}
        </div>
      </div>

      {/* Bottom Status Footer */}
      <div className="p-2 border-t border-[var(--bd)] bg-[var(--bg-2)] text-[0.5625rem] text-[var(--tx-4)] flex items-center justify-between shrink-0 select-none">
        <span>CONFIG SPECIFICATION v0.1.0 · STORAGE: LOCALSTORAGE</span>
        <span>STATE AUTO-COMMITTED</span>
      </div>
    </div>
  );
};
