"""
Précis: Structural Document Retention Pipeline (Tables & Lists).

Provides robust, feature-flagged structural retention for HTML documents:
- Prose-structure separation with clean prose preservation.
- Compact GitHub-Flavored Markdown (GFM) table extraction and threshold-based selection.
- Hierarchical, structure-aware list extraction (ordered, unordered, nested, key-value).
- Conservative table-list overlap deduplication to suppress distractor list append.
- Exact context-budget accounting ensuring strict adherence to the hardware token ceiling.

Feature Flag:
    PRECIS_ENABLE_LIST_EXTRACTION (default: False)
    When disabled, preserves the existing table-retention path bit-compatibly.
"""

from __future__ import annotations

import hashlib
import html
import math
import os
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, Set, Tuple

from precis.graph.schema import Fact, StructuralEvidence

if TYPE_CHECKING:
    from precis.graph.store import FactStore



FLAG_NAME = "PRECIS_ENABLE_LIST_EXTRACTION"
DEFAULT_MAX_TABLE_TOKENS = 500
DEFAULT_TOKEN_CEILING = 2048


# ==============================================================================
# 1. Feature Flag Configuration & Safe Validation
# ==============================================================================

def parse_feature_flag(val: Any) -> bool:
    """
    Safely parse feature flag value into a boolean.

    Raises ValueError on unrecognized string or invalid type to prevent
    silent misconfiguration.
    """
    if val is None:
        return False
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        if val == 1:
            return True
        if val == 0:
            return False
        raise ValueError(
            f"Invalid numeric value for {FLAG_NAME}: {val}. Expected 1 (enabled) or 0 (disabled)."
        )
    if isinstance(val, str):
        cleaned = val.strip().lower()
        if cleaned in ("1", "true", "yes", "on"):
            return True
        if cleaned in ("0", "false", "no", "off", ""):
            return False
        raise ValueError(
            f"Invalid string value for {FLAG_NAME}: '{val}'. "
            "Expected 'true'/'false', '1'/'0', 'yes'/'no', or 'on'/'off'."
        )
    raise ValueError(
        f"Invalid type for {FLAG_NAME}: {type(val).__name__}. Expected bool or str."
    )


def is_list_extraction_enabled(override: bool | None = None) -> bool:
    """
    Determine if list extraction is enabled.

    Order of precedence:
    1. Explicit function override if not None.
    2. PRECIS_ENABLE_LIST_EXTRACTION environment variable.
    3. Default: False.
    """
    if override is not None:
        return parse_feature_flag(override)
    raw_env = os.getenv(FLAG_NAME)
    return parse_feature_flag(raw_env)


# ==============================================================================
# 2. Token Estimation & Text Helpers
# ==============================================================================

def clean_tag_text(text: str) -> str:
    """Strip HTML tags, unescape HTML entities, and collapse whitespace."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def estimate_text_tokens(text: str) -> int:
    """
    Subword expansion estimation (~1.3 tokens per whitespace-delimited word).
    Matches canonical Précis token-estimation method.
    """
    if not text or not text.strip():
        return 0
    words = len(text.strip().split())
    return max(1, int(math.ceil(words * 1.3)))


# ==============================================================================
# 3. Data Structures
# ==============================================================================

@dataclass
class ParsedTableCell:
    tag: str
    text: str


@dataclass
class ParsedTableRow:
    row_idx: int
    raw_html: str
    cells: List[ParsedTableCell]


@dataclass
class ParsedTable:
    table_idx: int
    caption: str
    headers: List[str]
    rows: List[ParsedTableRow]
    raw_html: str


@dataclass
class StructuredBlock:
    block_id: int
    block_type: Literal["table", "ordered_list", "unordered_list"]
    start_char: int
    end_char: int
    caption: str
    headers: List[str]
    rows: List[List[str]]
    raw_html: str
    is_truncated_eof: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedListItem:
    raw_text: str
    clean_text: str
    depth: int
    item_index: int
    parent_prefix: str
    entity_binding: Optional[Tuple[str, str]]
    qualifiers: List[str]


@dataclass
class ParsedListBlock:
    block_id: int
    list_type: Literal["unordered", "ordered"]
    items: List[ParsedListItem]
    is_nested: bool
    context_tokens_est: int


# ==============================================================================
# 4. Table Document Parsing & Markdown Rendering
# ==============================================================================

class StructuralDocumentParser(HTMLParser):
    """
    Structural HTML Parser with explicit recovery rules.
    Decompiles input document into:
    1. Clean prose stream with structured blocks excised and replaced with '\\n\\n'.
    2. StructuredBlock stream tracking table headers, rows, list items, and character offsets.
    """

    def __init__(self, raw_html: str):
        super().__init__()
        self.raw_html = raw_html
        self.clean_prose_parts: List[str] = []
        self.struct_blocks: List[StructuredBlock] = []

        # Nesting and parser state
        self.table_depth = 0
        self.cell_depth = 0
        self.list_depth = 0
        self.li_depth = 0

        # Current block tracking
        self.current_block_type: Optional[Literal["table", "ordered_list", "unordered_list"]] = None
        self.block_start_idx = 0
        self.block_start_char = 0
        self.current_rows: List[List[str]] = []
        self.current_row: List[str] = []
        self.current_cell_parts: List[str] = []
        self.caption = ""
        self.in_caption = False
        self.headers: List[str] = []
        self.row_has_th: List[bool] = []
        self.current_row_has_th = False

    def parse(self) -> Tuple[str, List[StructuredBlock]]:
        """Parse the document and return (clean_prose, structured_blocks)."""
        self.feed(self.raw_html)
        # EOF recovery: close any unclosed table or list
        if self.table_depth > 0 or self.list_depth > 0:
            self._close_structured_block(is_eof=True)

        clean_prose = "".join(self.clean_prose_parts)
        # If document had no structured elements, preserve exact byte identity
        if not self.struct_blocks and not self.table_depth and not self.list_depth:
            clean_prose = self.raw_html

        return clean_prose, self.struct_blocks

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        ltag = tag.lower()

        if ltag == "table":
            if self.table_depth == 0 and self.list_depth == 0:
                self.current_block_type = "table"
                self.block_start_idx = len("".join(self.clean_prose_parts))
                self.current_rows = []
                self.current_row = []
                self.caption = ""
                self.headers = []
                self.row_has_th = []
                self.current_row_has_th = False
                self.clean_prose_parts.append("\n\n")
            self.table_depth += 1
            return

        if ltag in ("ul", "ol"):
            if self.table_depth == 0 and self.list_depth == 0:
                self.current_block_type = "unordered_list" if ltag == "ul" else "ordered_list"
                self.block_start_idx = len("".join(self.clean_prose_parts))
                self.current_rows = []
                self.current_row = []
                self.clean_prose_parts.append("\n\n")
            self.list_depth += 1
            return

        if self.table_depth > 0:
            if ltag == "caption":
                self.in_caption = True
            elif ltag == "tr":
                if self.cell_depth > 0:
                    self._close_cell()
                if self.current_row:
                    self.current_rows.append(self.current_row)
                    self.row_has_th.append(self.current_row_has_th)
                    self.current_row = []
                    self.current_row_has_th = False
            elif ltag in ("th", "td"):
                if self.cell_depth > 0:
                    self._close_cell()
                self.cell_depth += 1
                if ltag == "th":
                    self.current_row_has_th = True
                self.current_cell_parts = []
            elif ltag in ("p", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article"):
                # If we encounter a top-level block element outside any cell, close unclosed table
                if self.cell_depth == 0:
                    self._close_structured_block(is_eof=False)
                    self.clean_prose_parts.append(f"<{tag}>")
            return

        if self.list_depth > 0:
            if ltag == "li":
                if self.li_depth > 0:
                    self._close_li()
                self.li_depth += 1
                self.current_cell_parts = []
            elif ltag in ("p", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article"):
                if self.li_depth == 0:
                    self._close_structured_block(is_eof=False)
                    self.clean_prose_parts.append(f"<{tag}>")
            return

        # Regular prose tag
        self.clean_prose_parts.append(f"<{tag}>")

    def handle_endtag(self, tag: str):
        ltag = tag.lower()

        if ltag == "table":
            if self.table_depth > 0:
                self.table_depth -= 1
                if self.table_depth == 0:
                    self._close_structured_block(is_eof=False)
            return

        if ltag in ("ul", "ol"):
            if self.list_depth > 0:
                self.list_depth -= 1
                if self.list_depth == 0 and self.table_depth == 0:
                    self._close_structured_block(is_eof=False)
            return

        if self.table_depth > 0:
            if ltag == "caption":
                self.in_caption = False
            elif ltag in ("th", "td"):
                if self.cell_depth > 0:
                    self._close_cell()
            elif ltag == "tr":
                if self.cell_depth > 0:
                    self._close_cell()
                if self.current_row:
                    self.current_rows.append(self.current_row)
                    self.row_has_th.append(self.current_row_has_th)
                    self.current_row = []
                    self.current_row_has_th = False
            return

        if self.list_depth > 0:
            if ltag == "li":
                if self.li_depth > 0:
                    self._close_li()
            return

        self.clean_prose_parts.append(f"</{tag}>")

    def handle_data(self, data: str):
        if self.table_depth > 0:
            if self.in_caption:
                self.caption += data
            elif self.cell_depth > 0:
                self.current_cell_parts.append(data)
            return

        if self.list_depth > 0:
            if self.li_depth > 0:
                self.current_cell_parts.append(data)
            return

        self.clean_prose_parts.append(data)

    def _close_cell(self):
        text = " ".join("".join(self.current_cell_parts).split())
        self.current_row.append(text)
        self.current_cell_parts = []
        self.cell_depth = max(0, self.cell_depth - 1)

    def _close_li(self):
        text = " ".join("".join(self.current_cell_parts).split())
        if text:
            self.current_rows.append([text])
        self.current_cell_parts = []
        self.li_depth = max(0, self.li_depth - 1)

    def _close_structured_block(self, is_eof: bool):
        if self.cell_depth > 0:
            self._close_cell()
        if self.li_depth > 0:
            self._close_li()
        if self.current_row:
            self.current_rows.append(self.current_row)
            self.row_has_th.append(self.current_row_has_th)
            self.current_row = []
            self.current_row_has_th = False

        if self.current_rows or self.caption:
            headers = []
            if self.current_block_type == "table" and self.current_rows:
                # Detect header row: explicit <th> in first row OR multiple short cells
                has_explicit_th = (bool(self.row_has_th) and self.row_has_th[0])
                first_row = self.current_rows[0]
                if (has_explicit_th or len(first_row) >= 2) and all(len(c) < 50 for c in first_row):
                    headers = first_row
                    data_rows = self.current_rows[1:]
                else:
                    headers = [f"Col_{i}" for i in range(len(first_row))]
                    data_rows = self.current_rows
            else:
                data_rows = self.current_rows

            block = StructuredBlock(
                block_id=len(self.struct_blocks),
                block_type=self.current_block_type or "table",
                start_char=self.block_start_idx,
                end_char=len("".join(self.clean_prose_parts)),
                caption=clean_tag_text(self.caption),
                headers=headers,
                rows=data_rows,
                raw_html="",
                is_truncated_eof=is_eof,
            )
            self.struct_blocks.append(block)

        self.table_depth = 0
        self.cell_depth = 0
        self.list_depth = 0
        self.li_depth = 0
        self.current_block_type = None
        self.current_rows = []
        self.current_row = []
        self.row_has_th = []
        self.current_row_has_th = False
        self.caption = ""
        self.clean_prose_parts.append("\n\n")


def escape_pipes(s: str) -> str:
    """Escape vertical pipe characters for GFM table cell syntax."""
    return s.replace("|", "\\|").strip()


def render_gfm_table_chunks(
    block: StructuredBlock,
    max_tokens: int = DEFAULT_MAX_TABLE_TOKENS,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Render StructuredBlock table as contiguous GitHub Flavored Markdown (GFM)
    chunks with header preservation and pipe escaping.
    """
    headers = [clean_tag_text(h) for h in block.headers]
    rows = [[clean_tag_text(c) for c in r] if isinstance(r, list) else [clean_tag_text(str(r))] for r in block.rows]
    caption = clean_tag_text(block.caption) if block.caption else ""

    header_status = "PRESERVED_EXPLICIT"
    if not headers and rows:
        headers = [f"Col_{i+1}" for i in range(len(rows[0]))]
        header_status = "SYNTHESIZED_FALLBACK"
    elif len(headers) == 1 and rows and len(rows[0]) == 2:
        caption = headers[0]
        headers = ["Property", "Value"]
        header_status = "TITLE_BANNER_TO_CAPTION"

    num_cols = max(len(headers), max((len(r) for r in rows), default=0))
    if len(headers) < num_cols:
        headers.extend([f"Col_{i+1}" for i in range(len(headers), num_cols)])

    norm_rows: List[List[str]] = []
    for r in rows:
        nr = list(r)
        if len(nr) < num_cols:
            nr.extend([""] * (num_cols - len(nr)))
        elif len(nr) > num_cols:
            nr = nr[:num_cols]
        norm_rows.append(nr)

    hdr_line = "| " + " | ".join(escape_pipes(h) for h in headers) + " |"
    sep_line = "| " + " | ".join("---" for _ in headers) + " |"
    rendered_row_lines = [
        "| " + " | ".join(escape_pipes(c) for c in r) + " |"
        for r in norm_rows
    ]

    prefix_lines = []
    if caption:
        prefix_lines.append(f"**Table: {caption}**")
    prefix_lines.extend([hdr_line, sep_line])
    prefix_text = "\n".join(prefix_lines)
    prefix_tokens = estimate_text_tokens(prefix_text)

    chunks: List[Dict[str, Any]] = []
    if not rendered_row_lines:
        full_text = prefix_text
        chunks.append({
            "chunk_idx": 0,
            "text": full_text,
            "start_row": 0,
            "end_row": 0,
            "row_count": 0,
            "estimated_tokens": estimate_text_tokens(full_text),
        })
    else:
        cur_row_lines: List[str] = []
        cur_start = 0
        cur_tokens = prefix_tokens

        for r_idx, r_line in enumerate(rendered_row_lines):
            r_tok = estimate_text_tokens(r_line)
            if cur_row_lines and (cur_tokens + r_tok > max_tokens):
                chunk_text = prefix_text + "\n" + "\n".join(cur_row_lines)
                chunks.append({
                    "chunk_idx": len(chunks),
                    "text": chunk_text,
                    "start_row": cur_start,
                    "end_row": r_idx - 1,
                    "row_count": len(cur_row_lines),
                    "estimated_tokens": estimate_text_tokens(chunk_text),
                })
                cur_row_lines = [r_line]
                cur_start = r_idx
                cur_tokens = prefix_tokens + r_tok
            else:
                cur_row_lines.append(r_line)
                cur_tokens += r_tok

        if cur_row_lines:
            chunk_text = prefix_text + "\n" + "\n".join(cur_row_lines)
            chunks.append({
                "chunk_idx": len(chunks),
                "text": chunk_text,
                "start_row": cur_start,
                "end_row": len(rendered_row_lines) - 1,
                "row_count": len(cur_row_lines),
                "estimated_tokens": estimate_text_tokens(chunk_text),
            })

    metadata = {
        "headers": headers,
        "header_status": header_status,
        "caption": caption,
        "original_row_count": len(rows),
        "rendered_row_count": len(norm_rows),
        "total_chunks": len(chunks),
    }
    return chunks, metadata


CUE_PATTERN = re.compile(
    r'\b(?:other\s+than|except(?:\s+for)?|excluding|aside\s+from|besides|not\s+including)\s+([a-z0-9\s,\'-]+?)(?:\s+in|\s+for|\s+of|\?|$)',
    re.IGNORECASE,
)

PLURAL_CATEGORY_WORDS = {
    "lakes", "colonies", "planets", "countries", "states", "universities",
    "teams", "schools", "players", "members", "episodes", "seasons", "cities",
    "mountains", "rivers", "islands", "presidents", "elements", "cars", "characters"
}

TARGET_ATTRIBUTES = {
    "air date", "date", "score", "tries", "enrollment", "students", "rank",
    "winner", "stadium", "points", "year", "capacity", "location", "rating"
}


@dataclass
class ExclusionInfo:
    phrase: str
    is_group: bool
    target_tokens: Set[str]


@dataclass
class TypedQualifiers:
    season: Optional[int] = None
    episode: Optional[int] = None
    rank: Optional[int] = None
    target_attrs: Set[str] = field(default_factory=set)
    is_superlative: bool = False


def extract_negative_constraint(query: str) -> Optional[ExclusionInfo]:
    """Extract negative exclusion constraint and classify as individual or group."""
    m = CUE_PATTERN.search(query)
    if not m:
        return None
    raw_target = m.group(1).strip()
    cleaned = re.sub(r'^(?:the|these|those|all)\s+', '', raw_target, flags=re.I).strip()
    words = cleaned.lower().split()
    if not words:
        return None
    is_group = any(w in PLURAL_CATEGORY_WORDS for w in words) or (
        len(words[-1]) > 3 and words[-1].endswith('s') and not words[-1].endswith('ss')
    )
    return ExclusionInfo(
        phrase=cleaned,
        is_group=is_group,
        target_tokens=set(words),
    )


def extract_typed_qualifiers(query: str) -> TypedQualifiers:
    """Extract typed season, episode, rank, and target attribute qualifiers."""
    tq = TypedQualifiers()
    m_s = re.search(r'\bseason\s*(\d+)\b', query, re.I)
    if m_s:
        tq.season = int(m_s.group(1))

    m_e = re.search(r'\b(?:episode|ep)\s*(\d+)\b', query, re.I)
    if m_e:
        tq.episode = int(m_e.group(1))

    m_r = re.search(r'\b(?:rank|no\.|#)\s*(\d+)\b', query, re.I)
    if m_r:
        tq.rank = int(m_r.group(1))
    elif re.search(r'\b(?:first|1st)\b', query, re.I):
        tq.rank = 1
    elif re.search(r'\b(?:second|2nd)\b', query, re.I):
        tq.rank = 2

    if re.search(r'\b(?:most|highest|greatest|leading|top|best)\b', query, re.I):
        tq.is_superlative = True
        if tq.rank is None:
            tq.rank = 1

    q_lower = query.lower()
    for attr in TARGET_ATTRIBUTES:
        if attr in q_lower:
            tq.target_attrs.add(attr)

    if re.search(r'\bwhen\b', q_lower):
        tq.target_attrs.add('date')
        tq.target_attrs.add('air date')
        tq.target_attrs.add('year')

    return tq


def score_and_select_tables(
    tables: List[ParsedTable],
    query: str,
    doc_text: str,
) -> List[Tuple[ParsedTable, float, str, Dict[str, Any]]]:
    """Score candidate tables and determine selection/rejection."""
    q_words = set(re.findall(r"\b[a-zA-Z]{3,}\b", query.lower()))
    excl = extract_negative_constraint(query)
    tq = extract_typed_qualifiers(query)

    scored_tables = []
    for table in tables:
        caption_lower = table.caption.lower()
        headers_lower = [h.lower() for h in table.headers]

        # 1. Negative constraint check
        if excl and not excl.is_group:
            if excl.phrase.lower() in caption_lower:
                scored_tables.append((table, -100.0, "REJECTED_EXCLUDED_ENTITY_TABLE", {"exclusion": excl.phrase}))
                continue

        # Header alignment
        n_hdr = sum(1 for h in headers_lower if any(qw in h for qw in q_words))
        n_attr = sum(1 for h in headers_lower if any(attr in h for attr in tq.target_attrs))
        # Caption alignment
        n_cap = sum(1 for qw in q_words if qw in caption_lower)
        # Content overlap in table rows
        sample_cells = " ".join(c.text.lower() for r in table.rows[:25] for c in r.cells)
        n_cell = 1 if any(qw in sample_cells for qw in q_words) else 0

        score = (2.0 * n_hdr) + (4.0 * n_attr) + (3.0 * n_cap) + (1.0 * n_cell)

        # Decision threshold
        if len(table.rows) <= 3 and (n_hdr >= 1 or n_cap >= 1):
            decision = "SELECTED_INFOBOX"
        elif score >= 2.0:
            decision = "SELECTED_MATCH"
        else:
            decision = "REJECTED_LOW_SCORE"

        meta = {
            "n_hdr": n_hdr,
            "n_attr": n_attr,
            "n_cap": n_cap,
            "score": score,
            "caption": table.caption,
            "headers": table.headers,
        }
        scored_tables.append((table, score, decision, meta))

    return scored_tables


# ==============================================================================
# 5. List Extraction & Formatting (Audited from Experiment 4.3/4.4)
# ==============================================================================

def clean_inline_text(text: str) -> str:
    """Strip markup tags, unescape entities, and normalize whitespace."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def extract_entity_binding(clean_text: str) -> Optional[Tuple[str, str]]:
    """Extract key-value or role-entity binding from list item text."""
    delims = [": ", " -- ", " - "]
    for d in delims:
        if d in clean_text:
            parts = clean_text.split(d, 1)
            k, v = parts[0].strip(), parts[1].strip()
            if 0 < len(k) < 60 and len(v) > 0:
                return (k, v)
    return None


class RobustListParser(HTMLParser):
    """
    Stack-based HTML list parser with parent prefix tracking and recovery.
    Correctly extracts nested lists, key-value items, and qualifiers.
    """

    def __init__(self):
        super().__init__()
        self.blocks: List[ParsedListBlock] = []
        self._list_stack: List[Tuple[Literal["unordered", "ordered"], int]] = []
        self._current_items: List[ParsedListItem] = []
        self._in_item: bool = False
        self._current_item_parts: List[str] = []
        self._item_depth: int = 0
        self._parent_prefixes: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        ltag = tag.lower()

        if ltag in ("ul", "ol"):
            ltype: Literal["unordered", "ordered"] = "unordered" if ltag == "ul" else "ordered"
            if self._in_item and self._current_item_parts:
                parent_text = clean_inline_text("".join(self._current_item_parts))
                self._close_item()
                self._parent_prefixes.append(parent_text)

            block_id = len(self.blocks)
            self._list_stack.append((ltype, block_id))

        elif ltag == "li":
            if self._in_item:
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
                    all_text = " ".join(it.clean_text for it in self._current_items)
                    tok_est = int(len(all_text.split()) * 1.3)
                    self.blocks.append(
                        ParsedListBlock(
                            block_id=b_id,
                            list_type=ltype,
                            items=list(self._current_items),
                            is_nested=len(self._parent_prefixes) > 0,
                            context_tokens_est=tok_est,
                        )
                    )
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
                qualifiers=parens,
            )
            self._current_items.append(item)
        self._current_item_parts = []
        self._in_item = False

    def close(self):
        super().close()
        if self._in_item:
            self._close_item()
        if self._current_items and self._list_stack:
            ltype, b_id = self._list_stack.pop()
            all_text = " ".join(it.clean_text for it in self._current_items)
            tok_est = int(len(all_text.split()) * 1.3)
            self.blocks.append(
                ParsedListBlock(
                    block_id=b_id,
                    list_type=ltype,
                    items=list(self._current_items),
                    is_nested=False,
                    context_tokens_est=tok_est,
                )
            )
            self._current_items = []


def extract_lists_from_html(html_content: str) -> List[ParsedListBlock]:
    """Parse HTML and extract structured list blocks."""
    if not html_content or not html_content.strip():
        return []
    parser = RobustListParser()
    parser.feed(html_content)
    parser.close()
    return parser.blocks


def is_nav_or_boilerplate_list(block: ParsedListBlock) -> bool:
    """
    Detect whether a list block is boilerplate or navigation links
    rather than factual document content.
    """
    if not block.items:
        return True
    nav_keywords = {
        "home", "about us", "contact", "privacy policy", "terms of service",
        "copyright", "help", "disclaimers", "navigation", "main page",
    }
    nav_matches = sum(1 for it in block.items if it.clean_text.lower() in nav_keywords)
    if nav_matches >= 2 or (nav_matches > 0 and len(block.items) <= 4):
        return True
    # Very short single-link item lists
    if len(block.items) == 1 and len(block.items[0].clean_text) < 15 and nav_matches > 0:
        return True
    return False


def render_list_to_markdown(block: ParsedListBlock) -> str:
    """
    Render a ParsedListBlock as compact markdown with hierarchy prefixes.
    Preserves subordinate role distinctions to prevent role conflation.
    """
    lines = []
    for idx, it in enumerate(block.items):
        prefix_str = f"[{it.parent_prefix}] " if it.parent_prefix else ""
        if block.list_type == "ordered":
            lines.append(f"{idx + 1}. {prefix_str}{it.clean_text}")
        else:
            lines.append(f"* {prefix_str}{it.clean_text}")
    return "\n".join(lines)


# ==============================================================================
# 6. Conservative Table-List Overlap Deduplication
# ==============================================================================

def deduplicate_table_list_overlap(
    list_blocks: List[ParsedListBlock],
    selected_tbl_blocks: List[StructuredBlock],
) -> Tuple[List[ParsedListBlock], List[Dict[str, Any]]]:
    """
    Conservative, structure-aware deduplication suppressing list sections whose
    content is already represented within selected table cells.

    Mitigates salience/distractor regressions (e.g. Scorpions songwriters in ef634417)
    while preserving novel list evidence.
    """
    if not selected_tbl_blocks or not list_blocks:
        return list_blocks, []

    # Gather normalized tokens and cell values across all selected tables
    table_cell_norm_set: Set[str] = set()
    table_tokens_set: Set[str] = set()

    for tb in selected_tbl_blocks:
        for r in tb.rows:
            for c in r:
                c_clean = clean_tag_text(c).lower()
                if c_clean:
                    table_cell_norm_set.add(c_clean)
                    for tok in re.findall(r"\w+", c_clean):
                        table_tokens_set.add(tok)

    surviving_blocks: List[ParsedListBlock] = []
    telemetry: List[Dict[str, Any]] = []

    for b in list_blocks:
        total_items = len(b.items)
        if total_items == 0:
            continue

        duplicate_items = 0
        novel_items = 0

        for it in b.items:
            it_text = it.clean_text.lower()
            # If item matches a table cell or is a substring of an exact cell
            if it_text in table_cell_norm_set or any(it_text in c_val for c_val in table_cell_norm_set):
                duplicate_items += 1
            else:
                # Check token-level containment
                it_toks = set(re.findall(r"\w+", it_text))
                if it_toks and it_toks.issubset(table_tokens_set):
                    duplicate_items += 1
                else:
                    novel_items += 1

        overlap_rate = duplicate_items / total_items

        # Conservative deduplication rule:
        # Suppress ONLY if >= 80% of items are already represented in selected table cells
        if overlap_rate >= 0.80:
            telemetry.append({
                "block_id": b.block_id,
                "action": "DEDUPLICATED_TABLE_OVERLAP",
                "total_items": total_items,
                "duplicate_items": duplicate_items,
                "overlap_rate": round(overlap_rate, 3),
            })
        else:
            surviving_blocks.append(b)
            if duplicate_items > 0:
                telemetry.append({
                    "block_id": b.block_id,
                    "action": "PRESERVED_PARTIAL_OVERLAP",
                    "total_items": total_items,
                    "duplicate_items": duplicate_items,
                    "overlap_rate": round(overlap_rate, 3),
                })

    return surviving_blocks, telemetry


# ==============================================================================
# 7. Unified Structural Context Builder
# ==============================================================================

def build_structural_context(
    raw_doc: str,
    query: str,
    table_threshold: float = 0.0,
    max_table_tokens: int = DEFAULT_MAX_TABLE_TOKENS,
    token_ceiling: int = DEFAULT_TOKEN_CEILING,
    enable_list_extraction: bool | None = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Construct packed prompt context from raw HTML document.

    When enable_list_extraction is False (or PRECIS_ENABLE_LIST_EXTRACTION is disabled):
        Constructs context using structural table retention at theta=0.0 alone,
        preserving the exact Condition D production path.

    When enable_list_extraction is True (or PRECIS_ENABLE_LIST_EXTRACTION is enabled):
        Appends deduplicated content lists with exact budget accounting and hard
        ceiling enforcement.
    """
    list_enabled = is_list_extraction_enabled(enable_list_extraction)

    # 1. Parse prose and table blocks
    parser = StructuralDocumentParser(raw_doc)
    clean_prose, blocks = parser.parse()
    tbl_blocks = [b for b in blocks if b.block_type == "table"]

    rendered_tables: Dict[int, Tuple[List[Dict[str, Any]], Dict[str, Any]]] = {}
    conversion_telemetry = []

    for b in tbl_blocks:
        try:
            chunks, meta = render_gfm_table_chunks(b, max_tokens=max_table_tokens)
            rendered_tables[b.block_id] = (chunks, meta)
            conversion_telemetry.append({
                "source_block_id": b.block_id,
                "caption": b.caption,
                "original_headers": b.headers,
                "rendered_headers": meta["headers"],
                "header_preservation_status": meta["header_status"],
                "original_row_count": meta["original_row_count"],
                "rendered_row_count": meta["rendered_row_count"],
                "row_preservation_rate": 1.0 if meta["original_row_count"] == meta["rendered_row_count"] else round(meta["rendered_row_count"] / max(1, meta["original_row_count"]), 4),
                "conversion_status": "SUCCESS",
            })
        except Exception as exc:
            conversion_telemetry.append({
                "source_block_id": b.block_id,
                "caption": b.caption,
                "original_headers": b.headers,
                "rendered_headers": [],
                "header_preservation_status": "FAILED",
                "original_row_count": len(b.rows),
                "rendered_row_count": 0,
                "row_preservation_rate": 0.0,
                "conversion_status": f"FAILURE: {exc}",
            })

    parsed_tables: List[ParsedTable] = []
    for b in tbl_blocks:
        p_rows: List[ParsedTableRow] = []
        for r_idx, r in enumerate(b.rows):
            cells = [ParsedTableCell(tag="td", text=c) for c in r]
            p_rows.append(ParsedTableRow(row_idx=r_idx, raw_html="", cells=cells))
        headers = b.headers if b.headers else [f"Col_{i}" for i in range(len(b.rows[0]))] if b.rows else []
        parsed_tables.append(
            ParsedTable(
                table_idx=b.block_id,
                caption=b.caption,
                headers=headers,
                rows=p_rows,
                raw_html="",
            )
        )

    scored_tables = score_and_select_tables(parsed_tables, query, raw_doc) if parsed_tables else []
    selected_tbl_ids: Set[int] = set()
    selection_telemetry = []

    for table, score, decision, _ in scored_tables:
        is_negative_excluded = (score < 0.0) or (decision == "REJECTED_EXCLUDED_ENTITY_TABLE")
        is_infobox = "infobox" in decision.lower()
        is_selected = (not is_negative_excluded) and ((score >= table_threshold) or is_infobox)

        if is_selected:
            selected_tbl_ids.add(table.table_idx)
            dec_str = "SELECTED_INFOBOX" if is_infobox else f"SELECTED_THRESHOLD_{table_threshold}"
        else:
            dec_str = decision if is_negative_excluded else f"REJECTED: below threshold {table_threshold}"

        selection_telemetry.append({
            "block_id": table.table_idx,
            "score": score,
            "decision": dec_str,
            "threshold": table_threshold,
        })

    # 2. Pack Clean Prose
    clean_prose_str = clean_prose.strip()
    clean_prose_has_content = bool(clean_tag_text(clean_prose_str))
    clean_prose_tokens = estimate_text_tokens(clean_prose_str) if clean_prose_has_content else 0

    packed_parts: List[str] = []
    cur_tokens = 0
    table_chunks_packed = 0
    table_tokens_packed = 0
    packed_rows = 0

    if clean_prose_str and clean_prose_tokens > 0:
        packed_parts.append(f"### Clean Prose:\n{clean_prose_str}")
        cur_tokens += clean_prose_tokens

    # 3. Pack Selected Tables
    sorted_tables = sorted(
        [t for t in scored_tables if t[0].table_idx in selected_tbl_ids],
        key=lambda x: x[1],
        reverse=True,
    )
    total_selected_rows = sum(len(b.rows) for b in tbl_blocks if b.block_id in selected_tbl_ids)

    for t_item in sorted_tables:
        t_idx = t_item[0].table_idx
        if t_idx in rendered_tables:
            chunks, _ = rendered_tables[t_idx]
            for ch in chunks:
                if cur_tokens + ch["estimated_tokens"] <= token_ceiling:
                    packed_parts.append(ch["text"])
                    cur_tokens += ch["estimated_tokens"]
                    table_chunks_packed += 1
                    table_tokens_packed += ch["estimated_tokens"]
                    packed_rows += ch["row_count"]

    # 4. If list extraction is DISABLED: return exact Condition D result
    if not list_enabled:
        full_context = "\n\n".join(packed_parts)
        telemetry = {
            "conversion": conversion_telemetry,
            "selection": selection_telemetry,
            "selected_tables_count": len(selected_tbl_ids),
            "selected_rows_count": total_selected_rows,
            "packed_rows_count": packed_rows,
            "clean_prose_estimated_tokens": clean_prose_tokens,
            "table_chunks_packed_count": table_chunks_packed,
            "table_chunks_estimated_tokens": table_tokens_packed,
            "total_context_estimated_tokens": cur_tokens,
            "ceiling_violation": cur_tokens > token_ceiling,
            "zero_context": len(full_context.strip()) == 0,
            "list_extraction_enabled": False,
        }
        return full_context, telemetry

    # 5. List Extraction (Enabled Path)
    raw_list_blocks = extract_lists_from_html(raw_doc)
    content_list_blocks = [b for b in raw_list_blocks if not is_nav_or_boilerplate_list(b)]

    # Apply conservative table-list overlap deduplication
    selected_tbl_blocks = [b for b in tbl_blocks if b.block_id in selected_tbl_ids]
    deduped_blocks, dedup_telem = deduplicate_table_list_overlap(content_list_blocks, selected_tbl_blocks)

    lists_packed = 0
    list_items_packed = 0
    list_tokens_packed = 0

    separator_overhead = estimate_text_tokens("\n\n")

    for b in deduped_blocks:
        md_list = render_list_to_markdown(b)
        list_header = "### Structured List:\n"
        list_chunk = f"{list_header}{md_list}"
        tok_est = estimate_text_tokens(list_chunk)

        budget_remaining = token_ceiling - cur_tokens - separator_overhead

        if budget_remaining <= 0:
            break

        if tok_est <= budget_remaining:
            packed_parts.append(list_chunk)
            cur_tokens += tok_est + separator_overhead
            lists_packed += 1
            list_items_packed += len(b.items)
            list_tokens_packed += tok_est
        else:
            # Partial line-level packing with exact header deduction
            trunc_header = "### Structured List (Budget Truncated):\n"
            trunc_header_tokens = estimate_text_tokens(trunc_header)
            net_line_budget = budget_remaining - trunc_header_tokens

            if net_line_budget > 30:
                truncated_lines = []
                sub_tok = 0
                for line in md_list.split("\n"):
                    l_tok = estimate_text_tokens(line)
                    if sub_tok + l_tok <= net_line_budget:
                        truncated_lines.append(line)
                        sub_tok += l_tok
                    else:
                        break

                if truncated_lines:
                    packed_chunk = f"{trunc_header}" + "\n".join(truncated_lines)
                    chunk_tokens = estimate_text_tokens(packed_chunk)
                    if cur_tokens + chunk_tokens + separator_overhead <= token_ceiling:
                        packed_parts.append(packed_chunk)
                        cur_tokens += chunk_tokens + separator_overhead
                        lists_packed += 1
                        list_items_packed += len(truncated_lines)
                        list_tokens_packed += chunk_tokens
            break

    # 6. Final Assembled Context Verification & Hard Ceiling Enforcement
    full_context = "\n\n".join(packed_parts)
    final_tokens = estimate_text_tokens(full_context) if full_context else 0

    if final_tokens > token_ceiling:
        # Drop last packed items if multiple parts
        while len(packed_parts) > 1 and estimate_text_tokens("\n\n".join(packed_parts)) > token_ceiling:
            dropped = packed_parts.pop()
            if "### Structured List" in dropped:
                lists_packed = max(0, lists_packed - 1)
        full_context = "\n\n".join(packed_parts)
        # If single item (e.g. prose) still exceeds ceiling, trim words deterministically
        if estimate_text_tokens(full_context) > token_ceiling:
            words = full_context.split()
            k = len(words)
            while k > 0 and estimate_text_tokens(" ".join(words[:k])) > token_ceiling:
                k -= 1
            full_context = " ".join(words[:k])
        final_tokens = estimate_text_tokens(full_context) if full_context else 0

    telemetry = {
        "conversion": conversion_telemetry,
        "selection": selection_telemetry,
        "selected_tables_count": len(selected_tbl_ids),
        "selected_rows_count": total_selected_rows,
        "packed_rows_count": packed_rows,
        "clean_prose_estimated_tokens": clean_prose_tokens,
        "table_chunks_packed_count": table_chunks_packed,
        "table_chunks_estimated_tokens": table_tokens_packed,
        "total_context_estimated_tokens": final_tokens,
        "ceiling_violation": final_tokens > token_ceiling,
        "zero_context": len(full_context.strip()) == 0,
        "list_extraction_enabled": True,
        "content_list_blocks_found": len(content_list_blocks),
        "deduplicated_list_blocks_count": len(dedup_telem),
        "deduplication_telemetry": dedup_telem,
        "list_blocks_packed": lists_packed,
        "list_items_packed": list_items_packed,
        "list_tokens_estimated": list_tokens_packed,
    }

    return full_context, telemetry


# ==============================================================================
# 8. Ingestion-Side Structural Extraction & Persisted Query Assembly
# ==============================================================================

def extract_structural_evidence_from_document(
    raw_doc: str,
    source_doc: str,
) -> Tuple[str, List[StructuralEvidence]]:
    """
    Extract table entries and list items deterministically during ingestion.
    Preserves association with source_doc and returns (clean_prose, structural_records).
    """
    if not raw_doc or not raw_doc.strip():
        return "", []

    parser = StructuralDocumentParser(raw_doc)
    clean_prose, blocks = parser.parse()
    tbl_blocks = [b for b in blocks if b.block_type == "table"]

    doc_slug = re.sub(r"[^a-zA-Z0-9_-]", "_", source_doc) if source_doc else "doc"
    structural_records: List[StructuralEvidence] = []

    # 1. Extract table entries
    for b in tbl_blocks:
        try:
            chunks, meta = render_gfm_table_chunks(b, max_tokens=DEFAULT_MAX_TABLE_TOKENS)
            for ch_idx, ch in enumerate(chunks):
                chunk_text = ch["text"]
                content_hash = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()[:12]
                rec_id = f"{doc_slug}_struct_tbl_{b.block_id}_{ch_idx}_{content_hash}"
                searchable_text = f"{b.caption} {' '.join(b.headers)} {chunk_text}".strip()
                structural_records.append(
                    StructuralEvidence(
                        id=rec_id,
                        source_doc=source_doc,
                        structure_type="table",
                        content=chunk_text,
                        searchable_text=searchable_text,
                        metadata={
                            "block_id": b.block_id,
                            "chunk_idx": ch_idx,
                            "caption": b.caption,
                            "headers": b.headers,
                            "row_count": ch.get("row_count", len(b.rows)),
                            "order_index": b.block_id,
                        },
                    )
                )
        except Exception:
            pass

    # 2. Extract list items
    raw_list_blocks = extract_lists_from_html(raw_doc)
    content_list_blocks = [b for b in raw_list_blocks if not is_nav_or_boilerplate_list(b)]

    # Deduplicate against table blocks to avoid distractor repetition
    deduped_blocks, _ = deduplicate_table_list_overlap(content_list_blocks, tbl_blocks)

    for b in deduped_blocks:
        md_list = render_list_to_markdown(b)
        list_chunk = f"### Structured List:\n{md_list}"
        content_hash = hashlib.sha256(list_chunk.encode("utf-8")).hexdigest()[:12]
        rec_id = f"{doc_slug}_struct_list_{b.block_id}_{content_hash}"
        searchable_items = [
            f"[{it.parent_prefix}] {it.clean_text}" if it.parent_prefix else it.clean_text
            for it in b.items
        ]
        searchable_text = "\n".join(searchable_items)
        structural_records.append(
            StructuralEvidence(
                id=rec_id,
                source_doc=source_doc,
                structure_type="list",
                content=list_chunk,
                searchable_text=searchable_text,
                metadata={
                    "block_id": b.block_id,
                    "item_count": len(b.items),
                    "is_nested": b.is_nested,
                    "order_index": b.block_id,
                },
            )
        )

    return clean_prose, structural_records


def assemble_structural_query_context(
    query: str,
    store: Any,
    token_ceiling: int,
    top_k: int = 100,
    exclude_modalities: Optional[Set[str]] = None,
) -> Tuple[str, List[Fact], Dict[str, Any], bool]:
    """
    Retrieve persisted structural evidence and SVOA facts from store,
    deduplicate overlapping information, and assemble into packed context
    strictly bounded by token_ceiling.

    Returns:
        (context_str, facts_used, telemetry, use_structural)
        If no relevant structural evidence is found, returns (context_str, facts_used, telemetry, False)
        where context_str is standard fact-based context.
    """
    from precis.pipeline.packer import _render_fact_parts, pack_context, render_context

    pack_res = pack_context(
        query=query,
        store=store,
        token_ceiling=token_ceiling,
        top_k=top_k,
        exclude_modalities=exclude_modalities,
    )

    if not hasattr(store, "query_similar_structural"):
        return render_context(pack_res.packed_facts), pack_res.packed_facts, {}, False

    struct_candidates = store.query_similar_structural(query, n_results=10)
    if not struct_candidates:
        return render_context(pack_res.packed_facts), pack_res.packed_facts, {}, False

    # Filter structural candidates for relevance to query
    q_words = set(re.findall(r"\b[a-zA-Z]{3,}\b", query.lower()))
    relevant_struct: List[Tuple[StructuralEvidence, float]] = []

    for item, sim in struct_candidates:
        searchable_lower = item.searchable_text.lower()
        has_kw_match = any(qw in searchable_lower for qw in q_words)
        # Relevance: cosine similarity >= 0.25, or keyword match with similarity >= 0.15
        if sim >= 0.25 or (has_kw_match and sim >= 0.15):
            relevant_struct.append((item, sim))

    if not relevant_struct:
        return render_context(pack_res.packed_facts), pack_res.packed_facts, {}, False

    # Multi-document isolation & similarity-dominant ranking policy:
    fact_docs = {f.source_doc for f in pack_res.packed_facts if f.source_doc}
    top_doc = pack_res.packed_facts[0].source_doc if pack_res.packed_facts else None

    # Filter eligible candidates across document groups
    eligible_candidates: List[Tuple[StructuralEvidence, float]] = []
    for item, sim in relevant_struct:
        if not fact_docs:
            eligible_candidates.append((item, sim))
        elif item.source_doc in fact_docs:
            eligible_candidates.append((item, sim))
        elif sim >= 0.40:
            # Candidates from documents with no SVOA facts remain eligible when structural similarity qualifies
            eligible_candidates.append((item, sim))

    if not eligible_candidates:
        return render_context(pack_res.packed_facts), pack_res.packed_facts, {}, False

    # Score and rank candidates across groups together with deterministic tie-breaking
    def _candidate_rank_key(cand: Tuple[StructuralEvidence, float]) -> Tuple[float, float, str]:
        item, sim = cand
        affinity_mult = 1.0
        if fact_docs and item.source_doc in fact_docs:
            affinity_mult += 0.15
        if top_doc and item.source_doc == top_doc:
            affinity_mult += 0.10
        blended_score = sim * affinity_mult
        return (-round(blended_score, 6), -round(sim, 6), item.id)

    ranked_struct = sorted(eligible_candidates, key=_candidate_rank_key)
    selected_struct = ranked_struct[:3]

    if not selected_struct:
        return render_context(pack_res.packed_facts), pack_res.packed_facts, {}, False

    # Context assembly and exact budget accounting
    separator_overhead = estimate_text_tokens("\n\n")
    packed_parts: List[str] = []
    cur_tokens = 0
    lists_packed = 0
    tables_packed = 0
    packed_struct_docs: Set[str] = set()

    # Pack structural evidence first
    for item, _ in selected_struct:
        budget_remaining = token_ceiling - cur_tokens - separator_overhead
        if budget_remaining <= 0:
            break

        tok_est = estimate_text_tokens(item.content)
        if tok_est <= budget_remaining:
            packed_parts.append(item.content)
            cur_tokens += tok_est + separator_overhead
            if item.source_doc:
                packed_struct_docs.add(item.source_doc)
            if item.structure_type == "list":
                lists_packed += 1
            else:
                tables_packed += 1
        elif item.structure_type == "list":
            trunc_header = "### Structured List (Budget Truncated):\n"
            trunc_header_tokens = estimate_text_tokens(trunc_header)
            net_line_budget = budget_remaining - trunc_header_tokens
            if net_line_budget > 30:
                lines = [l for l in item.content.split("\n") if not l.startswith("### Structured List")]
                truncated_lines = []
                sub_tok = 0
                for line in lines:
                    l_tok = estimate_text_tokens(line)
                    if sub_tok + l_tok <= net_line_budget:
                        truncated_lines.append(line)
                        sub_tok += l_tok
                    else:
                        break
                if truncated_lines:
                    packed_chunk = f"{trunc_header}" + "\n".join(truncated_lines)
                    chunk_tokens = estimate_text_tokens(packed_chunk)
                    if cur_tokens + chunk_tokens + separator_overhead <= token_ceiling:
                        packed_parts.append(packed_chunk)
                        cur_tokens += chunk_tokens + separator_overhead
                        if item.source_doc:
                            packed_struct_docs.add(item.source_doc)
                        lists_packed += 1
            break

    # Guarded Structural-Priority Policy & Fallback Semantics:
    # If no structural items could be packed (e.g. table exceeds budget ceiling),
    # fall back to standard SVOA fact-based context.
    if lists_packed == 0 and tables_packed == 0:
        return render_context(pack_res.packed_facts), pack_res.packed_facts, {}, False

    # Structural-priority SVOA suppression:
    # When structural evidence from document D is successfully packed, suppress SVOA facts
    # originating from D to eliminate hybrid contamination, distractor flooding, and preambles.
    # Preserve eligible facts from other documents in the store.
    struct_combined_content = " ".join(part.lower() for part in packed_parts)
    surviving_facts: List[Fact] = []
    suppressed_same_doc_facts = 0
    retained_cross_doc_facts = 0

    for f in pack_res.packed_facts:
        if f.source_doc and f.source_doc in packed_struct_docs:
            suppressed_same_doc_facts += 1
            continue

        subj = f.subject.strip().lower()
        obj = f.object.strip().lower()
        if subj and obj and (subj in struct_combined_content) and (obj in struct_combined_content):
            continue

        surviving_facts.append(f)
        retained_cross_doc_facts += 1

    # Pack surviving SVOA facts in remaining budget
    facts_packed: List[Fact] = []
    for f_idx, fact in enumerate(surviving_facts, 1):
        budget_remaining = token_ceiling - cur_tokens - separator_overhead
        if budget_remaining <= 0:
            break
        fact_line = f"Fact {f_idx}: {' '.join(_render_fact_parts(fact))}"
        f_tok = estimate_text_tokens(fact_line)
        if f_tok <= budget_remaining:
            packed_parts.append(fact_line)
            cur_tokens += f_tok + separator_overhead
            facts_packed.append(fact)

    # Enforce hard ceiling on final assembled context
    full_context = "\n\n".join(packed_parts)
    final_tokens = estimate_text_tokens(full_context) if full_context else 0

    if final_tokens > token_ceiling:
        while len(packed_parts) > 1 and estimate_text_tokens("\n\n".join(packed_parts)) > token_ceiling:
            packed_parts.pop()
        full_context = "\n\n".join(packed_parts)
        if estimate_text_tokens(full_context) > token_ceiling:
            words = full_context.split()
            k = len(words)
            while k > 0 and estimate_text_tokens(" ".join(words[:k])) > token_ceiling:
                k -= 1
            full_context = " ".join(words[:k])
        final_tokens = estimate_text_tokens(full_context) if full_context else 0

    telemetry = {
        "structural_items_found": len(struct_candidates),
        "structural_items_selected": len(selected_struct),
        "lists_packed": lists_packed,
        "tables_packed": tables_packed,
        "facts_packed": len(facts_packed),
        "structural_priority_active": True,
        "suppressed_same_doc_facts": suppressed_same_doc_facts,
        "retained_cross_doc_facts": retained_cross_doc_facts,
        "total_context_estimated_tokens": final_tokens,
        "ceiling_violation": final_tokens > token_ceiling,
    }

    return full_context, facts_packed, telemetry, True


