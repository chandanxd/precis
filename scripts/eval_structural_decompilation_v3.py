#!/usr/bin/env python3
"""
Précis Experiment 3: Isolated Structural Document Decompilation Harness.

Evaluates whether separating prose from structured HTML content at the document-ingestion
boundary prevents malformed table-derived facts from entering the prose/SVOA extraction path,
while preserving valid evidence, maintaining prose-only invariance, and respecting the +10%
context-overhead guardrail.

Strict isolation constraints:
- Zero modifications to production code under backend/src/precis/.
- All logic, parsers, adapters, and evaluators reside strictly in this script.
- Outputs written exclusively to results/diagnostic_structural_decompilation_v3/.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import os
import random
import re
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Set, Tuple

# Ensure backend/src is on import path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import scipy.stats

from precis.evaluation.metrics import (
    compute_exact_match,
    compute_rouge_l,
    normalize_answer,
)
from precis.graph.schema import Fact
from precis.graph.store import FactStore
from precis.pipeline.coref import resolve_coreferences
from precis.pipeline.inference import (
    CONCISE_PROMPT_TEMPLATE,
    OLLAMA_DEFAULT_BASE_URL,
    generate_answer,
)
from precis.pipeline.orchestrator import ingest_document
from precis.pipeline.packer import pack_context, render_context
from precis.pipeline.sdh import score_facts_with_store
from precis.pipeline.svoa import extract_facts

from eval_table_selection_v2 import (
    ParsedTable,
    ParsedTableCell,
    ParsedTableRow,
    ScoredRow,
    check_containment,
    check_exact_match,
    clean_tag_text,
    contains_answer,
    extract_list_propositions,
    rank_table_rows,
    score_and_select_tables,
    synthesize_table_facts,
)

# Canonical benchmark invariants
DEFAULT_MODEL = "qwen2.5-coder:7b"
DEFAULT_TEMP = 0.0
DEFAULT_TOP_P = 0.9
DEFAULT_MAX_TOKENS = 512
DEFAULT_SEED = 42
DEFAULT_TOKEN_CEILING = 2048


# ==============================================================================
# 1. Structural Document Representation & State-Machine Parser
# ==============================================================================

@dataclass
class StructuredBlock:
    block_id: int
    block_type: Literal["table", "ordered_list", "unordered_list"]
    start_char: int
    end_char: int
    caption: str
    headers: List[str]
    rows: List[List[str]]  # Extracted cell text grid
    raw_html: str
    is_truncated_eof: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class StructuralDocumentParser(HTMLParser):
    """
    Structural HTML Parser with explicit recovery rules.
    Decompiles input document into:
    1. Clean prose stream with structured blocks excised and replaced with '

'.
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

# ==============================================================================
# 2. Sortable-Name Normalizer (Pattern 1 Only) & Structured Block Adapter
# ==============================================================================

def normalize_sortable_name_pattern1(text: str) -> str:
    """
    Condition C Sortable-Name Normalization (Pattern 1 Only).
    Normalizes demonstrated duplicated Wikipedia sort-key patterns like:
    'Last , First First Last' -> 'First Last'.
    Strictly leaves ordinary 'Last, First', numbers, units, locations, and all other strings unchanged.
    """
    text = text.strip()
    # Guard: numbers / units
    if re.search(r'\d', text):
        return text
    # Guard: exactly one comma
    if text.count(',') != 1:
        return text

    parts = text.split(',')
    last = parts[0].strip()
    rest = parts[1].strip()

    # Both parts must consist of alphabetic name characters
    if not re.match(r"^[A-Za-z\s\.'\-]+$", last) or not re.match(r"^[A-Za-z\s\.'\-]+$", rest):
        return text

    # Pattern 1 check: rest ends with last (case-insensitive)
    if rest.lower().endswith(last.lower()):
        prefix = rest[:-len(last)].strip()
        tokens = prefix.split()
        if len(tokens) >= 2 and len(tokens) % 2 == 0:
            half = len(tokens) // 2
            first_half = ' '.join(tokens[:half])
            second_half = ' '.join(tokens[half:])
            if first_half.lower() == second_half.lower():
                return f'{first_half} {last}'
    return text


def adapt_structured_blocks_to_facts(
    blocks: List[StructuredBlock],
    query: str,
    doc_text: str,
    source_doc: str,
    normalize_names: bool = False,
    max_facts: int = 15,
) -> Tuple[List[Fact], Dict[str, Any]]:
    """
    Adapter converting StructuredBlock objects into query-aware Fact propositions.
    Utilizes Experiment 2 selection and row ranking logic without touching production code.
    """
    candidate_facts: List[Fact] = []
    telemetry = []

    # 1. Process table blocks
    table_blocks = [b for b in blocks if b.block_type == "table"]
    parsed_tables: List[ParsedTable] = []

    for b in table_blocks:
        parsed_rows: List[ParsedTableRow] = []
        for r_idx, r in enumerate(b.rows):
            cells = []
            for c_idx, cell_text in enumerate(r):
                final_text = normalize_sortable_name_pattern1(cell_text) if normalize_names else cell_text
                tag = "th" if (r_idx == 0 and not b.headers) else "td"
                cells.append(ParsedTableCell(tag=tag, text=final_text))
            parsed_rows.append(ParsedTableRow(row_idx=r_idx, raw_html="", cells=cells))

        headers = b.headers if b.headers else [f"Col_{i}" for i in range(len(b.rows[0]))] if b.rows else []
        parsed_tables.append(ParsedTable(
            table_idx=b.block_id,
            caption=b.caption,
            headers=headers,
            rows=parsed_rows,
            raw_html=b.raw_html,
        ))

    if parsed_tables:
        scored_tables = score_and_select_tables(parsed_tables, query, doc_text)
        for table, t_score, t_decision, t_meta in scored_tables:
            if not t_decision.startswith("SELECTED"):
                telemetry.append({
                    "block_id": table.table_idx,
                    "decision": t_decision,
                    "score": t_score,
                })
                continue

            selected_rows, r_telem = rank_table_rows(table, query, doc_text, max_selected_rows=5)
            headers = table.headers if table.headers else [f"Col_{i}" for i in range(len(table.rows[0].cells))] if table.rows else []
            t_facts = synthesize_table_facts(selected_rows, headers, source_doc, query, max_facts=10)

            # Augment facts with explicit provenance metadata
            for f in t_facts:
                if f.adjuncts is None:
                    f.adjuncts = {}
                f.adjuncts["source_structure"] = ["table_row"]
                f.adjuncts["source_block_id"] = [str(table.table_idx)]
                if normalize_names:
                    f.adjuncts["name_normalized"] = ["true"]

            candidate_facts.extend(t_facts)
            telemetry.append({
                "block_id": table.table_idx,
                "decision": t_decision,
                "score": t_score,
                "facts_generated": len(t_facts),
            })
            if len(candidate_facts) >= max_facts:
                break

    # 2. Process list blocks if remaining budget
    list_blocks = [b for b in blocks if b.block_type in ("unordered_list", "ordered_list")]
    for b in list_blocks:
        if len(candidate_facts) >= max_facts:
            break
        list_html = f"<ul>{''.join(f'<li>{item[0]}</li>' for item in b.rows if item)}</ul>"
        l_facts = extract_list_propositions(
            list_html,
            source_doc=source_doc,
            max_facts=max_facts - len(candidate_facts),
        )
        for f in l_facts:
            if f.adjuncts is None:
                f.adjuncts = {}
            f.adjuncts["source_structure"] = ["list_item"]
            f.adjuncts["source_block_id"] = [str(b.block_id)]
        candidate_facts.extend(l_facts)

    final_facts = candidate_facts[:max_facts]
    return final_facts, {"blocks": telemetry, "total_facts": len(final_facts)}


# ==============================================================================
# 3. Conservative Cross-Path Deduplication Semantics
# ==============================================================================

def deduplicate_facts(
    prose_facts: List[Fact],
    struct_facts: List[Fact],
) -> Tuple[List[Fact], Dict[str, Any]]:
    """
    Conservative cross-path deduplication:
    - Retains prose fact when triple (subject, verb, object) matches normalized structured fact.
    - Preserves both facts if modalities conflict (asserted vs negated).
    - Preserves both facts if non-empty qualifiers (temporal, location, manner, role, qualifier) conflict.
    - Missing qualifiers are NOT treated as conflicts.
    - Augments prose fact with 'corroborated_by' provenance.
    - Records explicit retention and suppression telemetry.
    """
    dedup_events = []
    filtered_struct_facts: List[Fact] = []
    CHECKED_QUALIFIERS = ["temporal", "location", "manner", "role", "qualifier"]

    def norm_triple(f: Fact) -> Tuple[str, str, str]:
        return (f.subject.strip().lower(), f.verb.strip().lower(), f.object.strip().lower())

    def norm_val(v: str) -> str:
        return " ".join(v.strip().lower().split())

    prose_map: Dict[Tuple[str, str, str], Fact] = {}
    for pf in prose_facts:
        prose_map[norm_triple(pf)] = pf

    for sf in struct_facts:
        s_trip = norm_triple(sf)
        if s_trip in prose_map:
            pf = prose_map[s_trip]

            # 1. Modality guard
            if pf.modality != sf.modality:
                filtered_struct_facts.append(sf)
                dedup_events.append({
                    "action": "RETAIN_STRUCTURED",
                    "reason": "MODALITY_MISMATCH",
                    "matched_triple": list(s_trip),
                    "prose_modality": pf.modality,
                    "struct_modality": sf.modality,
                })
                continue

            # 2. Comprehensive non-empty qualifier conflict checks
            p_adj = pf.adjuncts or {}
            s_adj = sf.adjuncts or {}
            conflict_key = None

            for qk in CHECKED_QUALIFIERS:
                p_vals = {norm_val(v) for v in p_adj.get(qk, []) if norm_val(v)}
                s_vals = {norm_val(v) for v in s_adj.get(qk, []) if norm_val(v)}
                # Only conflict if BOTH sides specify non-empty values and have NO intersection
                if p_vals and s_vals and not (p_vals & s_vals):
                    conflict_key = qk
                    break

            if conflict_key:
                filtered_struct_facts.append(sf)
                dedup_events.append({
                    "action": "RETAIN_STRUCTURED",
                    "reason": f"CONFLICT_{conflict_key.upper()}",
                    "matched_triple": list(s_trip),
                    "prose_values": p_adj.get(conflict_key, []),
                    "struct_values": s_adj.get(conflict_key, []),
                })
                continue

            # 3. Deduplication confirmed: suppress structured fact, corroborate prose fact
            if pf.adjuncts is None:
                pf.adjuncts = {}
            corrob = pf.adjuncts.setdefault("corroborated_by", [])
            corrob.append(f"struct_block_{sf.adjuncts.get('source_block_id', ['0'])[0]}")
            dedup_events.append({
                "action": "SUPPRESS_STRUCTURED_DUPLICATE",
                "reason": "EXACT_DUPLICATE_CORROBORATED",
                "matched_triple": list(s_trip),
                "prose_fact_subject": pf.subject,
            })
        else:
            filtered_struct_facts.append(sf)
            dedup_events.append({
                "action": "RETAIN_STRUCTURED",
                "reason": "UNIQUE_TRIPLE",
                "matched_triple": list(s_trip),
            })

    all_facts = prose_facts + filtered_struct_facts
    return all_facts, {
        "dedup_count": sum(1 for e in dedup_events if e["action"] == "SUPPRESS_STRUCTURED_DUPLICATE"),
        "events": dedup_events,
    }

# ==============================================================================
# 4. Stage A: Deterministic Unit & Forensic Test Suite (Zero LLM Inference)
# ==============================================================================

def run_stage_a_suite(docs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the Stage A deterministic unit and forensic test suite.
    Runs 100% offline with zero LLM inference.
    """
    results: Dict[str, Any] = {"tests": {}, "all_passed": False}

    # Test A1: Forensic bad74caad5 Great Lakes Leakage & Preservation Test
    try:
        sid_lakes = "bad74caad55343f9ad68de7cd705689a"
        assert sid_lakes in docs, f"Historical sample {sid_lakes} not found in dataset! Silent fallback prohibited."
        raw_doc_lakes = docs[sid_lakes]["document"]
        q_lakes = "name three large lakes other than the great lakes in the united states"

        parser = StructuralDocumentParser(raw_doc_lakes)
        clean_prose, blocks = parser.parse()

        # Prose check: table excised
        assert "<table" not in clean_prose.lower(), "Table tags still present in clean prose!"
        # Prose SVOA check: zero leakage of Great Lakes
        p_res = resolve_coreferences(clean_prose)
        p_facts = extract_facts(p_res, source_doc=sid_lakes)
        leaked = [f for f in p_facts if any(lake in f'{f.subject} {f.verb} {f.object}' for lake in ['Superior', 'Huron', 'Michigan', 'Erie', 'Ontario'])]
        assert len(leaked) == 0, f"Leaked {len(leaked)} Great Lakes facts into prose SVOA!"

        # Structured check: Great Salt Lake and Lake of the Woods preserved
        s_facts, _ = adapt_structured_blocks_to_facts(blocks, q_lakes, raw_doc_lakes, sid_lakes)
        salt_found = any("great salt lake" in f.subject.lower() or "great salt lake" in f.object.lower() for f in s_facts)
        woods_found = any("lake of the woods" in f.subject.lower() or "lake of the woods" in f.object.lower() for f in s_facts)
        assert salt_found, "Great Salt Lake not extracted by structured adapter!"
        assert woods_found, "Lake of the Woods not extracted by structured adapter!"

        results["tests"]["test_a1_great_lakes_leakage"] = {
            "passed": True,
            "clean_prose_len": len(clean_prose),
            "prose_facts": len(p_facts),
            "leaked_facts": len(leaked),
            "struct_facts": len(s_facts),
            "verified_historical_sid": sid_lakes,
            "verified_salt_lake": salt_found,
            "verified_woods_lake": woods_found,
        }
    except Exception as e:
        results["tests"]["test_a1_great_lakes_leakage"] = {"passed": False, "error": str(e)}

    # Test A2: Multi-Row & Multi-Header Table Integrity
    try:
        doc = "<p>Lead.</p><Table><Tr><Th>Rank</Th><Th>Country</Th><Th>Gold</Th></Tr><Tr><Td>1</Td><Td>USA</Td><Td>39</Td></Tr><Tr><Td>2</Td><Td>China</Td><Td>38</Td></Tr></Table><p>Tail.</p>"
        parser = StructuralDocumentParser(doc)
        prose, blocks = parser.parse()
        assert len(blocks) == 1
        assert blocks[0].block_type == "table"
        assert blocks[0].headers == ["Rank", "Country", "Gold"]
        assert len(blocks[0].rows) == 2
        assert blocks[0].rows[0] == ["1", "USA", "39"]
        results["tests"]["test_a2_multi_row_multi_header_table"] = {"passed": True}
    except Exception as e:
        results["tests"]["test_a2_multi_row_multi_header_table"] = {"passed": False, "error": str(e)}

    # Test A3: Caption and Headers
    try:
        doc = "<Table><Caption>Olympic Medal Tally</Caption><Tr><Th>Nation</Th></Tr><Tr><Td>Norway</Td></Tr></Table>"
        parser = StructuralDocumentParser(doc)
        prose, blocks = parser.parse()
        assert len(blocks) == 1
        assert blocks[0].caption == "Olympic Medal Tally"
        assert blocks[0].headers == ["Nation"]
        results["tests"]["test_a3_caption_and_headers"] = {"passed": True}
    except Exception as e:
        results["tests"]["test_a3_caption_and_headers"] = {"passed": False, "error": str(e)}

    # Test A4: Lists Nested in Prose
    try:
        doc = "The ingredients are listed below: <ol><li>Flour</li><li>Sugar</li></ol> Mix them well in a large bowl."
        parser = StructuralDocumentParser(doc)
        prose, blocks = parser.parse()
        assert len(blocks) == 1
        assert blocks[0].block_type == "ordered_list"
        assert len(blocks[0].rows) == 2
        assert "Flour" in blocks[0].rows[0]
        assert "Mix them well" in prose
        results["tests"]["test_a4_lists_nested_in_prose"] = {"passed": True}
    except Exception as e:
        results["tests"]["test_a4_lists_nested_in_prose"] = {"passed": False, "error": str(e)}

    # Test A5: Adversarial Surrounding Prose Preservation
    try:
        doc = "Leading intro sentence about physics.<Table><Tr><Th>H1</Th></Tr><Tr><Td>D1</Td></Tr></Table>Trailing conclusion sentence about chemistry."
        parser = StructuralDocumentParser(doc)
        prose, blocks = parser.parse()
        assert "Leading intro sentence about physics." in prose
        assert "Trailing conclusion sentence about chemistry." in prose
        assert "<table" not in prose.lower()
        results["tests"]["test_a5_surrounding_prose_preservation"] = {"passed": True}
    except Exception as e:
        results["tests"]["test_a5_surrounding_prose_preservation"] = {"passed": False, "error": str(e)}

    # Test A6: Abbreviations and Dates in Cells
    try:
        doc = "<Table><Tr><Th>Title</Th><Th>Air date</Th></Tr><Tr><Td>Pilot</Td><Td>Oct. 24, 2017</Td></Tr></Table>"
        parser = StructuralDocumentParser(doc)
        prose, blocks = parser.parse()
        assert len(blocks) == 1
        assert blocks[0].rows[0][1] == "Oct. 24, 2017"
        results["tests"]["test_a6_abbreviations_and_dates"] = {"passed": True}
    except Exception as e:
        results["tests"]["test_a6_abbreviations_and_dates"] = {"passed": False, "error": str(e)}

    # Test A7: Multiple Tables in Document
    try:
        doc = "Intro.<Table id='t1'><Tr><Th>T1</Th></Tr><Tr><Td>A</Td></Tr></Table>Middle sentence.<Table id='t2'><Tr><Th>T2</Th></Tr><Tr><Td>B</Td></Tr></Table>End."
        parser = StructuralDocumentParser(doc)
        prose, blocks = parser.parse()
        assert len(blocks) == 2
        assert blocks[0].rows[0] == ["A"]
        assert blocks[1].rows[0] == ["B"]
        assert "Middle sentence." in prose
        results["tests"]["test_a7_multiple_tables_in_document"] = {"passed": True}
    except Exception as e:
        results["tests"]["test_a7_multiple_tables_in_document"] = {"passed": False, "error": str(e)}

    # Test A8: Deterministic Prose-Only Invariance
    try:
        doc = "This is a pure prose document. It contains multiple sentences. There are no tables or lists anywhere in this document."
        parser = StructuralDocumentParser(doc)
        prose, blocks = parser.parse()
        assert prose == doc, "Prose-only document was altered by parser!"
        assert len(blocks) == 0, "Structured blocks detected in prose-only document!"
        results["tests"]["test_a8_prose_only_invariance"] = {"passed": True}
    except Exception as e:
        results["tests"]["test_a8_prose_only_invariance"] = {"passed": False, "error": str(e)}

    # Test A9: Malformed / Unclosed HTML Recovery
    try:
        doc = "<p>Intro.</p><Table><Tr><Th>Header</Th></Tr><Tr><Td>Data 1</Td></Tr><p>Following paragraph after unclosed table."
        parser = StructuralDocumentParser(doc)
        prose, blocks = parser.parse()
        assert len(blocks) == 1
        assert blocks[0].rows[0] == ["Data 1"]
        assert "Following paragraph after unclosed table." in prose
        results["tests"]["test_a9_malformed_unclosed_html_recovery"] = {"passed": True}
    except Exception as e:
        results["tests"]["test_a9_malformed_unclosed_html_recovery"] = {"passed": False, "error": str(e)}

    # Test A10: Conservative Cross-Path Deduplication Semantics
    try:
        # 1. Matching qualifier (deduped): both have matching location
        pf_match_qual = Fact(subject="France", verb="capital is", object="Paris", modality="asserted", source_doc="d1", sentence_id=0, raw_sentence="", adjuncts={"location": ["Europe"]})
        sf_match_qual = Fact(subject="France", verb="capital is", object="Paris", modality="asserted", source_doc="d1", sentence_id=1, raw_sentence="", adjuncts={"location": ["Europe"], "source_block_id": ["10"]})

        # 2. Missing qualifier on one side (deduped): prose has location, structured has no qualifiers
        pf_missing_qual = Fact(subject="Germany", verb="capital is", object="Berlin", modality="asserted", source_doc="d1", sentence_id=2, raw_sentence="", adjuncts={"location": ["Europe"]})
        sf_missing_qual = Fact(subject="Germany", verb="capital is", object="Berlin", modality="asserted", source_doc="d1", sentence_id=3, raw_sentence="", adjuncts={"source_block_id": ["11"]})

        # 3. Conflicting temporal (retained, reason CONFLICT_TEMPORAL)
        pf_conf_temp = Fact(subject="Alice", verb="was born in", object="1990", modality="asserted", source_doc="d1", sentence_id=4, raw_sentence="", adjuncts={"temporal": ["1990"]})
        sf_conf_temp = Fact(subject="Alice", verb="was born in", object="1990", modality="asserted", source_doc="d1", sentence_id=5, raw_sentence="", adjuncts={"temporal": ["1994"], "source_block_id": ["12"]})

        # 4. Conflicting location (retained, reason CONFLICT_LOCATION)
        pf_conf_loc = Fact(subject="Bob", verb="lives in", object="Apartment", modality="asserted", source_doc="d1", sentence_id=6, raw_sentence="", adjuncts={"location": ["London"]})
        sf_conf_loc = Fact(subject="Bob", verb="lives in", object="Apartment", modality="asserted", source_doc="d1", sentence_id=7, raw_sentence="", adjuncts={"location": ["Rome"], "source_block_id": ["13"]})

        # 5. Conflicting role (retained, reason CONFLICT_ROLE)
        pf_conf_role = Fact(subject="Carol", verb="worked as", object="Employee", modality="asserted", source_doc="d1", sentence_id=8, raw_sentence="", adjuncts={"role": ["Manager"]})
        sf_conf_role = Fact(subject="Carol", verb="worked as", object="Employee", modality="asserted", source_doc="d1", sentence_id=9, raw_sentence="", adjuncts={"role": ["Intern"], "source_block_id": ["14"]})

        # 6. Conflicting manner (retained, reason CONFLICT_MANNER)
        pf_conf_man = Fact(subject="David", verb="spoke to", object="Press", modality="asserted", source_doc="d1", sentence_id=10, raw_sentence="", adjuncts={"manner": ["Cautiously"]})
        sf_conf_man = Fact(subject="David", verb="spoke to", object="Press", modality="asserted", source_doc="d1", sentence_id=11, raw_sentence="", adjuncts={"manner": ["Boldly"], "source_block_id": ["15"]})

        # 7. Conflicting qualifier (retained, reason CONFLICT_QUALIFIER)
        pf_conf_qual = Fact(subject="Eve", verb="won", object="Award", modality="asserted", source_doc="d1", sentence_id=12, raw_sentence="", adjuncts={"qualifier": ["Official"]})
        sf_conf_qual = Fact(subject="Eve", verb="won", object="Award", modality="asserted", source_doc="d1", sentence_id=13, raw_sentence="", adjuncts={"qualifier": ["Honorary"], "source_block_id": ["16"]})

        # 8. Conflicting modality (retained, reason MODALITY_MISMATCH)
        pf_conf_mod = Fact(subject="Frank", verb="attended", object="Yale", modality="asserted", source_doc="d1", sentence_id=14, raw_sentence="")
        sf_conf_mod = Fact(subject="Frank", verb="attended", object="Yale", modality="negated", source_doc="d1", sentence_id=15, raw_sentence="", adjuncts={"source_block_id": ["17"]})

        p_facts = [pf_match_qual, pf_missing_qual, pf_conf_temp, pf_conf_loc, pf_conf_role, pf_conf_man, pf_conf_qual, pf_conf_mod]
        s_facts = [sf_match_qual, sf_missing_qual, sf_conf_temp, sf_conf_loc, sf_conf_role, sf_conf_man, sf_conf_qual, sf_conf_mod]

        all_facts, telem = deduplicate_facts(p_facts, s_facts)

        assert telem["dedup_count"] == 2, f"Expected 2 deduplicated, got {telem['dedup_count']}"
        assert len(all_facts) == 14, f"Expected 14 total facts (8 prose + 6 retained structured), got {len(all_facts)}"

        # Check telemetry events
        events_by_reason = {e["reason"]: e for e in telem["events"]}
        assert "EXACT_DUPLICATE_CORROBORATED" in [e["reason"] for e in telem["events"] if e["action"] == "SUPPRESS_STRUCTURED_DUPLICATE"]
        assert events_by_reason["CONFLICT_TEMPORAL"]["action"] == "RETAIN_STRUCTURED"
        assert events_by_reason["CONFLICT_LOCATION"]["action"] == "RETAIN_STRUCTURED"
        assert events_by_reason["CONFLICT_ROLE"]["action"] == "RETAIN_STRUCTURED"
        assert events_by_reason["CONFLICT_MANNER"]["action"] == "RETAIN_STRUCTURED"
        assert events_by_reason["CONFLICT_QUALIFIER"]["action"] == "RETAIN_STRUCTURED"
        assert events_by_reason["MODALITY_MISMATCH"]["action"] == "RETAIN_STRUCTURED"

        # Check corroboration
        assert "corroborated_by" in pf_match_qual.adjuncts
        assert "corroborated_by" in pf_missing_qual.adjuncts
        assert "corroborated_by" not in (pf_conf_temp.adjuncts or {})
        assert "corroborated_by" not in (pf_conf_loc.adjuncts or {})
        assert "corroborated_by" not in (pf_conf_role.adjuncts or {})
        assert "corroborated_by" not in (pf_conf_man.adjuncts or {})
        assert "corroborated_by" not in (pf_conf_qual.adjuncts or {})
        assert "corroborated_by" not in (pf_conf_mod.adjuncts or {})

        results["tests"]["test_a10_conservative_cross_path_dedup"] = {
            "passed": True,
            "dedup_count": telem["dedup_count"],
            "total_facts": len(all_facts),
            "reasons_tested": list(events_by_reason.keys()),
        }
    except Exception as e:
        results["tests"]["test_a10_conservative_cross_path_dedup"] = {"passed": False, "error": str(e)}

    # Test A11: Wikipedia Sortable-Name Normalization (Pattern 1 Only)
    try:
        positives = [
            ("Barry , Gareth Gareth Barry", "Gareth Barry"),
            ("Chu , Julie Julie Chu", "Julie Chu"),
            ("Diggins , Jessica Jessica Diggins", "Jessica Diggins"),
            ("Rau , Benegal Narsing Benegal Narsing Rau", "Benegal Narsing Rau"),
        ]
        negatives = [
            ("Barry , Gareth", "Barry , Gareth"),  # Pattern 1 only: Ordinary Last, First UNCHANGED!
            ("Austin, Texas", "Austin, Texas"),
            ("Washington, D.C.", "Washington, D.C."),
            ("31,700 sq mi", "31,700 sq mi"),
            ("1,234,567", "1,234,567"),
            ("Smith, Kline & French", "Smith, Kline & French"),
        ]
        for inp, exp in positives:
            assert normalize_sortable_name_pattern1(inp) == exp, f"Positive failed: {inp} -> {normalize_sortable_name_pattern1(inp)} != {exp}"
        for inp, exp in negatives:
            assert normalize_sortable_name_pattern1(inp) == exp, f"Negative failed: {inp} -> {normalize_sortable_name_pattern1(inp)} != {exp}"
        results["tests"]["test_a11_sortable_name_pattern1"] = {"passed": True}
    except Exception as e:
        results["tests"]["test_a11_sortable_name_pattern1"] = {"passed": False, "error": str(e)}

    # Test A12: End-to-End Source Provenance, Separation, and Ordering
    try:
        fixture_doc = (
            "Marie Curie won the Nobel Prize in Physics.\n"
            "<Table>\n"
            "  <Tr><Th>Scientist</Th><Th>Discovery</Th></Tr>\n"
            "  <Tr><Td>Albert Einstein</Td><Td>photoelectric effect</Td></Tr>\n"
            "</Table>\n"
            "<ul>\n"
            "  <li>Galileo Galilei - Italian astronomer who observed Jupiter moons</li>\n"
            "</ul>"
        )
        fixture_sid = "fixture_doc_a12"
        fixture_query = "what did albert einstein and galileo discover"

        # 1. Structural parser pass
        parser = StructuralDocumentParser(fixture_doc)
        prose, blocks = parser.parse()

        # 2. Prose extraction path
        res_prose = resolve_coreferences(prose)
        p_facts = extract_facts(res_prose, source_doc=fixture_sid)
        for f in p_facts:
            if f.adjuncts is None:
                f.adjuncts = {}
            f.adjuncts["source_structure"] = ["prose"]

        # 3. Structured extraction path
        s_facts, _ = adapt_structured_blocks_to_facts(
            blocks=blocks,
            query=fixture_query,
            doc_text=fixture_doc,
            source_doc=fixture_sid,
            normalize_names=False,
            max_facts=10,
        )

        # Assertions on prose facts
        assert len(p_facts) > 0, "No prose facts extracted from fixture!"
        for pf in p_facts:
            assert pf.adjuncts.get("source_structure") == ["prose"], f"Prose fact missing 'prose' source_structure: {pf}"
            trip_str = f"{pf.subject} {pf.verb} {pf.object}".lower()
            assert "einstein" not in trip_str, f"Table entity 'Einstein' leaked into prose extraction: {trip_str}"
            assert "galileo" not in trip_str, f"List entity 'Galileo' leaked into prose extraction: {trip_str}"

        # Assertions on table-derived facts
        t_facts = [f for f in s_facts if f.adjuncts.get("source_structure") == ["table_row"]]
        assert len(t_facts) > 0, "No table facts extracted by structured adapter!"
        for tf in t_facts:
            assert tf.adjuncts.get("source_structure") == ["table_row"], f"Table fact missing 'table_row' tag: {tf}"
            assert tf.adjuncts.get("source_block_id") == ["0"], f"Table fact has incorrect source_block_id: {tf.adjuncts.get('source_block_id')}"
            assert "einstein" in tf.subject.lower() or "einstein" in tf.object.lower()

        # Assertions on list-derived facts
        l_facts = [f for f in s_facts if f.adjuncts.get("source_structure") == ["list_item"]]
        assert len(l_facts) > 0, "No list facts extracted by structured adapter!"
        for lf in l_facts:
            assert lf.adjuncts.get("source_structure") == ["list_item"], f"List fact missing 'list_item' tag: {lf}"
            assert lf.adjuncts.get("source_block_id") == ["1"], f"List fact has incorrect source_block_id: {lf.adjuncts.get('source_block_id')}"
            assert "galileo" in lf.subject.lower() or "galileo" in lf.object.lower()

        # Negative assertion: validation fails if provenance is missing or incorrect
        def validate_provenance_integrity(facts: List[Fact]) -> bool:
            for f in facts:
                if not f.adjuncts or "source_structure" not in f.adjuncts:
                    return False
                struct_type = f.adjuncts["source_structure"][0]
                if struct_type not in ("prose", "table_row", "list_item"):
                    return False
                if struct_type in ("table_row", "list_item") and "source_block_id" not in f.adjuncts:
                    return False
            return True

        assert validate_provenance_integrity(p_facts + s_facts) is True
        unprovenanced_fact = Fact(subject="Fake", verb="is", object="Fake")
        assert validate_provenance_integrity([unprovenanced_fact]) is False
        corrupted_fact = Fact(subject="Fake", verb="is", object="Fake", adjuncts={"source_structure": ["table_row"]})
        assert validate_provenance_integrity([corrupted_fact]) is False

        # Assert deterministic ordering across 5 repeated runs
        for _ in range(5):
            _, rep_blocks = StructuralDocumentParser(fixture_doc).parse()
            rep_s_facts, _ = adapt_structured_blocks_to_facts(
                blocks=rep_blocks,
                query=fixture_query,
                doc_text=fixture_doc,
                source_doc=fixture_sid,
                normalize_names=False,
                max_facts=10,
            )
            assert [(f.subject, f.verb, f.object) for f in rep_s_facts] == [(f.subject, f.verb, f.object) for f in s_facts]

        results["tests"]["test_a12_source_provenance_and_ordering"] = {
            "passed": True,
            "prose_facts_count": len(p_facts),
            "table_facts_count": len(t_facts),
            "list_facts_count": len(l_facts),
            "table_block_ids": list({f.adjuncts['source_block_id'][0] for f in t_facts}),
            "list_block_ids": list({f.adjuncts['source_block_id'][0] for f in l_facts}),
        }
    except Exception as e:
        results["tests"]["test_a12_source_provenance_and_ordering"] = {"passed": False, "error": str(e)}

    # Test A13: Structured Content Availability
    try:
        doc = "<Table><Tr><Th>Player</Th><Th>Goals</Th></Tr><Tr><Td>Messi</Td><Td>800</Td></Tr></Table>"
        parser = StructuralDocumentParser(doc)
        _, blocks = parser.parse()
        s_facts, _ = adapt_structured_blocks_to_facts(blocks, "who scored goals", doc, "doc_messi")
        assert len(s_facts) > 0
        assert any("messi" in f.subject.lower() for f in s_facts)
        results["tests"]["test_a13_structured_content_availability"] = {"passed": True}
    except Exception as e:
        results["tests"]["test_a13_structured_content_availability"] = {"passed": False, "error": str(e)}

    # Test A14: Legitimate Prose Mentioning Table Entity Preserved
    try:
        doc = "Lake Superior is located in North America.<Table><Tr><Th>Lake</Th></Tr><Tr><Td>Lake Superior</Td></Tr></Table>"
        parser = StructuralDocumentParser(doc)
        prose, blocks = parser.parse()
        assert "Lake Superior is located in North America." in prose
        p_facts = extract_facts(resolve_coreferences(prose), source_doc="d_sup")
        sup_found = any("lake superior" in f.subject.lower() for f in p_facts)
        assert sup_found, "Legitimate prose mentioning table entity was lost!"
        results["tests"]["test_a14_legitimate_prose_preserved"] = {"passed": True}
    except Exception as e:
        results["tests"]["test_a14_legitimate_prose_preserved"] = {"passed": False, "error": str(e)}

    # Test A15: Nested Table and List Inside Table Cells
    try:
        doc = "<Table><Tr><Td>Outer cell <Ul><Li>Inner bullet</Li></Ul> and <Table><Tr><Td>Inner table</Td></Tr></Table> trailing cell text</Td></Tr></Table><p>Post prose.</p>"
        parser = StructuralDocumentParser(doc)
        prose, blocks = parser.parse()
        assert len(blocks) == 1, f"Expected 1 parent block, got {len(blocks)}"
        assert "Post prose." in prose
        results["tests"]["test_a15_nested_blocks_inside_cell"] = {"passed": True}
    except Exception as e:
        results["tests"]["test_a15_nested_blocks_inside_cell"] = {"passed": False, "error": str(e)}

    results["all_passed"] = all(v["passed"] for v in results["tests"].values())
    return results

# ==============================================================================
# 5. Pipeline Runners for Condition Inference
# ==============================================================================

def run_condition_inference_v3(
    q: str,
    raw_doc: str,
    sid: str,
    condition: Literal["cond_a", "cond_b", "cond_c"],
    model: str = DEFAULT_MODEL,
    base_svoa_cache: Optional[Dict[str, List[Fact]]] = None,
) -> Tuple[str, int, int]:
    """
    Execute pipeline ingestion, packing, and Ollama inference for Condition A, B, or C.
    """
    store = FactStore(in_memory=True, collection_name=f"t_{uuid.uuid4().hex[:8]}")

    if condition == "cond_a":
        # Baseline: Raw unstripped document through Prose SVOA
        if base_svoa_cache is not None and "cond_a" in base_svoa_cache:
            facts = base_svoa_cache["cond_a"]
        else:
            resolved_doc = resolve_coreferences(raw_doc)
            facts = extract_facts(resolved_doc, source_doc=sid)
            for f in facts:
                if f.adjuncts is None:
                    f.adjuncts = {}
                f.adjuncts["source_structure"] = ["prose"]
            if base_svoa_cache is not None:
                base_svoa_cache["cond_a"] = facts
        struct_count = 0
    else:
        # Condition B and C: Structural Decompilation
        parser = StructuralDocumentParser(raw_doc)
        clean_prose, blocks = parser.parse()

        # Prose SVOA on clean prose
        if base_svoa_cache is not None and "decompiled_prose" in base_svoa_cache:
            p_facts = base_svoa_cache["decompiled_prose"]
        else:
            resolved_prose = resolve_coreferences(clean_prose)
            p_facts = extract_facts(resolved_prose, source_doc=sid)
            for f in p_facts:
                if f.adjuncts is None:
                    f.adjuncts = {}
                f.adjuncts["source_structure"] = ["prose"]
            if base_svoa_cache is not None:
                base_svoa_cache["decompiled_prose"] = p_facts

        # Structured extraction via adapter
        normalize_names = (condition == "cond_c")
        s_facts, _ = adapt_structured_blocks_to_facts(
            blocks,
            query=q,
            doc_text=raw_doc,
            source_doc=sid,
            normalize_names=normalize_names,
            max_facts=15,
        )

        # Conservative cross-path deduplication
        facts, _ = deduplicate_facts(p_facts, s_facts)
        struct_count = len(s_facts)

    scored_facts = score_facts_with_store(facts, store)
    store.add_facts(scored_facts)

    pack = pack_context(q, store, token_ceiling=DEFAULT_TOKEN_CEILING)
    ctx_str = render_context(pack.packed_facts)

    res = generate_answer(
        query=q,
        context=ctx_str,
        model=model,
        temperature=DEFAULT_TEMP,
        top_p=DEFAULT_TOP_P,
        max_tokens=DEFAULT_MAX_TOKENS,
        prompt_style="concise",
    )
    if res.answer is None or not res.answer.strip():
        raise RuntimeError(
            f"[INFERENCE ERROR] Operational inference failure: empty or unscorable response "
            f"for sample '{sid}', condition '{condition}'"
        )
    return res.answer, pack.tokens_used, struct_count


# ==============================================================================
# 6. Stage B: Historical Diagnostic Replay (N=59 Unique Cases)
# ==============================================================================

def run_stage_b_replay(
    docs: Dict[str, Any],
    stage_b_ids: List[str],
    model: str,
    output_dir: Path,
) -> Dict[str, Any]:
    """
    Replay previously inspected historical diagnostic cases.
    Evaluates Conditions A, B, and C under strictly frozen inference parameters.
    Treats all results as diagnostic and non-confirmatory.
    """
    print("\n" + "=" * 80)
    print(f"RUNNING STAGE B: HISTORICAL DIAGNOSTIC REPLAY (N={len(stage_b_ids)} Unique Cases)")
    print("=" * 80)

    records: List[Dict[str, Any]] = []
    out_file = output_dir / "eval_records_stage_b.jsonl"
    if out_file.exists():
        out_file.unlink()

    for idx, sid in enumerate(stage_b_ids):
        doc_entry = docs.get(sid)
        if not doc_entry:
            continue

        q = doc_entry["question"]
        gold = doc_entry["gold_answer"]
        answers = doc_entry.get("answers", [gold])
        raw_doc = doc_entry["document"]

        print(f"[{idx+1}/{len(stage_b_ids)}] Stage B {sid[:8]} | '{q[:40]}...'")

        # Ingestion cache to avoid recomputing Coref/SVOA across conditions
        base_cache: Dict[str, List[Fact]] = {}

        # 1. Condition A (Baseline Concise)
        ans_a, tok_a, _ = run_condition_inference_v3(q, raw_doc, sid, "cond_a", model, base_cache)
        em_a = check_exact_match(ans_a, gold, answers)
        cont_a = check_containment(ans_a, gold, answers)

        # 2. Condition B (Isolated Decompilation)
        ans_b, tok_b, sc_b = run_condition_inference_v3(q, raw_doc, sid, "cond_b", model, base_cache)
        em_b = check_exact_match(ans_b, gold, answers)
        cont_b = check_containment(ans_b, gold, answers)

        # 3. Condition C (Decompilation + Sortable-Name Normalization Pattern 1)
        ans_c, tok_c, sc_c = run_condition_inference_v3(q, raw_doc, sid, "cond_c", model, base_cache)
        em_c = check_exact_match(ans_c, gold, answers)
        cont_c = check_containment(ans_c, gold, answers)

        rec = {
            "sample_id": sid,
            "question": q,
            "gold_answer": gold,
            "cond_a": {"exact_match": em_a, "containment": cont_a, "predicted_answer": ans_a, "context_tokens": tok_a},
            "cond_b": {"exact_match": em_b, "containment": cont_b, "predicted_answer": ans_b, "context_tokens": tok_b, "struct_facts": sc_b},
            "cond_c": {"exact_match": em_c, "containment": cont_c, "predicted_answer": ans_c, "context_tokens": tok_c, "struct_facts": sc_c},
            "b_vs_a": {"em_win": em_b and not em_a, "em_loss": em_a and not em_b, "token_delta": tok_b - tok_a},
            "c_vs_a": {"em_win": em_c and not em_a, "em_loss": em_a and not em_c, "token_delta": tok_c - tok_a},
        }
        records.append(rec)
        with open(out_file, "a") as f:
            f.write(json.dumps(rec) + "\n")

    # Summary
    n = len(records)
    em_a_rate = sum(r["cond_a"]["exact_match"] for r in records) / n if n else 0.0
    em_b_rate = sum(r["cond_b"]["exact_match"] for r in records) / n if n else 0.0
    em_c_rate = sum(r["cond_c"]["exact_match"] for r in records) / n if n else 0.0

    cont_a_rate = sum(r["cond_a"]["containment"] for r in records) / n if n else 0.0
    cont_b_rate = sum(r["cond_b"]["containment"] for r in records) / n if n else 0.0
    cont_c_rate = sum(r["cond_c"]["containment"] for r in records) / n if n else 0.0

    tok_a_avg = sum(r["cond_a"]["context_tokens"] for r in records) / n if n else 0.0
    tok_b_avg = sum(r["cond_b"]["context_tokens"] for r in records) / n if n else 0.0
    tok_c_avg = sum(r["cond_c"]["context_tokens"] for r in records) / n if n else 0.0

    b_wins = sum(r["b_vs_a"]["em_win"] for r in records)
    b_losses = sum(r["b_vs_a"]["em_loss"] for r in records)
    c_wins = sum(r["c_vs_a"]["em_win"] for r in records)
    c_losses = sum(r["c_vs_a"]["em_loss"] for r in records)

    summary = {
        "cohort_name": "stage_b_diagnostic_replay",
        "n_unique_samples": n,
        "cond_a": {"em": em_a_rate, "containment": cont_a_rate, "avg_tokens": tok_a_avg},
        "cond_b": {"em": em_b_rate, "containment": cont_b_rate, "avg_tokens": tok_b_avg, "overhead_vs_a": (tok_b_avg - tok_a_avg) / tok_a_avg if tok_a_avg else 0.0, "em_wins": b_wins, "em_losses": b_losses},
        "cond_c": {"em": em_c_rate, "containment": cont_c_rate, "avg_tokens": tok_c_avg, "overhead_vs_a": (tok_c_avg - tok_a_avg) / tok_a_avg if tok_a_avg else 0.0, "em_wins": c_wins, "em_losses": c_losses},
    }
    with open(output_dir / "stage_b_replay.json", "w") as f:
        json.dump(summary, f, indent=2)

    return summary

# ==============================================================================
# 7. Stage C: Sample Manifest Generator & Disjointness Auditor
# ==============================================================================

def compute_stage_c_config_fingerprint(
    model: str = DEFAULT_MODEL,
    temp: float = DEFAULT_TEMP,
    top_p: float = DEFAULT_TOP_P,
    seed: int = DEFAULT_SEED,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    token_ceiling: int = DEFAULT_TOKEN_CEILING,
    prompt_template_name: str = "CONCISE_PROMPT_TEMPLATE",
    manifest_hash: Optional[str] = None,
    manifest_cohort: str = "confirmatory_decompilation_v3",
) -> Dict[str, Any]:
    """
    Generate a stable, configuration fingerprint for Stage C confirmatory evaluation.
    Guarantees that records cannot be resumed or combined across differing configurations.
    """
    config_dict = {
        "model": model,
        "temperature": temp,
        "top_p": top_p,
        "seed": seed,
        "max_tokens": max_tokens,
        "token_ceiling": token_ceiling,
        "prompt_template": prompt_template_name,
        "harness_version": "experiment_3_v3_safety_hardened",
        "condition_implementations": {
            "cond_a": "raw_html_coref_prose_svoa",
            "cond_b": "decompiled_prose_structured_adapter_dedup",
            "cond_c": "decompiled_prose_structured_adapter_dedup_sortable_name_pattern1",
        },
        "scoring": {
            "exact_match": "check_exact_match_v2",
            "containment": "check_containment_v2",
        },
        "manifest_cohort": manifest_cohort,
        "manifest_hash": manifest_hash or "",
    }
    raw_str = json.dumps(config_dict, sort_keys=True)
    fingerprint_hash = hashlib.sha256(raw_str.encode("utf-8")).hexdigest()
    return {
        "fingerprint": fingerprint_hash,
        "config": config_dict,
    }


def validate_stage_c_record(
    rec: Dict[str, Any],
    manifest_sids: Optional[Set[str]] = None,
    line_idx: Optional[int] = None,
) -> None:
    """
    Validate that a Stage C sample record is complete, well-formed, and strictly conformant.
    Raises ValueError on any missing, unexpected, partial, failed, or unscorable condition results.
    """
    loc_str = f" at line {line_idx+1}" if line_idx is not None else ""
    if not isinstance(rec, dict):
        raise ValueError(f"[SAFETY ERROR] Malformed record{loc_str}: expected dict, got {type(rec).__name__}")

    sid = rec.get("sample_id")
    if not sid or not isinstance(sid, str):
        raise ValueError(f"[SAFETY ERROR] Record{loc_str} is missing a valid 'sample_id'")

    if manifest_sids is not None and sid not in manifest_sids:
        raise ValueError(
            f"[SAFETY ERROR] Record{loc_str} has unexpected sample_id '{sid}' "
            f"which is not present in the active confirmatory manifest!"
        )

    stratum = rec.get("stratum")
    if stratum not in ("table_bearing", "prose_only"):
        raise ValueError(
            f"[SAFETY ERROR] Record for '{sid}'{loc_str} has invalid stratum '{stratum}' "
            f"(expected 'table_bearing' or 'prose_only')"
        )

    for cond_name in ("cond_a", "cond_b", "cond_c"):
        if cond_name not in rec or not isinstance(rec[cond_name], dict):
            raise ValueError(
                f"[SAFETY ERROR] Record for '{sid}'{loc_str} is missing required condition '{cond_name}'"
            )
        c_dict = rec[cond_name]
        status = c_dict.get("status")
        if status != "success":
            raise ValueError(
                f"[SAFETY ERROR] Record for '{sid}'{loc_str} has invalid or failed status '{status}' "
                f"for condition '{cond_name}' (expected 'success')"
            )
        for req_field in ("exact_match", "containment", "context_tokens"):
            if req_field not in c_dict:
                raise ValueError(
                    f"[SAFETY ERROR] Record for '{sid}'{loc_str} missing field '{req_field}' in '{cond_name}'"
                )
        if not isinstance(c_dict["exact_match"], bool):
            raise ValueError(
                f"[SAFETY ERROR] Record for '{sid}'{loc_str} field 'exact_match' in '{cond_name}' must be boolean"
            )
        if not isinstance(c_dict["containment"], bool):
            raise ValueError(
                f"[SAFETY ERROR] Record for '{sid}'{loc_str} field 'containment' in '{cond_name}' must be boolean"
            )
        if not isinstance(c_dict["context_tokens"], (int, float)) or c_dict["context_tokens"] < 0:
            raise ValueError(
                f"[SAFETY ERROR] Record for '{sid}'{loc_str} field 'context_tokens' in '{cond_name}' must be non-negative"
            )
        pred = c_dict.get("predicted_answer")
        if pred is None or not isinstance(pred, str):
            raise ValueError(
                f"[SAFETY ERROR] Record for '{sid}'{loc_str} missing string 'predicted_answer' in '{cond_name}'"
            )
        if cond_name in ("cond_b", "cond_c"):
            if "struct_facts" not in c_dict or not isinstance(c_dict["struct_facts"], int):
                raise ValueError(
                    f"[SAFETY ERROR] Record for '{sid}'{loc_str} missing integer 'struct_facts' in '{cond_name}'"
                )

    for cmp_name in ("b_vs_a", "c_vs_a"):
        if cmp_name not in rec or not isinstance(rec[cmp_name], dict):
            raise ValueError(
                f"[SAFETY ERROR] Record for '{sid}'{loc_str} missing required comparison '{cmp_name}'"
            )
        cmp_dict = rec[cmp_name]
        for fld in ("em_win", "em_loss", "token_delta"):
            if fld not in cmp_dict:
                raise ValueError(
                    f"[SAFETY ERROR] Record for '{sid}'{loc_str} missing comparison field '{fld}' in '{cmp_name}'"
                )

    if stratum == "prose_only":
        inv = rec.get("invariance_audit")
        if not isinstance(inv, dict):
            raise ValueError(
                f"[SAFETY ERROR] Record for '{sid}'{loc_str} missing 'invariance_audit' dictionary"
            )
        if "upstream_invariant" not in inv or not isinstance(inv["upstream_invariant"], bool):
            raise ValueError(
                f"[SAFETY ERROR] Record for '{sid}'{loc_str} missing boolean 'upstream_invariant' in invariance_audit"
            )


def audit_and_generate_manifest(
    docs: Dict[str, Any],
    output_dir: Path,
    seed: int = DEFAULT_SEED,
    allow_resume: bool = False,
) -> Tuple[List[Dict[str, Any]], Set[str], str]:
    """
    Audit historical exclusions across Exp 1, Exp 2, Exp 3 Stage B, and Paper failure analysis.
    Generate or validate a strictly disjoint confirmatory sample of N=300 (200 Table, 100 Prose).
    Returns (manifest_records, exclusions, manifest_hash).
    """
    manifest_file = output_dir / "sample_manifest.jsonl"
    exclusions_file = output_dir / "historical_exclusions.json"

    exclusions: Set[str] = set()

    # Exp 1
    p1 = REPO_ROOT / "results" / "diagnostic_table_extraction_v1"
    if p1.exists():
        for f in p1.glob("*.json*"):
            try:
                with open(f) as fp:
                    for line in fp:
                        try:
                            d = json.loads(line)
                            for k in ["sample_id", "doc_id", "id"]:
                                if k in d and isinstance(d[k], str):
                                    exclusions.add(d[k])
                        except Exception:
                            pass
            except Exception:
                pass

    # Exp 2
    p2 = REPO_ROOT / "results" / "diagnostic_table_selection_v2"
    if p2.exists():
        for f in p2.glob("*.json*"):
            try:
                with open(f) as fp:
                    for line in fp:
                        try:
                            d = json.loads(line)
                            for k in ["sample_id", "doc_id", "id"]:
                                if k in d and isinstance(d[k], str):
                                    exclusions.add(d[k])
                        except Exception:
                            pass
            except Exception:
                pass

    # Paper failure analysis
    p_fail = REPO_ROOT / "paper" / "tables" / "enhanced_failure_analysis_v3_rerun" / "failure_analysis.jsonl"
    if p_fail.exists():
        with open(p_fail) as fp:
            for line in fp:
                try:
                    d = json.loads(line)
                    for k in ["sample_id", "doc_id", "id"]:
                        if k in d and isinstance(d[k], str):
                            exclusions.add(d[k])
                except Exception:
                    pass

    # Explicit diagnostic cases
    for sid in [
        "bad74caad55343f9ad68de7cd705689a",
        "51c8273468a74ec68c54e9dbfa6c7203",
        "2240c51d94504dc2a279339cbba9a8e0",
        "dcb364bb50c945e2b3770eb57975204d",
    ]:
        exclusions.add(sid)

    # Stage B (Experiment 3 Diagnostic Replay manifest - direct inclusion)
    p_stage_b = REPO_ROOT / "results" / "diagnostic_structural_decompilation_v3" / "sample_manifest_stage_b.jsonl"
    if p_stage_b.exists():
        with open(p_stage_b) as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    if d.get("type") == "sample_record":
                        sid = d.get("sample_id")
                        if sid and isinstance(sid, str):
                            exclusions.add(sid)
                    elif d.get("type") == "manifest_header":
                        continue
                    else:
                        for k in ["sample_id", "doc_id", "id"]:
                            if k in d and isinstance(d[k], str):
                                exclusions.add(d[k])
                except Exception:
                    pass

    # Check for existing manifest and exclusions
    if manifest_file.exists() and manifest_file.stat().st_size > 0:
        if not allow_resume:
            raise FileExistsError(
                f"[SAFETY ERROR] Non-empty manifest already exists at {manifest_file} "
                f"({manifest_file.stat().st_size} bytes). Refusing silent overwrite. "
                f"To safely reuse the validated manifest for a resumed run, pass --resume. "
                f"For a clean run, specify a fresh --output-dir."
            )
        existing_records: List[Dict[str, Any]] = []
        existing_m_hash = None
        with open(manifest_file) as f:
            for line in f:
                if line.strip():
                    try:
                        d = json.loads(line)
                        if d.get("type") == "manifest_header":
                            existing_m_hash = d.get("manifest_hash")
                        elif d.get("type") == "sample_record":
                            existing_records.append(d)
                    except Exception:
                        pass
        if len(existing_records) != 300:
            raise ValueError(
                f"[SAFETY ERROR] Existing manifest at {manifest_file} contains {len(existing_records)} "
                f"sample records (expected exactly 300). Corrupted manifest cannot be resumed."
            )
        if not existing_m_hash:
            existing_m_hash = hashlib.sha256(",".join(r["sample_id"] for r in existing_records).encode("utf-8")).hexdigest()
        print(f"Validated resume: reusing existing manifest ({len(existing_records)} samples, hash: {existing_m_hash[:12]}...)")
        return existing_records, exclusions, existing_m_hash

    if exclusions_file.exists() and exclusions_file.stat().st_size > 0 and not allow_resume:
        raise FileExistsError(
            f"[SAFETY ERROR] Non-empty historical exclusions file already exists at {exclusions_file} "
            f"({exclusions_file.stat().st_size} bytes). Refusing silent overwrite without --resume."
        )

    # Partition available documents
    table_candidates: List[Dict[str, Any]] = []
    prose_candidates: List[Dict[str, Any]] = []

    for did, d in docs.items():
        if did in exclusions:
            continue
        raw = d.get("document", "")
        has_t = "<table" in raw.lower()
        has_l = "<ul" in raw.lower() or "<ol" in raw.lower()
        if has_t or has_l:
            table_candidates.append(d)
        else:
            prose_candidates.append(d)

    print(f"Exclusions cataloged: {len(exclusions)}")
    print(f"Available table/list candidates: {len(table_candidates)} (Required: 200)")
    print(f"Available prose-only candidates: {len(prose_candidates)} (Required: 100)")

    rng = random.Random(seed)
    rng.shuffle(table_candidates)
    rng.shuffle(prose_candidates)

    selected_table = table_candidates[:200]
    selected_prose = prose_candidates[:100]

    # Verify disjointness and uniqueness BEFORE writing any outputs
    selected_ids = [d["doc_id"] for d in selected_table + selected_prose]
    unique_selected_ids = set(selected_ids)
    assert len(unique_selected_ids) == len(selected_ids), (
        f"CRITICAL: Duplicate IDs in confirmatory sample: {len(selected_ids) - len(unique_selected_ids)} duplicates found!"
    )
    intersection = unique_selected_ids & exclusions
    assert len(intersection) == 0, f"CRITICAL: Confirmatory sample intersects exclusions by {len(intersection)} cases!"
    assert len(selected_table) == 200, f"Insufficient table candidates: {len(selected_table)}"
    assert len(selected_prose) == 100, f"Insufficient prose candidates: {len(selected_prose)}"

    manifest_hash = hashlib.sha256(",".join(selected_ids).encode("utf-8")).hexdigest()

    # Save historical exclusions audit only after sampling assertions pass
    with open(exclusions_file, "w") as f:
        json.dump({"total_exclusions": len(exclusions), "ids": sorted(list(exclusions))}, f, indent=2)

    manifest_records: List[Dict[str, Any]] = []
    with open(manifest_file, "w") as f:
        header = {
            "type": "manifest_header",
            "cohort_name": "confirmatory_decompilation_v3",
            "seed": seed,
            "manifest_hash": manifest_hash,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "stratum_1_table_bearing_count": 200,
            "stratum_2_prose_only_count": 100,
            "total_samples": 300,
        }
        f.write(json.dumps(header) + "\n")

        for d in selected_table:
            rec = {
                "type": "sample_record",
                "sample_id": d["doc_id"],
                "question": d["question"],
                "gold_answer": d["gold_answer"],
                "answers": d.get("answers", [d["gold_answer"]]),
                "stratum": "table_bearing",
                "has_table": "<table" in d["document"].lower(),
                "has_list": "<ul" in d["document"].lower() or "<ol" in d["document"].lower(),
            }
            manifest_records.append(rec)
            f.write(json.dumps(rec) + "\n")

        for d in selected_prose:
            rec = {
                "type": "sample_record",
                "sample_id": d["doc_id"],
                "question": d["question"],
                "gold_answer": d["gold_answer"],
                "answers": d.get("answers", [d["gold_answer"]]),
                "stratum": "prose_only",
                "has_table": False,
                "has_list": False,
            }
            manifest_records.append(rec)
            f.write(json.dumps(rec) + "\n")

    print(f"Successfully wrote {len(manifest_records)} samples to {manifest_file} (manifest_hash: {manifest_hash[:12]}...)")
    return manifest_records, exclusions, manifest_hash


# ==============================================================================
# 8. Stage C: Confirmatory Evaluation Runner (N=300)
# ==============================================================================

def run_stage_c_confirmatory(
    docs: Dict[str, Any],
    manifest_records: List[Dict[str, Any]],
    model: str,
    output_dir: Path,
    manifest_hash: Optional[str] = None,
    allow_resume: bool = False,
) -> List[Dict[str, Any]]:
    """
    Execute Stage C confirmatory evaluation across 300 samples under Conditions A, B, and C.
    Enforces configuration fingerprinting, safe non-empty artifact gating, and prose-only invariance diagnostics.
    """
    print("\n" + "=" * 80)
    print(f"RUNNING STAGE C: CONFIRMATORY DUAL-STRATUM EVALUATION (N={len(manifest_records)})")
    print("=" * 80)

    cfg_meta = compute_stage_c_config_fingerprint(
        model=model,
        temp=DEFAULT_TEMP,
        top_p=DEFAULT_TOP_P,
        seed=DEFAULT_SEED,
        max_tokens=DEFAULT_MAX_TOKENS,
        token_ceiling=DEFAULT_TOKEN_CEILING,
        prompt_template_name="CONCISE_PROMPT_TEMPLATE",
        manifest_hash=manifest_hash,
    )
    current_fingerprint = cfg_meta["fingerprint"]
    print(f"Active Stage C Configuration Fingerprint: {current_fingerprint}")

    manifest_sids = {item["sample_id"] for item in manifest_records if "sample_id" in item}

    out_file = output_dir / "eval_records_stage_c.jsonl"
    records: List[Dict[str, Any]] = []
    existing_sids: Set[str] = set()

    if out_file.exists() and out_file.stat().st_size > 0:
        if not allow_resume:
            raise FileExistsError(
                f"[SAFETY ERROR] Existing non-empty Stage C records found at {out_file} "
                f"({out_file.stat().st_size} bytes). Silently overwriting or appending without explicit "
                f"validation is prohibited. To resume safely, pass --resume. "
                f"To run a fresh evaluation, specify a new --output-dir."
            )

        header_found = False
        with open(out_file) as f:
            for line_idx, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    if d.get("type") == "run_header":
                        header_found = True
                        existing_fp = d.get("config_fingerprint")
                        if existing_fp != current_fingerprint:
                            raise ValueError(
                                f"[SAFETY ERROR] Configuration fingerprint mismatch! "
                                f"Existing run: {existing_fp} vs Current run: {current_fingerprint}. "
                                f"Refusing to mix results across differing configurations."
                            )
                    elif d.get("type") == "sample_record" or "sample_id" in d:
                        rec_fp = d.get("config_fingerprint")
                        if rec_fp and rec_fp != current_fingerprint:
                            raise ValueError(
                                f"[SAFETY ERROR] Record fingerprint mismatch at line {line_idx+1}! "
                                f"Record: {rec_fp} vs Current: {current_fingerprint}."
                            )
                        # Validate full record completeness and manifest membership BEFORE accepting
                        validate_stage_c_record(d, manifest_sids=manifest_sids, line_idx=line_idx)
                        sid = d["sample_id"]
                        if sid in existing_sids:
                            raise ValueError(
                                f"[SAFETY ERROR] Duplicate resumed record detected at line {line_idx+1}! "
                                f"Sample ID '{sid}' appears multiple times in {out_file}. "
                                f"Refusing to resume corrupted records with duplicate entries."
                            )
                        existing_sids.add(sid)
                        records.append(d)
                except json.JSONDecodeError as e:
                    raise ValueError(
                        f"[SAFETY ERROR] Malformed JSON in existing records at line {line_idx+1}: {e}. "
                        f"Corrupted file cannot be safely resumed."
                    )
        if not header_found:
            raise ValueError(
                f"[SAFETY ERROR] Existing records at {out_file} lack a validated run_header fingerprint. "
                f"Refusing unverified resume."
            )
        print(f"Validated resume: loaded {len(records)} existing matching confirmatory records (Fingerprint: {current_fingerprint[:12]}...).")
    elif not out_file.exists() or out_file.stat().st_size == 0:
        header_rec = {
            "type": "run_header",
            "cohort_name": "confirmatory_decompilation_v3",
            "config_fingerprint": current_fingerprint,
            "config": cfg_meta["config"],
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        }
        with open(out_file, "w") as f:
            f.write(json.dumps(header_rec) + "\n")

    for idx, item in enumerate(manifest_records):
        sid = item["sample_id"]
        if sid in existing_sids:
            continue

        doc_entry = docs[sid]
        q = doc_entry["question"]
        gold = doc_entry["gold_answer"]
        answers = doc_entry.get("answers", [gold])
        raw_doc = doc_entry["document"]
        stratum = item["stratum"]

        print(f"[{idx+1}/{len(manifest_records)}] Stage C ({stratum[:5]}) {sid[:8]} | '{q[:35]}...'")

        base_cache: Dict[str, List[Fact]] = {}

        # 1. Condition A (Baseline Concise)
        ans_a, tok_a, _ = run_condition_inference_v3(q, raw_doc, sid, "cond_a", model, base_cache)
        em_a = check_exact_match(ans_a, gold, answers)
        cont_a = check_containment(ans_a, gold, answers)

        # 2. Condition B (Isolated Decompilation)
        ans_b, tok_b, sc_b = run_condition_inference_v3(q, raw_doc, sid, "cond_b", model, base_cache)
        em_b = check_exact_match(ans_b, gold, answers)
        cont_b = check_containment(ans_b, gold, answers)

        # 3. Condition C (Decompilation + Sortable-Name Normalization Pattern 1)
        ans_c, tok_c, sc_c = run_condition_inference_v3(q, raw_doc, sid, "cond_c", model, base_cache)
        em_c = check_exact_match(ans_c, gold, answers)
        cont_c = check_containment(ans_c, gold, answers)

        # Prose-only upstream invariance diagnostic (does not modify inputs, prompts, or conditions)
        invariance_info = None
        if stratum == "prose_only":
            parser_diag = StructuralDocumentParser(raw_doc)
            c_prose, c_blocks = parser_diag.parse()
            prose_byte_id = (c_prose == raw_doc)
            zero_blocks = (len(c_blocks) == 0)
            a_facts = base_cache.get("cond_a", [])
            b_facts = base_cache.get("decompiled_prose", [])
            facts_id = ([(f.subject, f.verb, f.object) for f in a_facts] == [(f.subject, f.verb, f.object) for f in b_facts])
            tokens_id = (tok_b == tok_a and tok_c == tok_a)
            invariance_info = {
                "prose_byte_identical": prose_byte_id,
                "zero_structured_blocks": zero_blocks,
                "facts_identical": facts_id,
                "context_tokens_identical": tokens_id,
                "upstream_invariant": prose_byte_id and zero_blocks and facts_id and tokens_id,
            }

        rec = {
            "type": "sample_record",
            "config_fingerprint": current_fingerprint,
            "sample_id": sid,
            "stratum": stratum,
            "question": q,
            "gold_answer": gold,
            "answers": answers,
            "cond_a": {"status": "success", "exact_match": em_a, "containment": cont_a, "predicted_answer": ans_a, "context_tokens": tok_a},
            "cond_b": {"status": "success", "exact_match": em_b, "containment": cont_b, "predicted_answer": ans_b, "context_tokens": tok_b, "struct_facts": sc_b},
            "cond_c": {"status": "success", "exact_match": em_c, "containment": cont_c, "predicted_answer": ans_c, "context_tokens": tok_c, "struct_facts": sc_c},
            "b_vs_a": {"em_win": em_b and not em_a, "em_loss": em_a and not em_b, "token_delta": tok_b - tok_a},
            "c_vs_a": {"em_win": em_c and not em_a, "em_loss": em_a and not em_c, "token_delta": tok_c - tok_a},
            "invariance_audit": invariance_info,
        }
        validate_stage_c_record(rec, manifest_sids=manifest_sids)
        records.append(rec)
        with open(out_file, "a") as f:
            f.write(json.dumps(rec) + "\n")

    return records


# ==============================================================================
# 9. Aggregate Summary & Multiplicity-Adjusted Statistical Tests
# ==============================================================================

def compute_aggregate_summary(
    records: List[Dict[str, Any]],
    output_dir: Path,
    expected_sample_count: Optional[int] = 300,
    expected_table_count: Optional[int] = 200,
    expected_prose_count: Optional[int] = 100,
    manifest_sids: Optional[Set[str]] = None,
    allow_overwrite: bool = False,
    enforce_guardrails: bool = False,
) -> Dict[str, Any]:
    """
    Compute statistical metrics across strata with Holm-Bonferroni correction.
    Requires complete, validated cohort records and enforces fail-closed guardrails.
    """
    summary_file = output_dir / "aggregate_summary.json"
    if summary_file.exists() and summary_file.stat().st_size > 0 and not allow_overwrite:
        raise FileExistsError(
            f"[SAFETY ERROR] Non-empty aggregate summary already exists at {summary_file}. "
            f"Refusing silent overwrite without explicit allow_overwrite / --resume flag."
        )

    seen_sample_ids: Set[str] = set()
    for r_idx, r in enumerate(records):
        # Validate full record completeness and manifest membership BEFORE computing summary
        validate_stage_c_record(r, manifest_sids=manifest_sids, line_idx=r_idx)
        sid = r["sample_id"]
        if sid in seen_sample_ids:
            raise ValueError(
                f"[SAFETY ERROR] Duplicate record detected in aggregate summary calculation (record {r_idx+1})! "
                f"Sample ID '{sid}' appears multiple times. "
                f"Refusing to compute metrics on corrupted records with duplicates."
            )
        seen_sample_ids.add(sid)

    if expected_sample_count is not None and len(seen_sample_ids) != expected_sample_count:
        raise ValueError(
            f"[SAFETY ERROR] Incomplete cohort for aggregate summary! Found {len(seen_sample_ids)} "
            f"unique samples (expected exactly {expected_sample_count}). "
            f"Confirmatory evaluation requires all {expected_sample_count} samples to be evaluated."
        )

    stratum_1 = [r for r in records if r.get("stratum") == "table_bearing"]
    stratum_2 = [r for r in records if r.get("stratum") == "prose_only"]

    if expected_table_count is not None and len(stratum_1) != expected_table_count:
        raise ValueError(
            f"[SAFETY ERROR] Stratum 1 (table-bearing) count mismatch: found {len(stratum_1)} "
            f"(expected exactly {expected_table_count})."
        )
    if expected_prose_count is not None and len(stratum_2) != expected_prose_count:
        raise ValueError(
            f"[SAFETY ERROR] Stratum 2 (prose-only) count mismatch: found {len(stratum_2)} "
            f"(expected exactly {expected_prose_count})."
        )

    def strat_metrics(subset: List[Dict[str, Any]]) -> Dict[str, Any]:
        n = len(subset)
        if n == 0:
            return {}

        em_a = sum(r["cond_a"]["exact_match"] for r in subset) / n
        em_b = sum(r["cond_b"]["exact_match"] for r in subset) / n
        em_c = sum(r["cond_c"]["exact_match"] for r in subset) / n

        cont_a = sum(r["cond_a"]["containment"] for r in subset) / n
        cont_b = sum(r["cond_b"]["containment"] for r in subset) / n
        cont_c = sum(r["cond_c"]["containment"] for r in subset) / n

        tok_a = sum(r["cond_a"]["context_tokens"] for r in subset) / n
        tok_b = sum(r["cond_b"]["context_tokens"] for r in subset) / n
        tok_c = sum(r["cond_c"]["context_tokens"] for r in subset) / n

        # Paired McNemar for B vs A
        b_wins = sum(r["b_vs_a"]["em_win"] for r in subset)
        b_losses = sum(r["b_vs_a"]["em_loss"] for r in subset)
        b_p = scipy.stats.binomtest(b_wins, b_wins + b_losses, 0.5).pvalue if (b_wins + b_losses) > 0 else 1.0

        # Paired McNemar for C vs A
        c_wins = sum(r["c_vs_a"]["em_win"] for r in subset)
        c_losses = sum(r["c_vs_a"]["em_loss"] for r in subset)
        c_p = scipy.stats.binomtest(c_wins, c_wins + c_losses, 0.5).pvalue if (c_wins + c_losses) > 0 else 1.0

        # Wilcoxon for tokens B vs A
        deltas_b = [r["b_vs_a"]["token_delta"] for r in subset]
        w_b_p = scipy.stats.wilcoxon(deltas_b).pvalue if any(d != 0 for d in deltas_b) else 1.0

        # Wilcoxon for tokens C vs A
        deltas_c = [r["c_vs_a"]["token_delta"] for r in subset]
        w_c_p = scipy.stats.wilcoxon(deltas_c).pvalue if any(d != 0 for d in deltas_c) else 1.0

        overhead_b = (tok_b - tok_a) / tok_a if tok_a else 0.0
        overhead_c = (tok_c - tok_a) / tok_a if tok_a else 0.0

        return {
            "n_samples": n,
            "cond_a": {"em": em_a, "containment": cont_a, "avg_tokens": tok_a},
            "cond_b": {
                "em": em_b,
                "containment": cont_b,
                "avg_tokens": tok_b,
                "overhead_vs_a": overhead_b,
                "em_wins": b_wins,
                "em_losses": b_losses,
                "mcnemar_p_unadjusted": b_p,
                "wilcoxon_token_p": w_b_p,
            },
            "cond_c": {
                "em": em_c,
                "containment": cont_c,
                "avg_tokens": tok_c,
                "overhead_vs_a": overhead_c,
                "em_wins": c_wins,
                "em_losses": c_losses,
                "mcnemar_p_unadjusted": c_p,
                "wilcoxon_token_p": w_c_p,
            },
        }

    s1_res = strat_metrics(stratum_1)
    s2_res = strat_metrics(stratum_2)

    # Multiplicity correction across primary comparisons (B vs A, C vs A on Stratum 1 EM)
    p_vals = [
        ("B_vs_A", s1_res.get("cond_b", {}).get("mcnemar_p_unadjusted", 1.0)),
        ("C_vs_A", s1_res.get("cond_c", {}).get("mcnemar_p_unadjusted", 1.0)),
    ]
    p_vals.sort(key=lambda x: x[1])
    # Holm step-down
    holm_results = {}
    alpha = 0.05
    for rank, (name, p) in enumerate(p_vals):
        adj_alpha = alpha / (len(p_vals) - rank)
        rejected = p <= adj_alpha
        holm_results[name] = {
            "raw_p": p,
            "holm_threshold": adj_alpha,
            "significant": rejected,
        }

    # Summarize upstream invariance for Stratum 2
    upstream_invariance_passed = True
    if stratum_2:
        inv_count = sum(1 for r in stratum_2 if r.get("invariance_audit", {}).get("upstream_invariant") is True)
        upstream_invariance_passed = (inv_count == len(stratum_2))
        s2_res["upstream_invariance_all_passed"] = upstream_invariance_passed
        s2_res["upstream_invariance_passed_count"] = inv_count
        s2_res["upstream_invariance_total_count"] = len(stratum_2)

    config_fp = records[0].get("config_fingerprint") if records else "unknown"

    overhead_passed = (s1_res.get("cond_b", {}).get("overhead_vs_a", 1.0) <= 0.10)
    confirmatory_passed = overhead_passed and upstream_invariance_passed

    summary = {
        "cohort_name": "stage_c_confirmatory_summary",
        "config_fingerprint": config_fp,
        "confirmatory_outcome": "PASS" if confirmatory_passed else "FAIL_GUARDRAIL",
        "stratum_1_table_bearing": s1_res,
        "stratum_2_prose_only": s2_res,
        "holm_bonferroni_primary_tests": holm_results,
        "overhead_guardrail_passed": overhead_passed,
        "upstream_invariance_guardrail_passed": upstream_invariance_passed,
    }

    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)

    if enforce_guardrails and not confirmatory_passed:
        raise RuntimeError(
            f"[GUARDRAIL FAILURE] Preregistered confirmatory guardrails failed! "
            f"overhead_passed={overhead_passed}, upstream_invariance_passed={upstream_invariance_passed}."
        )

    return summary


# ==============================================================================
# 10. CLI & Staged Dispatcher
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="Précis Experiment 3 Runner")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help="Ollama LLM model")
    parser.add_argument("--output-dir", type=str, default="results/diagnostic_structural_decompilation_v3")
    parser.add_argument("--dataset-path", type=str, default="backend/data/nq_subset/nq_dev.jsonl")
    parser.add_argument("--stage-a-only", action="store_true", help="Run only Stage A deterministic suite")
    parser.add_argument("--stage-b-only", action="store_true", help="Run only Stage B diagnostic replay")
    parser.add_argument("--stage-c-only", action="store_true", help="Run only Stage C confirmatory evaluation")
    parser.add_argument("--aggregate-only", action="store_true", help="Compute aggregate summary from existing jsonl")
    parser.add_argument("--resume", action="store_true", help="Safely resume existing Stage C records if configuration fingerprint matches exactly")

    args = parser.parse_args()
    out_path = Path(args.output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("PRÉCIS EXPERIMENT 3: ISOLATED STRUCTURAL DOCUMENT DECOMPILATION")
    print(f"Model: {args.model} | Decoding: Greedy (T={DEFAULT_TEMP}, top_p={DEFAULT_TOP_P}, seed={DEFAULT_SEED})")
    print(f"Output Directory: {out_path}")
    print("=" * 80)

    # 1. Load documents
    print("\n[Step 1] Loading documents from nq_dev...")
    with open(args.dataset_path) as f:
        docs = {d["doc_id"]: d for line in f if line.strip() for d in [json.loads(line)]}
    print(f"Loaded {len(docs)} documents.")

    # Aggregate only mode
    if args.aggregate_only:
        c_records = []
        c_file = out_path / "eval_records_stage_c.jsonl"
        manifest_file = out_path / "sample_manifest.jsonl"
        if not manifest_file.exists():
            raise FileNotFoundError(
                f"[SAFETY ERROR] Manifest file {manifest_file} missing. Cannot verify aggregate completeness."
            )
        manifest_sids = set()
        with open(manifest_file) as f:
            for line in f:
                if line.strip():
                    d = json.loads(line)
                    if d.get("type") == "sample_record" and "sample_id" in d:
                        manifest_sids.add(d["sample_id"])
        if len(manifest_sids) != 300:
            raise ValueError(
                f"[SAFETY ERROR] Manifest at {manifest_file} contains {len(manifest_sids)} samples (expected 300)."
            )
        if not c_file.exists():
            raise FileNotFoundError(f"[SAFETY ERROR] Records file {c_file} missing.")
        with open(c_file) as f:
            c_records = [
                d for line in f if line.strip()
                for d in [json.loads(line)]
                if d.get("type") != "run_header" and "stratum" in d
            ]
        summary = compute_aggregate_summary(
            c_records,
            out_path,
            manifest_sids=manifest_sids,
            allow_overwrite=args.resume,
            enforce_guardrails=True,
        )
        print("Aggregate summary computed successfully: all confirmatory guardrails passed.")
        return

    # 2. Stage A
    if not args.stage_b_only and not args.stage_c_only:
        print("\n[Step 2] Executing Stage A Deterministic Unit & Forensic Suite (Zero LLM Inference)...")
        stage_a_res = run_stage_a_suite(docs)
        with open(out_path / "stage_a_results.json", "w") as f:
            json.dump(stage_a_res, f, indent=2)

        if not stage_a_res["all_passed"]:
            print("[CRITICAL ERROR] Stage A failed! Halting execution before Stage B.")
            for k, v in stage_a_res["tests"].items():
                if not v.get("passed"):
                    print(f"  - FAILED: {k} -> {v.get('error')}")
            sys.exit(1)
        print(f"Stage A passed cleanly ({len(stage_a_res['tests'])}/{len(stage_a_res['tests'])} tests passed).")

        if args.stage_a_only:
            print("Stage A only requested. Halting.")
            return

    # 3. Stage B
    if not args.stage_c_only:
        print("\n[Step 3] Executing Stage B Historical Diagnostic Replay (59 Unique Cases)..." )
        # Build 59 unique IDs
        cb_ids = []
        cb_file = REPO_ROOT / "results" / "diagnostic_table_selection_v2" / "eval_records_cohort_b.jsonl"
        if cb_file.exists():
            with open(cb_file) as f:
                for line in f:
                    if line.strip():
                        cb_ids.append(json.loads(line)["sample_id"])

        explicit = [
            "bad74caad55343f9ad68de7cd705689a",
            "51c8273468a74ec68c54e9dbfa6c7203",
            "2240c51d94504dc2a279339cbba9a8e0",
            "dcb364bb50c945e2b3770eb57975204d",
        ]
        exp1_clusters = [
            "cde724cb582f43b4956b1bdae72860ec",
            "ef5ae1bfbf4a4f8e8388d076236a4069",
            "1aaee123c19e49e2af80d5e53d1f76ce",
            "b98f6e8089e245789007186bfe8c9c12",
            "d79cf47218e54495ba21ea59ca54fc57",
            "9dd3961d209a41abac49a36413371d6c",
        ]

        seen_b = set()
        stage_b_ids = []
        for sid in cb_ids + explicit + exp1_clusters:
            if sid not in seen_b:
                seen_b.add(sid)
                stage_b_ids.append(sid)

        # Serialize Stage B sample manifest
        manifest_b_file = out_path / "sample_manifest_stage_b.jsonl"
        with open(manifest_b_file, "w") as f:
            header = {
                "type": "manifest_header",
                "cohort_name": "stage_b_diagnostic_replay",
                "total_samples": len(stage_b_ids),
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            }
            f.write(json.dumps(header) + "\n")
            for sid in stage_b_ids:
                d = docs[sid]
                rec = {
                    "type": "sample_record",
                    "sample_id": sid,
                    "question": d["question"],
                    "gold_answer": d["gold_answer"],
                    "answers": d.get("answers", [d["gold_answer"]]),
                    "source": "cohort_b" if sid in cb_ids else ("explicit" if sid in explicit else "exp1_cluster"),
                    "has_table": "<table" in d["document"].lower(),
                    "has_list": "<ul" in d["document"].lower() or "<ol" in d["document"].lower(),
                }
                f.write(json.dumps(rec) + "\n")

        stage_b_summary = run_stage_b_replay(docs, stage_b_ids, args.model, out_path)
        print(f"Stage B completed cleanly ({stage_b_summary['n_unique_samples']} cases replayed).")

        if args.stage_b_only:
            print("Stage B only requested. Halting.")
            return

    # 4. Stage C
    print("\n[Step 4] Auditing historical exclusions and generating confirmatory manifest...")
    manifest_records, exclusions, manifest_hash = audit_and_generate_manifest(
        docs, out_path, seed=DEFAULT_SEED, allow_resume=args.resume
    )

    print("\n[Step 5] Executing Stage C Confirmatory Evaluation (N=300)...")
    c_records = run_stage_c_confirmatory(
        docs, manifest_records, args.model, out_path, manifest_hash=manifest_hash, allow_resume=args.resume
    )

    print("\n[Step 6] Computing Aggregate Summary & Multiplicity Adjustments...")
    manifest_sids = {r["sample_id"] for r in manifest_records if "sample_id" in r}
    summary = compute_aggregate_summary(
        c_records,
        out_path,
        manifest_sids=manifest_sids,
        allow_overwrite=args.resume,
        enforce_guardrails=True,
    )
    print("=" * 80)
    print("EXPERIMENT 3 COMPLETED SUCCESSFULLY: ALL CONFIRMATORY GUARDRAILS PASSED")
    print("=" * 80)


if __name__ == "__main__":
    main()
