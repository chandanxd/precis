import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EvaluationView } from "./EvaluationView";

describe("EvaluationView", () => {
  it("shows only findings that the README states word for word", () => {
    const readme = readFileSync(resolve(__dirname, "../../../../../README.md"), "utf8")
      .replace(/`|\*\*/g, "")
      .replace(/\s+/g, " ");
    const { container } = render(<EvaluationView />);
    const findings = [...container.querySelectorAll("li")].map((li) =>
      li.textContent!.replace(/\s+/g, " ").trim(),
    );
    expect(findings.length).toBeGreaterThan(0);
    for (const finding of findings) expect(readme).toContain(finding);
  });
});
