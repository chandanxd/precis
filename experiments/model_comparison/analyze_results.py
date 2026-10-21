#!/usr/bin/env python3
"""
Statistical analysis and decision engine for Précis model selection experiment.
Implements:
1. Stage A screening and candidate selection with containment guardrail and tie-breakers.
2. Stage B inferential analysis:
   - H1 McNemar paired test (two-sided & one-sided)
   - H2 Paired cluster-bootstrap (10,000 resamples) for Delta_gap with 95% CI
   - Rigorous classification (Supported iff CI > 0; Inconclusive if 0 in CI; Opposite iff CI < 0)
3. Stage C prompt-ablation analysis (standard vs concise).
4. Export to results.json and formatted markdown tables.
"""

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import stats


def load_jsonl(file_path: Path) -> List[Dict[str, Any]]:
    records = []
    if not file_path.exists():
        return records
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if line_str:
                records.append(json.loads(line_str))
    return records


def compute_metrics_summary(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute summary statistics for a list of evaluation records."""
    if not records:
        return {}

    n = len(records)
    em_count = sum(1 for r in records if r.get("exact_match", False))
    cont_count = sum(1 for r in records if r.get("containment_correct", False))

    rouge_scores = [
        r["rouge_l"] if isinstance(r["rouge_l"], (int, float)) else r["rouge_l"].get("f1", 0.0)
        for r in records if r.get("rouge_l") is not None
    ]
    minilm_scores = [r["minilm_cosine"] for r in records if r.get("minilm_cosine") is not None]
    bert_scores = [
        r["bert_score"] if isinstance(r["bert_score"], (int, float)) else r["bert_score"].get("f1", 0.0)
        for r in records if r.get("bert_score") is not None
    ]
    latencies = [r["latency_ms"] for r in records if r.get("latency_ms") is not None]
    tokens = [r["generated_tokens"] for r in records if r.get("generated_tokens") is not None]

    return {
        "count": n,
        "exact_match": {
            "count": em_count,
            "rate": em_count / n if n > 0 else 0.0,
        },
        "containment": {
            "count": cont_count,
            "rate": cont_count / n if n > 0 else 0.0,
        },
        "rouge_l_f1": {
            "mean": float(np.mean(rouge_scores)) if rouge_scores else 0.0,
            "std": float(np.std(rouge_scores)) if rouge_scores else 0.0,
        },
        "minilm_cosine": {
            "mean": float(np.mean(minilm_scores)) if minilm_scores else 0.0,
            "std": float(np.std(minilm_scores)) if minilm_scores else 0.0,
        },
        "bert_score_f1": {
            "mean": float(np.mean(bert_scores)) if bert_scores else 0.0,
            "std": float(np.std(bert_scores)) if bert_scores else 0.0,
        },
        "latency_ms": {
            "mean": float(np.mean(latencies)) if latencies else 0.0,
            "p50": float(np.percentile(latencies, 50)) if latencies else 0.0,
            "p90": float(np.percentile(latencies, 90)) if latencies else 0.0,
        },
        "generated_tokens": {
            "mean": float(np.mean(tokens)) if tokens else 0.0,
            "p50": float(np.percentile(tokens, 50)) if tokens else 0.0,
        },
    }


def mcnemar_test(pairs_a: List[int], pairs_b: List[int]) -> Dict[str, Any]:
    """
    Compute McNemar test between binary outcomes A and B.
    pairs_a: outcome for system A (1 = correct, 0 = incorrect)
    pairs_b: outcome for system B (1 = correct, 0 = incorrect)
    """
    assert len(pairs_a) == len(pairs_b), "Pair lengths must match"
    n = len(pairs_a)

    # Contingency table:
    # b: A correct, B incorrect
    # c: A incorrect, B correct
    n00 = sum(1 for a, b in zip(pairs_a, pairs_b) if a == 0 and b == 0)
    n01 = sum(1 for a, b in zip(pairs_a, pairs_b) if a == 0 and b == 1)  # c
    n10 = sum(1 for a, b in zip(pairs_a, pairs_b) if a == 1 and b == 0)  # b
    n11 = sum(1 for a, b in zip(pairs_a, pairs_b) if a == 1 and b == 1)

    b = n10
    c = n01
    discordant = b + c

    # Exact binomial test on discordant pairs
    if discordant == 0:
        p_two_sided = 1.0
        p_greater = 1.0
    else:
        binom = stats.binomtest(b, n=discordant, p=0.5, alternative="two-sided")
        p_two_sided = binom.pvalue
        binom_greater = stats.binomtest(b, n=discordant, p=0.5, alternative="greater")
        p_greater = binom_greater.pvalue

    odds_ratio = b / c if c > 0 else (float("inf") if b > 0 else 1.0)

    return {
        "n": n,
        "table": {
            "n00": n00,
            "n01_ref_only": n01,
            "n10_cand_only": n10,
            "n11_both": n11,
        },
        "discordant_pairs": discordant,
        "odds_ratio": odds_ratio,
        "p_value_two_sided": p_two_sided,
        "p_value_one_sided_greater": p_greater,
    }


def bootstrap_gap_difference(
    cand_precis_em: List[int],
    cand_naive_em: List[int],
    ref_precis_em: List[int],
    ref_naive_em: List[int],
    n_resamples: int = 10000,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Paired bootstrap for Delta_gap across samples.
    For sample i:
      delta_cand(i) = cand_precis(i) - cand_naive(i)
      delta_ref(i) = ref_precis(i) - ref_naive(i)
      Delta(i) = delta_cand(i) - delta_ref(i)
    Delta_gap = mean(Delta(i))
    """
    n = len(cand_precis_em)
    assert len(cand_naive_em) == n == len(ref_precis_em) == len(ref_naive_em)

    deltas = np.array([
        (cp - cn) - (rp - rn)
        for cp, cn, rp, rn in zip(cand_precis_em, cand_naive_em, ref_precis_em, ref_naive_em)
    ], dtype=float)

    point_estimate = float(np.mean(deltas))

    # Point estimates of components
    cand_p_em = float(np.mean(cand_precis_em))
    cand_n_em = float(np.mean(cand_naive_em))
    ref_p_em = float(np.mean(ref_precis_em))
    ref_n_em = float(np.mean(ref_naive_em))

    cand_gap = cand_p_em - cand_n_em
    ref_gap = ref_p_em - ref_n_em

    rng = np.random.default_rng(seed)
    indices = rng.integers(0, n, size=(n_resamples, n))
    bootstrap_samples = deltas[indices]  # shape: (n_resamples, n)
    bootstrap_means = np.mean(bootstrap_samples, axis=1)

    ci_lower = float(np.percentile(bootstrap_means, 2.5))
    ci_upper = float(np.percentile(bootstrap_means, 97.5))
    std_err = float(np.std(bootstrap_means))

    # Rigorous prespecified decision rule:
    # Supported: CI lower > 0
    # Inconclusive: CI lower <= 0 <= CI upper
    # Opposite direction: CI upper < 0
    if ci_lower > 0.0:
        classification = "SUPPORTED"
    elif ci_upper < 0.0:
        classification = "OPPOSITE_DIRECTION"
    else:
        classification = "INCONCLUSIVE"

    return {
        "point_estimate": point_estimate,
        "std_error": std_err,
        "ci_95": [ci_lower, ci_upper],
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "n_resamples": n_resamples,
        "classification": classification,
        "components": {
            "cand_precis_em": cand_p_em,
            "cand_naive_em": cand_n_em,
            "cand_gap": cand_gap,
            "ref_precis_em": ref_p_em,
            "ref_naive_em": ref_n_em,
            "ref_gap": ref_gap,
        },
    }


def analyze_stage_a(raw_dir: Path) -> Dict[str, Any]:
    """Analyze all Stage A outputs and select winning candidate."""
    print("\n=======================================================")
    print("STAGE A: DEVELOPMENT SCREENING ANALYSIS")
    print("=======================================================")

    controlled_models = [
        ("qwen2.5-coder:7b", "stage_a_qwen2_5-coder_7b.jsonl", 7.0),
        ("qwen3.5:4b", "stage_a_qwen3_5_4b.jsonl", 4.0),
        ("qwen3.5:9b", "stage_a_qwen3_5_9b.jsonl", 9.0),
        ("gemma4:e2b", "stage_a_gemma4_e2b.jsonl", 2.0),
        ("gemma4:e4b", "stage_a_gemma4_e4b.jsonl", 4.0),
        ("gemma4:12b", "stage_a_gemma4_12b.jsonl", 12.0),
    ]

    exploratory_models = [
        ("deepseek-r1:8b", "stage_a_deepseek-r1_8b_exploratory.jsonl", 8.0),
    ]

    model_results = {}

    for tag, filename, params in controlled_models:
        path = raw_dir / filename
        if not path.exists():
            continue
        records = load_jsonl(path)
        naive_recs = [r for r in records if r.get("condition") == "naive_rag"]
        precis_recs = [r for r in records if r.get("condition") == "precis_full"]

        naive_summary = compute_metrics_summary(naive_recs)
        precis_summary = compute_metrics_summary(precis_recs)

        em_p = precis_summary.get("exact_match", {}).get("rate", 0.0)
        em_n = naive_summary.get("exact_match", {}).get("rate", 0.0)
        cont_p = precis_summary.get("containment", {}).get("rate", 0.0)
        cont_n = naive_summary.get("containment", {}).get("rate", 0.0)

        lat_p = precis_summary.get("latency_ms", {}).get("mean", 0.0)

        model_results[tag] = {
            "model_tag": tag,
            "params_b": params,
            "sample_count": len(precis_recs),
            "naive_rag": naive_summary,
            "precis_full": precis_summary,
            "deltas": {
                "em_gap_precis_minus_naive": em_p - em_n,
                "cont_gap_precis_minus_naive": cont_p - cont_n,
            },
            "selection_keys": {
                "precis_em": em_p,
                "precis_cont": cont_p,
                "precis_latency_mean": lat_p,
                "params_b": params,
            },
        }

    # Reference model baseline
    ref_tag = "qwen2.5-coder:7b"
    ref_data = model_results.get(ref_tag)
    if not ref_data:
        print("Warning: Reference model qwen2.5-coder:7b not yet evaluated on Stage A.")
        return {"stage_a_models": model_results, "selected_candidate": None}

    ref_cont = ref_data["selection_keys"]["precis_cont"]
    ref_em = ref_data["selection_keys"]["precis_em"]
    print(f"Reference Model ({ref_tag}): Précis EM = {ref_em:.4f}, Précis Containment = {ref_cont:.4f}")

    # Candidate evaluation against guardrail
    candidates = [
        m for tag, m in model_results.items()
        if tag != ref_tag
    ]

    qualifying_candidates = []
    disqualified_candidates = []

    for c in candidates:
        tag = c["model_tag"]
        cont = c["selection_keys"]["precis_cont"]
        em = c["selection_keys"]["precis_em"]
        lat = c["selection_keys"]["precis_latency_mean"]

        # Guardrail check
        if cont >= ref_cont:
            qualifying_candidates.append(c)
            print(f"  [QUALIFIED] {tag:15s} | EM: {em:.4f} | Cont: {cont:.4f} (>= {ref_cont:.4f}) | Latency: {lat:.1f}ms")
        else:
            disqualified_candidates.append(c)
            print(f"  [GUARDRAIL FAIL] {tag:15s} | EM: {em:.4f} | Cont: {cont:.4f} (< {ref_cont:.4f}) | Latency: {lat:.1f}ms")

    selected_candidate = None
    selection_reason = ""

    if qualifying_candidates:
        # Sort by:
        # 1. Highest Précis EM (descending)
        # 2. Highest Précis Containment (descending)
        # 3. Lowest mean latency (ascending)
        # 4. Smallest parameter count (ascending)
        qualifying_candidates.sort(
            key=lambda x: (
                -x["selection_keys"]["precis_em"],
                -x["selection_keys"]["precis_cont"],
                x["selection_keys"]["precis_latency_mean"],
                x["selection_keys"]["params_b"],
            )
        )
        selected_candidate = qualifying_candidates[0]
        selection_reason = (
            f"Ranked #1 among {len(qualifying_candidates)} qualifying models. "
            f"Précis EM: {selected_candidate['selection_keys']['precis_em']:.4f}, "
            f"Containment: {selected_candidate['selection_keys']['precis_cont']:.4f} >= {ref_cont:.4f}."
        )
        print(f"\n--> Selected Winning Candidate: {selected_candidate['model_tag']}")
        print(f"    Reason: {selection_reason}")
    else:
        selection_reason = (
            "FALLBACK TRIGGERED: Zero candidates satisfied the Stage A containment guardrail "
            f"(Cont >= {ref_cont:.4f}). As prespecified, the guardrail is NOT relaxed. "
            "Stage B will run the reference model as control, with the highest-EM candidate evaluated purely as exploratory."
        )
        print(f"\n--> {selection_reason}")

    # Process exploratory deepseek-r1:8b if present
    exploratory_results = {}
    for tag, filename, params in exploratory_models:
        path = raw_dir / filename
        if not path.exists():
            continue
        records = load_jsonl(path)
        naive_recs = [r for r in records if r.get("condition") == "naive_rag"]
        precis_recs = [r for r in records if r.get("condition") == "precis_full"]
        exploratory_results[tag] = {
            "model_tag": tag,
            "sample_count": len(precis_recs),
            "naive_rag": compute_metrics_summary(naive_recs),
            "precis_full": compute_metrics_summary(precis_recs),
            "note": "Reasoning mode enabled (512 tokens). Not eligible for non-thinking candidate ranking.",
        }

    return {
        "reference_model": ref_tag,
        "reference_precis_cont_threshold": ref_cont,
        "controlled_models": model_results,
        "qualifying_count": len(qualifying_candidates),
        "disqualified_count": len(disqualified_candidates),
        "selected_candidate": selected_candidate["model_tag"] if selected_candidate else None,
        "selection_details": selected_candidate,
        "selection_reason": selection_reason,
        "exploratory_models": exploratory_results,
    }


def analyze_stage_b(
    raw_dir: Path,
    selected_candidate_tag: str,
    ref_tag: str = "qwen2.5-coder:7b",
) -> Dict[str, Any]:
    """Analyze Stage B held-out evaluation and test H1 & H2."""
    print("\n=======================================================")
    print("STAGE B: HELD-OUT EVALUATION & INFERENTIAL TESTING")
    print("=======================================================")

    ref_file = raw_dir / f"stage_b_{ref_tag.replace(':', '_').replace('.', '_')}.jsonl"
    cand_file = raw_dir / f"stage_b_{selected_candidate_tag.replace(':', '_').replace('.', '_')}.jsonl"

    if not ref_file.exists() or not cand_file.exists():
        print(f"Stage B output files not ready: ref={ref_file.exists()}, cand={cand_file.exists()}")
        return {}

    ref_records = load_jsonl(ref_file)
    cand_records = load_jsonl(cand_file)

    ref_map = {(r["sample_id"], r["condition"]): r for r in ref_records}
    cand_map = {(r["sample_id"], r["condition"]): r for r in cand_records}

    sample_ids = sorted(list({r["sample_id"] for r in ref_records}))
    print(f"Total evaluated held-out samples: {len(sample_ids)}")

    cand_precis_em = []
    cand_naive_em = []
    ref_precis_em = []
    ref_naive_em = []

    cand_precis_cont = []
    cand_naive_cont = []
    ref_precis_cont = []
    ref_naive_cont = []

    for sid in sample_ids:
        cp = cand_map.get((sid, "precis_full"), {})
        cn = cand_map.get((sid, "naive_rag"), {})
        rp = ref_map.get((sid, "precis_full"), {})
        rn = ref_map.get((sid, "naive_rag"), {})

        cand_precis_em.append(1 if cp.get("exact_match") else 0)
        cand_naive_em.append(1 if cn.get("exact_match") else 0)
        ref_precis_em.append(1 if rp.get("exact_match") else 0)
        ref_naive_em.append(1 if rn.get("exact_match") else 0)

        cand_precis_cont.append(1 if cp.get("containment_correct") else 0)
        cand_naive_cont.append(1 if cn.get("containment_correct") else 0)
        ref_precis_cont.append(1 if rp.get("containment_correct") else 0)
        ref_naive_cont.append(1 if rn.get("containment_correct") else 0)

    # 1. Primary Hypothesis H1: McNemar test on Précis EM (Candidate vs Reference)
    h1_mcnemar = mcnemar_test(pairs_a=cand_precis_em, pairs_b=ref_precis_em)
    h1_supported = bool(h1_mcnemar["p_value_one_sided_greater"] < 0.05 and (sum(cand_precis_em) > sum(ref_precis_em)))

    # 2. Primary Hypothesis H2: Bootstrap CI on Delta_gap
    h2_bootstrap = bootstrap_gap_difference(
        cand_precis_em=cand_precis_em,
        cand_naive_em=cand_naive_em,
        ref_precis_em=ref_precis_em,
        ref_naive_em=ref_naive_em,
        n_resamples=10000,
        seed=42,
    )

    print(f"\n--- H1 Outcome (Précis EM Superiority) ---")
    print(f"Reference ({ref_tag}) EM: {sum(ref_precis_em)}/{len(sample_ids)} ({sum(ref_precis_em)/len(sample_ids):.4f})")
    print(f"Candidate ({selected_candidate_tag}) EM: {sum(cand_precis_em)}/{len(sample_ids)} ({sum(cand_precis_em)/len(sample_ids):.4f})")
    print(f"Discordant pairs: {h1_mcnemar['discordant_pairs']} (Cand-only: {h1_mcnemar['table']['n10_cand_only']}, Ref-only: {h1_mcnemar['table']['n01_ref_only']})")
    print(f"McNemar p-value (one-sided greater): {h1_mcnemar['p_value_one_sided_greater']:.4f}")
    print(f"H1 Supported: {h1_supported}")

    print(f"\n--- H2 Outcome (Gap Reduction) ---")
    print(f"Delta_gap point estimate: {h2_bootstrap['point_estimate']:+.4f}")
    print(f"95% Bootstrap CI: [{h2_bootstrap['ci_lower']:+.4f}, {h2_bootstrap['ci_upper']:+.4f}]")
    print(f"Classification: {h2_bootstrap['classification']}")

    ref_precis_recs = [r for r in ref_records if r.get("condition") == "precis_full"]
    ref_naive_recs = [r for r in ref_records if r.get("condition") == "naive_rag"]
    cand_precis_recs = [r for r in cand_records if r.get("condition") == "precis_full"]
    cand_naive_recs = [r for r in cand_records if r.get("condition") == "naive_rag"]

    return {
        "n_samples": len(sample_ids),
        "reference_model": {
            "model_tag": ref_tag,
            "precis_full": compute_metrics_summary(ref_precis_recs),
            "naive_rag": compute_metrics_summary(ref_naive_recs),
        },
        "selected_candidate": {
            "model_tag": selected_candidate_tag,
            "precis_full": compute_metrics_summary(cand_precis_recs),
            "naive_rag": compute_metrics_summary(cand_naive_recs),
        },
        "h1_hypothesis": {
            "description": f"H1: {selected_candidate_tag} achieves higher Précis EM than {ref_tag}.",
            "cand_precis_em_count": sum(cand_precis_em),
            "ref_precis_em_count": sum(ref_precis_em),
            "mcnemar": h1_mcnemar,
            "supported": h1_supported,
        },
        "h2_hypothesis": {
            "description": "H2: Selected candidate reduces the EM gap between Précis and Naive RAG relative to reference model.",
            "bootstrap_results": h2_bootstrap,
            "supported": bool(h2_bootstrap["classification"] == "SUPPORTED"),
            "inconclusive": bool(h2_bootstrap["classification"] == "INCONCLUSIVE"),
            "opposite_direction": bool(h2_bootstrap["classification"] == "OPPOSITE_DIRECTION"),
        },
    }


def analyze_stage_c(raw_dir: Path, selected_candidate_tag: str) -> Dict[str, Any]:
    """Analyze Stage C prompt ablation (Standard vs Concise)."""
    print("\n=======================================================")
    print("STAGE C: PROMPT FORMATTING ABLATION ANALYSIS")
    print("=======================================================")

    std_file = raw_dir / f"stage_b_{selected_candidate_tag.replace(':', '_').replace('.', '_')}.jsonl"
    concise_file = raw_dir / f"stage_c_{selected_candidate_tag.replace(':', '_').replace('.', '_')}_concise.jsonl"

    if not std_file.exists() or not concise_file.exists():
        return {}

    std_records = load_jsonl(std_file)
    concise_records = load_jsonl(concise_file)

    std_precis = [r for r in std_records if r.get("condition") == "precis_full"]
    concise_precis = [r for r in concise_records if r.get("condition") == "precis_full"]

    std_map = {r["sample_id"]: r for r in std_precis}
    concise_map = {r["sample_id"]: r for r in concise_precis}

    sample_ids = sorted(list(std_map.keys() & concise_map.keys()))

    std_em = [1 if std_map[sid].get("exact_match") else 0 for sid in sample_ids]
    concise_em = [1 if concise_map[sid].get("exact_match") else 0 for sid in sample_ids]

    mcnemar = mcnemar_test(pairs_a=concise_em, pairs_b=std_em)

    std_tokens = [std_map[sid]["generated_tokens"] for sid in sample_ids if "generated_tokens" in std_map[sid]]
    concise_tokens = [concise_map[sid]["generated_tokens"] for sid in sample_ids if "generated_tokens" in concise_map[sid]]

    brevity_ratio = (np.mean(concise_tokens) / np.mean(std_tokens)) if std_tokens and np.mean(std_tokens) > 0 else 1.0

    return {
        "n_samples": len(sample_ids),
        "model_tag": selected_candidate_tag,
        "standard_prompt": compute_metrics_summary(std_precis),
        "concise_prompt": compute_metrics_summary(concise_precis),
        "em_mcnemar": mcnemar,
        "mean_tokens_standard": float(np.mean(std_tokens)) if std_tokens else 0.0,
        "mean_tokens_concise": float(np.mean(concise_tokens)) if concise_tokens else 0.0,
        "brevity_ratio": float(brevity_ratio),
    }


def make_serializable(obj):
    if isinstance(obj, (np.bool_, np.integer)):
        return bool(obj) if isinstance(obj, np.bool_) else int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, dict):
        return {k: make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [make_serializable(v) for v in obj]
    return obj


def main():
    parser = argparse.ArgumentParser(description="Analyze Précis model comparison results.")
    parser.add_argument("--raw-dir", type=str, default="experiments/model_comparison/raw_outputs")
    parser.add_argument("--output-json", type=str, default="experiments/model_comparison/results.json")
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    out_json = Path(args.output_json)

    # 1. Analyze Stage A
    stage_a_res = analyze_stage_a(raw_dir)

    # 2. Analyze Stage B if candidate is selected and outputs exist
    selected_candidate = stage_a_res.get("selected_candidate")
    stage_b_res = {}
    if selected_candidate:
        stage_b_res = analyze_stage_b(raw_dir, selected_candidate_tag=selected_candidate)

    # 3. Analyze Stage C if outputs exist
    stage_c_res = {}
    if selected_candidate:
        stage_c_res = analyze_stage_c(raw_dir, selected_candidate_tag=selected_candidate)

    # Consolidate complete results
    final_output = {
        "stage_a": stage_a_res,
        "stage_b": stage_b_res,
        "stage_c": stage_c_res,
    }

    out_json.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(make_serializable(final_output), f, indent=2)

    print(f"\n[DONE] Full results exported to {out_json}")


if __name__ == "__main__":
    main()
