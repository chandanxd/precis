// @ts-nocheck — ported code written for a less strict TS config
import { useState, useEffect } from "react";
import { watchMotion } from "./services/motion";
import type { HardwareProfile, Theme } from "./types/api";
import { checkBackendHealth, fetchHardware } from "./services/api";
import { Header } from "./components/common/Header";
import { ChatView } from "./components/chat/ChatView";
import { FactExplorer } from "./components/graph/FactExplorer";
import { DocumentManager } from "./components/documents/DocumentManager";
import { HardwarePanel } from "./components/system/HardwarePanel";
import { EvaluationView } from "./components/evaluation/EvaluationView";
import { SecurityView } from "./components/security/SecurityView";
import { SettingsView } from "./components/settings/SettingsView";
import { RouterProvider } from "./components/common/Router";
import { useRouter } from "./services/router";

function AppContent() {
  const { activeTab } = useRouter();
  const [theme, setTheme] = useState<Theme>(() => {
    try {
      const saved = localStorage.getItem("precis_theme");
      if (saved === "light" || saved === "dark") return saved;
    } catch {
      // storage unavailable: use the default
    }
    return "dark";
  });
  const [hardware, setHardware] = useState<HardwareProfile | null>(null);
  const [isOnline, setIsOnline] = useState<boolean | null>(null);

  // Synchronize HTML theme data-attribute
  useEffect(() => watchMotion(), []);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem("precis_theme", theme);
    } catch {
      // storage unavailable: theme still applies for this session
    }
  }, [theme]);

  // Initial system detection
  useEffect(() => {
    checkBackendHealth().then((online) => {
      setIsOnline(online);
    });
    fetchHardware()
      .then((hw) => {
        setHardware(hw);
      })
      .catch(() => {
        setHardware(null);
      });
  }, []);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  };

  return (
    <div className="precis-app h-screen w-screen overflow-hidden flex flex-col text-[var(--tx)] font-sans relative">
      <div className="precis-aurora" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <div className="precis-grid" aria-hidden="true" />
      <div className="precis-particles" aria-hidden="true">
        {Array.from({ length: 14 }).map((_, i) => (
          <span
            key={i}
            style={{
              left: `${(i * 37) % 100}%`,
              animationDelay: `${-(i * 1.7) % 18}s`,
              animationDuration: `${12 + (i % 7) * 2}s`,
              width: `${2 + (i % 3)}px`,
              height: `${2 + (i % 3)}px`,
            }}
          />
        ))}
      </div>
      <div className="precis-comets" aria-hidden="true">
        <i />
        <i />
        <i />
      </div>
      {/* Top Navigation & Telemetry Bar */}
      <Header
        activeTab={activeTab}
        theme={theme}
        toggleTheme={toggleTheme}
        hardware={hardware}
        isOnline={isOnline}
      />

      {/* Main Application Area — Full-Screen Edge-to-Edge Responsive Grid */}
      <main
        key={activeTab}
        className="flex-1 min-h-0 w-full flex flex-col overflow-hidden relative z-10 animate-tab-fade"
      >
        {activeTab === "chat" && <ChatView />}
        {activeTab === "facts" && <FactExplorer />}
        {activeTab === "documents" && <DocumentManager />}
        {activeTab === "system" && <HardwarePanel />}
        {activeTab === "evaluation" && <EvaluationView />}
        {activeTab === "security" && <SecurityView />}
        {activeTab === "settings" && <SettingsView theme={theme} onThemeChange={setTheme} />}
      </main>

      {/* Strict Monochrome Workstation Footer */}
      <footer className="precis-footer relative z-10 h-[1.75rem] px-[1rem] text-[0.5625rem] font-mono text-[var(--tx-4)] select-none shrink-0 flex items-center">
        <div className="w-full flex items-center justify-between gap-[0.5rem]">
          <div className="flex items-center gap-[0.75rem]">
            <span>PRÉCIS v0.1.0 · EPISTEMIC SVOA EDGE RAG</span>
            <span className="hidden sm:inline">|</span>
            <span className="hidden sm:inline">WORKBENCH MODE</span>
          </div>
          <div className="flex items-center gap-[0.75rem]">
            <span className="hidden md:inline">SPACY · FASTCOREF · CHROMADB · OLLAMA</span>
            <span>
              <span className="precis-gradient-text">● NEURAL CORE</span>
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export function App() {
  return (
    <RouterProvider>
      <AppContent />
    </RouterProvider>
  );
}

export default App;
