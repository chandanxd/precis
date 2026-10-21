import { createFileRoute, notFound } from "@tanstack/react-router";
import { KNOWN_TABS } from "@/precis/services/router";
import { PrecisClient } from "@/precis/PrecisClient";

export const Route = createFileRoute("/$")({
  beforeLoad: ({ params }) => {
    const first = (params._splat ?? "").split("/").filter(Boolean)[0];
    if (!first || !(KNOWN_TABS as readonly string[]).includes(first)) throw notFound();
  },
  head: () => ({
    meta: [
      { title: "Précis Workspace" },
      {
        name: "description",
        content: "Précis research workspace: facts, documents, hardware and settings.",
      },
      { property: "og:title", content: "Précis Workspace" },
      {
        property: "og:description",
        content: "Précis research workspace: facts, documents, hardware and settings.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: PrecisClient,
});
