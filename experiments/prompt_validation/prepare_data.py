#!/usr/bin/env python3
"""
Data preparation, cohort selection, and overlap audit script for
Précis Confirmatory Answer-Formatting Experiment.

Ensures:
1. Complete exclusion of canonical v3 samples, questions, and documents.
2. Complete exclusion of prior model-selection Stages A/B/C samples, questions, and documents.
3. Strict deduplication of normalized questions and document texts.
4. Deterministic selection of exactly 100 question-document pairs.
5. Export of machine-readable audit report: experiments/prompt_validation/audit_report.json.
6. Bit-for-bit context caching with SHA-256 integrity verification.
"""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# Add backend/src to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "src"))

from precis.evaluation.naive_rag import naive_rag_retrieve
from precis.graph.store import FactStore
from precis.pipeline.orchestrator import ingest_document
from precis.pipeline.packer import pack_context, render_context


def compute_hash(text: str) -> str:
    """Compute SHA-256 hash of a UTF-8 string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def norm_q_fn(q: str) -> str:
    """Exact question normalization: strip and lowercase."""
    return q.strip().lower()


def load_canonical_exclusions(
    canonical_results_path: Path,
    nq_dev_path: Path,
) -> Tuple[Set[str], Set[str], Set[str]]:
    """Load canonical v3 IDs, normalized questions, and document hashes."""
    canonical_ids: Set[str] = set()
    canonical_norm_qs: Set[str] = set()

    if canonical_results_path.exists():
        with open(canonical_results_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                d = json.loads(line)
                sid = str(d.get("sample_id") or d.get("doc_id") or "")
                if sid:
                    canonical_ids.add(sid)
                q = d.get("question", "").strip()
                if q:
                    canonical_norm_qs.add(norm_q_fn(q))

    # Match canonical IDs in nq_dev.jsonl to get exact canonical document hashes
    canonical_doc_hashes: Set[str] = set()
    if nq_dev_path.exists():
        with open(nq_dev_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                d = json.loads(line)
                sid = str(d.get("id") or d.get("doc_id") or "")
                if sid in canonical_ids:
                    doc = (d.get("document") or d.get("context") or "").strip()
                    if doc:
                        canonical_doc_hashes.add(compute_hash(doc))

    return canonical_ids, canonical_norm_qs, canonical_doc_hashes


def load_prior_manifest_exclusions(
    prior_manifest_path: Path,
) -> Tuple[Set[str], Set[str], Set[str]]:
    """Load prior model-selection Stages A/B/C IDs, normalized questions, and document hashes."""
    prior_ids: Set[str] = set()
    prior_norm_qs: Set[str] = set()
    prior_doc_hashes: Set[str] = set()

    if prior_manifest_path.exists():
        with open(prior_manifest_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                d = json.loads(line)
                if d.get("type") != "sample_record":
                    continue
                sid = str(d.get("sample_id") or "")
                nq = d.get("normalized_question") or ""
                dh = d.get("doc_hash") or ""
                if sid:
                    prior_ids.add(sid)
                if nq:
                    prior_norm_qs.add(nq)
                if dh:
                    prior_doc_hashes.add(dh)

    return prior_ids, prior_norm_qs, prior_doc_hashes


def audit_and_filter_pool(
    nq_dev_path: Path,
    canonical_ids: Set[str],
    canonical_norm_qs: Set[str],
    canonical_doc_hashes: Set[str],
    prior_ids: Set[str],
    prior_norm_qs: Set[str],
    prior_doc_hashes: Set[str],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Sequentially audit and filter nq_dev.jsonl records.
    Returns:
    - eligible_records: list of deduplicated, eligible sample records.
    - audit_report: complete statistics on sequential and marginal exclusions.
    """
    total_raw_records = 0
    seq_ex_empty = 0
    seq_ex_canonical_id = 0
    seq_ex_canonical_q = 0
    seq_ex_canonical_doc = 0
    seq_ex_prior_id = 0
    seq_ex_prior_q = 0
    seq_ex_prior_doc = 0
    seq_ex_pool_dup_q = 0
    seq_ex_pool_dup_doc = 0

    marginal_matches = {
        "canonical_id": 0,
        "canonical_q": 0,
        "canonical_doc": 0,
        "prior_id": 0,
        "prior_q": 0,
        "prior_doc": 0,
    }

    seen_pool_qs: Set[str] = set()
    seen_pool_docs: Set[str] = set()
    eligible_records: List[Dict[str, Any]] = []

    with open(nq_dev_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            if not line.strip():
                continue
            total_raw_records += 1
            d = json.loads(line)
            sid = str(d.get("id") or d.get("doc_id") or f"dev_{idx}")
            q = (d.get("question") or "").strip()
            doc = (d.get("document") or d.get("context") or "").strip()

            if not q or not doc:
                seq_ex_empty += 1
                continue

            nq = norm_q_fn(q)
            dh = compute_hash(doc)

            # Record marginal counts across the entire dataset
            if sid in canonical_ids:
                marginal_matches["canonical_id"] += 1
            if nq in canonical_norm_qs:
                marginal_matches["canonical_q"] += 1
            if dh in canonical_doc_hashes:
                marginal_matches["canonical_doc"] += 1
            if sid in prior_ids:
                marginal_matches["prior_id"] += 1
            if nq in prior_norm_qs:
                marginal_matches["prior_q"] += 1
            if dh in prior_doc_hashes:
                marginal_matches["prior_doc"] += 1

            # Priority-ordered sequential exclusions
            if sid in canonical_ids:
                seq_ex_canonical_id += 1
                continue
            if nq in canonical_norm_qs:
                seq_ex_canonical_q += 1
                continue
            if dh in canonical_doc_hashes:
                seq_ex_canonical_doc += 1
                continue
            if sid in prior_ids:
                seq_ex_prior_id += 1
                continue
            if nq in prior_norm_qs:
                seq_ex_prior_q += 1
                continue
            if dh in prior_doc_hashes:
                seq_ex_prior_doc += 1
                continue
            if nq in seen_pool_qs:
                seq_ex_pool_dup_q += 1
                continue
            if dh in seen_pool_docs:
                seq_ex_pool_dup_doc += 1
                continue

            seen_pool_qs.add(nq)
            seen_pool_docs.add(dh)

            gold_ans = d.get("gold_answer") or (d.get("answers", [""])[0])
            all_answers = d.get("answers", [gold_ans])

            eligible_records.append({
                "doc_id": sid,
                "question": q,
                "normalized_question": nq,
                "gold_answer": gold_ans,
                "answers": all_answers,
                "document": doc,
                "doc_hash": dh,
                "content_hash": compute_hash(f"{q}|{gold_ans}|{doc}"),
                "q_hash": compute_hash(nq),
            })

    # Verification: sequential counts must partition the entire dataset
    sum_seq = (
        seq_ex_empty
        + seq_ex_canonical_id
        + seq_ex_canonical_q
        + seq_ex_canonical_doc
        + seq_ex_prior_id
        + seq_ex_prior_q
        + seq_ex_prior_doc
        + seq_ex_pool_dup_q
        + seq_ex_pool_dup_doc
        + len(eligible_records)
    )
    assert sum_seq == total_raw_records, f"Sequential sum mismatch: {sum_seq} != {total_raw_records}"

    audit_report = {
        "dataset_path": str(nq_dev_path),
        "total_raw_records": total_raw_records,
        "marginal_matches": marginal_matches,
        "sequential_exclusions": {
            "empty_doc_or_question": seq_ex_empty,
            "canonical_v3_id": seq_ex_canonical_id,
            "canonical_v3_question": seq_ex_canonical_q,
            "canonical_v3_doc_hash": seq_ex_canonical_doc,
            "prior_experiment_id": seq_ex_prior_id,
            "prior_experiment_question": seq_ex_prior_q,
            "prior_experiment_doc_hash": seq_ex_prior_doc,
            "within_pool_duplicate_question": seq_ex_pool_dup_q,
            "within_pool_duplicate_doc_hash": seq_ex_pool_dup_doc,
            "total_excluded": total_raw_records - len(eligible_records),
        },
        "strictly_eligible_records": len(eligible_records),
    }

    return eligible_records, audit_report


def main():
    parser = argparse.ArgumentParser(description="Prepare cohort and cache contexts for prompt validation.")
    parser.add_argument("--audit-only", action="store_true", help="Perform preflight overlap audit and exit without generating contexts.")
    parser.add_argument("--num-samples", type=int, default=100, help="Number of samples to select.")
    args = parser.parse_args()

    canonical_path = PROJECT_ROOT / "results" / "nq_benchmark_svoa_enhanced_v3" / "per_question_results.jsonl"
    prior_manifest_path = PROJECT_ROOT / "experiments" / "model_comparison" / "sample_manifest.jsonl"
    nq_dev_path = PROJECT_ROOT / "backend" / "data" / "nq_subset" / "nq_dev.jsonl"

    exp_dir = PROJECT_ROOT / "experiments" / "prompt_validation"
    exp_dir.mkdir(parents=True, exist_ok=True)

    print("Auditing prior cohorts and screening NQ development dataset...")
    canonical_ids, canonical_qs, canonical_docs = load_canonical_exclusions(canonical_path, nq_dev_path)
    prior_ids, prior_qs, prior_docs = load_prior_manifest_exclusions(prior_manifest_path)

    print(f"Canonical v3: {len(canonical_ids)} IDs, {len(canonical_qs)} unique questions, {len(canonical_docs)} unique doc hashes")
    print(f"Prior Model Comparison: {len(prior_ids)} IDs, {len(prior_qs)} unique questions, {len(prior_docs)} unique doc hashes")

    eligible_records, audit_report = audit_and_filter_pool(
        nq_dev_path=nq_dev_path,
        canonical_ids=canonical_ids,
        canonical_norm_qs=canonical_qs,
        canonical_doc_hashes=canonical_docs,
        prior_ids=prior_ids,
        prior_norm_qs=prior_qs,
        prior_doc_hashes=prior_docs,
    )

    audit_file = exp_dir / "audit_report.json"
    with open(audit_file, "w", encoding="utf-8") as f:
        json.dump(audit_report, f, indent=2)

    print(f"\nAudit complete! Report written to {audit_file}")
    print(f"Total raw NQ records: {audit_report['total_raw_records']}")
    print(f"Total strictly eligible remaining records: {audit_report['strictly_eligible_records']}")

    if args.audit_only:
        print("[AUDIT-ONLY MODE] Pre-execution audit complete. Exiting without selecting final cohort or caching contexts.")
        return

    # Check sufficient samples
    if len(eligible_records) < args.num_samples:
        raise RuntimeError(f"Insufficient eligible records: {len(eligible_records)} < {args.num_samples}")

    # Deterministic selection: sort by SHA-256 of normalized question
    eligible_records.sort(key=lambda x: x["q_hash"])
    selected_samples = eligible_records[: args.num_samples]

    # Preflight verification of selected cohort
    sel_ids = {s["doc_id"] for s in selected_samples}
    sel_qs = {s["normalized_question"] for s in selected_samples}
    sel_docs = {s["doc_hash"] for s in selected_samples}

    assert len(sel_ids) == args.num_samples, "Duplicate doc_id in selected cohort!"
    assert len(sel_qs) == args.num_samples, "Duplicate question in selected cohort!"
    assert len(sel_docs) == args.num_samples, "Duplicate document in selected cohort!"

    assert not (sel_ids & canonical_ids), "Canonical ID leak in selected cohort!"
    assert not (sel_qs & canonical_qs), "Canonical question leak in selected cohort!"
    assert not (sel_docs & canonical_docs), "Canonical doc leak in selected cohort!"

    assert not (sel_ids & prior_ids), "Prior experiment ID leak in selected cohort!"
    assert not (sel_qs & prior_qs), "Prior experiment question leak in selected cohort!"
    assert not (sel_docs & prior_docs), "Prior experiment doc leak in selected cohort!"

    print(f"\n[VERIFIED] Selected {len(selected_samples)} samples with 0 overlap across all identifiers.")

    manifest_path = exp_dir / "sample_manifest.jsonl"
    print(f"Writing sample manifest to {manifest_path}...")
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(json.dumps({
            "type": "manifest_header",
            "experiment": "precis_confirmatory_answer_formatting",
            "cohort": "confirmatory_heldout_dev",
            "num_samples": len(selected_samples),
            "description": "Deduplicated held-out cohort from NQ dev with zero overlap with canonical v3 or model-comparison cohorts."
        }) + "\n")
        for s in selected_samples:
            f.write(json.dumps({
                "type": "sample_record",
                "cohort": "confirmatory_heldout_dev",
                "sample_id": s["doc_id"],
                "question": s["question"],
                "normalized_question": s["normalized_question"],
                "gold_answer": s["gold_answer"],
                "answers": s["answers"],
                "doc_hash": s["doc_hash"],
                "content_hash": s["content_hash"],
                "q_hash": s["q_hash"],
                "document": s["document"],
            }) + "\n")

    # Extract and cache contexts
    contexts_path = exp_dir / "cached_contexts.jsonl"
    print(f"\nExtracting and caching contexts to {contexts_path}...")
    cached_contexts = []

    for idx, s in enumerate(selected_samples):
        sid = s["doc_id"]
        q = s["question"]
        doc = s["document"]

        if (idx + 1) % 25 == 0 or idx == 0 or idx == len(selected_samples) - 1:
            print(f"  [{idx + 1}/{len(selected_samples)}] Caching sample: {sid}")

        # Naive RAG context
        naive_chunks, naive_words = naive_rag_retrieve(
            document=doc,
            query=q,
            top_k=5,
            chunk_size=512,
            overlap=128,
        )
        naive_context_str = "\n\n".join(naive_chunks) if naive_chunks else "(No context retrieved)"
        naive_checksum = compute_hash(naive_context_str)

        # Précis v3 context
        store = FactStore(in_memory=True, collection_name=f"prompt_cache_{idx}_{compute_hash(sid)[:8]}")
        ingest_document(doc, sid, store)
        pack_full = pack_context(query=q, store=store, token_ceiling=2048)
        precis_context_str = render_context(pack_full.packed_facts)
        precis_context_str = precis_context_str if precis_context_str.strip() else "(No relevant facts retrieved)"
        precis_checksum = compute_hash(precis_context_str)

        cached_contexts.append({
            "sample_id": sid,
            "cohort": "confirmatory_heldout_dev",
            "question": q,
            "gold_answer": s["gold_answer"],
            "naive_rag": {
                "context_text": naive_context_str,
                "context_words": len(naive_context_str.split()),
                "context_tokens_est": int(len(naive_context_str.split()) * 1.3),
                "retrieved_chunks_count": len(naive_chunks),
                "sha256": naive_checksum,
            },
            "precis_v3": {
                "context_text": precis_context_str,
                "context_words": len(precis_context_str.split()),
                "context_tokens_est": pack_full.tokens_used,
                "facts_considered": pack_full.facts_considered,
                "facts_packed": pack_full.facts_packed,
                "avg_sdh_score": pack_full.avg_sdh_score,
                "compression_rate": pack_full.compression_rate,
                "sha256": precis_checksum,
            }
        })

    with open(contexts_path, "w", encoding="utf-8") as f:
        for rec in cached_contexts:
            f.write(json.dumps(rec) + "\n")

    print(f"\n[DONE] Context caching complete! Cached {len(cached_contexts)} samples.")


if __name__ == "__main__":
    main()
