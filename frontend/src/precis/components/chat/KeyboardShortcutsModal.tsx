// @ts-nocheck — ported code written for a less strict TS config
import { useEffect, useRef } from "react";
import { Keyboard, X } from "lucide-react";

interface KeyboardShortcutsModalProps {
  isOpen: boolean;
  onClose: () => void;
  isMac?: boolean;
}

export const KeyboardShortcutsModal = ({
  isOpen,
  onClose,
  isMac = false,
}: KeyboardShortcutsModalProps) => {
  const modalRef = useRef<HTMLDivElement>(null);
  const prevActiveElementRef = useRef<HTMLElement | null>(null);

  const modKey = isMac ? "⌘" : "Ctrl";
  const shiftKey = isMac ? "⇧" : "Shift";

  useEffect(() => {
    if (isOpen) {
      prevActiveElementRef.current = document.activeElement as HTMLElement | null;
      modalRef.current?.focus();
    } else if (prevActiveElementRef.current) {
      prevActiveElementRef.current.focus();
      prevActiveElementRef.current = null;
    }
  }, [isOpen]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;
      if (e.key === "Escape") {
        e.preventDefault();
        e.stopPropagation();
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown, true);
    return () => window.removeEventListener("keydown", handleKeyDown, true);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const sections = [
    {
      title: "QUERY COMPOSER",
      shortcuts: [
        { keys: ["Enter"], desc: "Submit query" },
        { keys: ["Shift", "Enter"], desc: "Insert newline" },
        { keys: [modKey, "Enter"], desc: "Submit multiline query" },
        { keys: [modKey, "K"], desc: "Focus query input" },
      ],
    },
    {
      title: "SUPPORTING EVIDENCE & PREMISES",
      shortcuts: [
        { keys: ["Space"], desc: "Toggle evidence (header focused)" },
        { keys: ["↑", "↓"], desc: "Navigate premise rows" },
        { keys: ["Enter"], desc: "Select / expand focused premise" },
        { keys: ["Esc"], desc: "Deselect premise / close details" },
      ],
    },
    {
      title: "INSPECTOR & WORKBENCH",
      shortcuts: [
        { keys: [modKey, shiftKey, "I"], desc: "Focus Context Inspector" },
        { keys: [modKey, shiftKey, "C"], desc: "Copy active answer" },
        { keys: ["Alt", "↑ / ↓"], desc: "Switch response turn" },
      ],
    },
    {
      title: "SYSTEM & REFERENCE",
      shortcuts: [
        { keys: [modKey, "/"], desc: "Toggle this shortcut overlay" },
        { keys: ["Esc"], desc: "Close overlay" },
      ],
    },
  ];

  return (
    <div
      className="fixed inset-0 z-50 bg-black/65 backdrop-blur-[2px] flex items-center justify-center p-4 animate-in fade-in duration-150"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-label="Keyboard Shortcuts"
    >
      <div
        ref={modalRef}
        tabIndex={-1}
        className="w-full max-w-lg border border-[var(--bd-3)] bg-[var(--bg)] text-[var(--tx)] shadow-2xl p-5 flex flex-col gap-4 font-mono outline-none"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[var(--bd)] pb-3 select-none">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[var(--tx)]">
            <Keyboard size={14} strokeWidth={1.5} className="text-[var(--tx-2)]" />
            <span>WORKBENCH KEYBOARD SHORTCUTS</span>
          </div>

          <button
            type="button"
            onClick={onClose}
            title="Close shortcut reference (Esc)"
            className="flex items-center gap-1 text-[0.625rem] text-[var(--tx-3)] hover:text-[var(--tx)] border border-[var(--bd)] hover:border-[var(--bd-3)] px-1.5 py-0.5 transition-colors cursor-pointer"
          >
            <span>ESC</span>
            <X size={10} strokeWidth={2} />
          </button>
        </div>

        {/* Shortcuts Grid */}
        <div className="flex flex-col gap-4 max-h-[65vh] overflow-y-auto pr-1">
          {sections.map((section, sIdx) => (
            <div key={sIdx} className="flex flex-col gap-1.5">
              <div className="text-[0.625rem] font-bold text-[var(--tx-3)] uppercase tracking-wider">
                {section.title}
              </div>
              <div className="border border-[var(--bd)] bg-[var(--bg-2)] divide-y divide-[var(--bd)]">
                {section.shortcuts.map((sc, scIdx) => (
                  <div
                    key={scIdx}
                    className="flex items-center justify-between px-3 py-1.5 text-xs hover:bg-[var(--bg-3)] transition-colors"
                  >
                    <span className="text-[var(--tx-2)] text-[0.6875rem]">{sc.desc}</span>
                    <div className="flex items-center gap-1 shrink-0">
                      {sc.keys.map((k, kIdx) => (
                        <kbd
                          key={kIdx}
                          className="px-1.5 py-0.5 text-[0.625rem] font-mono bg-[var(--bg)] border border-[var(--bd-3)] text-[var(--tx)] shadow-[0_1px_0_rgba(255,255,255,0.08)] font-semibold"
                        >
                          {k}
                        </kbd>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="border-t border-[var(--bd)] pt-2.5 flex items-center justify-between text-[0.625rem] text-[var(--tx-3)] select-none">
          <span>Platform: {isMac ? "macOS (⌘)" : "Linux / Windows (Ctrl)"}</span>
          <span className="font-mono text-[var(--tx-4)]">
            Press Esc or click outside to dismiss
          </span>
        </div>
      </div>
    </div>
  );
};
