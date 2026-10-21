// @ts-nocheck — ported code written for a less strict TS config
import React, { useCallback, useMemo } from "react";
import { useLocation, useRouter as useTanstackRouter } from "@tanstack/react-router";
import type { ActiveTab } from "../../types/api";
import { RouterContext, parsePath, useRouter } from "../../services/router";
import type { RouteState } from "../../services/router";

export const RouterProvider = ({ children }: { children: React.ReactNode }) => {
  // TanStack Router owns the URL and history; this provider only derives the
  // workspace route from its location and navigates through it.
  const tsRouter = useTanstackRouter();
  const location = useLocation();

  const hash = location.hash
    ? location.hash.startsWith("#")
      ? location.hash
      : `#${location.hash}`
    : "";
  const route = useMemo<RouteState>(
    () => parsePath(location.pathname, hash),
    [location.pathname, hash],
  );

  const navigate = useCallback(
    (to: string, options?: { replace?: boolean }) => {
      const targetPath = to.startsWith("/") ? to : `/${to}`;
      void tsRouter.navigate({ to: targetPath, replace: options?.replace });
    },
    [tsRouter],
  );

  const navigateToTab = useCallback(
    (tab: ActiveTab, conversationId?: string) => {
      if (tab === "chat") {
        const target = conversationId ? `/chat/${conversationId}` : "/chat";
        navigate(target);
      } else {
        navigate(`/${tab}`);
      }
    },
    [navigate],
  );

  const value = useMemo(
    () => ({
      ...route,
      navigate,
      navigateToTab,
    }),
    [route, navigate, navigateToTab],
  );

  return <RouterContext.Provider value={value}>{children}</RouterContext.Provider>;
};

interface LinkProps extends React.AnchorHTMLAttributes<HTMLAnchorElement> {
  to: string;
  replace?: boolean;
  children: React.ReactNode;
}

export const Link = ({
  to,
  replace = false,
  children,
  className = "",
  onClick,
  ...rest
}: LinkProps) => {
  const { navigate } = useRouter();

  const handleClick = (e: React.MouseEvent<HTMLAnchorElement>) => {
    onClick?.(e);
    // Only intercept normal left clicks without modifier keys
    if (
      !e.defaultPrevented &&
      e.button === 0 &&
      !e.metaKey &&
      !e.ctrlKey &&
      !e.altKey &&
      !e.shiftKey
    ) {
      e.preventDefault();
      navigate(to, { replace });
    }
  };

  return (
    <a href={to} onClick={handleClick} className={className} {...rest}>
      {children}
    </a>
  );
};
