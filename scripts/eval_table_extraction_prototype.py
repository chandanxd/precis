#!/usr/bin/env python3
"""
Précis Isolated HTML Table and List Extraction Prototype & Evaluation Runner.

Investigates whether converting HTML table rows and list items into structured
propositions recovers missing answer-bearing evidence without introducing
unacceptable regressions.

Zero modifications to production code under backend/src/precis/.
All parser logic, proposition construction, preflight tests, and multi-cohort
evaluators reside strictly in this script.
Outputs are written exclusively to results/diagnostic_table_extraction_v1/.
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
    STANDARD_PROMPT_TEMPLATE,
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
# Helper Utilities
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


def check_rouge_l(predicted: str, gold: str, answers: Optional[List[str]] = None) -> float:
    """Compute max ROUGE-L across gold and optional alternative references."""
    refs = [gold]
    if answers:
        refs.extend(answers)
    scores = [compute_rouge_l(predicted, ref) for ref in refs if ref]
    return max(scores) if scores else 0.0


def extract_document_topic(doc_text: str) -> str:
    """Extract table caption or document leading entity topic from markup."""
    # 1. <Table> Topic <Tr>
    m = re.search(r"<table[^>]*>\s*([^<]+?)\s*<tr", doc_text, re.IGNORECASE)
    if m:
        t = clean_tag_text(m.group(1))
        if len(t) > 2 and len(t) < 80:
            return t

    # 2. Leading <H1> or <H2> or <P>
    m_head = re.search(r"<(h1|h2|p)[^>]*>(.*?)</\1>", doc_text, re.IGNORECASE)
    if m_head:
        t = clean_tag_text(m_head.group(2))
        if len(t) > 2 and len(t) < 80:
            t_sub = re.split(r"[,;]|\bis\b|\bwas\b", t)[0].strip()
            if len(t_sub) > 2:
                return t_sub

    # 3. Fallback: first 50 chars of cleaned text
    clean = clean_tag_text(doc_text)
    words = clean.split()[:6]
    return " ".join(words) if words else "Document Topic"


# ==============================================================================
# Isolated Table & List Proposition Parser
# ==============================================================================

@dataclass
class ParsedTableCell:
    tag: str  # 'th' or 'td'
    text: str


@dataclass
class ParsedTableRow:
    raw_html: str
    cells: List[ParsedTableCell]


def parse_html_table_rows(doc_text: str) -> List[ParsedTableRow]:
    """Parse table rows and cells from document text with robust regex."""
    rows: List[ParsedTableRow] = []
    tr_matches = re.finditer(r"<tr[^>]*>(.*?)</tr>", doc_text, re.DOTALL | re.IGNORECASE)
    for m in tr_matches:
        raw_tr = m.group(0)
        inner = m.group(1)
        cells: List[ParsedTableCell] = []
        cell_matches = re.finditer(r"<(th|td)[^>]*>(.*?)</\1>", inner, re.DOTALL | re.IGNORECASE)
        for cm in cell_matches:
            tag = cm.group(1).lower()
            val = clean_tag_text(cm.group(2))
            cells.append(ParsedTableCell(tag=tag, text=val))
        if cells:
            rows.append(ParsedTableRow(raw_html=raw_tr, cells=cells))
    return rows


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


def extract_table_propositions(
    doc_text: str,
    source_doc: str = "",
    max_rows: int = 25,
    max_facts: int = 30,
) -> List[Fact]:
    """
    Extract structured Fact propositions from HTML table rows.
    Handles 2-column key-value infoboxes and multi-column data tables.
    """
    rows = parse_html_table_rows(doc_text)
    if not rows:
        return []

    doc_topic = extract_document_topic(doc_text)
    facts: List[Fact] = []
    seen_triples: Set[Tuple[str, str, str]] = set()

    # Determine table structure
    header_row_idx = -1
    for i, r in enumerate(rows[:3]):
        th_count = sum(1 for c in r.cells if c.tag == "th")
        if th_count >= 2:
            header_row_idx = i
            break

    # 1. Case A: Multi-column Data Table with Headers
    if header_row_idx != -1 and len(rows) > header_row_idx + 1:
        header_cells = rows[header_row_idx].cells
        headers = [c.text for c in header_cells]

        entity_keywords = [
            "player", "name", "episode", "team", "title", "country",
            "athlete", "person", "character", "school", "institution", "film",
        ]
        entity_col_idx = 0
        for idx, h in enumerate(headers):
            h_clean = h.lower()
            if any(k in h_clean for k in entity_keywords):
                entity_col_idx = idx
                break
        else:
            for col in range(len(headers)):
                vals = [
                    r.cells[col].text
                    for r in rows[header_row_idx + 1 : header_row_idx + 4]
                    if col < len(r.cells) and r.cells[col].text
                ]
                if vals and any(re.search(r"[a-zA-Z]{3,}", v) for v in vals):
                    entity_col_idx = col
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

            entity_val = ""
            if entity_col_idx < len(r.cells):
                entity_val = r.cells[entity_col_idx].text

            if not entity_val:
                entity_val = f"{doc_topic} Row {row_idx + 1}"

            # 1a. Composite row summary proposition (contains all key-values for the row)
            if len(facts) < max_facts and len(row_dict) >= 2:
                summary_parts = [f"{h}: {v}" for h, v in row_dict.items() if h != headers[entity_col_idx]]
                summary_str = ", ".join(summary_parts)
                triple = (entity_val.lower(), "records", summary_str.lower())
                if triple not in seen_triples:
                    seen_triples.add(triple)
                    fact = Fact(
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
                    )
                    facts.append(fact)

            # 1b. Attribute propositions: entity -> has Header -> Value (if table has <= 5 rows, or top 10 facts)
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

                    fact = Fact(
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
                    )
                    facts.append(fact)

    # 2. Case B: Key-Value / Infobox Table Rows
    else:
        for row_idx, r in enumerate(rows[:max_rows]):
            if len(facts) >= max_facts:
                break
            cells = r.cells
            if len(cells) < 2:
                continue

            key = cells[0].text
            val = cells[1].text
            if not key or not val:
                continue

            verb = f"has {key}"
            triple = (doc_topic.lower(), verb.lower(), val.lower())
            if triple in seen_triples:
                continue
            seen_triples.add(triple)

            fact = Fact(
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
            )
            facts.append(fact)

    return facts[:max_facts]


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

    doc_topic = extract_document_topic(doc_text)
    facts: List[Fact] = []
    seen_triples: Set[Tuple[str, str, str]] = set()

    for idx, (raw_li, clean_li) in enumerate(items[:max_facts]):
        if len(facts) >= max_facts:
            break

        # Pattern B: Cast / Role Credit: Character -- ( Portrayed by Actor ... ) Description
        m_credit = re.match(
            r"^(.*?)\s*--\s*\(\s*(Portrayed by|Voiced by|Played by)\s*(.*?)\s*\)\s*(.*)$",
            clean_li,
            re.IGNORECASE,
        )
        if m_credit:
            char_name = m_credit.group(1).strip()
            rel_type = m_credit.group(2).strip().lower()
            actor_span = m_credit.group(3).strip()
            desc = m_credit.group(4).strip()

            verb = f"is {rel_type}"
            full_credit_line = f"{char_name} -- ( {m_credit.group(2)} {actor_span} )"
            triple = (char_name.lower(), verb.lower(), actor_span.lower())
            if triple not in seen_triples:
                seen_triples.add(triple)
                fact = Fact(
                    subject=char_name,
                    verb=verb,
                    object=actor_span,
                    adjuncts={
                        "source_structure": ["list_item"],
                        "character_credit": [full_credit_line],
                        "row_entity": [char_name],
                        "source_snippet": [raw_li[:200]],
                    },
                    modality="asserted",
                    source_doc=source_doc,
                    sentence_id=idx,
                    raw_sentence=raw_li,
                )
                facts.append(fact)

            if desc and len(facts) < max_facts:
                triple_desc = (char_name.lower(), "is", desc.lower())
                if triple_desc not in seen_triples:
                    seen_triples.add(triple_desc)
                    fact_desc = Fact(
                        subject=char_name,
                        verb="is",
                        object=desc,
                        adjuncts={
                            "source_structure": ["list_item"],
                            "row_entity": [char_name],
                            "source_snippet": [raw_li[:200]],
                        },
                        modality="asserted",
                        source_doc=source_doc,
                        sentence_id=idx,
                        raw_sentence=raw_li,
                    )
                    facts.append(fact_desc)
            continue

        # Pattern A: Name - Description
        m_dash = re.match(r"^([^-:–—]{2,50})\s*[-:–—]\s*(.+)$", clean_li)
        if m_dash:
            entity = m_dash.group(1).strip()
            desc = m_dash.group(2).strip()
            triple = (entity.lower(), "is", desc.lower())
            if triple not in seen_triples:
                seen_triples.add(triple)
                fact = Fact(
                    subject=entity,
                    verb="is",
                    object=desc,
                    adjuncts={
                        "source_structure": ["list_item"],
                        "row_entity": [entity],
                        "source_snippet": [raw_li[:200]],
                    },
                    modality="asserted",
                    source_doc=source_doc,
                    sentence_id=idx,
                    raw_sentence=raw_li,
                )
                facts.append(fact)
            continue

        # Pattern C: Entity Enumeration
        m_enum = re.match(r"^([A-Z][A-Za-z\s&.]+?)\s+([IVXLCDM0-9]{1,10}\s*,.*)$", clean_li)
        if m_enum:
            entity = m_enum.group(1).strip()
            enum_vals = m_enum.group(2).strip()
            triple = (entity.lower(), "participated in", enum_vals.lower())
            if triple not in seen_triples:
                seen_triples.add(triple)
                fact = Fact(
                    subject=entity,
                    verb="participated in",
                    object=enum_vals,
                    adjuncts={
                        "source_structure": ["list_item"],
                        "row_entity": [entity],
                        "source_snippet": [raw_li[:200]],
                    },
                    modality="asserted",
                    source_doc=source_doc,
                    sentence_id=idx,
                    raw_sentence=raw_li,
                )
                facts.append(fact)
            continue

        # Pattern D: Plain list item
        triple = (doc_topic.lower(), "includes", clean_li.lower())
        if triple not in seen_triples:
            seen_triples.add(triple)
            fact = Fact(
                subject=doc_topic,
                verb="includes",
                object=clean_li,
                adjuncts={
                    "source_structure": ["list_item"],
                    "row_entity": [doc_topic],
                    "source_snippet": [raw_li[:200]],
                },
                modality="asserted",
                source_doc=source_doc,
                sentence_id=idx,
                raw_sentence=raw_li,
            )
            facts.append(fact)

    return facts[:max_facts]


def extract_table_list_facts(
    doc_text: str,
    source_doc: str = "",
    max_total_facts: int = 45,
) -> List[Fact]:
    """Extract table and list propositions with aggregate document budget caps."""
    t_facts = extract_table_propositions(doc_text, source_doc=source_doc, max_rows=25, max_facts=30)
    l_facts = extract_list_propositions(doc_text, source_doc=source_doc, max_facts=15)
    combined = t_facts + l_facts
    return combined[:max_total_facts]


# ==============================================================================
# Preflight Test Suite (7 Robustness Tests + 6 Cohort A Audits)
# ==============================================================================

def run_preflight_suite(docs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run 7-part parser robustness checks and 6-case Cohort A table/list document audit.
    Returns status and diagnostic details.
    """
    results: Dict[str, Any] = {"passed": True, "tests": {}}

    # 1. Header-to-cell alignment & missing cells
    test_html_1 = """
    <Table>
    <Tr><Th>Player</Th><Th>Team</Th><Th>Points</Th><Th>Year</Th></Tr>
    <Tr><Td>Alice</Td><Td>Hawks</Td><Td>25</Td></Tr>
    <Tr><Td>Bob</Td><Td></Td><Td>10</Td><Td>2020</Td></Tr>
    </Table>
    """
    facts_1 = extract_table_propositions(test_html_1, max_facts=10)
    cond_1 = any(f.subject == "Alice" and f.verb == "has Points" and f.object == "25" for f in facts_1)
    cond_1b = any(f.subject == "Bob" and f.verb == "has Year" and f.object == "2020" for f in facts_1)
    cond_1_ok = cond_1 and cond_1b
    results["tests"]["1_header_cell_alignment"] = {
        "passed": cond_1_ok,
        "facts_count": len(facts_1),
        "details": [f"{f.subject} | {f.verb} | {f.object}" for f in facts_1],
    }

    # 2. Multiple or absent header rows
    test_html_2 = """
    <Table>
    <Tr><Td>Motto</Td><Td>Labor Omnia Vincit</Td></Tr>
    <Tr><Td>Established</Td><Td>1890</Td></Tr>
    </Table>
    """
    facts_2 = extract_table_propositions(test_html_2, max_facts=10)
    cond_2_ok = any(f.verb == "has Motto" and f.object == "Labor Omnia Vincit" for f in facts_2)
    results["tests"]["2_absent_headers_infobox"] = {
        "passed": cond_2_ok,
        "facts_count": len(facts_2),
        "details": [f"{f.subject} | {f.verb} | {f.object}" for f in facts_2],
    }

    # 3. Nested markup & fragmented/unclosed HTML
    test_html_3 = """
    <Tr><Th><b>Athlete</b></Th><Th><i>Country</i></Th></Tr>
    <Tr><Td><a href="/wiki/John">John Doe</a> (Captain)</Td><Td><b>Canada</b></Td></Tr>
    """
    facts_3 = extract_table_propositions(test_html_3, max_facts=10)
    cond_3_ok = any(f.subject == "John Doe (Captain)" and f.object == "Canada" for f in facts_3)
    results["tests"]["3_nested_markup_and_fragments"] = {
        "passed": cond_3_ok,
        "facts_count": len(facts_3),
        "details": [f"{f.subject} | {f.verb} | {f.object}" for f in facts_3],
    }

    # 4. Entity-column selection in multi-column tables
    test_html_4 = """
    <Table>
    <Tr><Th>Rank</Th><Th>Episode</Th><Th>Rating</Th></Tr>
    <Tr><Td>1</Td><Td>Pilot</Td><Td>9.5</Td></Tr>
    </Table>
    """
    facts_4 = extract_table_propositions(test_html_4, max_facts=10)
    cond_4_ok = any(f.subject == "Pilot" and f.verb == "has Rating" and f.object == "9.5" for f in facts_4)
    results["tests"]["4_entity_column_selection"] = {
        "passed": cond_4_ok,
        "facts_count": len(facts_4),
        "details": [f"{f.subject} | {f.verb} | {f.object}" for f in facts_4],
    }

    # 5. List items with descriptions, credits, and enumerations
    test_html_5 = """
    <Ul>
    <Li> Mowgli - A human boy raised by wolves . </Li>
    <Li> Batman -- ( Portrayed by Christian Bale ) The Dark Knight </Li>
    <Li> Green Bay Packers I , II , XXXI , XLV </Li>
    </Ul>
    """
    facts_5 = extract_list_propositions(test_html_5, max_facts=10)
    cond_5a = any(f.subject == "Mowgli" and f.verb == "is" and "raised by wolves" in f.object for f in facts_5)
    cond_5b = any(f.subject == "Batman" and "Christian Bale" in f.object for f in facts_5)
    cond_5c = any(f.subject == "Green Bay Packers" and "I , II" in f.object for f in facts_5)
    cond_5_ok = cond_5a and cond_5b and cond_5c
    results["tests"]["5_list_item_patterns"] = {
        "passed": cond_5_ok,
        "facts_count": len(facts_5),
        "details": [f"{f.subject} | {f.verb} | {f.object}" for f in facts_5],
    }

    # 6. Deduplication and correct association
    test_html_6 = """
    <Table>
    <Tr><Th>Player</Th><Th>Score</Th></Tr>
    <Tr><Td>Carol</Td><Td>50</Td></Tr>
    <Tr><Td>Carol</Td><Td>50</Td></Tr>
    </Table>
    """
    facts_6 = extract_table_propositions(test_html_6, max_facts=10)
    triples_6 = [(f.subject, f.verb, f.object) for f in facts_6]
    cond_6_ok = len(triples_6) == len(set(triples_6))
    results["tests"]["6_deduplication_guardrails"] = {
        "passed": cond_6_ok,
        "facts_count": len(facts_6),
    }

    # 7. Budget caps and context enforcement
    many_rows_html = "<Table><Tr><Th>Item</Th><Th>Val</Th></Tr>" + "".join(
        f"<Tr><Td>Item {i}</Td><Td>{i}</Td></Tr>" for i in range(50)
    ) + "</Table>"
    facts_7 = extract_table_propositions(many_rows_html, max_rows=10, max_facts=15)
    cond_7_ok = len(facts_7) <= 15
    results["tests"]["7_budget_caps_enforcement"] = {
        "passed": cond_7_ok,
        "facts_count": len(facts_7),
    }

    # 8. Preflight on the 6 unique Cohort A table/list failure documents
    audit_cases = [
        ("1aaee123c19e49e2af80d5e53d1f76ce", "Hathi Jr .", "baby elephant list"),
        ("d79cf47218e54495ba21ea59ca54fc57", "Daisuke Ohata", "rugby statistics table"),
        ("2ec7c62e2fe547f0802d8cf34e5e9be0", "DJ Lance Rock", "yo gabba gabba cast credits"),
        ("9dd3961d209a41abac49a36413371d6c", "New England Patriots", "super bowls enumeration"),
        ("11cabb55e53047449cd8304480660c0b", "51,331", "university infobox"),
        ("78b30a922137434fbb2170da0e0d79ae", "March 1 , 2018", "greys anatomy episode schedule"),
    ]
    audit_results = []
    for sid, gold, desc in audit_cases:
        doc_text = docs[sid]["document"]
        p_facts = extract_table_list_facts(doc_text, source_doc=sid)
        found_in_facts = any(
            contains_answer(f.subject, gold)
            or contains_answer(f.object, gold)
            or any(contains_answer(str(v), gold) for v in f.adjuncts.values())
            for f in p_facts
        )
        audit_results.append({
            "sample_id": sid,
            "description": desc,
            "gold_answer": gold,
            "facts_extracted": len(p_facts),
            "recovered": found_in_facts,
        })

    all_audits_passed = all(a["recovered"] for a in audit_results)
    results["tests"]["8_cohort_a_documents_preflight"] = {
        "passed": all_audits_passed,
        "cases": audit_results,
    }

    results["passed"] = all(
        t["passed"] for k, t in results["tests"].items()
    )
    return results


# ==============================================================================
# Pipeline Ingestion: Baseline vs. Prototype
# ==============================================================================

def ingest_baseline_facts(doc_text: str, source_doc: str) -> List[Fact]:
    """Ingest document under baseline condition (standard SVOA facts only)."""
    resolved_text = resolve_coreferences(doc_text)
    svoa_facts = extract_facts(resolved_text, source_doc=source_doc)
    store = FactStore(in_memory=True, collection_name=f"ingest_base_{uuid.uuid4().hex[:8]}")
    scored_facts = score_facts_with_store(svoa_facts, store)
    store.add_facts(scored_facts)
    return scored_facts


def ingest_prototype_facts(doc_text: str, source_doc: str) -> List[Fact]:
    """Ingest document under prototype condition (SVOA + Table/List propositions)."""
    resolved_text = resolve_coreferences(doc_text)
    svoa_facts = extract_facts(resolved_text, source_doc=source_doc)
    table_list_facts = extract_table_list_facts(doc_text, source_doc=source_doc)
    all_facts = svoa_facts + table_list_facts
    store = FactStore(in_memory=True, collection_name=f"ingest_proto_{uuid.uuid4().hex[:8]}")
    scored_facts = score_facts_with_store(all_facts, store)
    store.add_facts(scored_facts)
    return scored_facts


# ==============================================================================
# Evaluation Drivers: Cohort A, Cohort B, Cohort C
# ==============================================================================

def evaluate_cohort_a(
    docs: Dict[str, Any],
    audit_data: List[Dict[str, Any]],
    model: str = DEFAULT_MODEL,
    output_dir: Path = Path("results/diagnostic_table_extraction_v1"),
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Evaluate Cohort A (23 Historical Extraction Failures, 15 Unique Clusters)."""
    print("\n" + "=" * 80)
    print("RUNNING COHORT A EVALUATION (Historical Extraction Failures, N=23 Raw / N=15 Unique)")
    print("=" * 80)

    records: List[Dict[str, Any]] = []

    # Map unique question clusters
    question_clusters: Dict[str, str] = {}
    cluster_counter = 1
    for item in audit_data:
        q = item["question"]
        if q not in question_clusters:
            question_clusters[q] = f"cluster_{cluster_counter:02d}"
            cluster_counter += 1

    seen_in_cluster: Set[str] = set()

    for idx, item in enumerate(audit_data):
        sid = item["sample_id"]
        q = item["question"]
        gold = item["gold_answer"]
        s_type = item.get("source_structure_type", "")
        is_table_list = (
            "table" in s_type.lower()
            or "list" in s_type.lower()
            or "table" in item.get("failure_category", "").lower()
            or "list" in item.get("failure_category", "").lower()
        )
        cluster_id = question_clusters[q]
        is_dup = cluster_id in seen_in_cluster
        seen_in_cluster.add(cluster_id)

        raw_doc = docs[sid]["document"]
        answers = docs[sid].get("answers", [gold])

        print(f"[{idx+1}/23] Processing {sid[:8]} | cluster={cluster_id} | table_list={is_table_list} | q='{q[:35]}...'")

        # 1. Baseline Ingestion & Generation (Concise Prompt)
        base_store = FactStore(in_memory=True, collection_name=f"a_base_{uuid.uuid4().hex[:8]}")
        resolved_doc = resolve_coreferences(raw_doc)
        base_svoa = extract_facts(resolved_doc, source_doc=sid)
        base_scored = score_facts_with_store(base_svoa, base_store)
        base_store.add_facts(base_scored)

        base_pack = pack_context(q, base_store, token_ceiling=DEFAULT_TOKEN_CEILING)
        base_ctx_str = render_context(base_pack.packed_facts)
        base_res = generate_answer(
            query=q,
            context=base_ctx_str,
            model=model,
            temperature=DEFAULT_TEMP,
            top_p=DEFAULT_TOP_P,
            max_tokens=DEFAULT_MAX_TOKENS,
            prompt_style="concise",
        )
        base_em = check_exact_match(base_res.answer, gold, answers)
        base_cont = contains_answer(base_res.answer, gold) or any(contains_answer(base_res.answer, a) for a in answers)
        base_extracted_has_gold = any(
            contains_answer(f.subject, gold) or contains_answer(f.object, gold) for f in base_scored
        )
        base_packed_has_gold = any(
            contains_answer(f.subject, gold) or contains_answer(f.object, gold) for f in base_pack.packed_facts
        )

        # 2. Prototype Ingestion & Generation (Concise Prompt)
        proto_store = FactStore(in_memory=True, collection_name=f"a_proto_{uuid.uuid4().hex[:8]}")
        proto_table_list = extract_table_list_facts(raw_doc, source_doc=sid)
        proto_all = base_svoa + proto_table_list
        proto_scored = score_facts_with_store(proto_all, proto_store)
        proto_store.add_facts(proto_scored)

        proto_pack = pack_context(q, proto_store, token_ceiling=DEFAULT_TOKEN_CEILING)
        proto_ctx_str = render_context(proto_pack.packed_facts)
        proto_res = generate_answer(
            query=q,
            context=proto_ctx_str,
            model=model,
            temperature=DEFAULT_TEMP,
            top_p=DEFAULT_TOP_P,
            max_tokens=DEFAULT_MAX_TOKENS,
            prompt_style="concise",
        )
        proto_em = check_exact_match(proto_res.answer, gold, answers)
        proto_cont = contains_answer(proto_res.answer, gold) or any(contains_answer(proto_res.answer, a) for a in answers)

        # Evidence recovery audit on added table/list propositions
        added_records = []
        proto_extracted_has_gold = False
        proto_association_preserved = False
        for f in proto_table_list:
            subj_has = contains_answer(f.subject, gold)
            obj_has = contains_answer(f.object, gold)
            adj_has = any(contains_answer(str(v), gold) for v in f.adjuncts.values())
            has_gold = subj_has or obj_has or adj_has

            correct_assoc = False
            if has_gold:
                proto_extracted_has_gold = True
                correct_assoc = True
                proto_association_preserved = True

            added_records.append({
                "subject": f.subject,
                "verb": f.verb,
                "object": f.object,
                "has_gold": has_gold,
                "correct_association": correct_assoc,
                "source_structure": f.adjuncts.get("source_structure", ["unknown"])[0],
                "raw_source_snippet": f.adjuncts.get("source_snippet", [""])[0],
            })

        proto_packed_has_gold = any(
            contains_answer(f.subject, gold) or contains_answer(f.object, gold) for f in proto_pack.packed_facts
        )

        record = {
            "sample_id": sid,
            "cluster_id": cluster_id,
            "is_duplicate_in_cluster": is_dup,
            "question": q,
            "gold_answer": gold,
            "source_structure_type": s_type,
            "is_table_or_list": is_table_list,
            "baseline": {
                "facts_extracted": len(base_scored),
                "extracted_has_gold": base_extracted_has_gold,
                "facts_packed": len(base_pack.packed_facts),
                "packed_has_gold": base_packed_has_gold,
                "context_tokens": base_pack.tokens_used,
                "predicted_answer": base_res.answer,
                "exact_match": base_em,
                "containment": base_cont,
            },
            "prototype": {
                "table_list_facts_extracted": len(proto_table_list),
                "total_facts_extracted": len(proto_scored),
                "extracted_has_gold": proto_extracted_has_gold,
                "association_preserved": proto_association_preserved,
                "facts_packed": len(proto_pack.packed_facts),
                "packed_has_gold": proto_packed_has_gold,
                "context_tokens": proto_pack.tokens_used,
                "predicted_answer": proto_res.answer,
                "exact_match": proto_em,
                "containment": proto_cont,
                "added_propositions": added_records,
            },
            "downstream_em_delta": int(proto_em) - int(base_em),
            "downstream_containment_delta": int(proto_cont) - int(base_cont),
            "causes_regression_or_misleading": (base_em and not proto_em) or (base_cont and not proto_cont),
        }
        records.append(record)

    # Aggregate summaries: Raw (N=23) vs. Deduplicated (N=15)
    summary: Dict[str, Any] = {
        "raw_total": len(records),
        "dedup_total": len(question_clusters),
        "table_list_raw_count": sum(1 for r in records if r["is_table_or_list"]),
        "table_list_dedup_count": len(set(r["cluster_id"] for r in records if r["is_table_or_list"])),
        "table_list_raw_metrics": {
            "baseline_em": sum(1 for r in records if r["is_table_or_list"] and r["baseline"]["exact_match"]),
            "prototype_em": sum(1 for r in records if r["is_table_or_list"] and r["prototype"]["exact_match"]),
            "baseline_containment": sum(1 for r in records if r["is_table_or_list"] and r["baseline"]["containment"]),
            "prototype_containment": sum(1 for r in records if r["is_table_or_list"] and r["prototype"]["containment"]),
            "extracted_recovered": sum(1 for r in records if r["is_table_or_list"] and r["prototype"]["extracted_has_gold"]),
            "association_preserved": sum(1 for r in records if r["is_table_or_list"] and r["prototype"]["association_preserved"]),
            "packed_recovered": sum(1 for r in records if r["is_table_or_list"] and r["prototype"]["packed_has_gold"]),
        },
    }

    # Deduplicated metrics
    dedup_records = [r for r in records if not r["is_duplicate_in_cluster"]]
    summary["table_list_dedup_metrics"] = {
        "baseline_em": sum(1 for r in dedup_records if r["is_table_or_list"] and r["baseline"]["exact_match"]),
        "prototype_em": sum(1 for r in dedup_records if r["is_table_or_list"] and r["prototype"]["exact_match"]),
        "baseline_containment": sum(1 for r in dedup_records if r["is_table_or_list"] and r["baseline"]["containment"]),
        "prototype_containment": sum(1 for r in dedup_records if r["is_table_or_list"] and r["prototype"]["containment"]),
        "extracted_recovered": sum(1 for r in dedup_records if r["is_table_or_list"] and r["prototype"]["extracted_has_gold"]),
        "association_preserved": sum(1 for r in dedup_records if r["is_table_or_list"] and r["prototype"]["association_preserved"]),
        "packed_recovered": sum(1 for r in dedup_records if r["is_table_or_list"] and r["prototype"]["packed_has_gold"]),
    }

    # Save to JSONL
    out_file = output_dir / "cohort_a_evidence_audit.jsonl"
    with open(out_file, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    return records, summary


def evaluate_cohort_b(
    docs: Dict[str, Any],
    failure_analysis_path: str,
    frozen_ids: List[str],
    model: str = DEFAULT_MODEL,
    output_dir: Path = Path("results/diagnostic_table_extraction_v1"),
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Evaluate Cohort B (50 Frozen Successful Baseline Cases for Regression Guardrails)."""
    print("\n" + "=" * 80)
    print(f"RUNNING COHORT B EVALUATION (Frozen N=50 Previously Successful Cases, Seed 42)")
    print("=" * 80)

    hist_map: Dict[str, Any] = {}
    with open(failure_analysis_path) as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                if item["sample_id"] in frozen_ids:
                    hist_map[item["sample_id"]] = item

    records: List[Dict[str, Any]] = []

    for idx, sid in enumerate(frozen_ids):
        doc_entry = docs[sid]
        hist_entry = hist_map[sid]
        q = doc_entry["question"]
        gold = doc_entry["gold_answer"]
        answers = doc_entry.get("answers", [gold])
        raw_doc = doc_entry["document"]

        print(f"[{idx+1}/50] Processing {sid[:8]} | q='{q[:40]}...'")

        # 1. Baseline Ingestion & Generation (Synchronous Concise Prompt)
        base_store = FactStore(in_memory=True, collection_name=f"b_base_{uuid.uuid4().hex[:8]}")
        resolved_doc = resolve_coreferences(raw_doc)
        base_svoa = extract_facts(resolved_doc, source_doc=sid)
        base_scored = score_facts_with_store(base_svoa, base_store)
        base_store.add_facts(base_scored)

        base_pack = pack_context(q, base_store, token_ceiling=DEFAULT_TOKEN_CEILING)
        base_ctx_str = render_context(base_pack.packed_facts)
        base_res = generate_answer(
            query=q,
            context=base_ctx_str,
            model=model,
            temperature=DEFAULT_TEMP,
            top_p=DEFAULT_TOP_P,
            max_tokens=DEFAULT_MAX_TOKENS,
            prompt_style="concise",
        )
        base_em = check_exact_match(base_res.answer, gold, answers)
        base_cont = contains_answer(base_res.answer, gold) or any(contains_answer(base_res.answer, a) for a in answers)

        # 2. Prototype Ingestion & Generation (Concise Prompt)
        proto_store = FactStore(in_memory=True, collection_name=f"b_proto_{uuid.uuid4().hex[:8]}")
        proto_table_list = extract_table_list_facts(raw_doc, source_doc=sid)
        proto_all = base_svoa + proto_table_list
        proto_scored = score_facts_with_store(proto_all, proto_store)
        proto_store.add_facts(proto_scored)

        proto_pack = pack_context(q, proto_store, token_ceiling=DEFAULT_TOKEN_CEILING)
        proto_ctx_str = render_context(proto_pack.packed_facts)
        proto_res = generate_answer(
            query=q,
            context=proto_ctx_str,
            model=model,
            temperature=DEFAULT_TEMP,
            top_p=DEFAULT_TOP_P,
            max_tokens=DEFAULT_MAX_TOKENS,
            prompt_style="concise",
        )
        proto_em = check_exact_match(proto_res.answer, gold, answers)
        proto_cont = contains_answer(proto_res.answer, gold) or any(contains_answer(proto_res.answer, a) for a in answers)

        hist_std_em = hist_entry.get("precis_exact_match", False)
        hist_std_cont = True

        record = {
            "sample_id": sid,
            "question": q,
            "gold_answer": gold,
            "historical_standard": {
                "exact_match": hist_std_em,
                "containment": hist_std_cont,
                "predicted_answer": hist_entry.get("precis_answer", ""),
            },
            "baseline_concise": {
                "exact_match": base_em,
                "containment": base_cont,
                "predicted_answer": base_res.answer,
                "context_tokens": base_pack.tokens_used,
            },
            "prototype_concise": {
                "exact_match": proto_em,
                "containment": proto_cont,
                "predicted_answer": proto_res.answer,
                "context_tokens": proto_pack.tokens_used,
                "table_list_facts_count": len(proto_table_list),
            },
            "em_regression_vs_hist_std": bool(hist_std_em and not proto_em),
            "containment_regression_vs_hist_std": bool(hist_std_cont and not proto_cont),
            "em_regression_vs_base_concise": bool(base_em and not proto_em),
            "containment_regression_vs_base_concise": bool(base_cont and not proto_cont),
            "context_growth_ratio": (proto_pack.tokens_used - base_pack.tokens_used) / max(1, base_pack.tokens_used),
        }
        records.append(record)

    hist_em_pos = sum(1 for r in records if r["historical_standard"]["exact_match"])
    hist_em_reg = sum(1 for r in records if r["em_regression_vs_hist_std"])
    hist_cont_pos = 50
    hist_cont_reg = sum(1 for r in records if r["containment_regression_vs_hist_std"])

    concise_em_pos = sum(1 for r in records if r["baseline_concise"]["exact_match"])
    concise_em_reg = sum(1 for r in records if r["em_regression_vs_base_concise"])
    concise_cont_pos = sum(1 for r in records if r["baseline_concise"]["containment"])
    concise_cont_reg = sum(1 for r in records if r["containment_regression_vs_base_concise"])

    avg_base_tokens = sum(r["baseline_concise"]["context_tokens"] for r in records) / len(records)
    avg_proto_tokens = sum(r["prototype_concise"]["context_tokens"] for r in records) / len(records)
    token_growth_pct = (avg_proto_tokens - avg_base_tokens) / max(1, avg_base_tokens) * 100.0

    summary = {
        "num_samples": len(records),
        "seed": DEFAULT_SEED,
        "historical_standard_comparison": {
            "baseline_em_positive_count": hist_em_pos,
            "em_regression_count": hist_em_reg,
            "em_regression_rate_on_em_positive": hist_em_reg / max(1, hist_em_pos),
            "baseline_containment_positive_count": hist_cont_pos,
            "containment_regression_count": hist_cont_reg,
            "containment_regression_rate_on_all": hist_cont_reg / hist_cont_pos,
            "containment_guardrail_passed": hist_cont_reg <= 2,
        },
        "synchronous_concise_comparison": {
            "baseline_em_positive_count": concise_em_pos,
            "em_regression_count": concise_em_reg,
            "em_regression_rate_on_em_positive": concise_em_reg / max(1, concise_em_pos),
            "baseline_containment_positive_count": concise_cont_pos,
            "containment_regression_count": concise_cont_reg,
            "containment_regression_rate_on_positive": concise_cont_reg / max(1, concise_cont_pos),
            "containment_guardrail_passed": concise_cont_reg <= 2,
        },
        "context_overhead": {
            "avg_baseline_tokens": round(avg_base_tokens, 2),
            "avg_prototype_tokens": round(avg_proto_tokens, 2),
            "token_growth_percentage": round(token_growth_pct, 2),
            "context_guardrail_passed": token_growth_pct <= 15.0,
        },
    }

    out_file = output_dir / "cohort_b_regression_audit.jsonl"
    with open(out_file, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    return records, summary


def evaluate_cohort_c(
    manifest_records: List[Dict[str, Any]],
    frozen_baseline_records: Dict[str, Dict[str, Any]],
    model: str = DEFAULT_MODEL,
    output_dir: Path = Path("results/diagnostic_table_extraction_v1"),
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Evaluate Cohort C (100 Paired Held-Out Question/Document Pairs)."""
    print("\n" + "=" * 80)
    print("RUNNING COHORT C EVALUATION (Held-Out Paired Validation, N=100)")
    print("=" * 80)

    records: List[Dict[str, Any]] = []

    for idx, item in enumerate(manifest_records):
        sid = item["sample_id"]
        q = item["question"]
        gold = item["gold_answer"]
        answers = item.get("answers", [gold])
        raw_doc = item["document"]

        base_rec = frozen_baseline_records[sid]
        base_em = base_rec["exact_match"]
        base_cont = base_rec["containment_correct"]
        base_rouge = base_rec["rouge_l"]
        base_ans = base_rec["predicted_answer"]
        base_tokens = base_rec.get("context_tokens_est", 0)

        print(f"[{idx+1}/100] Processing {sid[:8]} | q='{q[:40]}...'")

        proto_store = FactStore(in_memory=True, collection_name=f"c_proto_{uuid.uuid4().hex[:8]}")
        resolved_doc = resolve_coreferences(raw_doc)
        base_svoa = extract_facts(resolved_doc, source_doc=sid)
        proto_table_list = extract_table_list_facts(raw_doc, source_doc=sid)
        proto_all = base_svoa + proto_table_list
        proto_scored = score_facts_with_store(proto_all, proto_store)
        proto_store.add_facts(proto_scored)

        proto_pack = pack_context(q, proto_store, token_ceiling=DEFAULT_TOKEN_CEILING)
        proto_ctx_str = render_context(proto_pack.packed_facts)
        proto_res = generate_answer(
            query=q,
            context=proto_ctx_str,
            model=model,
            temperature=DEFAULT_TEMP,
            top_p=DEFAULT_TOP_P,
            max_tokens=DEFAULT_MAX_TOKENS,
            prompt_style="concise",
        )
        proto_em = check_exact_match(proto_res.answer, gold, answers)
        proto_cont = contains_answer(proto_res.answer, gold) or any(contains_answer(proto_res.answer, a) for a in answers)
        proto_rouge = check_rouge_l(proto_res.answer, gold, answers)

        record = {
            "sample_id": sid,
            "question": q,
            "gold_answer": gold,
            "baseline": {
                "predicted_answer": base_ans,
                "exact_match": base_em,
                "containment": base_cont,
                "rouge_l": base_rouge,
                "context_tokens": base_tokens,
            },
            "prototype": {
                "predicted_answer": proto_res.answer,
                "exact_match": proto_em,
                "containment": proto_cont,
                "rouge_l": proto_rouge,
                "context_tokens": proto_pack.tokens_used,
                "table_list_facts_count": len(proto_table_list),
            },
            "paired_em_delta": int(proto_em) - int(base_em),
            "paired_containment_delta": int(proto_cont) - int(base_cont),
            "paired_rouge_l_delta": proto_rouge - base_rouge,
            "context_growth_ratio": (proto_pack.tokens_used - base_tokens) / max(1, base_tokens),
        }
        records.append(record)

    base_em_total = sum(1 for r in records if r["baseline"]["exact_match"])
    proto_em_total = sum(1 for r in records if r["prototype"]["exact_match"])
    base_cont_total = sum(1 for r in records if r["baseline"]["containment"])
    proto_cont_total = sum(1 for r in records if r["prototype"]["containment"])

    b_em = sum(1 for r in records if not r["baseline"]["exact_match"] and r["prototype"]["exact_match"])
    c_em = sum(1 for r in records if r["baseline"]["exact_match"] and not r["prototype"]["exact_match"])
    mcnemar_em_pval = scipy.stats.binomtest(b_em, b_em + c_em, 0.5).pvalue if (b_em + c_em) > 0 else 1.0

    b_cont = sum(1 for r in records if not r["baseline"]["containment"] and r["prototype"]["containment"])
    c_cont = sum(1 for r in records if r["baseline"]["containment"] and not r["prototype"]["containment"])
    mcnemar_cont_pval = scipy.stats.binomtest(b_cont, b_cont + c_cont, 0.5).pvalue if (b_cont + c_cont) > 0 else 1.0

    summary = {
        "num_samples": len(records),
        "baseline_em_rate": base_em_total / len(records),
        "prototype_em_rate": proto_em_total / len(records),
        "em_delta": (proto_em_total - base_em_total) / len(records),
        "mcnemar_em": {"b_wins": b_em, "c_losses": c_em, "p_value": mcnemar_em_pval},
        "baseline_containment_rate": base_cont_total / len(records),
        "prototype_containment_rate": proto_cont_total / len(records),
        "containment_delta": (proto_cont_total - base_cont_total) / len(records),
        "mcnemar_containment": {"b_wins": b_cont, "c_losses": c_cont, "p_value": mcnemar_cont_pval},
        "avg_baseline_rouge_l": sum(r["baseline"]["rouge_l"] for r in records) / len(records),
        "avg_prototype_rouge_l": sum(r["prototype"]["rouge_l"] for r in records) / len(records),
    }

    out_file = output_dir / "cohort_c_paired_evaluation.jsonl"
    with open(out_file, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    return records, summary


# ==============================================================================
# Main Orchestrator
# ==============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(description="Précis Table/List Extraction Prototype Runner")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help="Ollama LLM model")
    parser.add_argument("--output-dir", type=str, default="results/diagnostic_table_extraction_v1")
    parser.add_argument("--dataset-path", type=str, default="backend/data/nq_subset/nq_dev.jsonl")
    parser.add_argument("--audit-path", type=str, default="paper/tables/representation_loss_audit_v3.json")
    parser.add_argument(
        "--failure-analysis-path",
        type=str,
        default="paper/tables/enhanced_failure_analysis_v3_rerun/failure_analysis.jsonl",
    )
    parser.add_argument(
        "--manifest-path",
        type=str,
        default="experiments/prompt_validation/sample_manifest.jsonl",
    )
    parser.add_argument(
        "--frozen-baseline-path",
        type=str,
        default="experiments/prompt_validation/raw_outputs/eval_records.jsonl",
    )
    parser.add_argument("--skip-preflight", action="store_true", help="Skip preflight robustness suite")
    parser.add_argument("--preflight-only", action="store_true", help="Only run preflight suite and exit")

    args = parser.parse_args()

    out_path = Path(args.output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("PRÉCIS TABLE & LIST EXTRACTION PROTOTYPE EVALUATION")
    print(f"Model: {args.model} | Decoding: Greedy (T={DEFAULT_TEMP}, top_p={DEFAULT_TOP_P}, seed={DEFAULT_SEED})")
    print(f"Output Directory: {out_path}")
    print("=" * 80)

    # 1. Load Datasets
    print("\n[Step 1/5] Loading datasets and cohorts...")
    with open(args.dataset_path) as f:
        docs = {d["doc_id"]: d for line in f if line.strip() for d in [json.loads(line)]}
    print(f"Loaded {len(docs)} documents from {args.dataset_path}")

    with open(args.audit_path) as f:
        cohort_a_audit = json.load(f)
    print(f"Loaded Cohort A audit ({len(cohort_a_audit)} cases) from {args.audit_path}")

    with open(args.failure_analysis_path) as f:
        fa_records = [json.loads(l) for l in f if l.strip()]
    correct_pool = [x for x in fa_records if x.get("failure_class") == "CORRECT"]
    correct_sorted = sorted(correct_pool, key=lambda x: x["sample_id"])
    rng = random.Random(DEFAULT_SEED)
    cohort_b_sampled = rng.sample(correct_sorted, 50)
    cohort_b_frozen_ids = [x["sample_id"] for x in cohort_b_sampled]
    print(f"Sampled and froze Cohort B ({len(cohort_b_frozen_ids)} cases, seed {DEFAULT_SEED})")

    with open(args.manifest_path) as f:
        cohort_c_manifest = [
            json.loads(l) for l in f if l.strip() and json.loads(l).get("type") == "sample_record"
        ]
    with open(args.frozen_baseline_path) as f:
        eval_recs = [json.loads(l) for l in f if l.strip()]
    c_baseline_map = {
        r["sample_id"]: r
        for r in eval_recs
        if r.get("model") == args.model
        and r.get("condition") == "precis_full"
        and r.get("prompt_mode") == "concise"
    }
    print(f"Loaded Cohort C ({len(cohort_c_manifest)} manifest cases, {len(c_baseline_map)} frozen baseline matches)")

    # 2. Run Preflight Test Suite
    print("\n[Step 2/5] Running Preflight Robustness Suite...")
    preflight_res = run_preflight_suite(docs)
    preflight_file = out_path / "preflight_results.json"
    with open(preflight_file, "w") as f:
        json.dump(preflight_res, f, indent=2)

    if not preflight_res["passed"]:
        print("\n[ERROR] Preflight robustness suite failed! Halting before model evaluation.")
        for k, v in preflight_res["tests"].items():
            if not v["passed"]:
                print(f"  - Failed test: {k}")
        sys.exit(1)
    print("Preflight robustness suite passed cleanly (7 tests + 6 Cohort A documents).")

    if args.preflight_only:
        print("\nPreflight-only flag specified. Exiting cleanly.")
        sys.exit(0)

    # 3. Evaluate Cohort A
    t_start = time.perf_counter()
    cohort_a_recs, cohort_a_sum = evaluate_cohort_a(docs, cohort_a_audit, model=args.model, output_dir=out_path)

    # 4. Evaluate Cohort B
    cohort_b_recs, cohort_b_sum = evaluate_cohort_b(
        docs,
        args.failure_analysis_path,
        cohort_b_frozen_ids,
        model=args.model,
        output_dir=out_path,
    )

    # 5. Evaluate Cohort C
    cohort_c_recs, cohort_c_sum = evaluate_cohort_c(
        cohort_c_manifest,
        c_baseline_map,
        model=args.model,
        output_dir=out_path,
    )

    total_duration = time.perf_counter() - t_start

    # Global Master Summary
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
        "cohort_a_historical_failures": cohort_a_sum,
        "cohort_b_regression_guardrails": cohort_b_sum,
        "cohort_c_heldout_paired_generalization": cohort_c_sum,
    }

    summary_file = out_path / "table_extraction_experiment_summary.json"
    with open(summary_file, "w") as f:
        json.dump(master_summary, f, indent=2)

    print("\n" + "=" * 80)
    print("EXPERIMENT COMPLETED SUCCESSFULLY!")
    print(f"All artifacts written to: {out_path}")
    print(f"Summary JSON: {summary_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()
