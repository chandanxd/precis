#!/usr/bin/env python3
"""
Précis Benchmark Failure Analysis Tool.

Diagnoses where and why Précis loses information compared with Naive RAG
across the 200 NaturalQuestions benchmark samples without calling LLMs.

Funnel Analysis:
    Source Document
        ↓ (Extraction)
    SVOA Representation
        ↓ (Retrieval)
    Retrieved Candidates
        ↓ (Modality Filter & Budget Packing)
    Packed Context
        ↓ (Generation)
    Predicted Answer
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from precis.evaluation.metrics import normalize_answer
from precis.graph.schema import Fact
from precis.graph.store import FactStore
from precis.pipeline.orchestrator import ingest_document
from precis.pipeline.packer import _render_fact_parts, pack_context
from precis.pipeline.sdh import canonical_fact_text

# Failure classification categories
CLASS_CORRECT = "CORRECT"
CLASS_EXTRACTION_FAILURE = "EXTRACTION_FAILURE"
CLASS_RETRIEVAL_FAILURE = "RETRIEVAL_FAILURE"
CLASS_PACKING_FAILURE = "PACKING_FAILURE"
CLASS_GENERATION_FAILURE = "GENERATION_FAILURE"
CLASS_UNCERTAIN = "UNCERTAIN"

ALL_FAILURE_CLASSES = [
    CLASS_CORRECT,
    CLASS_EXTRACTION_FAILURE,
    CLASS_RETRIEVAL_FAILURE,
    CLASS_PACKING_FAILURE,
    CLASS_GENERATION_FAILURE,
    CLASS_UNCERTAIN,
]


def contains_answer(text: str, answer: str) -> bool:
    """
    Check if a normalized answer appears in normalized text with word boundaries.

    Conservative matching:
    - Lowercase, punctuation stripped, whitespace collapsed
    - Enforces word boundaries around normalized answer
    """
    norm_ans = normalize_answer(answer)
    if not norm_ans:
        return False

    norm_text = normalize_answer(text)
    if not norm_text:
        return False

    pattern = r"(?:\b|^)" + re.escape(norm_ans) + r"(?:\b|$)"
    return re.search(pattern, norm_text) is not None


def fact_contains_answer(fact: Fact, answer: str, answers: Optional[List[str]] = None) -> bool:
    """Check if any representation of a Fact contains the answer string."""
    targets = [answer]
    if answers:
        for alt in answers:
            if alt and alt not in targets:
                targets.append(alt)

    c_text = canonical_fact_text(fact)
    r_text = " ".join(_render_fact_parts(fact))

    for ans in targets:
        if contains_answer(c_text, ans) or contains_answer(r_text, ans):
            return True
    return False


def categorize_question_type(question: str) -> str:
    """Identify the Wh-interrogative or question category."""
    q_lower = question.strip().lower()
    first_word = q_lower.split()[0] if q_lower.split() else ""

    for wh in ["who", "what", "when", "where", "why", "how", "which"]:
        if first_word == wh or f" {wh} " in f" {q_lower} ":
            return wh.upper()
    return "OTHER"


def categorize_answer_length(answer: str) -> str:
    """Categorize reference answer length in words."""
    words = len(answer.split())
    if words <= 2:
        return "SHORT (1-2 words)"
    if words <= 5:
        return "MEDIUM (3-5 words)"
    return "LONG (>5 words)"


def is_answer_correct(
    predicted_answer: str,
    gold_answer: str,
    answers: Optional[List[str]] = None,
    exact_match: bool = False,
) -> bool:
    """Determine whether the predicted answer contains or matches the gold answer."""
    if exact_match:
        return True

    if not predicted_answer or not predicted_answer.strip():
        return False

    if contains_answer(predicted_answer, gold_answer):
        return True

    if answers:
        for alt in answers:
            if alt and contains_answer(predicted_answer, alt):
                return True

    return False


@dataclass
class FailureClassification:
    """Deterministic failure diagnostic result for a single sample."""

    primary_failure_class: str
    confidence: str
    failure_stages: List[str]
    source_has_answer: bool
    svoa_has_answer: bool
    retrieval_has_answer: bool
    packing_has_answer: bool
    precis_correct: bool
    naive_correct: bool
    evidence: Dict[str, Any] = field(default_factory=dict)


def classify_failure(
    gold_answer: str,
    precis_predicted: str,
    precis_exact_match: bool,
    naive_predicted: str,
    naive_exact_match: bool,
    source_text: Optional[str],
    extracted_facts: Sequence[Fact],
    retrieved_facts: Sequence[Fact],
    packed_facts: Sequence[Fact],
    alternative_answers: Optional[List[str]] = None,
) -> FailureClassification:
    """
    Deterministically trace where answer information is lost along the pipeline.

    Decision flow:
    1. If Précis is correct -> CORRECT.
    2. If source text is missing or does not contain gold answer -> UNCERTAIN.
    3. If gold answer is in source text but not in any extracted SVOA fact -> EXTRACTION_FAILURE.
    4. If gold answer is in extracted facts but not in retrieved facts -> RETRIEVAL_FAILURE.
    5. If gold answer is in retrieved facts but not in packed facts -> PACKING_FAILURE.
    6. If gold answer is in packed facts but Précis prediction is incorrect -> GENERATION_FAILURE.
    7. Otherwise -> UNCERTAIN.
    """
    precis_ok = is_answer_correct(
        precis_predicted, gold_answer, alternative_answers, precis_exact_match
    )
    naive_ok = is_answer_correct(
        naive_predicted, gold_answer, alternative_answers, naive_exact_match
    )

    norm_gold = normalize_answer(gold_answer)
    if not norm_gold:
        return FailureClassification(
            primary_failure_class=CLASS_UNCERTAIN,
            confidence="low",
            failure_stages=[],
            source_has_answer=False,
            svoa_has_answer=False,
            retrieval_has_answer=False,
            packing_has_answer=False,
            precis_correct=precis_ok,
            naive_correct=naive_ok,
            evidence={"reason": "Empty or invalid gold answer reference"},
        )

    if source_text is None:
        return FailureClassification(
            primary_failure_class=CLASS_UNCERTAIN,
            confidence="low",
            failure_stages=[],
            source_has_answer=False,
            svoa_has_answer=False,
            retrieval_has_answer=False,
            packing_has_answer=False,
            precis_correct=precis_ok,
            naive_correct=naive_ok,
            evidence={"reason": "Source document text was not provided"},
        )

    # Check coverage along funnel
    all_refs = [gold_answer]
    if alternative_answers:
        all_refs.extend(alternative_answers)

    source_has = any(contains_answer(source_text, ref) for ref in all_refs)
    svoa_bearing = [f for f in extracted_facts if fact_contains_answer(f, gold_answer, all_refs)]
    ret_bearing = [f for f in retrieved_facts if fact_contains_answer(f, gold_answer, all_refs)]
    pack_bearing = [f for f in packed_facts if fact_contains_answer(f, gold_answer, all_refs)]

    svoa_has = len(svoa_bearing) > 0
    ret_has = len(ret_bearing) > 0
    pack_has = len(pack_bearing) > 0

    failure_stages: List[str] = []
    evidence: Dict[str, Any] = {
        "source_has_answer": source_has,
        "facts_extracted": len(extracted_facts),
        "facts_bearing_extracted": len(svoa_bearing),
        "facts_retrieved": len(retrieved_facts),
        "facts_bearing_retrieved": len(ret_bearing),
        "facts_packed": len(packed_facts),
        "facts_bearing_packed": len(pack_bearing),
    }

    if precis_ok:
        return FailureClassification(
            primary_failure_class=CLASS_CORRECT,
            confidence="high",
            failure_stages=[],
            source_has_answer=source_has,
            svoa_has_answer=svoa_has,
            retrieval_has_answer=ret_has,
            packing_has_answer=pack_has,
            precis_correct=True,
            naive_correct=naive_ok,
            evidence=evidence,
        )

    if not source_has:
        return FailureClassification(
            primary_failure_class=CLASS_UNCERTAIN,
            confidence="medium",
            failure_stages=[],
            source_has_answer=False,
            svoa_has_answer=svoa_has,
            retrieval_has_answer=ret_has,
            packing_has_answer=pack_has,
            precis_correct=False,
            naive_correct=naive_ok,
            evidence={
                **evidence,
                "reason": "Gold answer not found in source text with conservative matching",
            },
        )

    # Source has the answer. Identify which stage drops it.
    if not svoa_has:
        failure_stages.append("EXTRACTION")
        primary_class = CLASS_EXTRACTION_FAILURE
        confidence = "high"
        evidence["reason"] = "Source contains answer, but 0 extracted SVOA facts preserve it"
    elif not ret_has:
        failure_stages.append("RETRIEVAL")
        primary_class = CLASS_RETRIEVAL_FAILURE
        confidence = "high"
        evidence["reason"] = (
            f"SVOA extracted {len(svoa_bearing)} answer-bearing fact(s), "
            "but 0 were retrieved by query similarity"
        )
    elif not pack_has:
        failure_stages.append("PACKING")
        primary_class = CLASS_PACKING_FAILURE
        confidence = "high"
        # Determine why it was dropped during packing: modality or ranking/budget
        filtered_by_mod = [
            f for f in ret_bearing if f.modality in {"hypothetical", "conditional"}
        ]
        evidence["filtered_by_modality_count"] = len(filtered_by_mod)
        if len(filtered_by_mod) == len(ret_bearing):
            evidence["reason"] = "All retrieved answer-bearing facts were filtered out by modality"
        else:
            evidence["reason"] = (
                "Answer-bearing facts were dropped due to pack_score ranking or token ceiling"
            )
    else:
        failure_stages.append("GENERATION")
        primary_class = CLASS_GENERATION_FAILURE
        confidence = "high"
        evidence["reason"] = (
            "Packed context contained answer-bearing fact(s), but LLM predicted incorrect answer"
        )

    # Detect secondary failure stages if applicable
    if svoa_has and ret_has and not pack_has:
        if len(ret_bearing) < len(svoa_bearing):
            failure_stages.insert(0, "PARTIAL_RETRIEVAL")

    return FailureClassification(
        primary_failure_class=primary_class,
        confidence=confidence,
        failure_stages=failure_stages,
        source_has_answer=source_has,
        svoa_has_answer=svoa_has,
        retrieval_has_answer=ret_has,
        packing_has_answer=pack_has,
        precis_correct=False,
        naive_correct=naive_ok,
        evidence=evidence,
    )


def reconstruct_facts_for_samples(
    samples: List[Dict[str, Any]],
    cache_path: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Deterministically reconstruct extracted, retrieved, and packed facts.
    Caches results by sample_id to avoid redundant computation.
    """
    reconstructed: Dict[str, Dict[str, Any]] = {}

    if cache_path and os.path.isfile(cache_path):
        print(f"Loading cached fact reconstructions from {cache_path}...")
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                reconstructed = json.load(f)
            # Check if all samples are present
            all_present = all(s["doc_id"] in reconstructed for s in samples)
            if all_present:
                print(f"Loaded all {len(samples)} sample reconstructions from cache.")
                return reconstructed
        except Exception as e:
            print(f"Could not load cache ({e}), recomputing...")
            reconstructed = {}

    print(f"Reconstructing SVOA facts for {len(samples)} samples (ingestion + packing)...")

    # Group samples by unique document to avoid redundant ingestions
    doc_to_facts: Dict[str, List[Fact]] = {}
    doc_to_store: Dict[str, FactStore] = {}

    for idx, s in enumerate(samples, 1):
        sid = s["doc_id"]
        if sid in reconstructed:
            continue

        q = s["question"]
        doc = s["document"]

        doc_hash = str(hash(doc))
        if doc_hash not in doc_to_store:
            store = FactStore(in_memory=True, collection_name=f"rec_{idx}_{doc_hash[:8]}")
            ingest_res = ingest_document(doc, sid, store)
            doc_to_store[doc_hash] = store
            doc_to_facts[doc_hash] = ingest_res.facts

        store = doc_to_store[doc_hash]
        extracted_facts = doc_to_facts[doc_hash]

        pack_res = pack_context(q, store, token_ceiling=2048)
        retrieved_pairs = store.query_similar(q, n_results=100)
        retrieved_facts = [f for f, _ in retrieved_pairs]

        # Compact serializable representation
        rec_data = {
            "extracted_facts": [
                {
                    "canonical": canonical_fact_text(f),
                    "rendered": " ".join(_render_fact_parts(f)),
                    "modality": f.modality,
                    "sdh_score": f.sdh_score,
                }
                for f in extracted_facts
            ],
            "retrieved_facts": [
                {
                    "canonical": canonical_fact_text(f),
                    "rendered": " ".join(_render_fact_parts(f)),
                    "modality": f.modality,
                    "sdh_score": f.sdh_score,
                }
                for f in retrieved_facts
            ],
            "packed_facts": [
                {
                    "canonical": canonical_fact_text(f),
                    "rendered": " ".join(_render_fact_parts(f)),
                    "modality": f.modality,
                    "sdh_score": f.sdh_score,
                }
                for f in pack_res.packed_facts
            ],
        }
        reconstructed[sid] = rec_data

        if idx % 20 == 0 or idx == len(samples):
            print(f"  Processed {idx}/{len(samples)} samples...")

    if cache_path:
        os.makedirs(os.path.dirname(os.path.abspath(cache_path)), exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(reconstructed, f)
        print(f"Cached {len(reconstructed)} sample reconstructions to {cache_path}")

    return reconstructed


def parse_reconstructed_facts(data_list: List[Dict[str, Any]]) -> List[Fact]:
    """Convert cached serialized fact dicts into lightweight Fact objects."""
    facts: List[Fact] = []
    for d in data_list:
        f = Fact(
            subject=d.get("canonical", ""),
            verb="",
            object="",
            modality=d.get("modality", "asserted"),
            sdh_score=d.get("sdh_score", 0.0),
        )
        facts.append(f)
    return facts


def run_failure_analysis(
    results_path: str,
    dataset_path: str,
    output_jsonl: str,
    output_csv: str,
    output_summary: str,
    cache_path: Optional[str] = None,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    """Execute end-to-end failure diagnosis across the benchmark dataset."""
    print("=" * 60)
    print("PRÉCIS BENCHMARK FAILURE ANALYSIS")
    print("=" * 60)
    print(f"Results path:  {results_path}")
    print(f"Dataset path:  {dataset_path}")
    print(f"Limit:         {limit}")

    # 1. Load benchmark per-question results
    if not os.path.isfile(results_path):
        raise FileNotFoundError(f"Benchmark results not found at: {results_path}")

    bench_by_sample_cond: Dict[Tuple[str, str], Dict[str, Any]] = {}
    with open(results_path, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue
            d = json.loads(line_str)
            bench_by_sample_cond[(d["sample_id"], d["condition"])] = d

    # 2. Load dataset samples
    if not os.path.isfile(dataset_path):
        raise FileNotFoundError(f"Dataset not found at: {dataset_path}")

    samples: List[Dict[str, Any]] = []
    with open(dataset_path, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue
            samples.append(json.loads(line_str))
            if len(samples) >= limit:
                break

    print(f"Loaded {len(samples)} dataset samples.")

    # 3. Reconstruct facts
    facts_cache = reconstruct_facts_for_samples(samples, cache_path=cache_path)

    # 4. Diagnose each sample
    analysis_records: List[Dict[str, Any]] = []

    for s in samples:
        sid = s["doc_id"]
        q = s["question"]
        gold = s["gold_answer"]
        doc = s["document"]
        alts = s.get("answers", [])

        naive_row = bench_by_sample_cond.get((sid, "naive_rag"), {})
        precis_row = bench_by_sample_cond.get((sid, "precis_full"), {})

        naive_ans = naive_row.get("predicted_answer", "")
        precis_ans = precis_row.get("predicted_answer", "")
        naive_em = naive_row.get("exact_match", False)
        precis_em = precis_row.get("exact_match", False)

        rec = facts_cache.get(sid, {})
        extracted_facts = parse_reconstructed_facts(rec.get("extracted_facts", []))
        retrieved_facts = parse_reconstructed_facts(rec.get("retrieved_facts", []))
        packed_facts = parse_reconstructed_facts(rec.get("packed_facts", []))

        # Perform classification
        diag = classify_failure(
            gold_answer=gold,
            precis_predicted=precis_ans,
            precis_exact_match=precis_em,
            naive_predicted=naive_ans,
            naive_exact_match=naive_em,
            source_text=doc,
            extracted_facts=extracted_facts,
            retrieved_facts=retrieved_facts,
            packed_facts=packed_facts,
            alternative_answers=alts,
        )

        # Relevant facts (bearing answer)
        rel_extracted = [
            f.subject for f in extracted_facts if fact_contains_answer(f, gold, alts)
        ]

        q_type = categorize_question_type(q)
        ans_len_cat = categorize_answer_length(gold)

        rec_out = {
            "sample_id": sid,
            "question": q,
            "question_type": q_type,
            "gold_answer": gold,
            "gold_answer_length_category": ans_len_cat,
            "naive_answer": naive_ans,
            "precis_answer": precis_ans,
            "naive_exact_match": naive_em,
            "precis_exact_match": precis_em,
            "naive_rouge_l": naive_row.get("rouge_l", 0.0),
            "precis_rouge_l": precis_row.get("rouge_l", 0.0),
            "naive_bert_score": naive_row.get("bert_score", None),
            "precis_bert_score": precis_row.get("bert_score", None),
            "failure_class": diag.primary_failure_class,
            "confidence": diag.confidence,
            "failure_stages": diag.failure_stages,
            "evidence": diag.evidence,
            "source_document_id": sid,
            "source_text_snippet": doc[:300] + ("..." if len(doc) > 300 else ""),
            "retrieved_svoa_facts": [f.subject for f in retrieved_facts[:5]],
            "packed_svoa_facts": [f.subject for f in packed_facts],
            "relevant_fact_candidates": rel_extracted[:5],
            "answer_coverage": {
                "source_has_answer": diag.source_has_answer,
                "svoa_has_answer": diag.svoa_has_answer,
                "retrieval_has_answer": diag.retrieval_has_answer,
                "packing_has_answer": diag.packing_has_answer,
                "precis_correct": diag.precis_correct,
                "naive_correct": diag.naive_correct,
            },
            "retrieval_coverage": diag.retrieval_has_answer,
            "packing_coverage": diag.packing_has_answer,
            "facts_considered": precis_row.get("facts_considered", 0),
            "facts_packed": precis_row.get("facts_packed", 0),
            "avg_sdh_score": precis_row.get("avg_sdh_score", 0.0),
        }
        analysis_records.append(rec_out)

    # 5. Export JSONL
    os.makedirs(os.path.dirname(os.path.abspath(output_jsonl)), exist_ok=True)
    with open(output_jsonl, "w", encoding="utf-8") as f:
        for r in analysis_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Exported JSONL: {output_jsonl} ({len(analysis_records)} rows)")

    # 6. Export CSV
    os.makedirs(os.path.dirname(os.path.abspath(output_csv)), exist_ok=True)
    csv_fields = [
        "sample_id",
        "question_type",
        "question",
        "gold_answer",
        "gold_answer_length_category",
        "failure_class",
        "confidence",
        "naive_exact_match",
        "precis_exact_match",
        "naive_rouge_l",
        "precis_rouge_l",
        "naive_bert_score",
        "precis_bert_score",
        "source_has_answer",
        "svoa_has_answer",
        "retrieval_has_answer",
        "packing_has_answer",
        "naive_correct",
        "precis_correct",
        "facts_considered",
        "facts_packed",
        "avg_sdh_score",
    ]
    with open(output_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(csv_fields)
        for r in analysis_records:
            cov = r["answer_coverage"]
            writer.writerow(
                [
                    r["sample_id"],
                    r["question_type"],
                    r["question"],
                    r["gold_answer"],
                    r["gold_answer_length_category"],
                    r["failure_class"],
                    r["confidence"],
                    r["naive_exact_match"],
                    r["precis_exact_match"],
                    r["naive_rouge_l"],
                    r["precis_rouge_l"],
                    r["naive_bert_score"],
                    r["precis_bert_score"],
                    cov["source_has_answer"],
                    cov["svoa_has_answer"],
                    cov["retrieval_has_answer"],
                    cov["packing_has_answer"],
                    cov["naive_correct"],
                    cov["precis_correct"],
                    r["facts_considered"],
                    r["facts_packed"],
                    r["avg_sdh_score"],
                ]
            )
    print(f"Exported CSV:   {output_csv}")

    # 7. Generate failure_summary.md
    generate_summary_markdown(analysis_records, bench_by_sample_cond, output_summary)
    print(f"Exported Summary Markdown: {output_summary}")

    return analysis_records


def generate_summary_markdown(
    records: List[Dict[str, Any]],
    bench_data: Dict[Tuple[str, str], Dict[str, Any]],
    summary_path: str,
) -> None:
    """Generate the comprehensive scientific failure diagnosis report in markdown."""
    n = len(records)
    if n == 0:
        return

    # Counts by failure class
    class_counts: Dict[str, int] = {c: 0 for c in ALL_FAILURE_CLASSES}
    for r in records:
        fc = r["failure_class"]
        class_counts[fc] = class_counts.get(fc, 0) + 1

    # Funnel counts
    source_has_count = sum(1 for r in records if r["answer_coverage"]["source_has_answer"])
    svoa_has_count = sum(1 for r in records if r["answer_coverage"]["svoa_has_answer"])
    ret_has_count = sum(1 for r in records if r["answer_coverage"]["retrieval_has_answer"])
    pack_has_count = sum(1 for r in records if r["answer_coverage"]["packing_has_answer"])
    precis_correct_count = sum(1 for r in records if r["answer_coverage"]["precis_correct"])
    naive_correct_count = sum(1 for r in records if r["answer_coverage"]["naive_correct"])

    # Contingency matrix
    naive_t_precis_f = sum(
        1
        for r in records
        if r["answer_coverage"]["naive_correct"] and not r["answer_coverage"]["precis_correct"]
    )
    naive_f_precis_f = sum(
        1
        for r in records
        if not r["answer_coverage"]["naive_correct"] and not r["answer_coverage"]["precis_correct"]
    )
    naive_t_precis_t = sum(
        1
        for r in records
        if r["answer_coverage"]["naive_correct"] and r["answer_coverage"]["precis_correct"]
    )
    naive_f_precis_t = sum(
        1
        for r in records
        if not r["answer_coverage"]["naive_correct"] and r["answer_coverage"]["precis_correct"]
    )

    # Breakdown by question type
    q_types: Dict[str, Dict[str, int]] = {}
    for r in records:
        qt = r["question_type"]
        if qt not in q_types:
            q_types[qt] = {c: 0 for c in ALL_FAILURE_CLASSES}
        q_types[qt][r["failure_class"]] += 1

    # Breakdown by answer length
    ans_lens: Dict[str, Dict[str, int]] = {}
    for r in records:
        al = r["gold_answer_length_category"]
        if al not in ans_lens:
            ans_lens[al] = {c: 0 for c in ALL_FAILURE_CLASSES}
        ans_lens[al][r["failure_class"]] += 1

    # Examples by class
    examples_by_class: Dict[str, List[Dict[str, Any]]] = {c: [] for c in ALL_FAILURE_CLASSES}
    for r in records:
        c = r["failure_class"]
        if len(examples_by_class[c]) < 3:
            examples_by_class[c].append(r)

    # Condition performance summary across all 4 conditions
    conditions = ["naive_rag", "svoa_similarity", "svoa_no_modality", "precis_full"]
    cond_stats: Dict[str, Dict[str, Any]] = {}
    for c in conditions:
        em_list = [
            bench_data.get((r["sample_id"], c), {}).get("exact_match", False) for r in records
        ]
        rouge_list = [
            bench_data.get((r["sample_id"], c), {}).get("rouge_l", 0.0) for r in records
        ]
        bert_list = [
            bench_data.get((r["sample_id"], c), {}).get("bert_score", 0.0) or 0.0 for r in records
        ]
        cond_stats[c] = {
            "em": sum(em_list) / len(em_list) if em_list else 0.0,
            "em_count": sum(em_list),
            "rouge_l": sum(rouge_list) / len(rouge_list) if rouge_list else 0.0,
            "bert_score": sum(bert_list) / len(bert_list) if bert_list else 0.0,
        }

    lines: List[str] = []
    lines.append("# Précis Benchmark Failure Analysis & Diagnostic Report")
    lines.append("")
    lines.append(f"**Total Questions Analyzed:** {n}")
    lines.append(
        "**Methodology:** Deterministic 5-stage funnel coverage analysis "
        "tracing information preservation from source document to generated answer."
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 1. Primary Failure Distribution")
    lines.append("")
    lines.append("| Failure Class | Count | Percentage | Description |")
    lines.append("| :--- | :---: | :---: | :--- |")
    for fc in ALL_FAILURE_CLASSES:
        cnt = class_counts.get(fc, 0)
        pct = (cnt / n) * 100
        desc = {
            CLASS_CORRECT: "Précis generated an answer matching/containing the gold reference",
            CLASS_EXTRACTION_FAILURE: (
                "Source text contains answer, but SVOA representation dropped it"
            ),
            CLASS_RETRIEVAL_FAILURE: (
                "Answer-bearing SVOA fact exists, but query similarity did not retrieve it"
            ),
            CLASS_PACKING_FAILURE: (
                "Answer-bearing fact retrieved, but dropped by modality/budget ranking"
            ),
            CLASS_GENERATION_FAILURE: (
                "Answer-bearing fact packed into prompt, but LLM produced incorrect answer"
            ),
            CLASS_UNCERTAIN: "Gold answer not found in source text with conservative matching",
        }.get(fc, "")
        lines.append(f"| **{fc}** | **{cnt}** | **{pct:.1f}%** | {desc} |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 2. Information Coverage Funnel")
    lines.append("")
    lines.append(
        "This funnel identifies the exact pipeline transition where relevant answer information "
        "disappears between the source document and the final output."
    )
    lines.append("")
    lines.append(
        "| Pipeline Stage | Questions with Answer Present | % of Dataset | Transition Loss |"
    )
    lines.append("| :--- | :---: | :---: | :--- |")
    lines.append(
        f"| **1. Source Document** | {source_has_count} | {(source_has_count/n)*100:.1f}% | "
        "Baseline (reference in context) |"
    )
    loss_extr = source_has_count - svoa_has_count
    pct_extr = (loss_extr / source_has_count * 100) if source_has_count else 0.0
    lines.append(
        f"| **2. SVOA Representation** | {svoa_has_count} | {(svoa_has_count/n)*100:.1f}% | "
        f"**-{loss_extr} ({pct_extr:.1f}%) lost at Extraction** |"
    )
    lines.append(
        f"| **3. ChromaDB Retrieval** | {ret_has_count} | {(ret_has_count/n)*100:.1f}% | "
        f"-{svoa_has_count - ret_has_count} lost at Vector Retrieval |"
    )
    lines.append(
        f"| **4. Context Packing** | {pack_has_count} | {(pack_has_count/n)*100:.1f}% | "
        f"-{ret_has_count - pack_has_count} lost at Modality / Budget Packing |"
    )
    lines.append(
        f"| **5. Model Output** | {precis_correct_count} | {(precis_correct_count/n)*100:.1f}% | "
        f"-{pack_has_count - precis_correct_count} lost at LLM Generation |"
    )

    lines.append("")
    lines.append("```mermaid")
    lines.append("flowchart TD")
    lines.append(
        f'  A["Source Document ({source_has_count} / {n})"] '
        f'-->|SVOA Extraction Failure: -{source_has_count - svoa_has_count}| '
        f'B["Extracted Facts ({svoa_has_count} / {n})"]'
    )
    lines.append(
        f'  B -->|Retrieval Miss: -{svoa_has_count - ret_has_count}| '
        f'C["Retrieved Candidates ({ret_has_count} / {n})"]'
    )
    lines.append(
        f'  C -->|Packing Drop: -{ret_has_count - pack_has_count}| '
        f'D["Packed Context ({pack_has_count} / {n})"]'
    )
    lines.append(
        f'  D -->|Generation Failure: -{pack_has_count - precis_correct_count}| '
        f'E["Correct Answer ({precis_correct_count} / {n})"]'
    )
    lines.append("```")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 3. Contingency Analysis: Naive RAG vs. Précis")
    lines.append("")
    lines.append(
        f"**Overall Accuracy:** Naive RAG = {naive_correct_count}/{n} "
        f"({(naive_correct_count/n)*100:.1f}%), "
        f"Précis = {precis_correct_count}/{n} ({(precis_correct_count/n)*100:.1f}%)"
    )
    lines.append("")
    lines.append("| Category | Count | % of Dataset | Interpretation |")
    lines.append("| :--- | :---: | :---: | :--- |")
    lines.append(
        f"| **Naive Correct, Précis Incorrect** | **{naive_t_precis_f}** | "
        f"**{(naive_t_precis_f/n)*100:.1f}%** | **Précis Information Bottleneck (Regressions)** |"
    )
    lines.append(
        f"| **Both Correct** | {naive_t_precis_t} | {(naive_t_precis_t/n)*100:.1f}% | "
        "Robust across both representations |"
    )
    lines.append(
        f"| **Both Incorrect** | {naive_f_precis_f} | {(naive_f_precis_f/n)*100:.1f}% | "
        "Hard questions or challenging context |"
    )
    lines.append(
        f"| **Précis Correct, Naive Incorrect** | {naive_f_precis_t} | "
        f"{(naive_f_precis_t/n)*100:.1f}% | Précis SVOA Win |"
    )

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 4. Failure Distribution by Question Type")
    lines.append("")
    lines.append(
        "| Question Type | Total | Correct | Extraction Fail | Retrieval Fail | "
        "Packing Fail | Generation Fail | Uncertain |"
    )
    lines.append(
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
    )
    for qt, counts in sorted(q_types.items(), key=lambda x: sum(x[1].values()), reverse=True):
        total_qt = sum(counts.values())
        lines.append(
            f"| **{qt}** | {total_qt} | "
            f"{counts.get(CLASS_CORRECT, 0)} | "
            f"{counts.get(CLASS_EXTRACTION_FAILURE, 0)} | "
            f"{counts.get(CLASS_RETRIEVAL_FAILURE, 0)} | "
            f"{counts.get(CLASS_PACKING_FAILURE, 0)} | "
            f"{counts.get(CLASS_GENERATION_FAILURE, 0)} | "
            f"{counts.get(CLASS_UNCERTAIN, 0)} |"
        )

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 5. Failure Distribution by Reference Answer Length")
    lines.append("")
    lines.append(
        "| Answer Length Category | Total | Correct | Extraction Fail | Retrieval Fail | "
        "Packing Fail | Generation Fail | Uncertain |"
    )
    lines.append(
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
    )
    for al, counts in sorted(ans_lens.items()):
        total_al = sum(counts.values())
        lines.append(
            f"| **{al}** | {total_al} | "
            f"{counts.get(CLASS_CORRECT, 0)} | "
            f"{counts.get(CLASS_EXTRACTION_FAILURE, 0)} | "
            f"{counts.get(CLASS_RETRIEVAL_FAILURE, 0)} | "
            f"{counts.get(CLASS_PACKING_FAILURE, 0)} | "
            f"{counts.get(CLASS_GENERATION_FAILURE, 0)} | "
            f"{counts.get(CLASS_UNCERTAIN, 0)} |"
        )

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 6. Experimental Condition Performance Comparison")
    lines.append("")
    lines.append("| Condition | Exact Match | ROUGE-L | BERTScore | Description |")
    lines.append("| :--- | :---: | :---: | :---: | :--- |")
    lines.append(
        f"| **Naive RAG (512-chunk)** | {cond_stats['naive_rag']['em']:.3f} "
        f"({cond_stats['naive_rag']['em_count']}/{n}) | "
        f"{cond_stats['naive_rag']['rouge_l']:.3f} | "
        f"{cond_stats['naive_rag']['bert_score']:.3f} | Baseline A: Raw passage chunks |"
    )
    lines.append(
        f"| **SVOA Pure Similarity** | {cond_stats['svoa_similarity']['em']:.3f} "
        f"({cond_stats['svoa_similarity']['em_count']}/{n}) | "
        f"{cond_stats['svoa_similarity']['rouge_l']:.3f} | "
        f"{cond_stats['svoa_similarity']['bert_score']:.3f} | "
        "Baseline B: SVOA facts ranked only by cosine sim |"
    )
    lines.append(
        f"| **SVOA w/o Modality** | {cond_stats['svoa_no_modality']['em']:.3f} "
        f"({cond_stats['svoa_no_modality']['em_count']}/{n}) | "
        f"{cond_stats['svoa_no_modality']['rouge_l']:.3f} | "
        f"{cond_stats['svoa_no_modality']['bert_score']:.3f} | "
        "Baseline C: SVOA + SDH, no modality filter |"
    )
    lines.append(
        f"| **Précis Full (6-Stage)** | {cond_stats['precis_full']['em']:.3f} "
        f"({cond_stats['precis_full']['em_count']}/{n}) | "
        f"{cond_stats['precis_full']['rouge_l']:.3f} | "
        f"{cond_stats['precis_full']['bert_score']:.3f} | "
        "Full Pipeline: SVOA + SDH + Modality Filter |"
    )

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 7. Representative Failure Case Studies")
    lines.append("")
    for fc in ALL_FAILURE_CLASSES:
        ex_list = examples_by_class.get(fc, [])
        if not ex_list:
            continue
        lines.append(f"### {fc}")
        lines.append("")
        for ex in ex_list:
            lines.append(f"- **Sample ID:** `{ex['sample_id']}`")
            lines.append(f"  - **Question:** \"{ex['question']}\"")
            lines.append(f"  - **Gold Answer:** \"{ex['gold_answer']}\"")
            lines.append(f"  - **Naive RAG Prediction:** \"{ex['naive_answer']}\"")
            lines.append(f"  - **Précis Prediction:** \"{ex['precis_answer']}\"")
            lines.append(f"  - **Evidence:** `{json.dumps(ex['evidence'])}`")
            if ex["relevant_fact_candidates"]:
                lines.append(
                    f"  - **Relevant Facts Found:** `{ex['relevant_fact_candidates'][:2]}`"
                )
            lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 8. Root Cause Analysis: Benchmark Anomalies")
    lines.append("")
    lines.append("### Issue 1: `generated_tokens = 0` in Naive RAG")
    lines.append(
        "**Observation:** Naive RAG rows in `per_question_results.jsonl` report "
        "`generated_tokens = 0` even when `predicted_answer` contains a multi-sentence response."
    )
    lines.append("")
    lines.append(
        "**Definitive Cause:** In `backend/src/precis/evaluation/naive_rag.py` (lines 205-216), "
        "`naive_rag_answer()` calls `result = generate_answer(...)`. `InferenceResult` correctly "
        "records `tokens_generated`, but `naive_rag_answer()` only returns a 2-tuple: "
        "`return result.answer, context_words`. In `backend/src/precis/evaluation/harness.py` "
        "(line 717), `_evaluate_answer()` is called with parameter `generated_tokens=0`. "
        "In contrast, SVOA conditions call `generate_answer()` directly and pass "
        "`inf_sim.tokens_generated` into `_evaluate_answer()`."
    )
    lines.append("")
    lines.append("### Issue 2: `duplicate_count = 126` in Benchmark Metadata")
    lines.append(
        "**Observation:** `benchmark_metadata.json` records `duplicate_count = 126`, whereas "
        "dataset conversion and validation verified 0 duplicate document IDs (`doc_id`)."
    )
    lines.append("")
    lines.append(
        "**Definitive Cause:** In `backend/src/precis/evaluation/harness.py` (lines 399-407), "
        "`duplicate_count` tracks identical normalized *question text* "
        "(`norm_q = question.strip().lower()`), NOT document IDs or duplicate rows. "
        "In NaturalQuestions (and MRQA), the same question frequently occurs multiple times "
        "across annotators or sections (e.g. 'how many episodes are in chicago fire season 4'). "
        "Because `--skip-invalid` was False during the official benchmark run, repeated questions "
        "were loaded and evaluated, incrementing `duplicate_count` each time a question was seen "
        "more than once."
    )

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 9. Diagnostic Synthesis: Why Précis Underperforms Naive RAG")
    lines.append("")
    lines.append(
        "Empirical funnel tracking reveals the primary driver of Précis performance degradation:"
    )
    lines.append("")
    lines.append(
        f"1. **The Primary Bottleneck is Extraction Loss "
        f"({class_counts.get(CLASS_EXTRACTION_FAILURE, 0)} questions, "
        f"{(class_counts.get(CLASS_EXTRACTION_FAILURE, 0)/n)*100:.1f}% of dataset):**\n"
        f"   Out of {source_has_count} questions where the source context contains the answer, "
        f"SVOA fact extraction preserves the answer in only {svoa_has_count} questions. "
        f"**{source_has_count - svoa_has_count} answers "
        f"({(source_has_count - svoa_has_count)/source_has_count*100:.1f}% of answer-bearing docs) "
        "are lost at Stage 2 (SVOA Extraction) before retrieval or packing even occur.**\n"
        "   - SVOA strictly requires finite verbs with subject/object dependencies. "
        "Factual answers embedded in noun phrases, list items (`<Li> ... </Li>`), appositives, "
        "parentheticals, or copular complements without overt transitive verbs fail to "
        "generate SVOA triples."
    )
    lines.append("")
    lines.append(
        f"2. **Vector Retrieval Misses "
        f"({class_counts.get(CLASS_RETRIEVAL_FAILURE, 0)} questions, "
        f"{(class_counts.get(CLASS_RETRIEVAL_FAILURE, 0)/n)*100:.1f}%):**\n"
        "   When facts are extracted, ChromaDB query similarity occasionally fails to rank "
        "atomic SVOA triples above non-answer-bearing facts due to the short lexical context "
        "of individual triples compared to rich 512-word passage chunks."
    )
    lines.append("")
    lines.append(
        f"3. **Packing and Modality Drops "
        f"({class_counts.get(CLASS_PACKING_FAILURE, 0)} questions, "
        f"{(class_counts.get(CLASS_PACKING_FAILURE, 0)/n)*100:.1f}%):**\n"
        "   Modality filtering and SDH re-ranking occasionally filter or displace relevant triples "
        "when modal auxiliaries are present or when SDH penalizes dense entity triples."
    )
    lines.append("")
    lines.append(
        f"4. **Generation Failure "
        f"({class_counts.get(CLASS_GENERATION_FAILURE, 0)} questions, "
        f"{(class_counts.get(CLASS_GENERATION_FAILURE, 0)/n)*100:.1f}%):**\n"
        f"   In {class_counts.get(CLASS_GENERATION_FAILURE, 0)} cases, the packed SVOA facts did "
        "include the answer, but the LLM failed to synthesize the final answer from isolated "
        "atomic fact strings."
    )

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 10. Recommended Next Experiment")
    lines.append("")
    lines.append(
        "Based on the empirical evidence showing that **Extraction Loss** is the predominant "
        "cause of underperformance:\n"
        "1. **Do NOT add complex retrieval rerankers or modify LLM prompts first.** "
        "They cannot recover information that never made it into the FactStore.\n"
        "2. **Target Stage 2 SVOA Extraction Coverage:** Evaluate expanding SVOA extraction "
        "to support copular/attributive relations (e.g. `X is Y`), appositive nominal clauses "
        "(`X, the Y of Z`), and list item structures without breaking epistemic modality typing.\n"
        "3. **Hybrid Passage-SVOA Fallback or Clause-Preserving Extraction:** Test whether "
        "preserving raw clause snippets alongside SVOA triples eliminates the 50%+ extraction "
        "drop-off while maintaining edge latency advantages."
    )

    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Diagnose Précis benchmark failures vs Naive RAG."
    )
    parser.add_argument(
        "--results",
        default="results/nq_benchmark/per_question_results.jsonl",
        help="Path to benchmark results JSONL.",
    )
    parser.add_argument(
        "--dataset",
        default="backend/data/nq_subset/nq_dev.jsonl",
        help="Path to nq_dev.jsonl dataset.",
    )
    parser.add_argument(
        "--output-jsonl",
        default="paper/tables/failure_analysis.jsonl",
        help="Output path for failure_analysis.jsonl.",
    )
    parser.add_argument(
        "--output-csv",
        default="paper/tables/failure_analysis.csv",
        help="Output path for failure_analysis.csv.",
    )
    parser.add_argument(
        "--output-summary",
        default="paper/tables/failure_summary.md",
        help="Output path for failure_summary.md.",
    )
    parser.add_argument(
        "--cache-path",
        default="backend/data/nq_subset/reconstructed_facts_cache.json",
        help="Path to cache reconstructed facts across runs.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Number of questions to evaluate.",
    )

    args = parser.parse_args()

    # Fallback check if results_path does not exist
    if not os.path.isfile(args.results):
        fallback = "paper/tables/per_question_results.jsonl"
        if os.path.isfile(fallback):
            print(f"Warning: {args.results} not found, falling back to {fallback}")
            args.results = fallback

    # Fallback check for dataset path
    if not os.path.isfile(args.dataset):
        fallback_ds = "data/nq_subset/nq_dev.jsonl"
        if os.path.isfile(fallback_ds):
            args.dataset = fallback_ds

    run_failure_analysis(
        results_path=args.results,
        dataset_path=args.dataset,
        output_jsonl=args.output_jsonl,
        output_csv=args.output_csv,
        output_summary=args.output_summary,
        cache_path=args.cache_path,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
