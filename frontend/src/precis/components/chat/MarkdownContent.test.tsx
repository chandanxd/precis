import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MarkdownContent } from "./MarkdownContent";

const items = (container: HTMLElement) =>
  [...container.querySelectorAll("li")].map((li) => li.textContent);

describe("MarkdownContent", () => {
  it("splits a list the model wrote on one line", () => {
    const answer =
      "- Pawns: Move forward one square (two squares from their starting position), capture diagonally. " +
      "- Rooks: Move any number of squares horizontally or vertically. " +
      '- Knights: Jump in an "L" shape (2 squares one way, 1 square perpendicular). ' +
      "- Bishops: Move diagonally any distance. " +
      "- Queen: Combines rook and bishop moves—any number of squares. " +
      "- King: Moves one square in any direction.";
    const { container } = render(<MarkdownContent content={answer} />);
    expect(items(container).map((t) => t!.split(":")[0])).toEqual([
      "Pawns",
      "Rooks",
      "Knights",
      "Bishops",
      "Queen",
      "King",
    ]);
  });

  it("keeps an introduction before an inline list as its own paragraph", () => {
    const { container } = render(
      <MarkdownContent content="Each piece moves differently: - **Pawns:** forward. - **Rooks:** straight." />,
    );
    expect(container.querySelector("p")!.textContent).toBe("Each piece moves differently:");
    expect(items(container)).toEqual(["Pawns: forward.", "Rooks: straight."]);
  });

  it("does not split ordinary prose with a single dash", () => {
    const { container } = render(
      <MarkdownContent content="Revenue rose - Note: figures are unaudited." />,
    );
    expect(container.querySelectorAll("li")).toHaveLength(0);
  });

  it("reads star, indented, bullet-character and parenthesised lists", () => {
    const { container } = render(
      <MarkdownContent
        content={"*   **Pawns:** forward\n  - nested\n• Rooks\n\n1) first\n2) second"}
      />,
    );
    expect(items(container)).toEqual(["Pawns: forward", "nested", "Rooks", "first", "second"]);
    expect(container.querySelectorAll("ol li")).toHaveLength(2);
  });

  it("joins an indented continuation line onto its list item", () => {
    const { container } = render(
      <MarkdownContent content={"- Knights jump\n  over pieces\n- Kings"} />,
    );
    expect(items(container)).toEqual(["Knights jump over pieces", "Kings"]);
  });

  it("keeps single line breaks inside a paragraph", () => {
    const { container } = render(<MarkdownContent content={"Line one\r\nLine two"} />);
    expect(container.querySelectorAll("p br")).toHaveLength(1);
  });

  it("leaves code blocks untouched", () => {
    const code = "x - Foo: 1 - Bar: 2";
    const { container } = render(<MarkdownContent content={"```\n" + code + "\n```"} />);
    expect(container.querySelector("code")!.textContent).toBe(code);
    expect(container.querySelectorAll("li")).toHaveLength(0);
  });
});
