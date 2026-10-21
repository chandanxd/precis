#!/usr/bin/env python3
"""
Data preparation and context caching for Précis model-selection experiments.
Generates:
1. experiments/model_comparison/sample_manifest.jsonl
2. experiments/model_comparison/cached_contexts.jsonl
"""

import hashlib
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend" / "src"))

from precis.evaluation.naive_rag import naive_rag_retrieve
from precis.graph.store import FactStore
from precis.pipeline.orchestrator import ingest_document
from precis.pipeline.packer import pack_context, render_context


def compute_hash(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def main():
    dataset_path = Path("backend/data/nq_subset/nq_dev.jsonl")
    out_dir = Path("experiments/model_comparison")
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = out_dir / "sample_manifest.jsonl"
    contexts_path = out_dir / "cached_contexts.jsonl"

    print("Loading dataset:", dataset_path)
    with open(dataset_path, "r", encoding="utf-8") as f:
        all_lines = [json.loads(line) for line in f if line.strip()]

    print(f"Total lines in source dataset: {len(all_lines)}")

    # 1. Canonical 200 samples
    canonical_200 = all_lines[:200]
    canonical_doc_ids = set(d["doc_id"] for d in canonical_200)
    canonical_qs = set(d["question"].strip().lower() for d in canonical_200)
    canonical_content_hashes = set(
        compute_hash(f"{d['question'].strip()}|{d['gold_answer'].strip()}|{d['document'].strip()}")
        for d in canonical_200
    )
    canonical_doc_hashes = set(compute_hash(d["document"]) for d in canonical_200)

    # Group canonical 200 by question
    q_to_canonical = defaultdict(list)
    for idx, d in enumerate(canonical_200):
        norm_q = d["question"].strip().lower()
        q_to_canonical[norm_q].append(d)

    canonical_distinct_qs = sorted(q_to_canonical.keys())
    print(f"Canonical distinct questions: {len(canonical_distinct_qs)}")

    # Sort distinct questions by SHA-256 hash
    hashed_canonical_qs = sorted(canonical_distinct_qs, key=compute_hash)
    stage_a_clusters = hashed_canonical_qs[:35]
    remaining_clusters = hashed_canonical_qs[35:]

    stage_a_samples = [s for q in stage_a_clusters for s in q_to_canonical[q]]
    print(f"Stage A selected distinct questions: {len(stage_a_clusters)}")
    print(f"Stage A selected sample records: {len(stage_a_samples)}")

    # 2. Stage B candidate filtering
    candidate_pool = []
    seen_qs = set()
    seen_doc_ids = set()
    seen_doc_hashes = set()

    exclusions = {
        "empty_fields": 0,
        "canonical_doc_id_overlap": 0,
        "canonical_content_hash_overlap": 0,
        "canonical_question_overlap": 0,
        "canonical_document_overlap": 0,
        "duplicate_question_in_pool": 0,
        "duplicate_doc_id_in_pool": 0,
        "duplicate_document_in_pool": 0,
    }

    for d in all_lines:
        did = d.get("doc_id", "").strip()
        q = d.get("question", "").strip()
        norm_q = q.lower()
        doc = d.get("document", "").strip()
        ans = d.get("gold_answer", "").strip()

        if not (did and q and doc and ans):
            exclusions["empty_fields"] += 1
            continue
        if did in canonical_doc_ids:
            exclusions["canonical_doc_id_overlap"] += 1
            continue
        chash = compute_hash(f"{q}|{ans}|{doc}")
        if chash in canonical_content_hashes:
            exclusions["canonical_content_hash_overlap"] += 1
            continue
        if norm_q in canonical_qs:
            exclusions["canonical_question_overlap"] += 1
            continue
        dhash = compute_hash(doc)
        if dhash in canonical_doc_hashes:
            exclusions["canonical_document_overlap"] += 1
            continue
        if norm_q in seen_qs:
            exclusions["duplicate_question_in_pool"] += 1
            continue
        if did in seen_doc_ids:
            exclusions["duplicate_doc_id_in_pool"] += 1
            continue
        if dhash in seen_doc_hashes:
            exclusions["duplicate_document_in_pool"] += 1
            continue

        seen_qs.add(norm_q)
        seen_doc_ids.add(did)
        seen_doc_hashes.add(dhash)
        candidate_pool.append(d)

    print(f"Total eligible Stage B candidates: {len(candidate_pool)}")
    print("Exclusion counts:", json.dumps(exclusions, indent=2))

    # Sort eligible candidates by SHA-256 of question and select first 100
    candidate_pool_sorted = sorted(
        candidate_pool,
        key=lambda item: compute_hash(item["question"].strip().lower())
    )
    stage_b_samples = candidate_pool_sorted[:100]
    print(f"Stage B selected records: {len(stage_b_samples)}")

    # 3. Write Manifest
    manifest_records = []
    # Header record with provenance
    manifest_records.append({
        "type": "manifest_header",
        "dataset_source": "backend/data/nq_subset/nq_dev.jsonl",
        "total_source_lines": len(all_lines),
        "canonical_samples_count": len(canonical_200),
        "stage_a_clusters": len(stage_a_clusters),
        "stage_a_samples": len(stage_a_samples),
        "stage_b_eligible_pool": len(candidate_pool),
        "stage_b_samples": len(stage_b_samples),
        "exclusions": exclusions,
    })

    # Stage A records
    for s in stage_a_samples:
        norm_q = s["question"].strip().lower()
        manifest_records.append({
            "type": "sample_record",
            "cohort": "stage_a_dev",
            "sample_id": s["doc_id"],
            "cluster_id": compute_hash(norm_q)[:16],
            "question": s["question"],
            "normalized_question": norm_q,
            "gold_answer": s["gold_answer"],
            "all_answers": s.get("answers", [s["gold_answer"]]),
            "document": s["document"],
            "document_words": len(s["document"].split()),
            "doc_hash": compute_hash(s["document"]),
            "content_hash": compute_hash(f"{s['question'].strip()}|{s['gold_answer'].strip()}|{s['document'].strip()}"),
        })

    # Stage B records
    for s in stage_b_samples:
        norm_q = s["question"].strip().lower()
        manifest_records.append({
            "type": "sample_record",
            "cohort": "stage_b_eval",
            "sample_id": s["doc_id"],
            "cluster_id": compute_hash(norm_q)[:16],
            "question": s["question"],
            "normalized_question": norm_q,
            "gold_answer": s["gold_answer"],
            "all_answers": s.get("answers", [s["gold_answer"]]),
            "document": s["document"],
            "document_words": len(s["document"].split()),
            "doc_hash": compute_hash(s["document"]),
            "content_hash": compute_hash(f"{s['question'].strip()}|{s['gold_answer'].strip()}|{s['document'].strip()}"),
        })

    print(f"Writing sample manifest to {manifest_path}...")
    with open(manifest_path, "w", encoding="utf-8") as f:
        for rec in manifest_records:
            f.write(json.dumps(rec) + "\n")

    # 4. Extract and Cache Contexts with SHA-256 Checksums
    print(f"\nExtracting and caching contexts for {len(stage_a_samples) + len(stage_b_samples)} samples...")
    all_eval_samples = stage_a_samples + stage_b_samples

    cached_contexts = []
    for idx, s in enumerate(all_eval_samples):
        sid = s["doc_id"]
        q = s["question"]
        doc = s["document"]
        cohort = "stage_a_dev" if idx < len(stage_a_samples) else "stage_b_eval"

        if (idx + 1) % 25 == 0 or idx == 0 or idx == len(all_eval_samples) - 1:
            print(f"  [{idx + 1}/{len(all_eval_samples)}] Caching sample: {sid} ({cohort})")

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
        store = FactStore(in_memory=True, collection_name=f"cache_{idx}_{compute_hash(sid)[:8]}")
        ingest_document(doc, sid, store)
        pack_full = pack_context(query=q, store=store, token_ceiling=2048)
        precis_context_str = render_context(pack_full.packed_facts)
        precis_context_str = precis_context_str if precis_context_str.strip() else "(No relevant facts retrieved)"
        precis_checksum = compute_hash(precis_context_str)

        cached_contexts.append({
            "sample_id": sid,
            "cohort": cohort,
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

    print(f"Writing cached contexts to {contexts_path}...")
    with open(contexts_path, "w", encoding="utf-8") as f:
        for rec in cached_contexts:
            f.write(json.dumps(rec) + "\n")

    print("\nData preparation and context caching complete!")
    print(f"Manifest: {manifest_path} ({len(manifest_records)} lines)")
    print(f"Cached contexts: {contexts_path} ({len(cached_contexts)} lines)")


if __name__ == "__main__":
    main()
