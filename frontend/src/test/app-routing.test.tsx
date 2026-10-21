import { QueryClient } from "@tanstack/react-query";
import { createMemoryHistory, createRouter, rootRouteId } from "@tanstack/react-router";
import { describe, expect, it } from "vitest";

import { routeTree } from "@/routeTree.gen";

// Match routes without running loaders or rendering: loaders may need a server or
// network the test run lacks, and jsdom never loads the stylesheets React waits on.
describe("App routing", () => {
  it("matches a page for / instead of falling back to not found", () => {
    const router = createRouter({ routeTree, context: { queryClient: new QueryClient() } });

    const matches = router.matchRoutes("/");

    expect(matches.at(-1)?.routeId).not.toBe(rootRouteId);
  });
});

describe("Workspace routing", () => {
  const makeRouter = (path: string) =>
    createRouter({
      routeTree,
      context: { queryClient: new QueryClient() },
      history: createMemoryHistory({ initialEntries: [path] }),
    });

  it("redirects / to the chat tab", async () => {
    const router = makeRouter("/");
    await router.load();
    expect(router.state.location.pathname).toBe("/chat");
  });

  it("keeps all workspace tabs on one route so the workspace is not remounted", async () => {
    const router = makeRouter("/chat");
    await router.load();
    const chatRoute = router.state.matches.at(-1)?.routeId;
    await router.navigate({ to: "/documents" } as never);
    await router.navigate({ to: "/chat/abc" } as never);
    expect(router.state.location.pathname).toBe("/chat/abc");
    expect(router.state.matches.at(-1)?.routeId).toBe(chatRoute);
  });

  it("returns not found for unknown paths", async () => {
    const router = makeRouter("/definitely-not-a-page");
    await router.load();
    // beforeLoad throws notFound(); the router records it on a match for the root boundary.
    expect(
      router.state.matches.some(
        (m) => (m.error as { isNotFound?: boolean } | undefined)?.isNotFound,
      ),
    ).toBe(true);
  });
});
