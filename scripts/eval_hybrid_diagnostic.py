#!/usr/bin/env python3
"""
Précis Hybrid Diagnostic Experiment Runner.

Standalone evaluation script investigating hypothesis H_HYBRID:
Decomposed into:
- Experiment A: HYBRID-ORACLE-SPAN (Representation Usability on 29 Deficit Cases)
- Experiment B: PRECISION-PRESERVATION STRESS TEST (Distractor Vulnerability on 11 Win Cases)
- Experiment C: HYBRID-RETRIEVED-SPAN (End-to-End Discovery on 29 Deficit & 11 Win Cases)
- Synchronous V3 Rebaseline (Same-turn baseline for all 40 discordant cases)

Zero modifications to production code under backend/src/precis/.
All hybrid orchestration, retrieval, token-budget enforcement, and result serialization
live strictly in this script.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure backend/src is on import path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

from precis.evaluation.metrics import (
    DEFAULT_BERTSCORE_MODEL,
    compute_bert_score,
    compute_exact_match,
    compute_minilm_cosine,
    compute_rouge_l,
    is_bertscore_model_cached,
    normalize_answer,
)
from precis.graph.schema import Fact
from precis.graph.store import FactStore
from precis.pipeline.inference import (
    OLLAMA_DEFAULT_BASE_URL,
    PROMPT_TEMPLATE,
    generate_answer,
)
from precis.pipeline.orchestrator import ingest_document
from precis.pipeline.packer import pack_context, render_context
from precis.pipeline.sdh import (
    cosine_similarity,
    embed_text,
    embed_texts,
)

# Canonical benchmark constants
DEFAULT_MODEL = "qwen2.5-coder:7b"
DEFAULT_TEMP = 0.0
DEFAULT_TOP_P = 0.9
DEFAULT_MAX_TOKENS = 512
DEFAULT_SEED = 42
DEFAULT_TOKEN_CEILING = 2048


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


def estimate_tokens(text: str) -> int:
    """Standard token estimation matching v3 benchmark (words * 1.3)."""
    words = len(text.strip().split())
    return int(words * 1.3)


def segment_document_spans(doc_text: str) -> List[Tuple[str, str]]:
    """
    Segment source document into candidate evidence units:
    Returns list of (span_text, span_type) where span_type in ['table_row', 'list_item', 'prose_sentence'].
    """
    spans: List[Tuple[str, str]] = []
    seen = set()

    # 1. HTML Table rows
    if "<tr" in doc_text.lower():
        rows = re.findall(r"<tr[^>]*>.*?</tr>", doc_text, re.DOTALL | re.IGNORECASE)
        for r in rows:
            clean = re.sub(r"<[^>]+>", " ", r)
            clean = re.sub(r"\s+", " ", clean).strip()
            if len(clean) > 8 and clean not in seen:
                seen.add(clean)
                spans.append((clean, "table_row"))

    # 2. HTML List items
    if "<li" in doc_text.lower():
        items = re.findall(r"<li[^>]*>.*?</li>", doc_text, re.DOTALL | re.IGNORECASE)
        for item in items:
            clean = re.sub(r"<[^>]+>", " ", item)
            clean = re.sub(r"\s+", " ", clean).strip()
            if len(clean) > 8 and clean not in seen:
                seen.add(clean)
                spans.append((clean, "list_item"))

    # 3. Clean prose sentences
    clean_prose = re.sub(r"<[^>]+>", " ", doc_text)
    raw_sents = re.split(r"(?<=[.!?])\s+", clean_prose)
    for s in raw_sents:
        s_clean = re.sub(r"\s+", " ", s).strip()
        if len(s_clean) > 15 and s_clean not in seen:
            seen.add(s_clean)
            spans.append((s_clean, "prose_sentence"))

    return spans


def retrieve_top_spans(
    query: str,
    spans: List[Tuple[str, str]],
    top_k: int = 1,
) -> List[Tuple[str, str, float]]:
    """Retrieve top-K spans ranked by dense MiniLM cosine similarity to query."""
    if not spans:
        return []

    q_emb = embed_text(query)
    span_texts = [s[0] for s in spans]
    span_embs = embed_texts(span_texts)

    scored = []
    for (s_text, s_type), s_emb in zip(spans, span_embs):
        sim = cosine_similarity(q_emb, s_emb)
        scored.append((s_text, s_type, float(sim)))

    scored.sort(key=lambda x: x[2], reverse=True)
    return scored[:top_k]


def build_token_matched_hybrid_context(
    packed_facts: List[Fact],
    source_span: str,
    baseline_token_budget: int,
    token_ceiling: int = DEFAULT_TOKEN_CEILING,
) -> Tuple[str, int, bool]:
    """
    Constructs hybrid context honoring the strict token-matched invariant:
    Tokens(Hybrid) <= baseline_token_budget (and <= token_ceiling).
    Prunes lower-ranked SVOA facts from the bottom until facts + span fit.
    """
    span_formatted = f"[Source Evidence]:\n\"{source_span.strip()}\""
    span_tokens = estimate_tokens(span_formatted)

    effective_budget = min(baseline_token_budget, token_ceiling)

    # Greedily include facts from highest rank down until facts + span fit
    included_facts = list(packed_facts)
    while included_facts:
        facts_text = render_context(included_facts)
        total_text = f"{facts_text}\n\n{span_formatted}" if facts_text else span_formatted
        total_tokens = estimate_tokens(total_text)
        if total_tokens <= effective_budget:
            return total_text, total_tokens, True
        included_facts.pop()  # Drop lowest-ranked fact

    # If even 0 facts + span exceeds budget, include truncated span or span alone
    if span_tokens <= effective_budget:
        return span_formatted, span_tokens, True
    else:
        # Fallback to baseline facts alone if span is oversized
        facts_text = render_context(packed_facts)
        return facts_text, estimate_tokens(facts_text), False


@dataclass
class DiagnosticCaseRecord:
    sample_id: str
    question: str
    reference_answer: str
    canonical_naive_correct: bool
    canonical_precis_correct: bool
    cohort: str  # "DEFICIT_29" or "WIN_11"
    experiment: str  # "V3_REBASELINE", "EXP_A_ORACLE", "EXP_B_STRESS", "EXP_C_RETRIEVED"
    source_span_candidates_count: int
    selected_span: str
    retrieval_similarity: float
    span_source_type: str
    span_has_gold_evidence: bool
    v3_rebaseline_context_tokens: int
    hybrid_context_tokens: int
    token_constraint_satisfied: bool
    v3_rebaseline_answer: str
    predicted_answer: str
    exact_match: bool
    containment_correct: bool
    rouge_l: float
    bert_score: Optional[float]
    outcome_class: str
    diagnostic_failure_type: str
    notes: str


def run_hybrid_diagnostic(
    dataset_path: str = "backend/data/nq_subset/nq_dev.jsonl",
    audit_29_path: str = "paper/tables/audit_29_naive_only.json",
    audit_11_path: str = "paper/tables/audit_11_precis_only.json",
    r23_audit_path: str = "paper/tables/representation_loss_audit_v3.json",
    output_dir: str = "results/diagnostic_hybrid_n40",
    ollama_base_url: str = "http://127.0.0.1:11434",
    use_bertscore: bool = True,
) -> Dict[str, Any]:
    """Execute complete 3-part hybrid diagnostic and synchronous V3 rebaseline."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("PRÉCIS HYBRID DIAGNOSTIC EXPERIMENT (H_HYBRID)")
    print(f"Model: {DEFAULT_MODEL} | Temp: {DEFAULT_TEMP} | Top-p: {DEFAULT_TOP_P} | Seed: {DEFAULT_SEED}")
    print(f"Ollama URL: {ollama_base_url}")
    print("=" * 80)

    # 1. Load Datasets & Cohorts
    print("\n[Step 1/6] Loading canonical datasets and cohorts...")
    with open(dataset_path) as f:
        docs = {d["doc_id"]: d for line in f if line.strip() for d in [json.loads(line)]}

    with open(audit_29_path) as f:
        cohort_29 = json.load(f)

    with open(audit_11_path) as f:
        cohort_11 = json.load(f)

    r23_map = {}
    if os.path.exists(r23_audit_path):
        with open(r23_audit_path) as f:
            for item in json.load(f):
                r23_map[item["sample_id"]] = item.get("source_snippet_containing_answer", "")

    print(f"Loaded {len(docs)} benchmark documents.")
    print(f"Cohort Deficit: {len(cohort_29)} cases | Cohort Win: {len(cohort_11)} cases.")

    # Build audited oracle spans for 29 deficit cases
    oracle_spans: Dict[str, str] = {}
    for item in cohort_29:
        sid = item["sample_id"]
        gold = item["gold_answer"]
        doc = docs[sid]["document"]
        if sid in r23_map and r23_map[sid]:
            oracle_spans[sid] = r23_map[sid]
        else:
            # Fallback to verified regex/table extraction
            if "<tr" in doc or "<td" in doc:
                rows = re.findall(r"<tr[^>]*>.*?</tr>", doc, re.DOTALL | re.IGNORECASE)
                for r in rows:
                    if gold.lower() in r.lower():
                        oracle_spans[sid] = re.sub(r"\s+", " ", r).strip()
                        break
            if sid not in oracle_spans:
                sents = re.split(r"(?<=[.!?])\s+", doc)
                for s in sents:
                    if gold.lower() in s.lower():
                        oracle_spans[sid] = s.strip()
                        break
            if sid not in oracle_spans:
                for l in doc.split("\n"):
                    if gold.lower() in l.lower():
                        oracle_spans[sid] = l.strip()
                        break

    assert len(oracle_spans) == 29, f"Expected 29 oracle spans, found {len(oracle_spans)}"
    print("Audited oracle spans mapped for all 29 deficit cases.")

    # Data structures for results
    all_case_records: List[DiagnosticCaseRecord] = []
    v3_rebaseline_map: Dict[str, Dict[str, Any]] = {}

    # Combine 40 discordant cases: 29 Deficit + 11 Win
    discordant_40 = []
    for item in cohort_29:
        discordant_40.append((item, "DEFICIT_29"))
    for item in cohort_11:
        discordant_40.append((item, "WIN_11"))

    # =========================================================================
    # STEP 2: SYNCHRONOUS V3 REBASELINE (40 CASES)
    # =========================================================================
    print("\n[Step 2/6] Executing Synchronous V3 Rebaseline on 40 discordant cases...")
    t_start_rebaseline = time.perf_counter()

    for idx, (item, cohort_name) in enumerate(discordant_40):
        sid = item["sample_id"]
        q = item["question"]
        gold = item["gold_answer"]
        doc_text = docs[sid]["document"]

        print(f"  [{idx+1}/40] Rebaseline: {sid[:8]} ({cohort_name}) - {q[:50]}...")

        store = FactStore(in_memory=True, collection_name=f"diag_rebase_{sid[:12]}_{idx}")
        ingest_document(doc_text, sid, store)

        pack_full = pack_context(query=q, store=store, token_ceiling=DEFAULT_TOKEN_CEILING)
        ctx_v3 = render_context(pack_full.packed_facts)
        ctx_tokens = estimate_tokens(ctx_v3)

        inf_v3 = generate_answer(
            query=q,
            context=ctx_v3,
            model=DEFAULT_MODEL,
            base_url=ollama_base_url,
            temperature=DEFAULT_TEMP,
            top_p=DEFAULT_TOP_P,
            max_tokens=DEFAULT_MAX_TOKENS,
        )

        ans_v3 = inf_v3.answer
        em_v3 = compute_exact_match(ans_v3, gold)
        cont_v3 = contains_answer(ans_v3, gold)
        rouge_v3 = compute_rouge_l(ans_v3, gold)
        bert_v3 = compute_bert_score(ans_v3, gold) if use_bertscore else None

        v3_rebaseline_map[sid] = {
            "sample_id": sid,
            "question": q,
            "gold_answer": gold,
            "cohort": cohort_name,
            "packed_facts": pack_full.packed_facts,
            "context_text": ctx_v3,
            "context_tokens": ctx_tokens,
            "predicted_answer": ans_v3,
            "exact_match": em_v3,
            "containment_correct": cont_v3,
            "rouge_l": rouge_v3,
            "bert_score": bert_v3,
        }

    dur_rebaseline = time.perf_counter() - t_start_rebaseline
    print(f"Synchronous V3 Rebaseline completed in {dur_rebaseline:.1f}s.")

    # Save rebaseline artifact
    with open(out_path / "rebaseline_v3_results.jsonl", "w") as f:
        for sid, rec in v3_rebaseline_map.items():
            f.write(json.dumps({k: v for k, v in rec.items() if k != "packed_facts"}) + "\n")

    # =========================================================================
    # STEP 3: EXPERIMENT A - HYBRID-ORACLE-SPAN (29 DEFICIT CASES)
    # =========================================================================
    print("\n[Step 3/6] Executing Experiment A: HYBRID-ORACLE-SPAN (29 Deficit Cases)...")
    exp_a_records = []
    exp_a_recoveries = 0

    for idx, item in enumerate(cohort_29):
        sid = item["sample_id"]
        q = item["question"]
        gold = item["gold_answer"]
        rebase = v3_rebaseline_map[sid]
        base_tokens = rebase["context_tokens"]
        packed_facts = rebase["packed_facts"]

        oracle_span = oracle_spans[sid]
        facts_text = render_context(packed_facts)
        hybrid_ctx = f"{facts_text}\n\n[Originating Source Evidence]:\n\"{oracle_span.strip()}\""
        hybrid_tokens = estimate_tokens(hybrid_ctx)

        print(f"  [{idx+1}/29] Exp A (Oracle): {sid[:8]} | Span len: {len(oracle_span)}...")

        inf_a = generate_answer(
            query=q,
            context=hybrid_ctx,
            model=DEFAULT_MODEL,
            base_url=ollama_base_url,
            temperature=DEFAULT_TEMP,
            top_p=DEFAULT_TOP_P,
            max_tokens=DEFAULT_MAX_TOKENS,
        )

        ans_a = inf_a.answer
        em_a = compute_exact_match(ans_a, gold)
        cont_a = contains_answer(ans_a, gold)
        rouge_a = compute_rouge_l(ans_a, gold)
        bert_a = compute_bert_score(ans_a, gold) if use_bertscore else None

        if cont_a:
            outcome = "SUCCESSFUL_RECOVERY"
            diag_type = "REPRESENTATION_RESTORED"
            exp_a_recoveries += 1
        else:
            outcome = "GENERATION_FAILURE"
            diag_type = "GENERATOR_FAILED_DESPITE_ORACLE_EVIDENCE"

        record = DiagnosticCaseRecord(
            sample_id=sid,
            question=q,
            reference_answer=gold,
            canonical_naive_correct=True,
            canonical_precis_correct=False,
            cohort="DEFICIT_29",
            experiment="EXP_A_ORACLE",
            source_span_candidates_count=1,
            selected_span=oracle_span,
            retrieval_similarity=1.0,
            span_source_type="audited_oracle_span",
            span_has_gold_evidence=True,
            v3_rebaseline_context_tokens=base_tokens,
            hybrid_context_tokens=hybrid_tokens,
            token_constraint_satisfied=(hybrid_tokens <= DEFAULT_TOKEN_CEILING),
            v3_rebaseline_answer=rebase["predicted_answer"],
            predicted_answer=ans_a,
            exact_match=em_a,
            containment_correct=cont_a,
            rouge_l=rouge_a,
            bert_score=bert_a,
            outcome_class=outcome,
            diagnostic_failure_type=diag_type,
            notes=f"Prev failure: {item.get('fc', '')}",
        )
        exp_a_records.append(record)
        all_case_records.append(record)

    oracle_repair_rate = exp_a_recoveries / len(cohort_29)
    print(f"Experiment A Completed: Oracle-Span Repair Rate = {exp_a_recoveries}/29 ({oracle_repair_rate*100:.1f}%)")

    # =========================================================================
    # STEP 4: EXPERIMENT B - PRECISION-PRESERVATION STRESS TEST (11 WIN CASES)
    # =========================================================================
    print("\n[Step 4/6] Executing Experiment B: PRECISION-PRESERVATION STRESS TEST (11 Win Cases)...")
    exp_b_records = []
    exp_b_retained = 0
    exp_b_regressions = 0

    for idx, item in enumerate(cohort_11):
        sid = item["sample_id"]
        q = item["question"]
        gold = item["gold_answer"]
        doc_text = docs[sid]["document"]
        rebase = v3_rebaseline_map[sid]
        base_tokens = rebase["context_tokens"]
        packed_facts = rebase["packed_facts"]

        # Segment and non-oracle retrieve
        candidate_spans = segment_document_spans(doc_text)
        top_spans = retrieve_top_spans(q, candidate_spans, top_k=1)
        selected_span, span_type, sim = top_spans[0] if top_spans else ("", "none", 0.0)

        # Build token-matched hybrid context: Tokens(Hybrid) <= Tokens(V3 rebaseline)
        hybrid_ctx, hybrid_tokens, token_ok = build_token_matched_hybrid_context(
            packed_facts=packed_facts,
            source_span=selected_span,
            baseline_token_budget=base_tokens,
            token_ceiling=DEFAULT_TOKEN_CEILING,
        )

        span_has_gold = contains_answer(selected_span, gold)

        print(f"  [{idx+1}/11] Exp B: {sid[:8]} | Sim: {sim:.3f} | BaseTok: {base_tokens} | HybTok: {hybrid_tokens}...")

        inf_b = generate_answer(
            query=q,
            context=hybrid_ctx,
            model=DEFAULT_MODEL,
            base_url=ollama_base_url,
            temperature=DEFAULT_TEMP,
            top_p=DEFAULT_TOP_P,
            max_tokens=DEFAULT_MAX_TOKENS,
        )

        ans_b = inf_b.answer
        em_b = compute_exact_match(ans_b, gold)
        cont_b = contains_answer(ans_b, gold)
        rouge_b = compute_rouge_l(ans_b, gold)
        bert_b = compute_bert_score(ans_b, gold) if use_bertscore else None

        if cont_b:
            outcome = "RETAINED_WIN"
            diag_type = "PRECISION_PRESERVED"
            exp_b_retained += 1
        else:
            outcome = "REGRESSION"
            diag_type = "DISTRACTOR_REGRESSION"
            exp_b_regressions += 1

        record = DiagnosticCaseRecord(
            sample_id=sid,
            question=q,
            reference_answer=gold,
            canonical_naive_correct=False,
            canonical_precis_correct=True,
            cohort="WIN_11",
            experiment="EXP_B_STRESS",
            source_span_candidates_count=len(candidate_spans),
            selected_span=selected_span,
            retrieval_similarity=sim,
            span_source_type=span_type,
            span_has_gold_evidence=span_has_gold,
            v3_rebaseline_context_tokens=base_tokens,
            hybrid_context_tokens=hybrid_tokens,
            token_constraint_satisfied=token_ok,
            v3_rebaseline_answer=rebase["predicted_answer"],
            predicted_answer=ans_b,
            exact_match=em_b,
            containment_correct=cont_b,
            rouge_l=rouge_b,
            bert_score=bert_b,
            outcome_class=outcome,
            diagnostic_failure_type=diag_type,
            notes="Non-oracle span stress test",
        )
        exp_b_records.append(record)
        all_case_records.append(record)

    retention_rate = exp_b_retained / len(cohort_11)
    regression_rate = exp_b_regressions / len(cohort_11)
    print(f"Experiment B Completed: Win Retention = {exp_b_retained}/11 ({retention_rate*100:.1f}%) | Regressions = {exp_b_regressions}/11 ({regression_rate*100:.1f}%)")

    # =========================================================================
    # STEP 5: EXPERIMENT C - HYBRID-RETRIEVED-SPAN (29 DEFICIT PRIMARY, 40 TOTAL)
    # =========================================================================
    print("\n[Step 5/6] Executing Experiment C: HYBRID-RETRIEVED-SPAN (All 40 Discordant Cases)...")
    exp_c_records = []
    exp_c_d29_recoveries = 0
    exp_c_d29_retrieval_failures = 0
    exp_c_d29_gen_failures = 0

    for idx, (item, cohort_name) in enumerate(discordant_40):
        sid = item["sample_id"]
        q = item["question"]
        gold = item["gold_answer"]
        doc_text = docs[sid]["document"]
        rebase = v3_rebaseline_map[sid]
        base_tokens = rebase["context_tokens"]
        packed_facts = rebase["packed_facts"]

        # Dense non-oracle retrieval
        candidate_spans = segment_document_spans(doc_text)
        top_spans = retrieve_top_spans(q, candidate_spans, top_k=1)
        selected_span, span_type, sim = top_spans[0] if top_spans else ("", "none", 0.0)

        # Build token-matched hybrid context: Tokens(Hybrid) <= Tokens(V3 rebaseline)
        hybrid_ctx, hybrid_tokens, token_ok = build_token_matched_hybrid_context(
            packed_facts=packed_facts,
            source_span=selected_span,
            baseline_token_budget=base_tokens,
            token_ceiling=DEFAULT_TOKEN_CEILING,
        )

        span_has_gold = contains_answer(selected_span, gold)

        print(f"  [{idx+1}/40] Exp C: {sid[:8]} ({cohort_name}) | Sim: {sim:.3f} | SpanHasGold: {span_has_gold}...")

        inf_c = generate_answer(
            query=q,
            context=hybrid_ctx,
            model=DEFAULT_MODEL,
            base_url=ollama_base_url,
            temperature=DEFAULT_TEMP,
            top_p=DEFAULT_TOP_P,
            max_tokens=DEFAULT_MAX_TOKENS,
        )

        ans_c = inf_c.answer
        em_c = compute_exact_match(ans_c, gold)
        cont_c = contains_answer(ans_c, gold)
        rouge_c = compute_rouge_l(ans_c, gold)
        bert_c = compute_bert_score(ans_c, gold) if use_bertscore else None

        # Failure Taxonomy Classification
        if cont_c:
            outcome = "SUCCESSFUL_RECOVERY" if cohort_name == "DEFICIT_29" else "RETAINED_WIN"
            diag_type = "SUCCESSFUL_RECOVERY"
            if cohort_name == "DEFICIT_29":
                exp_c_d29_recoveries += 1
        else:
            if cohort_name == "WIN_11":
                outcome = "REGRESSION"
                diag_type = "DISTRACTOR_REGRESSION"
            else:
                # Deficit cohort failure taxonomy
                if not span_has_gold:
                    outcome = "RETRIEVAL_FAILURE"
                    diag_type = "SPAN_RETRIEVAL_MISSED_EVIDENCE"
                    exp_c_d29_retrieval_failures += 1
                else:
                    outcome = "GENERATION_FAILURE"
                    diag_type = "GENERATOR_FAILED_DESPITE_RETRIEVED_EVIDENCE"
                    exp_c_d29_gen_failures += 1

        record = DiagnosticCaseRecord(
            sample_id=sid,
            question=q,
            reference_answer=gold,
            canonical_naive_correct=(cohort_name == "DEFICIT_29"),
            canonical_precis_correct=(cohort_name == "WIN_11"),
            cohort=cohort_name,
            experiment="EXP_C_RETRIEVED",
            source_span_candidates_count=len(candidate_spans),
            selected_span=selected_span,
            retrieval_similarity=sim,
            span_source_type=span_type,
            span_has_gold_evidence=span_has_gold,
            v3_rebaseline_context_tokens=base_tokens,
            hybrid_context_tokens=hybrid_tokens,
            token_constraint_satisfied=token_ok,
            v3_rebaseline_answer=rebase["predicted_answer"],
            predicted_answer=ans_c,
            exact_match=em_c,
            containment_correct=cont_c,
            rouge_l=rouge_c,
            bert_score=bert_c,
            outcome_class=outcome,
            diagnostic_failure_type=diag_type,
            notes=f"Retrieved span type: {span_type}, sim: {sim:.3f}",
        )
        exp_c_records.append(record)
        all_case_records.append(record)

    print(f"Experiment C Completed: Deficit Recoveries = {exp_c_d29_recoveries}/29 | Retrieval Failures = {exp_c_d29_retrieval_failures} | Gen Failures = {exp_c_d29_gen_failures}")

    # =========================================================================
    # STEP 6: SERIALIZATION & SUMMARY METRICS
    # =========================================================================
    print("\n[Step 6/6] Serializing results and compiling research tables...")

    # Write per-case machine readable JSONL
    cases_file = out_path / "hybrid_diagnostic_cases.jsonl"
    with open(cases_file, "w") as f:
        for rec in all_case_records:
            f.write(json.dumps(asdict(rec)) + "\n")
    print(f"Wrote {len(all_case_records)} per-case records to {cases_file}")

    # Aggregate summaries
    summary_data = {
        "metadata": {
            "experiment_name": "Précis Hybrid Diagnostic Experiment",
            "target_hypothesis": "H_HYBRID",
            "model": DEFAULT_MODEL,
            "temperature": DEFAULT_TEMP,
            "top_p": DEFAULT_TOP_P,
            "max_tokens": DEFAULT_MAX_TOKENS,
            "seed": DEFAULT_SEED,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "selection_bias_disclosure": "This experiment is a mechanistic diagnostic on outcome-selected discordant cases and is not an unbiased estimate of general benchmark performance.",
        },
        "synchronous_v3_rebaseline": {
            "total_cases": 40,
            "deficit_cases_em": sum(1 for sid, r in v3_rebaseline_map.items() if r["cohort"] == "DEFICIT_29" and r["exact_match"]) / 29,
            "deficit_cases_containment": sum(1 for sid, r in v3_rebaseline_map.items() if r["cohort"] == "DEFICIT_29" and r["containment_correct"]) / 29,
            "win_cases_em": sum(1 for sid, r in v3_rebaseline_map.items() if r["cohort"] == "WIN_11" and r["exact_match"]) / 11,
            "win_cases_containment": sum(1 for sid, r in v3_rebaseline_map.items() if r["cohort"] == "WIN_11" and r["containment_correct"]) / 11,
            "mean_context_tokens": sum(r["context_tokens"] for r in v3_rebaseline_map.values()) / 40,
        },
        "experiment_a_oracle_span": {
            "cohort": "DEFICIT_29",
            "total_cases": 29,
            "successful_recoveries": exp_a_recoveries,
            "oracle_span_repair_rate": round(oracle_repair_rate, 4),
            "generation_failures": len(cohort_29) - exp_a_recoveries,
            "exact_match_count": sum(1 for r in exp_a_records if r.exact_match),
            "mean_rouge_l": round(sum(r.rouge_l for r in exp_a_records) / 29, 4),
            "mean_bert_score": round(sum(r.bert_score for r in exp_a_records if r.bert_score is not None) / 29, 4) if use_bertscore else None,
            "mean_context_tokens": round(sum(r.hybrid_context_tokens for r in exp_a_records) / 29, 1),
        },
        "experiment_b_precision_preservation": {
            "cohort": "WIN_11",
            "total_cases": 11,
            "retained_wins": exp_b_retained,
            "win_retention_rate": round(retention_rate, 4),
            "regressions": exp_b_regressions,
            "regression_rate": round(regression_rate, 4),
            "exact_match_count": sum(1 for r in exp_b_records if r.exact_match),
            "mean_rouge_l": round(sum(r.rouge_l for r in exp_b_records) / 11, 4),
            "mean_bert_score": round(sum(r.bert_score for r in exp_b_records if r.bert_score is not None) / 11, 4) if use_bertscore else None,
            "mean_context_tokens": round(sum(r.hybrid_context_tokens for r in exp_b_records) / 11, 1),
            "token_constraint_satisfied_count": sum(1 for r in exp_b_records if r.token_constraint_satisfied),
        },
        "experiment_c_retrieved_span": {
            "primary_cohort_deficit_29": {
                "total_cases": 29,
                "successful_recoveries": exp_c_d29_recoveries,
                "retrieved_span_recovery_rate": round(exp_c_d29_recoveries / 29, 4),
                "retrieval_failures": exp_c_d29_retrieval_failures,
                "generation_failures": exp_c_d29_gen_failures,
                "span_evidence_retrieval_rate": round(sum(1 for r in exp_c_records if r.cohort == "DEFICIT_29" and r.span_has_gold_evidence) / 29, 4),
            },
            "secondary_cohort_win_11": {
                "total_cases": 11,
                "retained_wins": sum(1 for r in exp_c_records if r.cohort == "WIN_11" and r.containment_correct),
                "regressions": sum(1 for r in exp_c_records if r.cohort == "WIN_11" and not r.containment_correct),
            },
            "token_constraint_satisfied_total": sum(1 for r in exp_c_records if r.token_constraint_satisfied),
        },
    }

    # Write summary JSON
    summary_file = Path("paper/tables/hybrid_diagnostic_results.json")
    with open(summary_file, "w") as f:
        json.dump(summary_data, f, indent=2)
    print(f"Wrote summary JSON to {summary_file}")

    # Write summary CSV
    csv_file = Path("paper/tables/hybrid_diagnostic_results.csv")
    with open(csv_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Experiment", "Cohort", "Total_Cases", "Primary_Metric", "Primary_Rate",
            "Secondary_Metric", "Secondary_Rate", "Mean_Context_Tokens", "Token_Matched_OK"
        ])
        writer.writerow([
            "V3_REBASELINE", "DISCORDANT_40", 40, "Containment", f"{sum(1 for r in v3_rebaseline_map.values() if r['containment_correct'])}/40",
            "Exact_Match", f"{sum(1 for r in v3_rebaseline_map.values() if r['exact_match'])}/40",
            round(summary_data["synchronous_v3_rebaseline"]["mean_context_tokens"], 1), "Baseline"
        ])
        writer.writerow([
            "EXP_A_ORACLE", "DEFICIT_29", 29, "Oracle_Repair_Rate", f"{exp_a_recoveries}/29 ({oracle_repair_rate*100:.1f}%)",
            "Generation_Failures", f"{29 - exp_a_recoveries}/29",
            summary_data["experiment_a_oracle_span"]["mean_context_tokens"], "Ceiling <= 2048"
        ])
        writer.writerow([
            "EXP_B_STRESS", "WIN_11", 11, "Win_Retention_Rate", f"{exp_b_retained}/11 ({retention_rate*100:.1f}%)",
            "Regressions", f"{exp_b_regressions}/11 ({regression_rate*100:.1f}%)",
            summary_data["experiment_b_precision_preservation"]["mean_context_tokens"], f"{summary_data['experiment_b_precision_preservation']['token_constraint_satisfied_count']}/11"
        ])
        writer.writerow([
            "EXP_C_RETRIEVED", "DEFICIT_29", 29, "Retrieved_Recovery_Rate", f"{exp_c_d29_recoveries}/29 ({exp_c_d29_recoveries/29*100:.1f}%)",
            "Retrieval_Failures", f"{exp_c_d29_retrieval_failures}/29",
            "Token_Matched", f"{summary_data['experiment_c_retrieved_span']['token_constraint_satisfied_total']}/40"
        ])
    print(f"Wrote summary CSV to {csv_file}")

    return summary_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Précis Hybrid Diagnostic Experiment Runner")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434", help="Local Ollama base URL")
    parser.add_argument("--output-dir", default="results/diagnostic_hybrid_n40", help="Directory for case traces")
    parser.add_argument("--no-bertscore", action="store_true", help="Skip DeBERTa BERTScore for faster execution")
    args = parser.parse_args()

    run_hybrid_diagnostic(
        ollama_base_url=args.ollama_url,
        output_dir=args.output_dir,
        use_bertscore=not args.no_bertscore,
    )
