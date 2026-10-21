import { createFileRoute, redirect } from "@tanstack/react-router";
import { PrecisClient } from "@/precis/PrecisClient";

export const Route = createFileRoute("/")({
  // The workspace lives under the "/$" route only, so moving between tabs never
  // remounts it by switching route components.
  beforeLoad: () => {
    throw redirect({ to: "/$", params: { _splat: "chat" } });
  },
  head: () => ({
    meta: [
      { title: "Précis — Epistemic AI Research Workspace" },
      {
        name: "description",
        content: "Ask questions over your documents with typed, evidence-backed answers.",
      },
      { property: "og:title", content: "Précis — Epistemic AI Research Workspace" },
      {
        property: "og:description",
        content: "Ask questions over your documents with typed, evidence-backed answers.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: PrecisClient,
});
