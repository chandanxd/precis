// @ts-nocheck — ported code written for a less strict TS config
import { useEffect, useRef, useState } from "react";
import {
  MessageSquare,
  Network,
  FileText,
  Cpu,
  Sun,
  Moon,
  Terminal,
  Settings,
  FlaskConical,
  ShieldCheck,
} from "lucide-react";
import type { ActiveTab, HardwareProfile, Theme } from "../../types/api";
import { Link } from "./Router";

interface HeaderProps {
  activeTab: ActiveTab;
  theme: Theme;
  toggleTheme: () => void;
  hardware: HardwareProfile | null;
  isOnline: boolean | null;
}

export const Header = ({ activeTab, theme, toggleTheme, hardware, isOnline }: HeaderProps) => {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const settingsRef = useRef<HTMLDivElement>(null);

  const navItems: { id: ActiveTab; label: string; icon: typeof MessageSquare; path: string }[] = [
    { id: "chat", label: "Query", icon: MessageSquare, path: "/chat" },
    { id: "facts", label: "Facts", icon: Network, path: "/facts" },
    { id: "documents", label: "Docs", icon: FileText, path: "/documents" },
    { id: "system", label: "Hardware", icon: Cpu, path: "/system" },
    { id: "settings", label: "Settings", icon: Settings, path: "/settings" },
  ];

  // Eval and Security live as sub-categories of Settings
  const settingsSubItems: {
    id: ActiveTab;
    label: string;
    icon: typeof MessageSquare;
    path: string;
  }[] = [
    { id: "settings", label: "Preferences", icon: Settings, path: "/settings" },
    { id: "evaluation", label: "Eval", icon: FlaskConical, path: "/evaluation" },
    { id: "security", label: "Security", icon: ShieldCheck, path: "/security" },
  ];

  const isSettingsGroupActive =
    activeTab === "settings" || activeTab === "evaluation" || activeTab === "security";

  useEffect(() => {
    if (!settingsOpen) return;
    const handlePointerDown = (e: MouseEvent) => {
      if (settingsRef.current && !settingsRef.current.contains(e.target as Node)) {
        setSettingsOpen(false);
      }
    };
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setSettingsOpen(false);
    };
    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [settingsOpen]);

  // Close the submenu whenever the route changes
  useEffect(() => {
    setSettingsOpen(false);
  }, [activeTab]);

  return (
    <header className="precis-header h-14 px-5 select-none shrink-0 flex items-center relative z-20">
      <div className="w-full flex items-center justify-between gap-3">
        {/* Brand and System Identity */}
        <Link to="/chat" className="flex items-center gap-3 group">
          <div className="precis-logo">
            <Terminal size={15} strokeWidth={2.4} />
          </div>
          <div className="flex flex-col leading-none">
            <span className="precis-wordmark">PRÉCIS</span>
            <span className="hidden md:inline text-[0.625rem] font-mono text-[var(--tx-3)] tracking-[0.2em] uppercase mt-1">
              Epistemic SVOA Engine
            </span>
          </div>
        </Link>

        {/* Main Navigation Tabs */}
        <nav className="precis-nav">
          {navItems.map((item) => {
            const Icon = item.icon;
            if (item.id === "settings") {
              return (
                <div key={item.id} ref={settingsRef} className="relative">
                  <button
                    type="button"
                    onClick={() => setSettingsOpen((o) => !o)}
                    aria-expanded={settingsOpen}
                    aria-haspopup="true"
                    className={`precis-nav-item ${isSettingsGroupActive ? "is-group-active" : ""}`}
                  >
                    <Icon size={14} strokeWidth={1.8} />
                    <span>{item.label}</span>
                    <span
                      className={`precis-nav-caret ${settingsOpen ? "is-open" : ""}`}
                      aria-hidden="true"
                    >
                      ▾
                    </span>
                  </button>
                  {settingsOpen && (
                    <div className="precis-nav-submenu" role="menu">
                      {settingsSubItems.map((sub) => {
                        const SubIcon = sub.icon;
                        return (
                          <Link
                            key={sub.id}
                            to={sub.path}
                            role="menuitem"
                            className={`precis-nav-subitem ${activeTab === sub.id ? "is-active" : ""}`}
                          >
                            <SubIcon size={13} strokeWidth={1.8} />
                            <span>{sub.label}</span>
                          </Link>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            }
            const isActive = activeTab === item.id;
            return (
              <Link
                key={item.id}
                to={item.path}
                className={`precis-nav-item ${isActive ? "is-active" : ""}`}
              >
                <Icon size={14} strokeWidth={1.8} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Telemetry Status & Theme Switcher */}
        <div className="flex items-center gap-3">
          <div className="hidden xl:flex items-center gap-2 font-mono text-[0.6875rem] text-[var(--tx-3)]">
            <span className="text-[var(--tx-2)] font-medium">
              {hardware?.recommended_model || "Unavailable"}
            </span>
            <span className="text-[var(--tx-4)]">·</span>
            <span>{hardware?.token_ceiling ? `${hardware.token_ceiling} tok` : "—"}</span>
            <span className="text-[var(--tx-4)]">·</span>
            <span className="uppercase text-[var(--tx-4)]">
              [{hardware?.recommended_mode || "standby"}]
            </span>
          </div>

          <div className="hidden sm:flex items-center gap-1.5 font-mono text-[0.6875rem] text-[var(--tx-3)]">
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                isOnline ? "bg-[var(--accent-strong)]" : "bg-[var(--tx-4)]"
              }`}
            />
            <span>{isOnline ? "Live" : "Offline"}</span>
          </div>

          <button
            type="button"
            onClick={toggleTheme}
            title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
            aria-label="Toggle theme"
            className={`precis-theme-toggle ${theme === "light" ? "is-light" : ""}`}
          >
            <span className="precis-theme-knob">
              {theme === "dark" ? (
                <Moon size={12} strokeWidth={2} />
              ) : (
                <Sun size={12} strokeWidth={2} />
              )}
            </span>
          </button>
        </div>
      </div>
    </header>
  );
};
