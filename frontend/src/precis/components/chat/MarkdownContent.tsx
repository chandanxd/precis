// @ts-nocheck — ported code written for a less strict TS config
/**
 * MarkdownContent: lightweight Markdown renderer (no external library).
 *
 * Supported constructs (as required by the spec):
 *   - ATX headings: # h1 through ###### h6
 *   - Paragraphs
 *   - Ordered lists  (1. item, 1) item)
 *   - Unordered lists (- / * / + / • item), indented or not
 *   - Single line breaks inside a paragraph (chat style)
 *   - Lists a model wrote on one line ("Moves: - Pawns: … - Rooks: …")
 *   - Fenced code blocks (```lang … ```)
 *   - Block quotes (> text)
 *   - Horizontal rules (---, ***, ___)
 *   - Inline: **bold**, *italic*, `code`, [link](url), ~~strikethrough~~
 *   - Safe: href values are sanitised; no innerHTML.
 *
 * Implementation intentionally avoids innerHTML and dangerouslySetInnerHTML
 * to prevent XSS.
 */
import React from "react";

// ─── Inline parser ────────────────────────────────────────────────────────────

interface InlineNode {
  type: "text" | "bold" | "italic" | "bolditalic" | "code" | "link" | "del";
  text?: string;
  href?: string;
  children?: InlineNode[];
}

function parseInline(src: string): InlineNode[] {
  if (!src) return [];
  const nodes: InlineNode[] = [];
  // Patterns ordered longest-match-first
  const re =
    /(\*\*\*(.+?)\*\*\*)|(\*\*(.+?)\*\*)|(\*(.+?)\*)|(__(.+?)__)|(~~(.+?)~~)|(`([^`]+)`)|(\[([^\]]+)\]\((https?:\/\/[^)]+)\))/g;
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(src)) !== null) {
    if (m.index > last) {
      nodes.push({ type: "text", text: src.slice(last, m.index) });
    }
    if (m[1]) nodes.push({ type: "bolditalic", children: parseInline(m[2]) });
    else if (m[3]) nodes.push({ type: "bold", children: parseInline(m[4]) });
    else if (m[5]) nodes.push({ type: "italic", children: parseInline(m[6]) });
    else if (m[7]) nodes.push({ type: "bold", children: parseInline(m[8]) });
    else if (m[9]) nodes.push({ type: "del", children: parseInline(m[10]) });
    else if (m[11]) nodes.push({ type: "code", text: m[12] });
    else if (m[13]) nodes.push({ type: "link", text: m[14], href: m[15] });
    last = re.lastIndex;
  }
  if (last < src.length) {
    nodes.push({ type: "text", text: src.slice(last) });
  }
  return nodes;
}

function renderInline(nodes: InlineNode[], key?: string): React.ReactNode {
  return nodes.map((n, i) => {
    const k = `${key ?? ""}-${i}`;
    switch (n.type) {
      case "text":
        return n.text;
      case "bold":
        return (
          <strong key={k} className="font-semibold text-[var(--tx)]">
            {renderInline(n.children!, k)}
          </strong>
        );
      case "italic":
        return (
          <em key={k} className="italic text-[var(--tx-2)]">
            {renderInline(n.children!, k)}
          </em>
        );
      case "bolditalic":
        return (
          <strong key={k} className="font-semibold italic text-[var(--tx)]">
            {renderInline(n.children!, k)}
          </strong>
        );
      case "del":
        return (
          <del key={k} className="line-through text-[var(--tx-3)]">
            {renderInline(n.children!, k)}
          </del>
        );
      case "code":
        return (
          <code
            key={k}
            className="font-mono text-[0.8125rem] px-1 py-0.5 rounded-sm bg-[var(--bg-3)] text-[var(--tx)] border border-[var(--bd)]"
          >
            {n.text}
          </code>
        );
      case "link":
        return (
          <a
            key={k}
            href={n.href}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[var(--accent-strong)] underline underline-offset-2 hover:opacity-80 transition-opacity"
          >
            {n.text}
          </a>
        );
      default:
        return null;
    }
  });
}

// ─── Block parser ─────────────────────────────────────────────────────────────

type BlockNode =
  | { type: "h"; level: 1 | 2 | 3 | 4 | 5 | 6; inline: string }
  | { type: "hr" }
  | { type: "code_block"; lang: string; code: string }
  | { type: "blockquote"; lines: string[] }
  | { type: "ul"; items: string[] }
  | { type: "ol"; items: string[] }
  | { type: "p"; inline: string };

const UL_MARKER = /^\s*[-*+•]\s+/;
const OL_MARKER = /^\s*\d+[.)]\s+/;
// " - Label:" where the label is short and capitalised, e.g. " - **Rooks:**".
const INLINE_ITEM = /(?:^|\s)-\s+(?=\*{0,2}[A-Z][^:\n]{0,40}:)/g;

/**
 * Small models sometimes write a list on one line ("Pieces: - Pawns: … - Rooks: …").
 * When a line holds two or more such " - Label:" items, put each on its own line.
 */
function splitInlineList(line: string): string[] {
  if (UL_MARKER.test(line) && !/\s-\s/.test(line.replace(UL_MARKER, ""))) return [line];
  const starts = [...line.matchAll(INLINE_ITEM)].map(
    (m) => m.index! + (m[0].startsWith("-") ? 0 : 1),
  );
  if (starts.length < 2) return [line];
  const out: string[] = [];
  const intro = line.slice(0, starts[0]).trim();
  if (intro) out.push(intro);
  starts.forEach((start, k) => out.push(line.slice(start, starts[k + 1] ?? line.length).trim()));
  return out;
}

function parseBlocks(markdown: string): BlockNode[] {
  let inFence = false;
  const lines = markdown
    .replace(/\r\n?/g, "\n")
    .split("\n")
    .flatMap((l) => {
      if (/^```/.test(l)) inFence = !inFence;
      // Code is left exactly as written.
      return inFence || /^```/.test(l) ? [l] : splitInlineList(l);
    });
  const blocks: BlockNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Fenced code block
    if (/^```/.test(line)) {
      const lang = line.slice(3).trim();
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !/^```/.test(lines[i])) {
        codeLines.push(lines[i]);
        i++;
      }
      i++; // consume closing ```
      blocks.push({ type: "code_block", lang, code: codeLines.join("\n") });
      continue;
    }

    // Horizontal rule
    if (/^(\*{3,}|-{3,}|_{3,})\s*$/.test(line)) {
      blocks.push({ type: "hr" });
      i++;
      continue;
    }

    // ATX Headings
    const hMatch = /^(#{1,6})\s+(.+)$/.exec(line);
    if (hMatch) {
      const level = Math.min(hMatch[1].length, 6) as 1 | 2 | 3 | 4 | 5 | 6;
      blocks.push({ type: "h", level, inline: hMatch[2].trim() });
      i++;
      continue;
    }

    // Blockquote
    if (/^>\s?/.test(line)) {
      const quoteLines: string[] = [];
      while (i < lines.length && /^>\s?/.test(lines[i])) {
        quoteLines.push(lines[i].replace(/^>\s?/, ""));
        i++;
      }
      blocks.push({ type: "blockquote", lines: quoteLines });
      continue;
    }

    // Lists. Nested items are flattened; indented lines without a marker
    // continue the previous item.
    const listType = UL_MARKER.test(line) ? "ul" : OL_MARKER.test(line) ? "ol" : null;
    if (listType) {
      const marker = listType === "ul" ? UL_MARKER : OL_MARKER;
      const items: string[] = [];
      while (i < lines.length) {
        const next = lines[i];
        if (marker.test(next)) {
          items.push(next.replace(marker, ""));
        } else if (/^\s{2,}\S/.test(next) && !UL_MARKER.test(next) && !OL_MARKER.test(next)) {
          items[items.length - 1] += ` ${next.trim()}`;
        } else {
          break;
        }
        i++;
      }
      blocks.push({ type: listType, items });
      continue;
    }

    // Blank line — skip
    if (/^\s*$/.test(line)) {
      i++;
      continue;
    }

    // Paragraph: accumulate until blank line or a block marker
    const paraLines: string[] = [];
    while (
      i < lines.length &&
      !/^\s*$/.test(lines[i]) &&
      !/^#{1,6}\s/.test(lines[i]) &&
      !/^```/.test(lines[i]) &&
      !UL_MARKER.test(lines[i]) &&
      !OL_MARKER.test(lines[i]) &&
      !/^>\s?/.test(lines[i]) &&
      !/^(\*{3,}|-{3,}|_{3,})\s*$/.test(lines[i])
    ) {
      paraLines.push(lines[i]);
      i++;
    }
    if (paraLines.length > 0) {
      // Keep single line breaks: chat answers use them for separate lines.
      blocks.push({ type: "p", inline: paraLines.join("\n") });
    }
  }
  return blocks;
}

// ─── Block renderer ────────────────────────────────────────────────────────────

const HEADING_STYLES: Record<number, string> = {
  1: "text-[1.25rem] font-bold text-[var(--tx)] mt-[0.9em] mb-[0.4em] leading-tight",
  2: "text-[1.1rem] font-semibold text-[var(--tx)] mt-[0.8em] mb-[0.35em] leading-tight",
  3: "text-[1rem] font-semibold text-[var(--tx)] mt-[0.7em] mb-[0.3em] leading-tight",
  4: "text-[0.9375rem] font-semibold text-[var(--tx)] mt-[0.6em] mb-[0.25em]",
  5: "text-[0.875rem] font-semibold text-[var(--tx)] mt-[0.5em] mb-[0.2em]",
  6: "text-[0.875rem] font-medium text-[var(--tx-2)] mt-[0.4em] mb-[0.15em]",
};

function renderBlock(block: BlockNode, idx: number): React.ReactNode {
  const key = `block-${idx}`;
  switch (block.type) {
    case "hr":
      return <hr key={key} className="border-[var(--bd)] my-[1em]" />;

    case "h": {
      const Tag = `h${block.level}` as keyof JSX.IntrinsicElements;
      return (
        <Tag key={key} className={HEADING_STYLES[block.level]}>
          {renderInline(parseInline(block.inline), key)}
        </Tag>
      );
    }

    case "code_block":
      return (
        <div
          key={key}
          className="my-[0.75em] rounded-sm overflow-hidden border border-[var(--bd-3)] bg-[var(--bg-2)]"
        >
          {block.lang && (
            <div className="flex items-center px-3 py-1 border-b border-[var(--bd)] bg-[var(--bg-3)]">
              <span className="text-[0.625rem] font-mono text-[var(--tx-4)] uppercase tracking-wider">
                {block.lang}
              </span>
            </div>
          )}
          <pre className="overflow-x-auto p-3">
            <code className="font-mono text-[0.8125rem] leading-[1.6] text-[var(--tx-2)] whitespace-pre">
              {block.code}
            </code>
          </pre>
        </div>
      );

    case "blockquote":
      return (
        <blockquote
          key={key}
          className="border-l-2 border-[var(--accent)] pl-3 my-[0.75em] text-[var(--tx-2)] italic"
        >
          {block.lines.map((l, li) => (
            <p key={li} className="leading-[1.7]">
              {renderInline(parseInline(l), `${key}-${li}`)}
            </p>
          ))}
        </blockquote>
      );

    case "ul":
      return (
        <ul
          key={key}
          className="list-disc list-outside pl-[1.5em] mb-[0.75em] flex flex-col gap-[0.25em] text-[var(--tx)]"
        >
          {block.items.map((item, ii) => (
            <li key={ii} className="leading-[1.6]">
              {renderInline(parseInline(item), `${key}-${ii}`)}
            </li>
          ))}
        </ul>
      );

    case "ol":
      return (
        <ol
          key={key}
          className="list-decimal list-outside pl-[1.5em] mb-[0.75em] flex flex-col gap-[0.25em] text-[var(--tx)]"
        >
          {block.items.map((item, ii) => (
            <li key={ii} className="leading-[1.6]">
              {renderInline(parseInline(item), `${key}-${ii}`)}
            </li>
          ))}
        </ol>
      );

    case "p":
      return (
        <p key={key} className="mb-[0.75em] last:mb-0 leading-[1.7] text-[var(--tx)]">
          {block.inline.split("\n").map((textLine, li) => (
            <React.Fragment key={li}>
              {li > 0 && <br />}
              {renderInline(parseInline(textLine), `${key}-${li}`)}
            </React.Fragment>
          ))}
        </p>
      );

    default:
      return null;
  }
}

// ─── Public component ──────────────────────────────────────────────────────────

interface MarkdownContentProps {
  content: string;
  className?: string;
}

export const MarkdownContent = ({ content, className = "" }: MarkdownContentProps) => {
  if (!content) return null;
  const blocks = parseBlocks(content);
  return (
    <div className={`precis-markdown ${className}`}>
      {blocks.map((block, idx) => renderBlock(block, idx))}
    </div>
  );
};
