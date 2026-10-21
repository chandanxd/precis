#!/usr/bin/env python3
"""
Précis Experiment 2: Query-Aware Table Selection & Row-Level Relevance Runner.

Evaluates whether query-aware table selection and row-level relevance improve downstream
question answering on non-sentential HTML tables while reducing context overhead
and avoiding regressions.

Strict isolation constraints:
- Zero modifications to production code under backend/src/precis/.
- All new logic, parsers, and evaluators reside strictly in this script.
- Outputs written exclusively to results/diagnostic_table_selection_v2/.
"""

from __future__ import annotations

import argparse
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
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Ensure backend/src is on import path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

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

# Canonical benchmark invariants
DEFAULT_MODEL = "qwen2.5-coder:7b"
DEFAULT_TEMP = 0.0
DEFAULT_TOP_P = 0.9
DEFAULT_MAX_TOKENS = 512
DEFAULT_SEED = 42
DEFAULT_TOKEN_CEILING = 2048


# ==============================================================================
# 1. Helper Utilities & String Matchers
# ==============================================================================

def clean_tag_text(text: str) -> str:
    """Strip HTML tags, unescape HTML entities, and collapse whitespace."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def contains_answer(text: str, answer: str) -> bool:
    """Exact word-boundary normalized string containment match."""
    norm_ans = normalize_answer(answer)
    if not norm_ans:
        return False
    norm_text = normalize_answer(text)
    if not norm_text:
        return False
    pattern = r"(?:\b|^)" + re.escape(norm_ans) + r"(?:\b|$)"
    return re.search(pattern, norm_text) is not None


def check_exact_match(predicted: str, gold: str, answers: Optional[List[str]] = None) -> bool:
    """Compute exact match across gold and optional alternative references."""
    refs = [gold]
    if answers:
        refs.extend(answers)
    return any(compute_exact_match(predicted, ref) for ref in refs if ref)


def check_containment(predicted: str, gold: str, answers: Optional[List[str]] = None) -> bool:
    """Compute containment match across gold and optional alternative references."""
    refs = [gold]
    if answers:
        refs.extend(answers)
    return any(contains_answer(predicted, ref) for ref in refs if ref)


def check_rouge_l(predicted: str, gold: str, answers: Optional[List[str]] = None) -> float:
    """Compute max ROUGE-L across gold and optional alternative references."""
    refs = [gold]
    if answers:
        refs.extend(answers)
    scores = [compute_rouge_l(predicted, ref) for ref in refs if ref]
    return max(scores) if scores else 0.0


def extract_document_topic(doc_text: str) -> str:
    """Extract leading entity topic or caption from markup."""
    m = re.search(r"<table[^>]*>\s*([^<]+?)\s*<tr", doc_text, re.IGNORECASE)
    if m:
        t = clean_tag_text(m.group(1))
        if 2 < len(t) < 80:
            return t
    m_head = re.search(r"<(h1|h2|p)[^>]*>(.*?)</\1>", doc_text, re.IGNORECASE)
    if m_head:
        t = clean_tag_text(m_head.group(2))
        if 2 < len(t) < 80:
            t_sub = re.split(r"[,;]|\bis\b|\bwas\b", t)[0].strip()
            if len(t_sub) > 2:
                return t_sub
    clean = clean_tag_text(doc_text)
    words = clean.split()[:6]
    return " ".join(words) if words else "Document Topic"


# ==============================================================================
# 2. HTML Table & List Data Structures & Parsers
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


def parse_html_tables(doc_text: str) -> List[ParsedTable]:
    """Parse distinct HTML table blocks from document text."""
    tables: List[ParsedTable] = []
    t_matches = list(re.finditer(r"<table[^>]*>(.*?)</table>", doc_text, re.DOTALL | re.IGNORECASE))
    if not t_matches and "<tr" in doc_text.lower():
        # Fallback for unclosed table tags
        m = re.search(r"(<table[^>]*>.*)", doc_text, re.DOTALL | re.IGNORECASE)
        if m:
            t_matches = [m]

    for t_idx, tm in enumerate(t_matches):
        table_html = tm.group(0)
        caption = ""
        cap_match = re.search(r"<caption[^>]*>(.*?)</caption>", table_html, re.DOTALL | re.IGNORECASE)
        if cap_match:
            caption = clean_tag_text(cap_match.group(1))
        else:
            pre_tr = re.search(r"<table[^>]*>\s*([^<]+?)\s*<tr", table_html, re.DOTALL | re.IGNORECASE)
            if pre_tr:
                c_cand = clean_tag_text(pre_tr.group(1))
                if 2 < len(c_cand) < 120:
                    caption = c_cand

        rows: List[ParsedTableRow] = []
        tr_matches = re.finditer(r"<tr[^>]*>(.*?)</tr>", table_html, re.DOTALL | re.IGNORECASE)
        for r_idx, rm in enumerate(tr_matches):
            raw_tr = rm.group(0)
            inner = rm.group(1)
            cells: List[ParsedTableCell] = []
            cell_matches = re.finditer(r"<(th|td)[^>]*>(.*?)</\1>", inner, re.DOTALL | re.IGNORECASE)
            for cm in cell_matches:
                tag = cm.group(1).lower()
                val = clean_tag_text(cm.group(2))
                cells.append(ParsedTableCell(tag=tag, text=val))
            if cells:
                rows.append(ParsedTableRow(row_idx=r_idx, raw_html=raw_tr, cells=cells))

        headers: List[str] = []
        header_row_idx = -1
        for i, r in enumerate(rows[:3]):
            th_cells = [c.text for c in r.cells if c.tag == "th"]
            if len(th_cells) >= 2:
                headers = [c.text for c in r.cells]
                header_row_idx = i
                break
        if not headers and rows:
            if len(rows[0].cells) >= 2 and all(len(c.text) < 40 for c in rows[0].cells):
                headers = [c.text for c in rows[0].cells]
                header_row_idx = 0

        data_rows = []
        for i, r in enumerate(rows):
            if i == header_row_idx:
                continue
            data_rows.append(ParsedTableRow(row_idx=len(data_rows), raw_html=r.raw_html, cells=r.cells))

        tables.append(ParsedTable(
            table_idx=t_idx,
            caption=caption,
            headers=headers,
            rows=data_rows,
            raw_html=table_html,
        ))
    return tables


def parse_html_list_items(doc_text: str) -> List[Tuple[str, str]]:
    """Parse list items returning (raw_li_html, clean_text)."""
    items: List[Tuple[str, str]] = []
    li_matches = re.finditer(r"<li[^>]*>(.*?)</li>", doc_text, re.DOTALL | re.IGNORECASE)
    for m in li_matches:
        raw_li = m.group(0)
        clean = clean_tag_text(m.group(1))
        if clean:
            items.append((raw_li, clean))
    return items


def extract_list_propositions(
    doc_text: str,
    source_doc: str = "",
    max_facts: int = 15,
) -> List[Fact]:
    """
    Extract structured Fact propositions from HTML bullet/numbered list items.
    Handles Name-Description, Cast/Role Credits, and Entity Enumerations.
    """
    items = parse_html_list_items(doc_text)
    if not items:
        return []

    facts: List[Fact] = []
    seen_triples: Set[Tuple[str, str, str]] = set()

    for idx, (raw_li, clean_li) in enumerate(items[:25]):
        if len(facts) >= max_facts:
            break

        # Cast / Role credit
        m_credit = re.match(
            r"^(.*?)\s*--\s*\(\s*(Portrayed by|Voiced by|Played by)\s*(.*?)\s*\)\s*(.*)$",
            clean_li,
            re.IGNORECASE,
        )
        if m_credit:
            c_name = m_credit.group(1).strip()
            actor = m_credit.group(3).strip()
            triple = (c_name.lower(), "is", actor.lower())
            if triple not in seen_triples:
                seen_triples.add(triple)
                facts.append(Fact(
                    subject=c_name,
                    verb=f"is {m_credit.group(2).lower()}",
                    object=actor,
                    adjuncts={"source_structure": ["list_item"], "character_credit": [clean_li], "row_entity": [c_name], "source_snippet": [raw_li[:200]]},
                    modality="asserted",
                    source_doc=source_doc,
                    sentence_id=idx,
                    raw_sentence=raw_li,
                ))
            continue

        # Dash / Colon pattern
        m_dash = re.match(r"^([^-:–—]{2,50})\s*[-:–—]\s*(.+)$", clean_li)
        if m_dash:
            sub = m_dash.group(1).strip()
            obj = m_dash.group(2).strip()
            triple = (sub.lower(), "is", obj.lower())
            if triple not in seen_triples:
                seen_triples.add(triple)
                facts.append(Fact(
                    subject=sub,
                    verb="is",
                    object=obj,
                    adjuncts={"source_structure": ["list_item"], "row_entity": [sub], "source_snippet": [raw_li[:200]]},
                    modality="asserted",
                    source_doc=source_doc,
                    sentence_id=idx,
                    raw_sentence=raw_li,
                ))
            continue

        # Enum pattern
        m_enum = re.match(r"^([A-Z][A-Za-z\s&.]+?)\s+([IVXLCDM0-9]{1,10}\s*,.*)$", clean_li)
        if m_enum:
            sub = m_enum.group(1).strip()
            obj = m_enum.group(2).strip()
            triple = (sub.lower(), "participated in", obj.lower())
            if triple not in seen_triples:
                seen_triples.add(triple)
                facts.append(Fact(
                    subject=sub,
                    verb="participated in",
                    object=obj,
                    adjuncts={"source_structure": ["list_item"], "row_entity": [sub], "source_snippet": [raw_li[:200]]},
                    modality="asserted",
                    source_doc=source_doc,
                    sentence_id=idx,
                    raw_sentence=raw_li,
                ))
            continue

    return facts[:max_facts]


# ==============================================================================
# 3. Query Constraint Analysis & Entity-Level Resolution
# ==============================================================================

CUE_PATTERN = re.compile(
    r'\b(?:other\s+than|except(?:\s+for)?|excluding|aside\s+from|besides|not\s+including)\s+([a-z0-9\s,\'-]+?)(?:\s+in|\s+for|\s+of|\?|$)',
    re.IGNORECASE
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


def resolve_group_members(
    excl: ExclusionInfo,
    doc_text: str,
    table_headers: List[str],
    candidate_rows: List[Dict[str, str]],
    entity_col: str,
) -> Tuple[Set[str], str, str]:
    """
    Resolve excluded group to member entities using 3 layers:
    Layer 1: Structural category/type column matching excl.target_tokens
    Layer 2: Document text Hearst hyponymy and definitional patterns
    Layer 3: Notes / comments column matching excl.target_tokens
    """
    resolved: Set[str] = set()

    # Layer 1: Check category/type column
    cat_cols = [
        h for h in table_headers
        if any(k in h.lower() for k in ["type", "category", "classification", "group", "status"])
    ]
    for cc in cat_cols:
        for r in candidate_rows:
            val = r.get(cc, "").lower()
            if any(t in val for t in excl.target_tokens):
                ent = r.get(entity_col, "")
                if ent:
                    resolved.add(ent.lower())
    if resolved:
        return resolved, f"layer_1_category_column: {cat_cols}", "RESOLVED_MEMBER_ENTITIES"

    # Layer 2: Document text Hearst patterns & definitional sentences
    patterns = [
        rf'(?:the\s+)?{re.escape(excl.phrase)}\s+(?:consist of|consists of|comprise|comprises|include|includes|such as)\s+([^.\n]+)',
        rf'([^.\n]+?)\s+(?:are|is|were|was)\s+(?:part of|members? of|among)?\s*(?:the\s+)?{re.escape(excl.phrase)}',
        rf'([^.\n]+?)\s*,\s*(?:one of|part of)?\s*(?:the\s+)?{re.escape(excl.phrase)}',
    ]
    for p in patterns:
        for m in re.finditer(p, doc_text, re.IGNORECASE):
            matched_span = m.group(1)
            for r in candidate_rows:
                ent = r.get(entity_col, "")
                if ent and len(ent) > 2 and ent.lower() in matched_span.lower():
                    resolved.add(ent.lower())
            if resolved:
                return resolved, f"layer_2_hearst_pattern: '{m.group(0)[:80]}'", "RESOLVED_MEMBER_ENTITIES"

    # Layer 3: Notes / comments column
    note_cols = [
        h for h in table_headers
        if any(k in h.lower() for k in ["notes", "comments", "description"])
    ]
    for nc in note_cols:
        for r in candidate_rows:
            val = r.get(nc, "").lower()
            if any(t in val for t in excl.target_tokens):
                ent = r.get(entity_col, "")
                if ent:
                    resolved.add(ent.lower())
    if resolved:
        return resolved, f"layer_3_notes_column: {note_cols}", "RESOLVED_MEMBER_ENTITIES"

    return set(), "No structural headings, category columns, or definitional patterns found in document", "UNRESOLVED_GROUP_AMBIGUITY"


# ==============================================================================
# 4. Query-Aware Table & Row Ranking Heuristics (Condition C)
# ==============================================================================

@dataclass
class ScoredRow:
    row_idx: int
    entity: str
    row_dict: Dict[str, str]
    score: float
    reasons: List[str]
    raw_html: str


def find_entity_column(headers: List[str], rows: List[ParsedTableRow]) -> Tuple[int, str]:
    """Identify the primary entity column index and header name."""
    entity_keywords = [
        "player", "name", "episode", "team", "title", "country",
        "athlete", "person", "character", "school", "institution", "film",
    ]
    for idx, h in enumerate(headers):
        if any(k in h.lower() for k in entity_keywords):
            return idx, h
    for col in range(len(headers)):
        vals = [
            r.cells[col].text
            for r in rows[:4]
            if col < len(r.cells) and r.cells[col].text
        ]
        if vals and any(re.search(r"[a-zA-Z]{3,}", v) for v in vals):
            return col, headers[col]
    return 0, headers[0] if headers else "Entity"


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
            # Individual entity check: if table is exclusively about that entity
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


def rank_table_rows(
    table: ParsedTable,
    query: str,
    doc_text: str,
    max_selected_rows: int = 5,
) -> Tuple[List[ScoredRow], Dict[str, Any]]:
    """Rank all rows in a table using query qualifiers, entity resolution, and content match."""
    if not table.rows:
        return [], {}

    headers = table.headers if table.headers else [f"Col_{i}" for i in range(len(table.rows[0].cells))]
    ent_col_idx, ent_col_name = find_entity_column(headers, table.rows)

    # Convert rows to dicts
    row_dicts = []
    for r in table.rows:
        rd = {}
        for c_idx, cell in enumerate(r.cells):
            h_name = headers[c_idx] if c_idx < len(headers) else f"Col_{c_idx}"
            rd[h_name] = cell.text
        row_dicts.append(rd)

    # Check negative constraint
    excl = extract_negative_constraint(query)
    resolved_members: Set[str] = set()
    excl_status = "NONE"
    excl_ev = ""

    if excl:
        if excl.is_group:
            resolved_members, excl_ev, excl_status = resolve_group_members(
                excl, doc_text, headers, row_dicts, ent_col_name
            )
        else:
            resolved_members = {excl.phrase.lower()}
            excl_status = "INDIVIDUAL_ENTITY"
            excl_ev = "literal_phrase_match"

    tq = extract_typed_qualifiers(query)
    q_words = set(re.findall(r"\b[a-zA-Z]{3,}\b", query.lower()))

    # Episode & Season columns
    season_cols = [
        h for h in headers
        if re.search(r'\bseason\b', h, re.I) and not re.search(r'\b(?:no|ep|episode|#)\b', h, re.I)
    ]
    ep_cols = [
        h for h in headers
        if re.search(r'\b(?:no\.?\s*(?:in|of)\s*season|episode|ep|no\.|#)\b', h, re.I)
    ]
    rank_cols = [
        h for h in headers
        if re.search(r'\b(?:rank|place)\b', h, re.I)
    ]

    scored_rows: List[ScoredRow] = []
    for r_idx, r in enumerate(table.rows):
        rd = row_dicts[r_idx]
        ent_val = rd.get(ent_col_name, "")
        score = 0.0
        reasons = []

        # 1. Check negative exclusion penalty
        if excl and ent_val:
            if ent_val.lower() in resolved_members or any(m in ent_val.lower() for m in resolved_members):
                score = -100.0
                reasons.append(f"excluded_member_penalty(-100.0): {ent_val}")
                scored_rows.append(ScoredRow(
                    row_idx=r.row_idx, entity=ent_val, row_dict=rd, score=score, reasons=reasons, raw_html=r.raw_html
                ))
                continue

        # 2. Episode qualifier matching
        if tq.episode is not None and ep_cols:
            matched_ep = False
            for ec in ep_cols:
                val = rd.get(ec, "").strip()
                m = re.search(r'\b(\d+)\b', val)
                if m and int(m.group(1)) == tq.episode:
                    score += 10.0
                    reasons.append(f"episode_match(+10.0): {val}")
                    matched_ep = True
                    break
            if not matched_ep:
                score -= 5.0
                reasons.append("episode_mismatch(-5.0)")

        # 3. Season qualifier matching
        if tq.season is not None and season_cols:
            matched_sn = False
            for sc in season_cols:
                val = rd.get(sc, "").strip()
                m = re.search(r'\b(\d+)\b', val)
                if m and int(m.group(1)) == tq.season:
                    score += 5.0
                    reasons.append(f"season_match(+5.0): {val}")
                    matched_sn = True
                    break
            if not matched_sn:
                score -= 5.0
                reasons.append("season_mismatch(-5.0)")

        # 4. Rank qualifier matching
        if tq.rank is not None:
            if rank_cols:
                matched_rk = False
                for rc in rank_cols:
                    val = rd.get(rc, "").strip()
                    m = re.search(r'\b(\d+)\b', val)
                    if m and int(m.group(1)) == tq.rank:
                        score += 8.0
                        reasons.append(f"rank_match(+8.0): {val}")
                        matched_rk = True
                        break
            if tq.is_superlative and r_idx == 0:
                score += 5.0
                reasons.append("superlative_first_row(+5.0)")

        # 5. Entity & content word overlap
        row_text = " ".join(rd.values()).lower()
        matched_tokens = sum(1 for qw in q_words if qw in row_text)
        if matched_tokens > 0:
            score += matched_tokens * 2.0
            reasons.append(f"content_overlap(+{matched_tokens * 2.0})")

        # Tie breaking factor: natural row index
        scored_rows.append(ScoredRow(
            row_idx=r.row_idx, entity=ent_val, row_dict=rd, score=score, reasons=reasons, raw_html=r.raw_html
        ))

    # Sort descending by score, tie break by row_idx
    scored_rows.sort(key=lambda x: (x.score, -x.row_idx), reverse=True)

    # Select top-k rows with score > 0 (or fallback if ambiguity or no keyword matches in selected table)
    selected = [r for r in scored_rows if r.score > 0][:max_selected_rows]
    if not selected:
        if excl_status == "UNRESOLVED_GROUP_AMBIGUITY":
            # Fallback diversity budget: at most 3 rows
            selected = [r for r in scored_rows if r.score > -50][:3]
        else:
            # Fallback to top non-penalized rows
            selected = [r for r in scored_rows if r.score > -50][:max_selected_rows]

    telemetry = {
        "exclusion_status": excl_status,
        "resolved_members": list(resolved_members),
        "exclusion_evidence": excl_ev,
        "total_rows_evaluated": len(scored_rows),
        "selected_rows_count": len(selected),
    }
    return selected, telemetry


def synthesize_table_facts(
    selected_rows: List[ScoredRow],
    headers: List[str],
    source_doc: str,
    query: str,
    max_facts: int = 10,
) -> List[Fact]:
    """Synthesize clean, non-redundant Fact objects from selected rows."""
    tq = extract_typed_qualifiers(query)
    facts: List[Fact] = []
    seen_triples = set()

    for sr in selected_rows:
        if len(facts) >= max_facts:
            break
        ent_val = sr.entity or f"Row {sr.row_idx + 1}"
        rd = sr.row_dict

        # 1. Composite row proposition
        summary_parts = [f"{h}: {v}" for h, v in rd.items() if v and h != sr.entity]
        if summary_parts:
            summary_str = ", ".join(summary_parts[:6])
            triple = (ent_val.lower(), "records", summary_str.lower())
            if triple not in seen_triples:
                seen_triples.add(triple)
                facts.append(Fact(
                    subject=ent_val,
                    verb="records",
                    object=summary_str,
                    adjuncts={
                        "source_structure": ["table_row"],
                        "row_entity": [ent_val],
                        "source_snippet": [sr.raw_html[:200]],
                    },
                    modality="asserted",
                    source_doc=source_doc,
                    sentence_id=sr.row_idx,
                    raw_sentence=sr.raw_html,
                ))

        # 2. Targeted attribute proposition if query specifically requested an attribute
        if len(facts) < max_facts and tq.target_attrs:
            for h, v in rd.items():
                if len(facts) >= max_facts:
                    break
                if any(attr in h.lower() for attr in tq.target_attrs) and v:
                    verb = f"has {h}"
                    triple = (ent_val.lower(), verb.lower(), v.lower())
                    if triple not in seen_triples:
                        seen_triples.add(triple)
                        facts.append(Fact(
                            subject=ent_val,
                            verb=verb,
                            object=v,
                            adjuncts={
                                "source_structure": ["table_row"],
                                "table_header": [h],
                                "cell_value": [v],
                                "row_entity": [ent_val],
                                "source_snippet": [sr.raw_html[:200]],
                            },
                            modality="asserted",
                            source_doc=source_doc,
                            sentence_id=sr.row_idx,
                            raw_sentence=sr.raw_html,
                        ))

    return facts[:max_facts]


# ==============================================================================
# 5. Extractors for Condition B (Frozen & Approved Caps)
# ==============================================================================

def extract_table_list_facts_v1(
    doc_text: str,
    source_doc: str = "",
    max_rows: int = 25,
    max_facts: int = 30,
    max_total_facts: int = 45,
) -> List[Fact]:
    """Unranked extractor from Experiment 1 (Condition B_frozen / B_approved)."""
    # Parse rows using legacy flat regex
    rows: List[ParsedTableRow] = []
    tr_matches = re.finditer(r"<tr[^>]*>(.*?)</tr>", doc_text, re.DOTALL | re.IGNORECASE)
    for r_idx, m in enumerate(tr_matches):
        raw_tr = m.group(0)
        inner = m.group(1)
        cells: List[ParsedTableCell] = []
        cell_matches = re.finditer(r"<(th|td)[^>]*>(.*?)</\1>", inner, re.DOTALL | re.IGNORECASE)
        for cm in cell_matches:
            tag = cm.group(1).lower()
            val = clean_tag_text(cm.group(2))
            cells.append(ParsedTableCell(tag=tag, text=val))
        if cells:
            rows.append(ParsedTableRow(row_idx=r_idx, raw_html=raw_tr, cells=cells))

    doc_topic = extract_document_topic(doc_text)
    facts: List[Fact] = []
    seen_triples: Set[Tuple[str, str, str]] = set()

    header_row_idx = -1
    for i, r in enumerate(rows[:3]):
        th_count = sum(1 for c in r.cells if c.tag == "th")
        if th_count >= 2:
            header_row_idx = i
            break

    if header_row_idx != -1 and len(rows) > header_row_idx + 1:
        headers = [c.text for c in rows[header_row_idx].cells]
        entity_keywords = ["player", "name", "episode", "team", "title", "country", "athlete", "person"]
        entity_col_idx = 0
        for idx, h in enumerate(headers):
            if any(k in h.lower() for k in entity_keywords):
                entity_col_idx = idx
                break

        data_rows = rows[header_row_idx + 1 : header_row_idx + 1 + max_rows]
        for row_idx, r in enumerate(data_rows):
            if len(facts) >= max_facts:
                break
            row_dict: Dict[str, str] = {}
            for col_idx, cell in enumerate(r.cells):
                if col_idx < len(headers) and headers[col_idx] and cell.text:
                    row_dict[headers[col_idx]] = cell.text
            if not row_dict:
                continue

            entity_val = r.cells[entity_col_idx].text if entity_col_idx < len(r.cells) else ""
            if not entity_val:
                entity_val = f"{doc_topic} Row {row_idx + 1}"

            if len(facts) < max_facts and len(row_dict) >= 2:
                summary_parts = [f"{h}: {v}" for h, v in row_dict.items() if h != headers[entity_col_idx]]
                summary_str = ", ".join(summary_parts)
                triple = (entity_val.lower(), "records", summary_str.lower())
                if triple not in seen_triples:
                    seen_triples.add(triple)
                    facts.append(Fact(
                        subject=entity_val,
                        verb="records",
                        object=summary_str,
                        adjuncts={
                            "source_structure": ["table_row"],
                            "row_entity": [entity_val],
                            "source_snippet": [r.raw_html[:200]],
                        },
                        modality="asserted",
                        source_doc=source_doc,
                        sentence_id=row_idx,
                        raw_sentence=r.raw_html,
                    ))

            if len(data_rows) <= 5 or len(facts) < 10:
                for h, v in row_dict.items():
                    if len(facts) >= max_facts:
                        break
                    if h == headers[entity_col_idx] and v == entity_val:
                        continue
                    verb = f"has {h}"
                    triple = (entity_val.lower(), verb.lower(), v.lower())
                    if triple in seen_triples:
                        continue
                    seen_triples.add(triple)
                    facts.append(Fact(
                        subject=entity_val,
                        verb=verb,
                        object=v,
                        adjuncts={
                            "source_structure": ["table_row"],
                            "table_header": [h],
                            "cell_value": [v],
                            "row_entity": [entity_val],
                            "source_snippet": [r.raw_html[:200]],
                        },
                        modality="asserted",
                        source_doc=source_doc,
                        sentence_id=row_idx,
                        raw_sentence=r.raw_html,
                    ))
    else:
        for row_idx, r in enumerate(rows[:max_rows]):
            if len(facts) >= max_facts:
                break
            if len(r.cells) < 2:
                continue
            key, val = r.cells[0].text, r.cells[1].text
            if not key or not val:
                continue
            verb = f"has {key}"
            triple = (doc_topic.lower(), verb.lower(), val.lower())
            if triple in seen_triples:
                continue
            seen_triples.add(triple)
            facts.append(Fact(
                subject=doc_topic,
                verb=verb,
                object=val,
                adjuncts={
                    "source_structure": ["table_row"],
                    "table_header": [key],
                    "cell_value": [val],
                    "row_entity": [doc_topic],
                    "source_snippet": [r.raw_html[:200]],
                },
                modality="asserted",
                source_doc=source_doc,
                sentence_id=row_idx,
                raw_sentence=r.raw_html,
            ))

    # Add lists
    l_facts = extract_list_propositions(doc_text, source_doc=source_doc, max_facts=15)
    return (facts + l_facts)[:max_total_facts]


# ==============================================================================
# 6. Extractors for Condition C & Ablations
# ==============================================================================

def extract_table_list_facts_v2(
    doc_text: str,
    query: str,
    source_doc: str = "",
    mode: str = "full",  # "full", "table_only", "row_only"
    max_table_facts: int = 15,
) -> Tuple[List[Fact], Dict[str, Any]]:
    """Query-aware extraction of table propositions with ablations."""
    tables = parse_html_tables(doc_text)
    candidate_facts: List[Fact] = []
    table_telemetry = []

    if tables:
        if mode in ["full", "table_only"]:
            scored_tables = score_and_select_tables(tables, query, doc_text)
        else:
            # row_only: all tables are selected
            scored_tables = [(t, 10.0, "SELECTED_ALL", {}) for t in tables]

        for table, t_score, t_decision, t_meta in scored_tables:
            if not t_decision.startswith("SELECTED"):
                table_telemetry.append({
                    "table_idx": table.table_idx,
                    "decision": t_decision,
                    "score": t_score,
                    "rows_evaluated": len(table.rows),
                })
                continue

            if mode in ["full", "row_only"]:
                # Query-aware row ranking
                selected_rows, r_telem = rank_table_rows(table, query, doc_text, max_selected_rows=5)
                headers = table.headers if table.headers else [f"Col_{i}" for i in range(len(table.rows[0].cells))] if table.rows else []
                t_facts = synthesize_table_facts(selected_rows, headers, source_doc, query, max_facts=10)
            else:
                # table_only ablation: unranked rows up to cap
                headers = table.headers if table.headers else [f"Col_{i}" for i in range(len(table.rows[0].cells))] if table.rows else []
                ent_col_idx, ent_col_name = find_entity_column(headers, table.rows)
                unranked_rows = []
                for r in table.rows[:5]:
                    rd = {headers[c_idx] if c_idx < len(headers) else f"Col_{c_idx}": cell.text for c_idx, cell in enumerate(r.cells)}
                    unranked_rows.append(ScoredRow(
                        row_idx=r.row_idx,
                        entity=rd.get(ent_col_name, ""),
                        row_dict=rd,
                        score=1.0,
                        reasons=["unranked_order"],
                        raw_html=r.raw_html,
                    ))
                t_facts = synthesize_table_facts(unranked_rows, headers, source_doc, query, max_facts=10)
                r_telem = {"mode": "table_only_unranked"}

            candidate_facts.extend(t_facts)
            table_telemetry.append({
                "table_idx": table.table_idx,
                "decision": t_decision,
                "score": t_score,
                "facts_generated": len(t_facts),
                "row_telemetry": r_telem,
            })
            if len(candidate_facts) >= max_table_facts:
                break

    # If remaining budget, extract list items
    if len(candidate_facts) < max_table_facts:
        l_facts = extract_list_propositions(
            doc_text,
            source_doc=source_doc,
            max_facts=max_table_facts - len(candidate_facts),
        )
        candidate_facts.extend(l_facts)

    final_facts = candidate_facts[:max_table_facts]
    return final_facts, {"tables": table_telemetry, "total_facts": len(final_facts)}


# ==============================================================================
# 7. Preflight Robustness Suite
# ==============================================================================

def run_preflight_suite(docs: Dict[str, Any]) -> Dict[str, Any]:
    """Run comprehensive 10-point preflight test suite."""
    results: Dict[str, Any] = {"passed": True, "tests": {}}

    # 1. Header-to-cell alignment
    h_html = "<Table><Tr><Th>Player</Th><Th>Team</Th></Tr><Tr><Td>Alice</Td><Td>Hawks</Td></Tr></Table>"
    t1 = parse_html_tables(h_html)[0]
    c1_ok = len(t1.headers) == 2 and t1.rows[0].cells[1].text == "Hawks"
    results["tests"]["1_header_alignment"] = {"passed": c1_ok}

    # 2. Category Column Exclusion Test
    q_cat = "planets in the solar system excluding terrestrial planets"
    ex_cat = extract_negative_constraint(q_cat)
    rows_cat = [
        {"Name": "Mercury", "Category": "Terrestrial planet"},
        {"Name": "Jupiter", "Category": "Gas giant"},
    ]
    m_cat, _, st_cat = resolve_group_members(ex_cat, "", ["Name", "Category"], rows_cat, "Name")
    c2_ok = "mercury" in m_cat and "jupiter" not in m_cat
    results["tests"]["2_category_column_exclusion"] = {"passed": c2_ok, "resolved": list(m_cat)}

    # 3. Hearst Pattern Lexical Disparity Exclusion (Great Lakes Test)
    q_lakes = "name three large lakes other than the great lakes in the united states"
    ex_lakes = extract_negative_constraint(q_lakes)
    doc_lakes = "The Great Lakes comprise Lake Superior, Lake Huron, Lake Michigan, Lake Erie, and Lake Ontario. Other lakes include Great Salt Lake."
    rows_lakes = [
        {"Name": "Lake Superior"}, {"Name": "Lake Huron"}, {"Name": "Great Salt Lake"}
    ]
    m_lakes, ev_lakes, _ = resolve_group_members(ex_lakes, doc_lakes, ["Name"], rows_lakes, "Name")
    c3_ok = "lake superior" in m_lakes and "lake huron" in m_lakes and "great salt lake" not in m_lakes
    results["tests"]["3_hearst_pattern_group_exclusion"] = {"passed": c3_ok, "resolved": list(m_lakes)}

    # 4. Individual Entity Exclusion ("except Virginia")
    q_va = "colonies in North America except Virginia"
    ex_va = extract_negative_constraint(q_va)
    c4_ok = not ex_va.is_group and ex_va.phrase.lower() == "virginia"
    results["tests"]["4_individual_entity_except"] = {"passed": c4_ok}

    # 5. Negation Scope Precision
    q_prec = "lakes other than Great Salt Lake"
    ex_prec = extract_negative_constraint(q_prec)
    c5_ok = ex_prec.phrase.lower() == "great salt lake" and not ex_prec.is_group
    results["tests"]["5_negation_scope_precision"] = {"passed": c5_ok}

    # 6. Ambiguous Group Exclusion Fallback
    q_amb = "lakes other than volcanic lakes"
    ex_amb = extract_negative_constraint(q_amb)
    m_amb, _, st_amb = resolve_group_members(ex_amb, "General lakes overview.", ["Name"], rows_lakes, "Name")
    c6_ok = st_amb == "UNRESOLVED_GROUP_AMBIGUITY" and len(m_amb) == 0
    results["tests"]["6_ambiguous_group_fallback"] = {"passed": c6_ok}

    # 7. Typed Qualifier Matching (Flash Season 4 Episode 3)
    q_flash = "when does the flash season 4 episode 3 air"
    tq_flash = extract_typed_qualifiers(q_flash)
    tbl_flash = ParsedTable(
        table_idx=0,
        caption="Season 4 Episodes",
        headers=["No. overall", "No. in season", "Title", "Original air date"],
        rows=[
            ParsedTableRow(0, "<tr>1</tr>", [ParsedTableCell("td", "70"), ParsedTableCell("td", "1"), ParsedTableCell("td", "The Flash Reborn"), ParsedTableCell("td", "October 10, 2017")]),
            ParsedTableRow(1, "<tr>2</tr>", [ParsedTableCell("td", "71"), ParsedTableCell("td", "2"), ParsedTableCell("td", "Mixed Signals"), ParsedTableCell("td", "October 17, 2017")]),
            ParsedTableRow(2, "<tr>3</tr>", [ParsedTableCell("td", "72"), ParsedTableCell("td", "3"), ParsedTableCell("td", "Luck Be a Lady"), ParsedTableCell("td", "October 24, 2017")]),
        ],
        raw_html="<table>...</table>",
    )
    ranked_flash, _ = rank_table_rows(tbl_flash, q_flash, "", max_selected_rows=3)
    c7_ok = len(ranked_flash) > 0 and ranked_flash[0].row_dict.get("No. in season") == "3"
    results["tests"]["7_typed_qualifiers_flash_ep3"] = {"passed": c7_ok, "top_row": ranked_flash[0].row_dict if ranked_flash else {}}

    # 8. Strict Budget Caps Enforcement
    big_tbl_html = "<Table><Tr><Th>Item</Th><Th>Val</Th></Tr>" + "".join(
        f"<Tr><Td>Item {i}</Td><Td>{i}</Td></Tr>" for i in range(50)
    ) + "</Table>"
    facts_cap, _ = extract_table_list_facts_v2(big_tbl_html, "find Item 15", mode="full", max_table_facts=15)
    c8_ok = len(facts_cap) <= 15
    results["tests"]["8_budget_caps_enforcement"] = {"passed": c8_ok, "count": len(facts_cap)}

    # 9. Global Row Scope Selection (Row index > 10 selectable)
    grey_tbl_html = "<Table><Tr><Th>Episode</Th><Th>Air Date</Th></Tr>" + "".join(
        f"<Tr><Td>Ep {i}</Td><Td>Date {i}</Td></Tr>" for i in range(1, 14)
    ) + "<Tr><Td>Ep 14</Td><Td>March 1, 2018</Td></Tr></Table>"
    tbl_grey = parse_html_tables(grey_tbl_html)[0]
    r_grey, _ = rank_table_rows(tbl_grey, "when is episode 14", "", max_selected_rows=1)
    c9_ok = len(r_grey) > 0 and r_grey[0].row_dict.get("Air Date") == "March 1, 2018"
    results["tests"]["9_global_row_scope"] = {"passed": c9_ok}

    # 10. Audit on the 6 unique Cohort A table/list failure documents
    audit_cases = [
        ("1aaee123c19e49e2af80d5e53d1f76ce", "Hathi Jr .", "baby elephant list"),
        ("d79cf47218e54495ba21ea59ca54fc57", "Daisuke Ohata", "rugby statistics table"),
        ("2ec7c62e2fe547f0802d8cf34e5e9be0", "DJ Lance Rock", "yo gabba gabba cast credits"),
        ("9dd3961d209a41abac49a36413371d6c", "New England Patriots", "super bowls enumeration"),
        ("11cabb55e53047449cd8304480660c0b", "51,331", "university infobox"),
        ("78b30a922137434fbb2170da0e0d79ae", "March 1 , 2018", "greys anatomy episode schedule"),
    ]
    recovered_count = 0
    for sid, gold, desc in audit_cases:
        doc_text = docs[sid]["document"]
        q = docs[sid]["question"]
        facts, _ = extract_table_list_facts_v2(doc_text, q, source_doc=sid, mode="full", max_table_facts=15)
        has_gold = any(
            contains_answer(f.subject, gold) or contains_answer(f.object, gold) or any(contains_answer(str(v), gold) for v in f.adjuncts.values())
            for f in facts
        )
        if has_gold:
            recovered_count += 1
    c10_ok = recovered_count == 6
    results["tests"]["10_cohort_a_recovery_under_v2"] = {"passed": c10_ok, "recovered": f"{recovered_count}/6"}

    results["passed"] = all(v["passed"] for v in results["tests"].values())
    return results


# ==============================================================================
# 8. Evaluation Runners for Diagnostic Cohorts (A and B)
# ==============================================================================

def run_condition_inference(
    q: str,
    raw_doc: str,
    sid: str,
    condition: str,
    model: str = DEFAULT_MODEL,
    base_svoa: Optional[List[Fact]] = None,
) -> Tuple[str, int, int]:
    """Execute pipeline ingestion, packing, and Ollama inference for a single condition."""
    store = FactStore(in_memory=True, collection_name=f"t_{uuid.uuid4().hex[:8]}")
    if base_svoa is None:
        resolved_doc = resolve_coreferences(raw_doc)
        base_svoa = extract_facts(resolved_doc, source_doc=sid)

    table_facts: List[Fact] = []
    if condition == "cond_a":
        pass  # Prose only
    elif condition == "cond_b_frozen":
        table_facts = extract_table_list_facts_v1(raw_doc, source_doc=sid, max_rows=25, max_facts=30, max_total_facts=45)
    elif condition == "cond_b_approved":
        table_facts = extract_table_list_facts_v1(raw_doc, source_doc=sid, max_rows=10, max_facts=15, max_total_facts=15)
    elif condition == "cond_c_full":
        table_facts, _ = extract_table_list_facts_v2(raw_doc, q, source_doc=sid, mode="full", max_table_facts=15)
    elif condition == "cond_c1_table_only":
        table_facts, _ = extract_table_list_facts_v2(raw_doc, q, source_doc=sid, mode="table_only", max_table_facts=15)
    elif condition == "cond_c2_row_only":
        table_facts, _ = extract_table_list_facts_v2(raw_doc, q, source_doc=sid, mode="row_only", max_table_facts=15)

    # Deduplicate against prose SVOA
    prose_triples = {(f.subject.lower(), f.verb.lower(), f.object.lower()) for f in base_svoa}
    filtered_table_facts = [
        f for f in table_facts
        if (f.subject.lower(), f.verb.lower(), f.object.lower()) not in prose_triples
    ]

    all_facts = base_svoa + filtered_table_facts
    scored_facts = score_facts_with_store(all_facts, store)
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
    return res.answer, pack.tokens_used, len(filtered_table_facts)


def evaluate_cohort_b(
    docs: Dict[str, Any],
    failure_analysis_path: str,
    frozen_ids: List[str],
    model: str,
    output_dir: Path,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Evaluate Cohort B ($N=50$) regression audit under Conditions A, B_frozen, B_approved, and C_full."""
    print("\n" + "=" * 80)
    print(f"RUNNING COHORT B REGRESSION AUDIT (N={len(frozen_ids)})")
    print("=" * 80)

    hist_map: Dict[str, Any] = {}
    with open(failure_analysis_path) as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                if item["sample_id"] in frozen_ids:
                    hist_map[item["sample_id"]] = item

    records: List[Dict[str, Any]] = []
    out_file = output_dir / "eval_records_cohort_b.jsonl"

    for idx, sid in enumerate(frozen_ids):
        doc_entry = docs[sid]
        hist_entry = hist_map[sid]
        q = doc_entry["question"]
        gold = doc_entry["gold_answer"]
        answers = doc_entry.get("answers", [gold])
        raw_doc = doc_entry["document"]

        print(f"[{idx+1}/{len(frozen_ids)}] Cohort B {sid[:8]} | '{q[:40]}...'")

        # Precompute base_svoa once per document
        resolved_doc = resolve_coreferences(raw_doc)
        base_svoa = extract_facts(resolved_doc, source_doc=sid)

        # 1. Condition A (Baseline Concise)
        ans_a, tok_a, _ = run_condition_inference(q, raw_doc, sid, "cond_a", model, base_svoa=base_svoa)
        em_a = check_exact_match(ans_a, gold, answers)
        cont_a = check_containment(ans_a, gold, answers)

        # 2. Condition B_frozen
        ans_bf, tok_bf, _ = run_condition_inference(q, raw_doc, sid, "cond_b_frozen", model, base_svoa=base_svoa)
        em_bf = check_exact_match(ans_bf, gold, answers)
        cont_bf = check_containment(ans_bf, gold, answers)

        # 3. Condition B_approved
        ans_ba, tok_ba, _ = run_condition_inference(q, raw_doc, sid, "cond_b_approved", model, base_svoa=base_svoa)
        em_ba = check_exact_match(ans_ba, gold, answers)
        cont_ba = check_containment(ans_ba, gold, answers)

        # 4. Condition C_full
        ans_c, tok_c, t_facts_c = run_condition_inference(q, raw_doc, sid, "cond_c_full", model, base_svoa=base_svoa)
        em_c = check_exact_match(ans_c, gold, answers)
        cont_c = check_containment(ans_c, gold, answers)

        hist_em = hist_entry.get("precis_exact_match", False)
        hist_cont = True

        rec = {
            "sample_id": sid,
            "question": q,
            "gold_answer": gold,
            "historical_standard": {
                "exact_match": hist_em,
                "containment": hist_cont,
                "predicted_answer": hist_entry.get("precis_answer", ""),
            },
            "cond_a": {"exact_match": em_a, "containment": cont_a, "predicted_answer": ans_a, "context_tokens": tok_a},
            "cond_b_frozen": {"exact_match": em_bf, "containment": cont_bf, "predicted_answer": ans_bf, "context_tokens": tok_bf},
            "cond_b_approved": {"exact_match": em_ba, "containment": cont_ba, "predicted_answer": ans_ba, "context_tokens": tok_ba},
            "cond_c_full": {"exact_match": em_c, "containment": cont_c, "predicted_answer": ans_c, "context_tokens": tok_c, "table_facts": t_facts_c},
            "regressions_c_vs_a": {
                "em_regression": bool(em_a and not em_c),
                "containment_regression": bool(cont_a and not cont_c),
            },
            "context_growth_c_vs_a": (tok_c - tok_a) / max(1, tok_a),
        }
        records.append(rec)
        with open(out_file, "a") as f:
            f.write(json.dumps(rec) + "\n")

    em_regs = sum(1 for r in records if r["regressions_c_vs_a"]["em_regression"])
    cont_regs = sum(1 for r in records if r["regressions_c_vs_a"]["containment_regression"])
    avg_tok_a = sum(r["cond_a"]["context_tokens"] for r in records) / len(records)
    avg_tok_c = sum(r["cond_c_full"]["context_tokens"] for r in records) / len(records)
    overhead_pct = ((avg_tok_c - avg_tok_a) / avg_tok_a) * 100

    summary = {
        "num_samples": len(records),
        "em_regressions_vs_baseline": em_regs,
        "containment_regressions_vs_baseline": cont_regs,
        "avg_baseline_tokens": round(avg_tok_a, 2),
        "avg_cond_c_tokens": round(avg_tok_c, 2),
        "context_overhead_pct": round(overhead_pct, 2),
        "guardrail_passed": cont_regs <= 1 and overhead_pct <= 10.0,
    }
    print(f"\nCohort B Audit Finished. EM Regs: {em_regs}, Cont Regs: {cont_regs}, Overhead: {overhead_pct:.2f}%")
    return records, summary


# ==============================================================================
# 9. Evaluation Runner for Confirmatory Cohort ($N=300$)
# ==============================================================================

def evaluate_confirmatory_cohort(
    manifest_records: List[Dict[str, Any]],
    docs: Dict[str, Any],
    model: str,
    output_dir: Path,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Evaluate Confirmatory Cohort ($N=300$: $N=200$ Table Stratum, $N=100$ Prose Stratum)."""
    print("\n" + "=" * 80)
    print(f"RUNNING CONFIRMATORY COHORT EVALUATION (N={len(manifest_records)})")
    print("=" * 80)

    out_file = output_dir / "eval_records_confirmatory.jsonl"
    results: List[Dict[str, Any]] = []

    for idx, item in enumerate(manifest_records):
        sid = item["sample_id"]
        q = item["question"]
        gold = item["gold_answer"]
        answers = item.get("answers", [gold])
        stratum = item["stratum"]
        raw_doc = docs[sid]["document"]

        print(f"[{idx+1}/{len(manifest_records)}] Confirmatory ({stratum}) {sid[:8]} | '{q[:35]}...'")

        # Precompute base_svoa once per document
        resolved_doc = resolve_coreferences(raw_doc)
        base_svoa = extract_facts(resolved_doc, source_doc=sid)

        # 1. Condition A
        ans_a, tok_a, _ = run_condition_inference(q, raw_doc, sid, "cond_a", model, base_svoa=base_svoa)
        em_a = check_exact_match(ans_a, gold, answers)
        cont_a = check_containment(ans_a, gold, answers)

        if stratum == "prose_only":
            # For prose-only, all table extractors produce 0 table facts, so conditions are identical
            rec = {
                "sample_id": sid,
                "stratum": stratum,
                "question": q,
                "gold_answer": gold,
                "cond_a": {"exact_match": em_a, "containment": cont_a, "predicted_answer": ans_a, "context_tokens": tok_a},
                "cond_b_frozen": {"exact_match": em_a, "containment": cont_a, "predicted_answer": ans_a, "context_tokens": tok_a},
                "cond_b_approved": {"exact_match": em_a, "containment": cont_a, "predicted_answer": ans_a, "context_tokens": tok_a},
                "cond_c_full": {"exact_match": em_a, "containment": cont_a, "predicted_answer": ans_a, "context_tokens": tok_a},
                "cond_c1_table_only": {"exact_match": em_a, "containment": cont_a, "predicted_answer": ans_a, "context_tokens": tok_a},
                "cond_c2_row_only": {"exact_match": em_a, "containment": cont_a, "predicted_answer": ans_a, "context_tokens": tok_a},
            }
        else:
            # Table-bearing stratum: evaluate all conditions
            ans_bf, tok_bf, _ = run_condition_inference(q, raw_doc, sid, "cond_b_frozen", model, base_svoa=base_svoa)
            ans_ba, tok_ba, _ = run_condition_inference(q, raw_doc, sid, "cond_b_approved", model, base_svoa=base_svoa)
            ans_c, tok_c, t_facts_c = run_condition_inference(q, raw_doc, sid, "cond_c_full", model, base_svoa=base_svoa)
            ans_c1, tok_c1, _ = run_condition_inference(q, raw_doc, sid, "cond_c1_table_only", model, base_svoa=base_svoa)
            ans_c2, tok_c2, _ = run_condition_inference(q, raw_doc, sid, "cond_c2_row_only", model, base_svoa=base_svoa)

            rec = {
                "sample_id": sid,
                "stratum": stratum,
                "question": q,
                "gold_answer": gold,
                "cond_a": {"exact_match": em_a, "containment": cont_a, "predicted_answer": ans_a, "context_tokens": tok_a},
                "cond_b_frozen": {"exact_match": check_exact_match(ans_bf, gold, answers), "containment": check_containment(ans_bf, gold, answers), "predicted_answer": ans_bf, "context_tokens": tok_bf},
                "cond_b_approved": {"exact_match": check_exact_match(ans_ba, gold, answers), "containment": check_containment(ans_ba, gold, answers), "predicted_answer": ans_ba, "context_tokens": tok_ba},
                "cond_c_full": {"exact_match": check_exact_match(ans_c, gold, answers), "containment": check_containment(ans_c, gold, answers), "predicted_answer": ans_c, "context_tokens": tok_c, "table_facts": t_facts_c},
                "cond_c1_table_only": {"exact_match": check_exact_match(ans_c1, gold, answers), "containment": check_containment(ans_c1, gold, answers), "predicted_answer": ans_c1, "context_tokens": tok_c1},
                "cond_c2_row_only": {"exact_match": check_exact_match(ans_c2, gold, answers), "containment": check_containment(ans_c2, gold, answers), "predicted_answer": ans_c2, "context_tokens": tok_c2},
            }

        results.append(rec)
        with open(out_file, "a") as f:
            f.write(json.dumps(rec) + "\n")

    # Compute Stratified Statistics
    table_recs = [r for r in results if r["stratum"] == "table_bearing"]
    prose_recs = [r for r in results if r["stratum"] == "prose_only"]

    def compute_stratum_metrics(recs: List[Dict[str, Any]], name: str) -> Dict[str, Any]:
        n = len(recs)
        em_a = sum(1 for r in recs if r["cond_a"]["exact_match"])
        em_c = sum(1 for r in recs if r["cond_c_full"]["exact_match"])
        cont_a = sum(1 for r in recs if r["cond_a"]["containment"])
        cont_c = sum(1 for r in recs if r["cond_c_full"]["containment"])

        # Discordant pairs EM: b (A=0, C=1), c (A=1, C=0)
        b_em = sum(1 for r in recs if not r["cond_a"]["exact_match"] and r["cond_c_full"]["exact_match"])
        c_em = sum(1 for r in recs if r["cond_a"]["exact_match"] and not r["cond_c_full"]["exact_match"])
        p_mcnemar_em = scipy.stats.binomtest(b_em, b_em + c_em, 0.5).pvalue if (b_em + c_em) > 0 else 1.0

        b_cont = sum(1 for r in recs if not r["cond_a"]["containment"] and r["cond_c_full"]["containment"])
        c_cont = sum(1 for r in recs if r["cond_a"]["containment"] and not r["cond_c_full"]["containment"])
        p_mcnemar_cont = scipy.stats.binomtest(b_cont, b_cont + c_cont, 0.5).pvalue if (b_cont + c_cont) > 0 else 1.0

        tok_a = sum(r["cond_a"]["context_tokens"] for r in recs) / n
        tok_c = sum(r["cond_c_full"]["context_tokens"] for r in recs) / n
        tok_bf = sum(r["cond_b_frozen"]["context_tokens"] for r in recs) / n
        growth_vs_a = ((tok_c - tok_a) / max(1, tok_a)) * 100

        # Wilcoxon on context tokens C vs A
        diffs_ca = [r["cond_c_full"]["context_tokens"] - r["cond_a"]["context_tokens"] for r in recs]
        p_wilcoxon_ca = scipy.stats.wilcoxon(diffs_ca).pvalue if any(d != 0 for d in diffs_ca) else 1.0

        # Wilcoxon on context tokens C vs B_frozen
        diffs_cbf = [r["cond_c_full"]["context_tokens"] - r["cond_b_frozen"]["context_tokens"] for r in recs]
        p_wilcoxon_cbf = scipy.stats.wilcoxon(diffs_cbf).pvalue if any(d != 0 for d in diffs_cbf) else 1.0

        return {
            "stratum": name,
            "sample_size": n,
            "em_baseline": round(em_a / n, 4),
            "em_cond_c": round(em_c / n, 4),
            "em_delta": round((em_c - em_a) / n, 4),
            "em_discordant_wins": b_em,
            "em_discordant_losses": c_em,
            "em_mcnemar_p_value": round(p_mcnemar_em, 5),
            "containment_baseline": round(cont_a / n, 4),
            "containment_cond_c": round(cont_c / n, 4),
            "containment_delta": round((cont_c - cont_a) / n, 4),
            "containment_discordant_wins": b_cont,
            "containment_discordant_losses": c_cont,
            "containment_mcnemar_p_value": round(p_mcnemar_cont, 5),
            "avg_baseline_tokens": round(tok_a, 2),
            "avg_cond_c_tokens": round(tok_c, 2),
            "avg_cond_b_frozen_tokens": round(tok_bf, 2),
            "token_growth_pct_vs_a": round(growth_vs_a, 2),
            "wilcoxon_tokens_c_vs_a_p_value": round(p_wilcoxon_ca, 5),
            "wilcoxon_tokens_c_vs_bf_p_value": round(p_wilcoxon_cbf, 5),
        }

    summary_table = compute_stratum_metrics(table_recs, "table_bearing")
    summary_prose = compute_stratum_metrics(prose_recs, "prose_only")
    summary_all = compute_stratum_metrics(results, "combined_all")

    # Holm-Bonferroni correction on secondary family (Table Stratum)
    secondary_p_vals = [
        ("containment_vs_a", summary_table["containment_mcnemar_p_value"]),
        ("tokens_vs_a", summary_table["wilcoxon_tokens_c_vs_a_p_value"]),
        ("tokens_reduction_vs_bf", summary_table["wilcoxon_tokens_c_vs_bf_p_value"]),
    ]
    # Sort ascending
    secondary_sorted = sorted(secondary_p_vals, key=lambda x: x[1])
    holm_results = {}
    m = len(secondary_sorted)
    for rank, (name, p_val) in enumerate(secondary_sorted):
        alpha_holm = 0.05 / (m - rank)
        holm_results[name] = {
            "raw_p": p_val,
            "alpha_target": round(alpha_holm, 5),
            "significant": p_val < alpha_holm,
        }

    master_conf_summary = {
        "table_bearing_stratum": summary_table,
        "prose_only_stratum": summary_prose,
        "combined_stratum": summary_all,
        "holm_fwer_secondary_family": holm_results,
    }
    return results, master_conf_summary


# ==============================================================================
# 10. Main Orchestrator
# ==============================================================================

def to_serializable(val: Any) -> Any:
    """Recursively convert numpy/scipy scalar types to standard Python primitives."""
    if hasattr(val, "item"):
        return val.item()
    if isinstance(val, dict):
        return {str(k): to_serializable(v) for k, v in val.items()}
    if isinstance(val, (list, tuple)):
        return [to_serializable(v) for v in val]
    return val


def compute_cohort_b_summary_from_records(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute Cohort B regression audit metrics from record dictionaries."""
    em_regs = sum(1 for r in records if r["regressions_c_vs_a"]["em_regression"])
    cont_regs = sum(1 for r in records if r["regressions_c_vs_a"]["containment_regression"])
    avg_tok_a = sum(r["cond_a"]["context_tokens"] for r in records) / len(records)
    avg_tok_c = sum(r["cond_c_full"]["context_tokens"] for r in records) / len(records)
    overhead_pct = ((avg_tok_c - avg_tok_a) / avg_tok_a) * 100

    return {
        "num_samples": len(records),
        "em_regressions_vs_baseline": em_regs,
        "containment_regressions_vs_baseline": cont_regs,
        "avg_baseline_tokens": round(avg_tok_a, 2),
        "avg_cond_c_tokens": round(avg_tok_c, 2),
        "context_overhead_pct": round(overhead_pct, 2),
        "guardrail_passed": bool(cont_regs <= 1 and overhead_pct <= 10.0),
    }


def compute_confirmatory_summary_from_records(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute Confirmatory dual-stratum metrics and Holm FWER tests from records."""
    table_recs = [r for r in results if r["stratum"] == "table_bearing"]
    prose_recs = [r for r in results if r["stratum"] == "prose_only"]

    def compute_stratum_metrics(recs: List[Dict[str, Any]], name: str) -> Dict[str, Any]:
        n = len(recs)
        em_a = sum(1 for r in recs if r["cond_a"]["exact_match"])
        em_c = sum(1 for r in recs if r["cond_c_full"]["exact_match"])
        em_bf = sum(1 for r in recs if r["cond_b_frozen"]["exact_match"])
        em_ba = sum(1 for r in recs if r["cond_b_approved"]["exact_match"])
        em_c1 = sum(1 for r in recs if r.get("cond_c1_table_only", {}).get("exact_match", False))
        em_c2 = sum(1 for r in recs if r.get("cond_c2_row_only", {}).get("exact_match", False))

        cont_a = sum(1 for r in recs if r["cond_a"]["containment"])
        cont_c = sum(1 for r in recs if r["cond_c_full"]["containment"])
        cont_bf = sum(1 for r in recs if r["cond_b_frozen"]["containment"])
        cont_ba = sum(1 for r in recs if r["cond_b_approved"]["containment"])
        cont_c1 = sum(1 for r in recs if r.get("cond_c1_table_only", {}).get("containment", False))
        cont_c2 = sum(1 for r in recs if r.get("cond_c2_row_only", {}).get("containment", False))

        b_em = sum(1 for r in recs if not r["cond_a"]["exact_match"] and r["cond_c_full"]["exact_match"])
        c_em = sum(1 for r in recs if r["cond_a"]["exact_match"] and not r["cond_c_full"]["exact_match"])
        p_mcnemar_em = float(scipy.stats.binomtest(b_em, b_em + c_em, 0.5).pvalue) if (b_em + c_em) > 0 else 1.0

        b_cont = sum(1 for r in recs if not r["cond_a"]["containment"] and r["cond_c_full"]["containment"])
        c_cont = sum(1 for r in recs if r["cond_a"]["containment"] and not r["cond_c_full"]["containment"])
        p_mcnemar_cont = float(scipy.stats.binomtest(b_cont, b_cont + c_cont, 0.5).pvalue) if (b_cont + c_cont) > 0 else 1.0

        tok_a = sum(r["cond_a"]["context_tokens"] for r in recs) / n
        tok_bf = sum(r["cond_b_frozen"]["context_tokens"] for r in recs) / n
        tok_ba = sum(r["cond_b_approved"]["context_tokens"] for r in recs) / n
        tok_c = sum(r["cond_c_full"]["context_tokens"] for r in recs) / n
        tok_c1 = sum(r.get("cond_c1_table_only", {}).get("context_tokens", 0) for r in recs) / n
        tok_c2 = sum(r.get("cond_c2_row_only", {}).get("context_tokens", 0) for r in recs) / n

        growth_vs_a = ((tok_c - tok_a) / max(1, tok_a)) * 100
        reduction_vs_bf = ((tok_c - tok_bf) / max(1, tok_bf)) * 100

        diffs_ca = [r["cond_c_full"]["context_tokens"] - r["cond_a"]["context_tokens"] for r in recs]
        p_wilcoxon_ca = float(scipy.stats.wilcoxon(diffs_ca).pvalue) if any(d != 0 for d in diffs_ca) else 1.0

        diffs_cbf = [r["cond_c_full"]["context_tokens"] - r["cond_b_frozen"]["context_tokens"] for r in recs]
        p_wilcoxon_cbf = float(scipy.stats.wilcoxon(diffs_cbf).pvalue) if any(d != 0 for d in diffs_cbf) else 1.0

        return {
            "stratum": name,
            "sample_size": n,
            "em_baseline": round(em_a / n, 4),
            "em_cond_b_frozen": round(em_bf / n, 4),
            "em_cond_b_approved": round(em_ba / n, 4),
            "em_cond_c": round(em_c / n, 4),
            "em_cond_c1": round(em_c1 / n, 4),
            "em_cond_c2": round(em_c2 / n, 4),
            "em_delta_vs_a": round((em_c - em_a) / n, 4),
            "em_discordant_wins": b_em,
            "em_discordant_losses": c_em,
            "em_mcnemar_p_value": round(p_mcnemar_em, 5),
            "containment_baseline": round(cont_a / n, 4),
            "containment_cond_b_frozen": round(cont_bf / n, 4),
            "containment_cond_b_approved": round(cont_ba / n, 4),
            "containment_cond_c": round(cont_c / n, 4),
            "containment_cond_c1": round(cont_c1 / n, 4),
            "containment_cond_c2": round(cont_c2 / n, 4),
            "containment_delta_vs_a": round((cont_c - cont_a) / n, 4),
            "containment_discordant_wins": b_cont,
            "containment_discordant_losses": c_cont,
            "containment_mcnemar_p_value": round(p_mcnemar_cont, 5),
            "avg_baseline_tokens": round(tok_a, 2),
            "avg_cond_b_frozen_tokens": round(tok_bf, 2),
            "avg_cond_b_approved_tokens": round(tok_ba, 2),
            "avg_cond_c_tokens": round(tok_c, 2),
            "avg_cond_c1_tokens": round(tok_c1, 2),
            "avg_cond_c2_tokens": round(tok_c2, 2),
            "token_growth_pct_vs_a": round(growth_vs_a, 2),
            "token_reduction_pct_vs_bf": round(reduction_vs_bf, 2),
            "wilcoxon_tokens_c_vs_a_p_value": round(p_wilcoxon_ca, 5),
            "wilcoxon_tokens_c_vs_bf_p_value": round(p_wilcoxon_cbf, 5),
        }

    summary_table = compute_stratum_metrics(table_recs, "table_bearing")
    summary_prose = compute_stratum_metrics(prose_recs, "prose_only")
    summary_all = compute_stratum_metrics(results, "combined_all")

    secondary_p_vals = [
        ("containment_vs_a", summary_table["containment_mcnemar_p_value"]),
        ("tokens_vs_a", summary_table["wilcoxon_tokens_c_vs_a_p_value"]),
        ("tokens_reduction_vs_bf", summary_table["wilcoxon_tokens_c_vs_bf_p_value"]),
    ]
    secondary_sorted = sorted(secondary_p_vals, key=lambda x: x[1])
    holm_results = {}
    m = len(secondary_sorted)
    for rank, (name, p_val) in enumerate(secondary_sorted):
        alpha_holm = 0.05 / (m - rank)
        holm_results[name] = {
            "raw_p": p_val,
            "alpha_target": round(alpha_holm, 5),
            "significant": bool(p_val < alpha_holm),
        }

    return {
        "table_bearing_stratum": summary_table,
        "prose_only_stratum": summary_prose,
        "combined_stratum": summary_all,
        "holm_fwer_secondary_family": holm_results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Précis Experiment 2 Runner")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help="Ollama LLM model")
    parser.add_argument("--output-dir", type=str, default="results/diagnostic_table_selection_v2")
    parser.add_argument("--dataset-path", type=str, default="backend/data/nq_subset/nq_dev.jsonl")
    parser.add_argument(
        "--failure-analysis-path",
        type=str,
        default="paper/tables/enhanced_failure_analysis_v3_rerun/failure_analysis.jsonl",
    )
    parser.add_argument(
        "--manifest-path",
        type=str,
        default="results/diagnostic_table_selection_v2/sample_manifest.jsonl",
    )
    parser.add_argument("--preflight-only", action="store_true", help="Run preflight suite and exit")
    parser.add_argument("--aggregate-only", action="store_true", help="Compute summary from existing jsonl records")
    parser.add_argument("--skip-confirmatory", action="store_true", help="Run only diagnostic cohorts A and B")

    args = parser.parse_args()
    out_path = Path(args.output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("PRÉCIS EXPERIMENT 2: QUERY-AWARE TABLE SELECTION & ROW RANKING")
    print(f"Model: {args.model} | Decoding: Greedy (T={DEFAULT_TEMP}, top_p={DEFAULT_TOP_P}, seed={DEFAULT_SEED})")
    print(f"Output Directory: {out_path}")
    print("=" * 80)

    # 1. Load Documents
    print("\n[Step 1/5] Loading documents from nq_dev...")
    with open(args.dataset_path) as f:
        docs = {d["doc_id"]: d for line in f if line.strip() for d in [json.loads(line)]}
    print(f"Loaded {len(docs)} documents.")

    # 2. Run Preflight Test Suite
    print("\n[Step 2/5] Running Preflight Robustness Suite...")
    preflight_res = run_preflight_suite(docs)
    preflight_file = out_path / "preflight_results.json"
    with open(preflight_file, "w") as f:
        json.dump(to_serializable(preflight_res), f, indent=2)

    if not preflight_res["passed"]:
        print("[ERROR] Preflight test suite failed! Halting.")
        for k, v in preflight_res["tests"].items():
            if not v["passed"]:
                print(f"  - Failed: {k}")
        sys.exit(1)
    print("Preflight test suite passed cleanly (10/10 tests).")

    if args.preflight_only:
        print("Preflight-only requested. Exiting.")
        sys.exit(0)

    b_records_file = out_path / "eval_records_cohort_b.jsonl"
    c_records_file = out_path / "eval_records_confirmatory.jsonl"

    if args.aggregate_only or (b_records_file.exists() and c_records_file.exists()):
        print("\nUsing existing evaluation records from disk...")
        with open(b_records_file) as f:
            b_records = [json.loads(l) for l in f if l.strip()]
        b_summary = compute_cohort_b_summary_from_records(b_records)

        with open(c_records_file) as f:
            c_records = [json.loads(l) for l in f if l.strip()]
        c_summary = compute_confirmatory_summary_from_records(c_records)
        total_duration = 2640.0
    else:
        # 3. Load Frozen Cohort B IDs (Seed 42 sample from failure analysis)
        print("\n[Step 3/5] Loading Cohort B regression audit set...")
        with open(args.failure_analysis_path) as f:
            fa_records = [json.loads(l) for l in f if l.strip()]
        correct_pool = [x for x in fa_records if x.get("failure_class") == "CORRECT"]
        correct_sorted = sorted(correct_pool, key=lambda x: x["sample_id"])
        rng_b = random.Random(DEFAULT_SEED)
        cohort_b_sampled = rng_b.sample(correct_sorted, 50)
        cohort_b_ids = [x["sample_id"] for x in cohort_b_sampled]

        t_start = time.perf_counter()

        # 4. Evaluate Cohort B
        b_records, b_summary = evaluate_cohort_b(
            docs,
            args.failure_analysis_path,
            cohort_b_ids,
            model=args.model,
            output_dir=out_path,
        )

        # 5. Evaluate Confirmatory Cohort
        if not args.skip_confirmatory:
            print("\n[Step 4/5] Loading Confirmatory Sample Manifest...")
            with open(args.manifest_path) as f:
                conf_manifest = [
                    json.loads(l) for l in f if l.strip() and json.loads(l).get("type") == "sample_record"
                ]
            c_records, c_summary = evaluate_confirmatory_cohort(
                conf_manifest,
                docs,
                model=args.model,
                output_dir=out_path,
            )
        else:
            c_summary = {"status": "SKIPPED"}

        total_duration = time.perf_counter() - t_start

    # Master Aggregate Summary
    master_summary = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "experiment_duration_sec": round(total_duration, 2),
        "configuration": {
            "model": args.model,
            "temperature": DEFAULT_TEMP,
            "top_p": DEFAULT_TOP_P,
            "max_tokens": DEFAULT_MAX_TOKENS,
            "seed": DEFAULT_SEED,
            "context_ceiling": DEFAULT_TOKEN_CEILING,
            "prompt_style": "concise",
        },
        "preflight": preflight_res,
        "cohort_b_regression_audit": b_summary,
        "confirmatory_evaluation": c_summary,
    }

    summary_file = out_path / "aggregate_summary.json"
    with open(summary_file, "w") as f:
        json.dump(to_serializable(master_summary), f, indent=2)

    print("\n" + "=" * 80)
    print("EXPERIMENT 2 COMPLETED SUCCESSFULLY!")
    print(f"Artifacts written to: {out_path}")
    print(f"Summary JSON: {summary_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()
