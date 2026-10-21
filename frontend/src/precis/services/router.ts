// @ts-nocheck — ported code written for a less strict TS config
import { createContext, useContext } from "react";
import type { ActiveTab } from "../types/api";

export interface RouteState {
  path: string;
  activeTab: ActiveTab;
  conversationId?: string;
}

export interface RouterContextType extends RouteState {
  navigate: (to: string, options?: { replace?: boolean }) => void;
  navigateToTab: (tab: ActiveTab, conversationId?: string) => void;
}

/** First path segments that map to a workspace tab; anything else is a 404. */
export const KNOWN_TABS = [
  "chat",
  "facts",
  "documents",
  "system",
  "evaluation",
  "security",
  "settings",
] as const;

export const RouterContext = createContext<RouterContextType | null>(null);

export function parsePath(pathname: string, hash: string): RouteState {
  const rawCandidate = hash && hash.startsWith("#") ? hash.slice(1) : pathname || "/";
  const raw = rawCandidate.startsWith("/") ? rawCandidate : `/${rawCandidate}`;

  // Clean trailing slash
  const clean = raw.length > 1 && raw.endsWith("/") ? raw.slice(0, -1) : raw;
  const parts = clean.split("/").filter(Boolean);

  if (parts.length === 0 || parts[0] === "chat") {
    return {
      path: clean,
      activeTab: "chat",
      conversationId: parts[1],
    };
  }

  if (parts[0] === "facts") {
    return { path: clean, activeTab: "facts" };
  }

  if (parts[0] === "documents") {
    return { path: clean, activeTab: "documents" };
  }

  if (parts[0] === "system") {
    return { path: clean, activeTab: "system" };
  }

  if (parts[0] === "evaluation") {
    return { path: clean, activeTab: "evaluation" };
  }

  if (parts[0] === "security") {
    return { path: clean, activeTab: "security" };
  }

  if (parts[0] === "settings") {
    return { path: clean, activeTab: "settings" };
  }

  // Fallback default
  return {
    path: "/chat",
    activeTab: "chat",
  };
}

export function useRouter(): RouterContextType {
  const ctx = useContext(RouterContext);
  if (!ctx) {
    throw new Error("useRouter must be used within a RouterProvider");
  }
  return ctx;
}
