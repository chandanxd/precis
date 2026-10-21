// @ts-nocheck — ported code written for a less strict TS config
import { useState, useRef } from "react";
import type { UserSettings, Modality, Theme } from "../../types/api";
import {
  loadSettings,
  saveSettings,
  testOllamaConnection,
  exportAllData,
  importAllData,
  resetToDemoBaseline,
  DEFAULT_SETTINGS,
} from "../../services/settings";
import { clearAllFacts } from "../../services/api";
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
} from "lucide-react";

interface SettingsViewProps {
  theme: Theme;
  onThemeChange: (theme: Theme) => void;
}

export const SettingsView = ({ theme, onThemeChange }: SettingsViewProps) => {
  const [settings, setSettings] = useState<UserSettings>(() => loadSettings());
  const [savedNotice, setSavedNotice] = useState<boolean>(false);

  // Ollama ping testing
  const [isTestingOllama, setIsTestingOllama] = useState<boolean>(false);
  const [ollamaResult, setOllamaResult] = useState<{
    success: boolean;
    message: string;
    models?: string[];
  } | null>(null);

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

  const handleTestOllama = async () => {
    setIsTestingOllama(true);
    setOllamaResult(null);
    try {
      const result = await testOllamaConnection(settings.ollamaBaseUrl);
      setOllamaResult(result);
      if (result.success && result.models && result.models.length > 0) {
        // If current model not in list and list has models, offer first
        if (!result.models.includes(settings.ollamaModel)) {
          updateSettings({ ollamaModel: result.models[0] });
        }
      }
    } finally {
      setIsTestingOllama(false);
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
            Local LLM generation parameters, SVOA epistemic constraints, and session backups
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

          {/* Active Model Identifier */}
          <div className="flex flex-col gap-1">
            <label className="text-[0.625rem] text-[var(--tx-3)] uppercase font-semibold">
              Model Tag (Ollama)
            </label>
            <div className="flex gap-1.5">
              <input
                type="text"
                value={settings.ollamaModel}
                onChange={(e) => updateSettings({ ollamaModel: e.target.value })}
                placeholder="e.g. llama3:8b-q4_K_M"
                className="flex-1 bg-[var(--bg)] border border-[var(--bd-3)] px-2 py-1 text-[0.6875rem] text-[var(--tx)] outline-none focus:border-[var(--tx)] font-mono"
              />
            </div>
            <div className="flex items-center gap-1 flex-wrap pt-0.5">
              <span className="text-[0.5625rem] text-[var(--tx-4)]">Presets:</span>
              {popularModels.map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => updateSettings({ ollamaModel: m })}
                  className={`px-1.5 py-0.5 text-[0.5625rem] border transition-colors cursor-pointer ${
                    settings.ollamaModel === m
                      ? "border-[var(--tx)] bg-[var(--inv-bg)] text-[var(--inv-tx)] font-bold"
                      : "border-[var(--bd)] bg-[var(--bg)] text-[var(--tx-3)] hover:text-[var(--tx)]"
                  }`}
                >
                  {m.split(":")[0]}
                </button>
              ))}
            </div>
          </div>

          {/* Token Ceiling Budget */}
          <div className="flex flex-col gap-1">
            <div className="flex items-center justify-between">
              <label className="text-[0.625rem] text-[var(--tx-3)] uppercase font-semibold">
                SVOA Context Token Ceiling
              </label>
              <span className="text-[0.6875rem] text-[var(--tx)] font-bold">
                {settings.tokenCeiling} TOKENS
              </span>
            </div>
            <div className="grid grid-cols-5 gap-1">
              {[512, 1024, 2048, 4096, 8192].map((ceil) => (
                <button
                  key={ceil}
                  type="button"
                  onClick={() => updateSettings({ tokenCeiling: ceil })}
                  className={`py-1 text-[0.625rem] border text-center transition-colors cursor-pointer ${
                    settings.tokenCeiling === ceil
                      ? "border-[var(--tx)] bg-[var(--inv-bg)] text-[var(--inv-tx)] font-bold"
                      : "border-[var(--bd)] bg-[var(--bg)] text-[var(--tx-3)] hover:text-[var(--tx)]"
                  }`}
                >
                  {ceil}
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

          {/* Ollama Base URL & Connectivity Test */}
          <div className="flex flex-col gap-1 pt-1 border-t border-[var(--bd)]">
            <label className="text-[0.625rem] text-[var(--tx-3)] uppercase font-semibold">
              Ollama Daemon Base URL
            </label>
            <div className="flex gap-1.5">
              <input
                type="text"
                value={settings.ollamaBaseUrl}
                onChange={(e) => updateSettings({ ollamaBaseUrl: e.target.value })}
                className="flex-1 bg-[var(--bg)] border border-[var(--bd-3)] px-2 py-1 text-[0.6875rem] text-[var(--tx)] outline-none focus:border-[var(--tx)] font-mono"
              />
              <button
                type="button"
                onClick={handleTestOllama}
                disabled={isTestingOllama}
                className="px-2.5 py-1 border border-[var(--tx)] bg-[var(--bg)] hover:bg-[var(--inv-bg)] hover:text-[var(--inv-tx)] text-[var(--tx)] text-[0.625rem] font-bold shrink-0 disabled:opacity-50 transition-colors cursor-pointer flex items-center gap-1"
              >
                <Server size={10} />
                <span>{isTestingOllama ? "PINGING..." : "TEST PING"}</span>
              </button>
            </div>
            {ollamaResult && (
              <div
                className={`text-[0.625rem] p-1.5 border mt-1 flex items-center gap-1.5 ${
                  ollamaResult.success
                    ? "border-[var(--bd-3)] bg-[var(--bg)] text-[var(--tx)] font-medium"
                    : "border-[var(--bd-3)] bg-[var(--bg)] text-[var(--tx-3)]"
                }`}
              >
                {ollamaResult.success ? (
                  <Check size={11} className="text-[var(--tx)] shrink-0" />
                ) : (
                  <AlertCircle size={11} className="text-[var(--tx-3)] shrink-0" />
                )}
                <span>{ollamaResult.message}</span>
              </div>
            )}
          </div>
        </div>

        {/* Panel 2: SVOA Epistemic Retrieval & Modality Filters */}
        <div className="border border-[var(--bd)] bg-[var(--bg-2)] p-3 flex flex-col gap-3">
          <div className="flex items-center justify-between border-b border-[var(--bd)] pb-2">
            <div className="flex items-center gap-1.5 text-[0.6875rem] font-bold text-[var(--tx)] uppercase">
              <Filter size={12} strokeWidth={1.5} />
              <span>2. EPISTEMIC SVOA CONSTRAINTS</span>
            </div>
            <span className="text-[0.5625rem] text-[var(--tx-4)] uppercase">
              STAGE 3-4 RETRIEVAL
            </span>
          </div>

          {/* Minimum SDH Salience Cutoff */}
          <div className="flex flex-col gap-1">
            <div className="flex items-center justify-between">
              <label className="text-[0.625rem] text-[var(--tx-3)] uppercase font-semibold">
                Minimum SDH Salience Score Cutoff
              </label>
              <span className="text-[0.6875rem] text-[var(--tx)] font-bold">
                {settings.minSdhScore.toFixed(2)}
              </span>
            </div>
            <input
              type="range"
              min="0.0"
              max="1.0"
              step="0.05"
              value={settings.minSdhScore}
              onChange={(e) => updateSettings({ minSdhScore: parseFloat(e.target.value) })}
              className="w-full accent-[var(--accent)] cursor-pointer"
            />
            <div className="flex items-center justify-between text-[0.5625rem] text-[var(--tx-4)] font-sans">
              <span>0.00 (Pass All Extracted Facts)</span>
              <span>0.50 (Recommended)</span>
              <span>0.85 (High Precision Only)</span>
            </div>
          </div>

          {/* Modality Filter Selection */}
          <div className="flex flex-col gap-1.5">
            <label className="text-[0.625rem] text-[var(--tx-3)] uppercase font-semibold">
              Permitted Epistemic Modalities
            </label>
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

          {/* Strict Negation Handling */}
          <div className="flex items-center justify-between border-t border-[var(--bd)] pt-2 mt-1">
            <div className="flex flex-col">
              <span className="text-[0.625rem] font-bold text-[var(--tx)] uppercase">
                Preserve Negation Assertions
              </span>
              <span className="text-[0.5625rem] text-[var(--tx-3)] font-sans">
                Never prune or deprioritize propositions marked with ¬ NEG during context
                compression
              </span>
            </div>
            <button
              type="button"
              onClick={() => updateSettings({ strictNegation: !settings.strictNegation })}
              className={`px-2.5 py-1 text-[0.625rem] border font-bold transition-colors cursor-pointer ${
                settings.strictNegation
                  ? "border-[var(--tx)] bg-[var(--inv-bg)] text-[var(--inv-tx)]"
                  : "border-[var(--bd)] bg-[var(--bg)] text-[var(--tx-3)]"
              }`}
            >
              {settings.strictNegation ? "ENFORCED" : "STANDARD"}
            </button>
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
                Whether evidence premise rows begin expanded or collapsed on new turns
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

          {/* Default Sidebar State */}
          <div className="flex items-center justify-between border-t border-[var(--bd)] pt-2">
            <div className="flex flex-col">
              <span className="text-[0.625rem] font-bold text-[var(--tx)] uppercase">
                Session Sidebar Default Layout
              </span>
              <span className="text-[0.5625rem] text-[var(--tx-3)] font-sans">
                Initial conversation rail width on launch (toggle with Ctrl/Cmd + B)
              </span>
            </div>
            <button
              type="button"
              onClick={() =>
                updateSettings({
                  defaultSidebarCollapsed: !settings.defaultSidebarCollapsed,
                })
              }
              className={`px-2.5 py-1 text-[0.625rem] border font-bold transition-colors cursor-pointer ${
                settings.defaultSidebarCollapsed
                  ? "border-[var(--tx)] bg-[var(--inv-bg)] text-[var(--inv-tx)]"
                  : "border-[var(--bd)] bg-[var(--bg)] text-[var(--tx-3)]"
              }`}
            >
              {settings.defaultSidebarCollapsed ? "COLLAPSED (w-10)" : "EXPANDED (w-64)"}
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
