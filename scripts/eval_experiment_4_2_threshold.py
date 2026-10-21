#!/usr/bin/env python3
"""
Précis Experiment 4.2: Full-Cohort Table-Selection Threshold Evaluation Runner.

Evaluates whether relaxing the table-selection threshold from theta=2.0 (Condition C)
to theta=0.0 (Condition D) improves end-to-end answer accuracy, answer containment,
and regression recovery on the frozen 200-case table-bearing confirmatory cohort
from Précis Experiment 3.

================================================================================
CANONICAL PROTOCOL INVARIANTS:
================================================================================
1. SOLE MANIPULATED VARIABLE:
   Condition C: Table retention with theta=2.0, include_lists=False.
   Condition D: Table retention with theta=0.0, include_lists=False.
   All other parameters (GFM table representation, header preservation, 100% row
   retention within selected tables up to 500-token chunks, 2,048 token ceiling,
   model, prompt, decoding, and scoring) are BIT-FOR-BIT IDENTICAL.

2. EVALUATION COHORT:
   Full canonical 200-case table-bearing confirmatory cohort from sample_manifest.jsonl.
   No outcome selection or cohort filtering.

3. FROZEN BASELINE REUSE:
   Condition A (Reference Naive RAG) and Condition B (Stage C Decompilation Baseline)
   are reused directly from verified frozen Stage C records.

4. EXPLICIT STATUS & DENOMINATOR ACCOUNTING:
   - 'success': Non-empty scored model response.
   - 'failed': Operational exception. EM, containment, ROUGE-L are strictly None.
   - 'unscorable': Empty or whitespace response. EM, containment, ROUGE-L are strictly None.
   - 'dry_run': Offline mode with zero model inference.
   A failed or unscorable response NEVER counts as an incorrect answer (exact_match=False).
   Paired tests evaluate only cases where both conditions succeeded.

5. EVIDENCE PATHWAY TRACKING:
   Tracks evidence presence at each stage:
   - evidence_in_source (raw document)
   - evidence_in_extracted_tables (all candidate tables in document)
   - evidence_in_selected_tables (tables passing threshold)
   - evidence_in_packed_context (retained within 2,048 token ceiling)
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import os
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Set, Tuple

# Ensure backend/src and scripts are on import path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import scipy.stats

from precis.evaluation.metrics import (
    compute_exact_match,
    compute_rouge_l,
    normalize_answer,
)
from precis.pipeline.inference import (
    CONCISE_PROMPT_TEMPLATE,
    OLLAMA_DEFAULT_BASE_URL,
    InferenceResult,
    OllamaConnectionError,
    OllamaInferenceError,
    build_prompt,
    check_ollama,
    generate_answer,
)
from eval_structural_decompilation_v3 import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL,
    DEFAULT_SEED,
    DEFAULT_TEMP,
    DEFAULT_TOKEN_CEILING,
    DEFAULT_TOP_P,
    StructuralDocumentParser,
    StructuredBlock,
)
from eval_table_selection_v2 import (
    ParsedTable,
    ParsedTableCell,
    ParsedTableRow,
    check_containment,
    check_exact_match,
    check_rouge_l,
    clean_tag_text,
    contains_answer,
    score_and_select_tables,
)

# Canonical benchmark invariants
EXPERIMENT_ID = "diagnostic_experiment_4_2_threshold"
MAX_TABLE_TOKENS = 500

# Verified Frozen Input SHA-256 Digests
EXPECTED_MANIFEST_HASH = "011553c0725621b7dda73aad12254d100e6fc15f49a5f80f4524156eb4e25db7"
EXPECTED_STAGE_C_HASH = "e10ea38f7cc7cfa9a98d494851de8c41c322b5f148dfff653077193917933687"
EXPECTED_DATASET_HASH = "14efc255a596433d6bf10dd853a1915474a5d3f6b47c593f77911ab4bb8eb491"


def compute_file_sha256(path: Path) -> str:
    """Compute hex SHA-256 digest of a file."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_config_fingerprint(
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMP,
    top_p: float = DEFAULT_TOP_P,
    seed: int = DEFAULT_SEED,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    token_ceiling: int = DEFAULT_TOKEN_CEILING,
    prompt_template: str = CONCISE_PROMPT_TEMPLATE,
    input_hashes: Optional[Dict[str, str]] = None,
) -> str:
    """Compute deterministic SHA-256 configuration fingerprint for Experiment 4.2."""
    config_dict = {
        "experiment_id": EXPERIMENT_ID,
        "model": model,
        "temperature": temperature,
        "top_p": top_p,
        "seed": seed,
        "max_tokens": max_tokens,
        "token_ceiling": token_ceiling,
        "prompt_template": prompt_template,
        "conditions": {
            "cond_a": "frozen_stage_c_naive_rag",
            "cond_b": "frozen_stage_c_decompilation_baseline",
            "cond_c": "gfm_table_retention_theta2_no_lists",
            "cond_d": "gfm_table_retention_theta0_no_lists",
        },
        "input_hashes": input_hashes or {},
    }
    payload = json.dumps(config_dict, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def estimate_text_tokens(text: str) -> int:
    """Subword heuristic estimator: int(len(words) * 1.3)."""
    words = len(text.split())
    return int(words * 1.3)


# ==============================================================================
# Markdown Table Rendering & Context Assembly
# ==============================================================================

def escape_pipes(s: str) -> str:
    """Escape vertical pipe characters for GFM table cell syntax."""
    return s.replace("|", "\\|").strip()


def render_gfm_table_chunks(
    block: StructuredBlock,
    max_tokens: int = MAX_TABLE_TOKENS,
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


def build_table_retention_context(
    raw_doc: str,
    query: str,
    table_threshold: float,
    max_table_tokens: int = MAX_TABLE_TOKENS,
    token_ceiling: int = DEFAULT_TOKEN_CEILING,
) -> Tuple[str, Dict[str, Any]]:
    """
    Construct packed prompt context from raw HTML document using compact GFM tables.
    table_threshold:
      theta=2.0 for Condition C
      theta=0.0 for Condition D
    include_lists: strictly False for both Condition C and Condition D.
    """
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

    # Build ParsedTable objects for scoring
    parsed_tables: List[ParsedTable] = []
    for b in tbl_blocks:
        p_rows: List[ParsedTableRow] = []
        for r_idx, r in enumerate(b.rows):
            cells = [ParsedTableCell(tag="td", text=c) for c in r]
            p_rows.append(ParsedTableRow(row_idx=r_idx, raw_html="", cells=cells))
        headers = b.headers if b.headers else [f"Col_{i}" for i in range(len(b.rows[0]))] if b.rows else []
        parsed_tables.append(ParsedTable(
            table_idx=b.block_id,
            caption=b.caption,
            headers=headers,
            rows=p_rows,
            raw_html="",
        ))

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

    # Context Packing
    clean_prose_str = clean_prose.strip()
    clean_prose_tokens = estimate_text_tokens(clean_prose_str) if clean_prose_str else 0

    packed_parts: List[str] = []
    cur_tokens = 0
    table_chunks_packed = 0
    table_tokens_packed = 0
    packed_rows = 0

    if clean_prose_str and clean_prose_tokens > 0:
        packed_parts.append(f"### Clean Prose:\n{clean_prose_str}")
        cur_tokens += clean_prose_tokens

    # Sort selected tables by score descending
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
    }

    return full_context, telemetry


# ==============================================================================
# Statistical Testing & Paired Differences
# ==============================================================================

def compute_mcnemar_exact(
    y_true_1: List[bool],
    y_true_2: List[bool],
) -> Dict[str, Any]:
    """
    McNemar's exact two-sided test for paired binary outcomes.
    Operates strictly over paired cases where both conditions succeeded.
    """
    if len(y_true_1) != len(y_true_2):
        raise ValueError(f"Mismatched sample lengths: {len(y_true_1)} vs {len(y_true_2)}")

    n = len(y_true_1)
    if n == 0:
        return {
            "status": "unavailable",
            "total_n": 0,
            "contingency_table": {"a_both_positive": 0, "b_cond1_pos_cond2_neg": 0, "c_cond1_neg_cond2_pos": 0, "d_both_negative": 0},
            "discordant_pairs": 0,
            "cond1_wins": 0,
            "cond2_wins": 0,
            "net_wins_cond1": 0,
            "risk_difference": None,
            "risk_difference_ci_95": None,
            "odds_ratio": None,
            "p_value": None,
            "statistically_significant_05": False,
        }

    a = sum(1 for y1, y2 in zip(y_true_1, y_true_2) if y1 and y2)
    b = sum(1 for y1, y2 in zip(y_true_1, y_true_2) if y1 and not y2)
    c = sum(1 for y1, y2 in zip(y_true_1, y_true_2) if not y1 and y2)
    d = sum(1 for y1, y2 in zip(y_true_1, y_true_2) if not y1 and not y2)

    n_disc = b + c
    if n_disc == 0:
        p_val = 1.0
        odds_ratio = 1.0
    else:
        res = scipy.stats.binomtest(b, n=n_disc, p=0.5, alternative="two-sided")
        p_val = float(res.pvalue)
        odds_ratio = float(b / c) if c > 0 else (float("inf") if b > 0 else 1.0)

    risk_diff = (b - c) / n if n > 0 else 0.0

    # 95% Confidence Interval for Risk Difference
    se = math.sqrt((b + c - ((b - c) ** 2) / n) / (n ** 2)) if n > 0 else 0.0
    ci_lower = max(-1.0, risk_diff - 1.96 * se)
    ci_upper = min(1.0, risk_diff + 1.96 * se)

    return {
        "status": "computed",
        "total_n": n,
        "contingency_table": {
            "a_both_positive": a,
            "b_cond1_pos_cond2_neg": b,
            "c_cond1_neg_cond2_pos": c,
            "d_both_negative": d,
        },
        "discordant_pairs": n_disc,
        "cond1_wins": b,
        "cond2_wins": c,
        "net_wins_cond1": b - c,
        "risk_difference": round(risk_diff, 4),
        "risk_difference_ci_95": [round(ci_lower, 4), round(ci_upper, 4)],
        "odds_ratio": round(odds_ratio, 4) if odds_ratio != float("inf") else "inf",
        "p_value": p_val,
        "statistically_significant_05": p_val < 0.05 if p_val is not None else False,
    }


def make_paired_case_diff(
    c1: Dict[str, Any],
    c2: Dict[str, Any],
) -> Dict[str, Any]:
    """Compute paired diff for a single case, strictly requiring both status == 'success'."""
    s1 = c1.get("status")
    s2 = c2.get("status")
    if s1 != "success" or s2 != "success":
        reasons = []
        if s1 != "success":
            reasons.append(f"cond1 status='{s1}'")
        if s2 != "success":
            reasons.append(f"cond2 status='{s2}'")
        return {
            "status": "excluded",
            "reason": "; ".join(reasons),
            "em_win": None,
            "em_loss": None,
            "containment_win": None,
            "containment_loss": None,
            "token_delta": None,
        }

    em1 = bool(c1.get("exact_match", False))
    em2 = bool(c2.get("exact_match", False))
    cont1 = bool(c1.get("containment", False))
    cont2 = bool(c2.get("containment", False))
    tok1 = c1.get("context_estimated_tokens", 0) or 0
    tok2 = c2.get("context_estimated_tokens", 0) or 0

    return {
        "status": "valid",
        "em_win": em1 and not em2,
        "em_loss": not em1 and em2,
        "containment_win": cont1 and not cont2,
        "containment_loss": not cont1 and cont2,
        "token_delta": tok1 - tok2,
    }


# ==============================================================================
# Cohort Verification & Frozen Baseline Loader
# ==============================================================================

def load_and_verify_frozen_cohort(
    manifest_path: Path,
    stage_c_path: Path,
    dataset_path: Path,
) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """
    Load and verify bit-for-bit the frozen manifest, Stage C records, and dataset.
    Returns:
    - 200 confirmatory manifest cases
    - Stage C records map (by sample_id)
    - Dataset raw docs map (by sample_id)
    """
    m_hash = compute_file_sha256(manifest_path)
    if m_hash != EXPECTED_MANIFEST_HASH:
        raise ValueError(f"Manifest hash mismatch: expected {EXPECTED_MANIFEST_HASH}, got {m_hash}")

    c_hash = compute_file_sha256(stage_c_path)
    if c_hash != EXPECTED_STAGE_C_HASH:
        raise ValueError(f"Stage C hash mismatch: expected {EXPECTED_STAGE_C_HASH}, got {c_hash}")

    d_hash = compute_file_sha256(dataset_path)
    if d_hash != EXPECTED_DATASET_HASH:
        raise ValueError(f"Dataset hash mismatch: expected {EXPECTED_DATASET_HASH}, got {d_hash}")

    # Load manifest
    manifest_cases = []
    with open(manifest_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("type") == "sample_record" and rec.get("stratum") == "table_bearing":
                manifest_cases.append(rec)

    if len(manifest_cases) != 200:
        raise ValueError(f"Expected 200 table_bearing cases in manifest, found {len(manifest_cases)}")

    unique_cids = {m["sample_id"] for m in manifest_cases}
    if len(unique_cids) != 200:
        raise ValueError(f"Expected 200 unique IDs in manifest, found {len(unique_cids)}")

    # Load Stage C records
    stage_c_records = {}
    with open(stage_c_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            cid = rec.get("sample_id") or rec.get("case_id")
            if cid:
                stage_c_records[cid] = rec

    for cid in unique_cids:
        if cid not in stage_c_records:
            raise KeyError(f"Missing case {cid} in Stage C records")
        rec = stage_c_records[cid]
        if rec["cond_a"]["status"] != "success" or rec["cond_b"]["status"] != "success":
            raise ValueError(f"Case {cid} has non-success status in Stage C baseline records")

    # Load dataset
    raw_docs = {}
    with open(dataset_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            cid = rec.get("sample_id") or rec.get("id") or rec.get("doc_id")
            if cid in unique_cids:
                raw_docs[cid] = rec

    if len(raw_docs) != 200:
        raise ValueError(f"Expected 200 dataset matches for cohort, found {len(raw_docs)}")

    return manifest_cases, stage_c_records, raw_docs


# ==============================================================================
# Aggregation & Reporting Helpers
# ==============================================================================

def compute_condition_summary(records: List[Dict[str, Any]], cond_key: str) -> Dict[str, Any]:
    """Compute aggregate summary metrics for a condition over the full cohort."""
    attempted = len(records)
    successes = [r[cond_key] for r in records if r[cond_key].get("status") == "success"]
    failed = sum(1 for r in records if r[cond_key].get("status") == "failed")
    unscorable = sum(1 for r in records if r[cond_key].get("status") == "unscorable")
    dry_run = sum(1 for r in records if r[cond_key].get("status") == "dry_run")
    scored_n = len(successes)

    if scored_n == 0:
        return {
            "cases_attempted": attempted,
            "status_counts": {
                "success": 0,
                "failed": failed,
                "unscorable": unscorable,
                "dry_run": dry_run,
            },
            "scored_denominator": 0,
            "exact_match_count": None,
            "exact_match_rate": None,
            "containment_count": None,
            "containment_rate": None,
            "rouge_l_mean": None,
            "rouge_l_median": None,
            "context_estimated_tokens": {"mean": None, "median": None, "p95": None},
            "full_prompt_model_tokens": {"mean": None, "median": None, "p95": None},
            "generated_tokens_mean": None,
            "latency_ms_mean": None,
            "empty_context_count": 0,
            "empty_context_rate": 0.0,
            "evidence_in_context_count": 0,
            "evidence_in_context_rate": 0.0,
        }

    em_cnt = sum(1 for s in successes if s.get("exact_match") is True)
    cont_cnt = sum(1 for s in successes if s.get("containment") is True)
    rouge_vals = [s.get("rouge_l", 0.0) for s in successes if s.get("rouge_l") is not None]

    est_toks = [s.get("context_estimated_tokens", 0) or 0 for s in successes]
    model_toks = [s.get("full_prompt_model_tokens") for s in successes if s.get("full_prompt_model_tokens") is not None]
    gen_toks = [s.get("generated_tokens", 0) or 0 for s in successes]
    latencies = [s.get("latency_ms", 0) or 0 for s in successes]

    empty_ctx = sum(1 for s in successes if (s.get("context_estimated_tokens", 0) or 0) == 0)
    ev_in_ctx = sum(1 for s in successes if s.get("evidence_in_packed_context") is True)

    sorted_est = sorted(est_toks)
    p95_idx = int(0.95 * len(sorted_est)) - 1 if sorted_est else 0

    sorted_model = sorted(model_toks) if model_toks else []
    p95_m_idx = int(0.95 * len(sorted_model)) - 1 if sorted_model else 0

    return {
        "cases_attempted": attempted,
        "status_counts": {
            "success": scored_n,
            "failed": failed,
            "unscorable": unscorable,
            "dry_run": dry_run,
        },
        "scored_denominator": scored_n,
        "exact_match_count": em_cnt,
        "exact_match_rate": round(em_cnt / scored_n, 4),
        "containment_count": cont_cnt,
        "containment_rate": round(cont_cnt / scored_n, 4),
        "rouge_l_mean": round(sum(rouge_vals) / len(rouge_vals), 4) if rouge_vals else 0.0,
        "rouge_l_median": round(float(scipy.stats.scoreatpercentile(rouge_vals, 50)), 4) if rouge_vals else 0.0,
        "context_estimated_tokens": {
            "mean": round(sum(est_toks) / len(est_toks), 1) if est_toks else 0.0,
            "median": round(float(scipy.stats.scoreatpercentile(est_toks, 50)), 1) if est_toks else 0.0,
            "p95": round(float(sorted_est[max(0, p95_idx)]), 1) if sorted_est else 0.0,
        },
        "full_prompt_model_tokens": {
            "mean": round(sum(model_toks) / len(model_toks), 1) if model_toks else None,
            "median": round(float(scipy.stats.scoreatpercentile(model_toks, 50)), 1) if model_toks else None,
            "p95": round(float(sorted_model[max(0, p95_m_idx)]), 1) if sorted_model else None,
        },
        "generated_tokens_mean": round(sum(gen_toks) / len(gen_toks), 1) if gen_toks else 0.0,
        "latency_ms_mean": round(sum(latencies) / len(latencies), 1) if latencies else 0.0,
        "empty_context_count": empty_ctx,
        "empty_context_rate": round(empty_ctx / scored_n, 4),
        "evidence_in_context_count": ev_in_ctx,
        "evidence_in_context_rate": round(ev_in_ctx / scored_n, 4),
    }


def compute_paired_comparison_summary(
    records: List[Dict[str, Any]],
    cond1_key: str,
    cond2_key: str,
    metric: str = "exact_match",
) -> Dict[str, Any]:
    """Compute paired comparison summary between two conditions on a given metric."""
    valid_pairs = []
    excluded_cases = []

    for r in records:
        c1 = r[cond1_key]
        c2 = r[cond2_key]
        s1 = c1.get("status")
        s2 = c2.get("status")
        cid = r["case_id"]

        if s1 == "success" and s2 == "success":
            valid_pairs.append((bool(c1.get(metric, False)), bool(c2.get(metric, False))))
        else:
            excluded_cases.append({"case_id": cid, "reason": f"cond1={s1}, cond2={s2}"})

    if not valid_pairs:
        return {
            "status": "unavailable",
            "evaluated_pairs": 0,
            "excluded_pairs_count": len(excluded_cases),
            "excluded_cases": excluded_cases,
            "mcnemar": compute_mcnemar_exact([], []),
        }

    y1 = [p[0] for p in valid_pairs]
    y2 = [p[1] for p in valid_pairs]
    mcn = compute_mcnemar_exact(y1, y2)

    return {
        "status": "computed",
        "evaluated_pairs": len(valid_pairs),
        "excluded_pairs_count": len(excluded_cases),
        "excluded_cases": excluded_cases,
        "mcnemar": mcn,
    }


# ==============================================================================
# Main Runner Loop
# ==============================================================================

def run_experiment_4_2(
    output_dir: Path,
    dry_run: bool = False,
    smoke_test: bool = False,
    force: bool = False,
    base_url: str = OLLAMA_DEFAULT_BASE_URL,
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMP,
    top_p: float = DEFAULT_TOP_P,
    seed: int = DEFAULT_SEED,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    token_ceiling: int = DEFAULT_TOKEN_CEILING,
) -> Dict[str, Any]:
    """Execute Experiment 4.2 full-cohort evaluation."""
    manifest_path = REPO_ROOT / "results" / "diagnostic_structural_decompilation_v3" / "sample_manifest.jsonl"
    stage_c_path = REPO_ROOT / "results" / "diagnostic_structural_decompilation_v3" / "eval_records_stage_c.jsonl"
    dataset_path = REPO_ROOT / "backend" / "data" / "nq_subset" / "nq_dev.jsonl"

    print("=" * 80)
    print("PRÉCIS EXPERIMENT 4.2: FULL-COHORT TABLE-SELECTION THRESHOLD EVALUATION")
    print("=" * 80)
    print(f"Output directory: {output_dir}")
    print(f"Dry run mode:     {dry_run}")
    print(f"Smoke test mode:  {smoke_test}")

    # Safety check on output directory
    if output_dir.exists() and any(output_dir.iterdir()) and not force:
        raise FileExistsError(
            f"Output directory {output_dir} already exists and is non-empty. "
            "Experiment 4.2 mandates never overwriting existing results without explicit --force."
        )
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Preflight Verification
    print("\n[Step 1/5] Verifying frozen cohort inputs bit-for-bit...")
    manifest_cases, stage_c_records, raw_docs = load_and_verify_frozen_cohort(
        manifest_path, stage_c_path, dataset_path
    )
    print(f"-> Verified manifest SHA-256: {EXPECTED_MANIFEST_HASH}")
    print(f"-> Verified Stage C SHA-256:  {EXPECTED_STAGE_C_HASH}")
    print(f"-> Verified dataset SHA-256:  {EXPECTED_DATASET_HASH}")
    print(f"-> Verified cohort size:      {len(manifest_cases)} unique table-bearing cases")

    input_hashes = {
        "sample_manifest_sha256": EXPECTED_MANIFEST_HASH,
        "stage_c_records_sha256": EXPECTED_STAGE_C_HASH,
        "nq_dev_dataset_sha256": EXPECTED_DATASET_HASH,
    }
    config_fingerprint = compute_config_fingerprint(
        model=model,
        temperature=temperature,
        top_p=top_p,
        seed=seed,
        max_tokens=max_tokens,
        token_ceiling=token_ceiling,
        input_hashes=input_hashes,
    )
    print(f"-> Configuration fingerprint: {config_fingerprint}")

    # Check Ollama if not dry-run
    if not dry_run:
        print("\n[Step 2/5] Checking Ollama daemon connectivity and resident model...")
        if not check_ollama(base_url):
            raise RuntimeError(f"Ollama daemon not reachable at {base_url}")
        print(f"-> Ollama daemon responsive at {base_url}")

    # Determine execution cohort
    eval_cases = manifest_cases
    if smoke_test:
        eval_cases = manifest_cases[:5]
        print(f"-> Smoke test active: evaluating first {len(eval_cases)} cases only.")

    print(f"\n[Step 3/5] Executing Condition C (theta=2.0) and Condition D (theta=0.0) on {len(eval_cases)} cases...")

    case_records: List[Dict[str, Any]] = []
    regression_recovery_records: List[Dict[str, Any]] = []

    start_time = time.time()

    for idx, m_case in enumerate(eval_cases, start=1):
        cid = m_case["sample_id"]
        doc_entry = raw_docs[cid]
        q = doc_entry["question"]
        gold = doc_entry["gold_answer"]
        answers = doc_entry.get("answers", [gold])
        raw_doc = doc_entry["document"]

        # Reused frozen predictions from Stage C
        frozen_c = stage_c_records[cid]
        cond_a_raw = frozen_c["cond_a"]
        cond_b_raw = frozen_c["cond_b"]

        cond_a = {
            "condition_id": "cond_a_reference",
            "predicted_answer": cond_a_raw.get("predicted_answer", ""),
            "raw_response": cond_a_raw.get("raw_response", ""),
            "exact_match": cond_a_raw.get("exact_match"),
            "containment": cond_a_raw.get("containment"),
            "rouge_l": cond_a_raw.get("rouge_l"),
            "context_estimated_tokens": cond_a_raw.get("context_tokens", 0),
            "full_prompt_model_tokens": None,
            "generated_tokens": 0,
            "latency_ms": 0,
            "status": cond_a_raw.get("status", "success"),
            "error_message": None,
            "provenance": {
                "source": "results/diagnostic_structural_decompilation_v3/eval_records_stage_c.jsonl",
                "stage_c_config_fingerprint": frozen_c.get("config_fingerprint"),
            },
        }

        cond_b = {
            "condition_id": "cond_b_baseline",
            "predicted_answer": cond_b_raw.get("predicted_answer", ""),
            "raw_response": cond_b_raw.get("raw_response", ""),
            "exact_match": cond_b_raw.get("exact_match"),
            "containment": cond_b_raw.get("containment"),
            "rouge_l": cond_b_raw.get("rouge_l"),
            "context_estimated_tokens": cond_b_raw.get("context_tokens", 0),
            "full_prompt_model_tokens": None,
            "generated_tokens": 0,
            "latency_ms": 0,
            "status": cond_b_raw.get("status", "success"),
            "error_message": None,
            "provenance": {
                "source": "results/diagnostic_structural_decompilation_v3/eval_records_stage_c.jsonl",
                "stage_c_config_fingerprint": frozen_c.get("config_fingerprint"),
                "struct_facts": cond_b_raw.get("struct_facts", 0),
            },
        }

        # Stage C historical classification
        em_a = bool(cond_a["exact_match"])
        em_b = bool(cond_b["exact_match"])
        if em_a and not em_b:
            stage_c_class = "P1_regression"
        elif not em_a and em_b:
            stage_c_class = "P2_recovery"
        elif em_a and em_b:
            stage_c_class = "both_win"
        else:
            stage_c_class = "both_loss"

        # Evidence checking on source document
        parser = StructuralDocumentParser(raw_doc)
        _, blocks = parser.parse()
        tbl_blocks = [b for b in blocks if b.block_type == "table"]

        ev_in_source = any(contains_answer(raw_doc, ans) for ans in answers)
        all_tables_text = " ".join(
            " ".join(b.headers) + " " + " ".join(" ".join(r) for r in b.rows) + " " + b.caption
            for b in tbl_blocks
        )
        ev_in_all_tables = any(contains_answer(all_tables_text, ans) for ans in answers)

        # Build Contexts
        # Condition C: theta=2.0
        ctx_c, telem_c = build_table_retention_context(
            raw_doc=raw_doc,
            query=q,
            table_threshold=2.0,
            max_table_tokens=MAX_TABLE_TOKENS,
            token_ceiling=token_ceiling,
        )

        # Condition D: theta=0.0
        ctx_d, telem_d = build_table_retention_context(
            raw_doc=raw_doc,
            query=q,
            table_threshold=0.0,
            max_table_tokens=MAX_TABLE_TOKENS,
            token_ceiling=token_ceiling,
        )

        # Check evidence in selected tables and packed contexts
        sel_c_ids = {s["block_id"] for s in telem_c["selection"] if s["decision"].startswith("SELECTED")}
        sel_c_text = " ".join(
            " ".join(b.headers) + " " + " ".join(" ".join(r) for r in b.rows) + " " + b.caption
            for b in tbl_blocks if b.block_id in sel_c_ids
        )
        ev_in_sel_c = any(contains_answer(sel_c_text, ans) for ans in answers)
        ev_in_ctx_c = any(contains_answer(ctx_c, ans) for ans in answers)

        sel_d_ids = {s["block_id"] for s in telem_d["selection"] if s["decision"].startswith("SELECTED")}
        sel_d_text = " ".join(
            " ".join(b.headers) + " " + " ".join(" ".join(r) for r in b.rows) + " " + b.caption
            for b in tbl_blocks if b.block_id in sel_d_ids
        )
        ev_in_sel_d = any(contains_answer(sel_d_text, ans) for ans in answers)
        ev_in_ctx_d = any(contains_answer(ctx_d, ans) for ans in answers)

        if dry_run:
            cond_c = {
                "condition_id": "cond_c_structural_retention_theta2",
                "threshold": 2.0,
                "predicted_answer": None,
                "raw_response": None,
                "exact_match": None,
                "containment": None,
                "rouge_l": None,
                "context_estimated_tokens": telem_c["total_context_estimated_tokens"],
                "full_prompt_model_tokens": None,
                "generated_tokens": 0,
                "latency_ms": 0,
                "status": "dry_run",
                "error_message": None,
                "selected_tables_count": telem_c["selected_tables_count"],
                "selected_rows_count": telem_c["selected_rows_count"],
                "packed_rows_count": telem_c["packed_rows_count"],
                "evidence_in_selected_tables": ev_in_sel_c,
                "evidence_in_packed_context": ev_in_ctx_c,
                "context_is_empty": telem_c["zero_context"],
                "provenance": {"harness": "eval_experiment_4_2_threshold.py", "mode": "dry_run"},
                "telemetry": telem_c,
            }
            cond_d = {
                "condition_id": "cond_d_structural_retention_theta0",
                "threshold": 0.0,
                "predicted_answer": None,
                "raw_response": None,
                "exact_match": None,
                "containment": None,
                "rouge_l": None,
                "context_estimated_tokens": telem_d["total_context_estimated_tokens"],
                "full_prompt_model_tokens": None,
                "generated_tokens": 0,
                "latency_ms": 0,
                "status": "dry_run",
                "error_message": None,
                "selected_tables_count": telem_d["selected_tables_count"],
                "selected_rows_count": telem_d["selected_rows_count"],
                "packed_rows_count": telem_d["packed_rows_count"],
                "evidence_in_selected_tables": ev_in_sel_d,
                "evidence_in_packed_context": ev_in_ctx_d,
                "context_is_empty": telem_d["zero_context"],
                "provenance": {"harness": "eval_experiment_4_2_threshold.py", "mode": "dry_run"},
                "telemetry": telem_d,
            }
        else:
            # Condition C live inference
            try:
                res_c = generate_answer(
                    query=q,
                    context=ctx_c,
                    model=model,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                    prompt_style="concise",
                    base_url=base_url,
                )
                raw_ans_c = res_c.answer if res_c.answer is not None else ""
                pred_c = raw_ans_c.strip()
                if not pred_c:
                    cond_c = {
                        "condition_id": "cond_c_structural_retention_theta2",
                        "threshold": 2.0,
                        "predicted_answer": "",
                        "raw_response": raw_ans_c,
                        "exact_match": None,
                        "containment": None,
                        "rouge_l": None,
                        "context_estimated_tokens": telem_c["total_context_estimated_tokens"],
                        "full_prompt_model_tokens": res_c.prompt_tokens,
                        "generated_tokens": res_c.tokens_generated,
                        "latency_ms": res_c.latency_ms,
                        "status": "unscorable",
                        "error_message": "Empty or whitespace model response",
                        "selected_tables_count": telem_c["selected_tables_count"],
                        "selected_rows_count": telem_c["selected_rows_count"],
                        "packed_rows_count": telem_c["packed_rows_count"],
                        "evidence_in_selected_tables": ev_in_sel_c,
                        "evidence_in_packed_context": ev_in_ctx_c,
                        "context_is_empty": telem_c["zero_context"],
                        "provenance": {"model": model, "prompt_style": "concise"},
                        "telemetry": telem_c,
                    }
                else:
                    cond_c = {
                        "condition_id": "cond_c_structural_retention_theta2",
                        "threshold": 2.0,
                        "predicted_answer": pred_c,
                        "raw_response": raw_ans_c,
                        "exact_match": check_exact_match(pred_c, gold, answers),
                        "containment": check_containment(pred_c, gold, answers),
                        "rouge_l": check_rouge_l(pred_c, gold, answers),
                        "context_estimated_tokens": telem_c["total_context_estimated_tokens"],
                        "full_prompt_model_tokens": res_c.prompt_tokens,
                        "generated_tokens": res_c.tokens_generated,
                        "latency_ms": res_c.latency_ms,
                        "status": "success",
                        "error_message": None,
                        "selected_tables_count": telem_c["selected_tables_count"],
                        "selected_rows_count": telem_c["selected_rows_count"],
                        "packed_rows_count": telem_c["packed_rows_count"],
                        "evidence_in_selected_tables": ev_in_sel_c,
                        "evidence_in_packed_context": ev_in_ctx_c,
                        "context_is_empty": telem_c["zero_context"],
                        "provenance": {"model": model, "prompt_style": "concise"},
                        "telemetry": telem_c,
                    }
            except Exception as exc:
                cond_c = {
                    "condition_id": "cond_c_structural_retention_theta2",
                    "threshold": 2.0,
                    "predicted_answer": None,
                    "raw_response": None,
                    "exact_match": None,
                    "containment": None,
                    "rouge_l": None,
                    "context_estimated_tokens": telem_c["total_context_estimated_tokens"],
                    "full_prompt_model_tokens": None,
                    "generated_tokens": 0,
                    "latency_ms": 0,
                    "status": "failed",
                    "error_message": str(exc),
                    "selected_tables_count": telem_c["selected_tables_count"],
                    "selected_rows_count": telem_c["selected_rows_count"],
                    "packed_rows_count": telem_c["packed_rows_count"],
                    "evidence_in_selected_tables": ev_in_sel_c,
                    "evidence_in_packed_context": ev_in_ctx_c,
                    "context_is_empty": telem_c["zero_context"],
                    "provenance": {"model": model, "prompt_style": "concise"},
                    "telemetry": telem_c,
                }

            # Condition D live inference
            try:
                res_d = generate_answer(
                    query=q,
                    context=ctx_d,
                    model=model,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                    prompt_style="concise",
                    base_url=base_url,
                )
                raw_ans_d = res_d.answer if res_d.answer is not None else ""
                pred_d = raw_ans_d.strip()
                if not pred_d:
                    cond_d = {
                        "condition_id": "cond_d_structural_retention_theta0",
                        "threshold": 0.0,
                        "predicted_answer": "",
                        "raw_response": raw_ans_d,
                        "exact_match": None,
                        "containment": None,
                        "rouge_l": None,
                        "context_estimated_tokens": telem_d["total_context_estimated_tokens"],
                        "full_prompt_model_tokens": res_d.prompt_tokens,
                        "generated_tokens": res_d.tokens_generated,
                        "latency_ms": res_d.latency_ms,
                        "status": "unscorable",
                        "error_message": "Empty or whitespace model response",
                        "selected_tables_count": telem_d["selected_tables_count"],
                        "selected_rows_count": telem_d["selected_rows_count"],
                        "packed_rows_count": telem_d["packed_rows_count"],
                        "evidence_in_selected_tables": ev_in_sel_d,
                        "evidence_in_packed_context": ev_in_ctx_d,
                        "context_is_empty": telem_d["zero_context"],
                        "provenance": {"model": model, "prompt_style": "concise"},
                        "telemetry": telem_d,
                    }
                else:
                    cond_d = {
                        "condition_id": "cond_d_structural_retention_theta0",
                        "threshold": 0.0,
                        "predicted_answer": pred_d,
                        "raw_response": raw_ans_d,
                        "exact_match": check_exact_match(pred_d, gold, answers),
                        "containment": check_containment(pred_d, gold, answers),
                        "rouge_l": check_rouge_l(pred_d, gold, answers),
                        "context_estimated_tokens": telem_d["total_context_estimated_tokens"],
                        "full_prompt_model_tokens": res_d.prompt_tokens,
                        "generated_tokens": res_d.tokens_generated,
                        "latency_ms": res_d.latency_ms,
                        "status": "success",
                        "error_message": None,
                        "selected_tables_count": telem_d["selected_tables_count"],
                        "selected_rows_count": telem_d["selected_rows_count"],
                        "packed_rows_count": telem_d["packed_rows_count"],
                        "evidence_in_selected_tables": ev_in_sel_d,
                        "evidence_in_packed_context": ev_in_ctx_d,
                        "context_is_empty": telem_d["zero_context"],
                        "provenance": {"model": model, "prompt_style": "concise"},
                        "telemetry": telem_d,
                    }
            except Exception as exc:
                cond_d = {
                    "condition_id": "cond_d_structural_retention_theta0",
                    "threshold": 0.0,
                    "predicted_answer": None,
                    "raw_response": None,
                    "exact_match": None,
                    "containment": None,
                    "rouge_l": None,
                    "context_estimated_tokens": telem_d["total_context_estimated_tokens"],
                    "full_prompt_model_tokens": None,
                    "generated_tokens": 0,
                    "latency_ms": 0,
                    "status": "failed",
                    "error_message": str(exc),
                    "selected_tables_count": telem_d["selected_tables_count"],
                    "selected_rows_count": telem_d["selected_rows_count"],
                    "packed_rows_count": telem_d["packed_rows_count"],
                    "evidence_in_selected_tables": ev_in_sel_d,
                    "evidence_in_packed_context": ev_in_ctx_d,
                    "context_is_empty": telem_d["zero_context"],
                    "provenance": {"model": model, "prompt_style": "concise"},
                    "telemetry": telem_d,
                }

        case_rec = {
            "case_id": cid,
            "question": q,
            "gold_answer": gold,
            "answers": answers,
            "stratum": "table_bearing",
            "priority_cohort": stage_c_class,
            "evidence_in_source": ev_in_source,
            "evidence_in_all_tables": ev_in_all_tables,
            "cond_a": cond_a,
            "cond_b": cond_b,
            "cond_c": cond_c,
            "cond_d": cond_d,
            "d_vs_c": make_paired_case_diff(cond_d, cond_c),
            "c_vs_b": make_paired_case_diff(cond_c, cond_b),
            "d_vs_b": make_paired_case_diff(cond_d, cond_b),
            "c_vs_a": make_paired_case_diff(cond_c, cond_a),
            "d_vs_a": make_paired_case_diff(cond_d, cond_a),
        }
        case_records.append(case_rec)

        # Failure Categorization for C and D
        def classify_failure(cond_data: Dict[str, Any], ev_sel: bool, ev_ctx: bool) -> str:
            if cond_data.get("exact_match") is True:
                return "NONE_CORRECT"
            if cond_data.get("status") in ["failed", "unscorable", "dry_run"]:
                return f"EXECUTION_{cond_data.get('status').upper()}"
            if not ev_in_source:
                return "NO_EVIDENCE_IN_SOURCE"
            if not ev_in_all_tables:
                return "EXTRACTION_OMISSION"
            if not ev_sel:
                return "SELECTION_FAILURE"
            if not ev_ctx:
                return "PACKING_FAILURE"
            if cond_data.get("containment") is True:
                return "SURFACE_FORM_MISMATCH"
            return "GENERATION_REASONING_FAILURE"

        fail_cat_c = classify_failure(cond_c, ev_in_sel_c, ev_in_ctx_c)
        fail_cat_d = classify_failure(cond_d, ev_in_sel_d, ev_in_ctx_d)

        audit_entry = {
            "case_id": cid,
            "question": q,
            "gold_answer": gold,
            "answers": answers,
            "stage_c_classification": stage_c_class,
            "cond_a_em": cond_a.get("exact_match"),
            "cond_b_em": cond_b.get("exact_match"),
            "cond_c_em": cond_c.get("exact_match"),
            "cond_d_em": cond_d.get("exact_match"),
            "cond_a_pred": cond_a.get("predicted_answer"),
            "cond_b_pred": cond_b.get("predicted_answer"),
            "cond_c_pred": cond_c.get("predicted_answer"),
            "cond_d_pred": cond_d.get("predicted_answer"),
            "transitions": {
                "d_fixes_c": bool(cond_d.get("exact_match") and not cond_c.get("exact_match")),
                "d_regresses_c": bool(not cond_d.get("exact_match") and cond_c.get("exact_match")),
                "c_recovers_b_rel_a": bool(cond_c.get("exact_match") and not cond_b.get("exact_match") and cond_a.get("exact_match")),
                "d_recovers_b_rel_a": bool(cond_d.get("exact_match") and not cond_b.get("exact_match") and cond_a.get("exact_match")),
                "c_loses_b_rec_rel_a": bool(not cond_c.get("exact_match") and cond_b.get("exact_match") and not cond_a.get("exact_match")),
                "d_loses_b_rec_rel_a": bool(not cond_d.get("exact_match") and cond_b.get("exact_match") and not cond_a.get("exact_match")),
            },
            "evidence_path": {
                "evidence_in_source": ev_in_source,
                "evidence_in_all_tables": ev_in_all_tables,
                "evidence_in_selected_tables_c": ev_in_sel_c,
                "evidence_in_selected_tables_d": ev_in_sel_d,
                "evidence_in_packed_context_c": ev_in_ctx_c,
                "evidence_in_packed_context_d": ev_in_ctx_d,
            },
            "failure_category_c": fail_cat_c,
            "failure_category_d": fail_cat_d,
        }
        regression_recovery_records.append(audit_entry)

        if idx % 20 == 0 or idx == len(eval_cases):
            elapsed = time.time() - start_time
            print(f"[{idx:3d}/{len(eval_cases)}] Processed in {elapsed:.1f}s | Latest: '{q[:40]}...'")

    # 4. Save Eval Records & Audit
    print("\n[Step 4/5] Serializing output records and paired statistical summaries...")

    records_file = output_dir / "eval_records.jsonl"
    with open(records_file, "w", encoding="utf-8") as f:
        run_header = {
            "type": "run_header",
            "experiment_id": EXPERIMENT_ID,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "dry_run": dry_run,
            "total_cases": len(case_records),
            "hyperparameters": {
                "model": model,
                "temperature": temperature,
                "top_p": top_p,
                "seed": seed,
                "max_tokens": max_tokens,
                "token_ceiling": token_ceiling,
                "cond_c_threshold": 2.0,
                "cond_d_threshold": 0.0,
                "include_lists": False,
            },
            "config_fingerprint": config_fingerprint,
            "input_hashes": input_hashes,
        }
        f.write(json.dumps(run_header) + "\n")
        for cr in case_records:
            f.write(json.dumps(cr) + "\n")

    audit_file = output_dir / "regression_recovery_audit.jsonl"
    with open(audit_file, "w", encoding="utf-8") as f:
        for ar in regression_recovery_records:
            f.write(json.dumps(ar) + "\n")

    # Aggregate summaries
    cond_summaries = {
        "cond_a": compute_condition_summary(case_records, "cond_a"),
        "cond_b": compute_condition_summary(case_records, "cond_b"),
        "cond_c": compute_condition_summary(case_records, "cond_c"),
        "cond_d": compute_condition_summary(case_records, "cond_d"),
    }

    paired_em = {
        "d_vs_c": compute_paired_comparison_summary(case_records, "cond_d", "cond_c", metric="exact_match"),
        "c_vs_b": compute_paired_comparison_summary(case_records, "cond_c", "cond_b", metric="exact_match"),
        "d_vs_b": compute_paired_comparison_summary(case_records, "cond_d", "cond_b", metric="exact_match"),
        "c_vs_a": compute_paired_comparison_summary(case_records, "cond_c", "cond_a", metric="exact_match"),
        "d_vs_a": compute_paired_comparison_summary(case_records, "cond_d", "cond_a", metric="exact_match"),
    }

    paired_cont = {
        "d_vs_c": compute_paired_comparison_summary(case_records, "cond_d", "cond_c", metric="containment"),
        "c_vs_b": compute_paired_comparison_summary(case_records, "cond_c", "cond_b", metric="containment"),
        "d_vs_b": compute_paired_comparison_summary(case_records, "cond_d", "cond_b", metric="containment"),
        "c_vs_a": compute_paired_comparison_summary(case_records, "cond_c", "cond_a", metric="containment"),
        "d_vs_a": compute_paired_comparison_summary(case_records, "cond_d", "cond_a", metric="containment"),
    }

    aggregate_summary = {
        "metadata": {
            "experiment_id": EXPERIMENT_ID,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "total_cases": len(case_records),
            "dry_run": dry_run,
            "smoke_test": smoke_test,
            "config_fingerprint": config_fingerprint,
        },
        "condition_summaries": cond_summaries,
    }

    paired_comparisons_summary = {
        "metadata": {
            "experiment_id": EXPERIMENT_ID,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "total_cases": len(case_records),
            "dry_run": dry_run,
        },
        "exact_match": paired_em,
        "containment": paired_cont,
    }

    summary_file = output_dir / "aggregate_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(aggregate_summary, f, indent=2)

    paired_file = output_dir / "paired_comparisons.json"
    with open(paired_file, "w", encoding="utf-8") as f:
        json.dump(paired_comparisons_summary, f, indent=2)

    # Validate JSON read-back
    with open(summary_file, "r", encoding="utf-8") as f:
        _ = json.load(f)
    with open(paired_file, "r", encoding="utf-8") as f:
        _ = json.load(f)
    print("-> JSON files successfully serialized and validated via read-back.")

    print("\n[Step 5/5] Experiment 4.2 data collection completed successfully.")
    return {
        "case_records": case_records,
        "aggregate_summary": aggregate_summary,
        "paired_comparisons": paired_comparisons_summary,
        "regression_recovery_records": regression_recovery_records,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Précis Experiment 4.2 Full-Cohort Table-Selection Threshold Evaluation Runner"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "results" / "diagnostic_experiment_4_v1" / "full_cohort_threshold_20261010",
        help="Directory to save experiment records and summary",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Execute context building and harness verification without calling LLM inference",
    )
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Run on first 5 cases only for quick integration testing",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow running into existing directory",
    )
    args = parser.parse_args()

    run_experiment_4_2(
        output_dir=args.output_dir,
        dry_run=args.dry_run,
        smoke_test=args.smoke_test,
        force=args.force,
    )


if __name__ == "__main__":
    main()
