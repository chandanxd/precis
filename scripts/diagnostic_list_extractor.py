"""
Diagnostic List Extractor for Experiment 4.3.

Provides isolated, structured HTML list parsing, entity-role binding,
hierarchy preservation for nested lists, and malformed HTML recovery.

Used solely for diagnostic testing in Experiment 4.3.
Does NOT modify or replace any production pipeline in backend/src/precis/.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any, Dict, List, Literal, Optional, Set, Tuple


@dataclass
class ParsedListItem:
    raw_text: str
    clean_text: str
    depth: int = 0
    item_index: int = 0
    parent_prefix: str = ""
    entity_binding: Optional[Tuple[str, str]] = None  # (subject, relation_or_role)
    qualifiers: List[str] = field(default_factory=list)


@dataclass
class ParsedListBlock:
    block_id: int
    list_type: Literal["unordered", "ordered"]
    items: List[ParsedListItem]
    is_nested: bool = False
    context_tokens_est: int = 0


def clean_inline_text(text: str) -> str:
    """Unescape HTML and collapse whitespace."""
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_entity_binding(item_text: str) -> Optional[Tuple[str, str]]:
    """
    Extract entity-to-role/value binding from standard list text.
    Handles:
      - 'Entity -- Role/Value'
      - 'Entity as Role'
      - 'Entity: Value'
      - 'Entity - Role'
    """
    # 1. Double hyphen or en-dash / em-dash
    m = re.match(r"^([^-\u2013\u2014]+)\s*(?:--|[\u2013\u2014])\s*(.+)$", item_text)
    if m:
        return (clean_inline_text(m.group(1)), clean_inline_text(m.group(2)))

    # 2. ' as ' (case-insensitive)
    m = re.match(r"^([A-Za-z0-9\s\.,'\"]+?)\s+as\s+([A-Za-z0-9\s\.,'\"/:()]+)$", item_text, re.IGNORECASE)
    if m:
        return (clean_inline_text(m.group(1)), clean_inline_text(m.group(2)))

    # 3. Colon separator (ensure colon is not within a URL or time)
    m = re.match(r"^([A-Za-z0-9\s\.,'\"]+?)\s*:\s*(.+)$", item_text)
    if m:
        subj = clean_inline_text(m.group(1))
        val = clean_inline_text(m.group(2))
        if len(subj) < 50:  # avoid splitting full sentences with colons
            return (subj, val)

    return None


class RobustListParser(HTMLParser):
    """
    HTMLParser subclass specialized for extracting content lists
    while preserving nesting hierarchies, qualifiers, and malformed tags.
    """

    def __init__(self):
        super().__init__()
        self.blocks: List[ParsedListBlock] = []
        self._list_stack: List[Tuple[Literal["unordered", "ordered"], int]] = []  # (type, block_idx)
        self._current_items: List[ParsedListItem] = []
        self._current_item_parts: List[str] = []
        self._in_item: bool = False
        self._item_depth: int = 0
        self._parent_prefixes: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        ltag = tag.lower()

        if ltag in ("ul", "ol"):
            ltype: Literal["unordered", "ordered"] = "unordered" if ltag == "ul" else "ordered"
            # If entering a nested list while an item is open, flush parent item then save prefix
            if self._in_item and self._current_item_parts:
                parent_text = clean_inline_text("".join(self._current_item_parts))
                self._close_item()
                self._parent_prefixes.append(parent_text)

            block_id = len(self.blocks)
            self._list_stack.append((ltype, block_id))

        elif ltag == "li":
            if self._in_item:
                # Malformed HTML recovery: <li> encountered without preceding </li>
                self._close_item()
            self._in_item = True
            self._current_item_parts = []
            self._item_depth = len(self._list_stack)

    def handle_endtag(self, tag: str):
        ltag = tag.lower()

        if ltag == "li":
            if self._in_item:
                self._close_item()

        elif ltag in ("ul", "ol"):
            if self._in_item:
                self._close_item()
            if self._list_stack:
                ltype, b_id = self._list_stack.pop()
                if self._current_items:
                    # Estimate tokens: words * 1.3
                    all_text = " ".join(it.clean_text for it in self._current_items)
                    tok_est = int(len(all_text.split()) * 1.3)
                    self.blocks.append(ParsedListBlock(
                        block_id=b_id,
                        list_type=ltype,
                        items=list(self._current_items),
                        is_nested=len(self._parent_prefixes) > 0,
                        context_tokens_est=tok_est
                    ))
                    self._current_items = []
            if self._parent_prefixes:
                self._parent_prefixes.pop()

    def handle_data(self, data: str):
        if self._in_item:
            self._current_item_parts.append(data)

    def _close_item(self):
        if not self._in_item:
            return
        raw = "".join(self._current_item_parts)
        clean = clean_inline_text(raw)
        if clean:
            prefix = " > ".join(self._parent_prefixes) if self._parent_prefixes else ""
            binding = extract_entity_binding(clean)
            parens = re.findall(r"\(([^)]+)\)", clean)
            item = ParsedListItem(
                raw_text=raw,
                clean_text=clean,
                depth=self._item_depth,
                item_index=len(self._current_items),
                parent_prefix=prefix,
                entity_binding=binding,
                qualifiers=parens
            )
            self._current_items.append(item)
        self._current_item_parts = []
        self._in_item = False

    def close(self):
        super().close()
        # EOF recovery: close any trailing open items
        if self._in_item:
            self._close_item()
        if self._current_items and self._list_stack:
            ltype, b_id = self._list_stack.pop()
            all_text = " ".join(it.clean_text for it in self._current_items)
            tok_est = int(len(all_text.split()) * 1.3)
            self.blocks.append(ParsedListBlock(
                block_id=b_id,
                list_type=ltype,
                items=list(self._current_items),
                is_nested=False,
                context_tokens_est=tok_est
            ))
            self._current_items = []


def extract_lists_from_html(html_content: str) -> List[ParsedListBlock]:
    """Parse HTML content and extract content list blocks."""
    parser = RobustListParser()
    parser.feed(html_content)
    parser.close()
    return parser.blocks


def is_nav_or_boilerplate_list(block: ParsedListBlock) -> bool:
    """
    Detect whether a list block is boilerplate / navigation links
    rather than factual document content.
    """
    if not block.items:
        return True
    # Heuristic 1: Extremely short average item length (< 12 chars) with many items (> 5)
    mean_len = sum(len(it.clean_text) for it in block.items) / len(block.items)
    nav_keywords = {"home", "about us", "contact", "privacy policy", "terms of service", "copyright"}
    nav_matches = sum(1 for it in block.items if it.clean_text.lower() in nav_keywords)
    if nav_matches >= 2 or (nav_matches > 0 and len(block.items) <= 4):
        return True
    return False


def render_list_to_markdown(block: ParsedListBlock) -> str:
    """Render a ParsedListBlock as compact markdown with prefixes and hierarchy."""
    lines = []
    for idx, it in enumerate(block.items):
        prefix_str = f"[{it.parent_prefix}] " if it.parent_prefix else ""
        if block.list_type == "ordered":
            lines.append(f"{idx + 1}. {prefix_str}{it.clean_text}")
        else:
            lines.append(f"* {prefix_str}{it.clean_text}")
    return "\n".join(lines)
