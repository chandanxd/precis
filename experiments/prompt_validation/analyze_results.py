#!/usr/bin/env python3
"""
Statistical analysis and error diagnostic engine for
Précis Confirmatory Answer-Formatting Experiment.

Implements:
1. Result ledger validation (verifies 800 evaluations, zero duplicates, non-empty outputs).
2. Primary hypothesis H1: Paired one-sided McNemar exact test on Précis EM (qwen3.5:4b concise vs standard)
   with containment degradation guardrails.
3. Secondary prompt-effect family H2 (H2a, H2b, H2c) with Holm-Bonferroni correction.
4. Model-separated retrieval x prompt interaction H3 via 10,000 paired bootstrap resamples (seed=42).
5. Cross-model testing family H4 with Holm-Bonferroni correction.
6. Error taxonomy and blinded 30-question review sheet generation (seed=42).
7. Export to experiments/prompt_validation/results.json.
"""

import argparse
import json
import math
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import stats

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXP_DIR = PROJECT_ROOT / "experiments" / "prompt_validation"


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


def validate_ledger(records: List[Dict[str, Any]], expected_samples: int = 100) -> Dict[str, Any]:
    """Validate completeness, uniqueness, and validity of eval_records.jsonl."""
    total_records = len(records)
    expected_total = expected_samples * 2 * 2 * 2  # 100 samples * 2 models * 2 conds * 2 prompts = 800

    keys = set()
    duplicates = 0
    empty_outputs = 0
    missing_fields = 0

    for r in records:
        key = (r.get("sample_id"), r.get("model"), r.get("condition"), r.get("prompt_mode"))
        if key in keys:
            duplicates += 1
        keys.add(key)

        pred = r.get("predicted_answer", "")
        if not pred or not pred.strip():
            empty_outputs += 1

        required = ["exact_match", "containment_correct", "rouge_l", "minilm_cosine", "bert_score"]
        if not all(k in r for k in required):
            missing_fields += 1

    valid = (total_records == expected_total) and (duplicates == 0) and (empty_outputs == 0) and (missing_fields == 0)

    return {
        "total_records": total_records,
        "expected_records": expected_total,
        "unique_keys": len(keys),
        "duplicates": duplicates,
        "empty_outputs": empty_outputs,
        "missing_fields": missing_fields,
        "valid": valid,
    }


def compute_metrics_summary(records: List[Dict[str, Any]]) -> Dict[str, Any]:
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


def mcnemar_paired_test(
    pairs_concise: List[int],
    pairs_standard: List[int],
    alternative: str = "greater",
) -> Dict[str, Any]:
    """
    McNemar paired exact test on binary outcomes.
    b: concise=1, standard=0
    c: concise=0, standard=1
    """
    assert len(pairs_concise) == len(pairs_standard)
    n = len(pairs_concise)

    n00 = sum(1 for c, s in zip(pairs_concise, pairs_standard) if c == 0 and s == 0)
    n01 = sum(1 for c, s in zip(pairs_concise, pairs_standard) if c == 0 and s == 1)  # c
    n10 = sum(1 for c, s in zip(pairs_concise, pairs_standard) if c == 1 and s == 0)  # b
    n11 = sum(1 for c, s in zip(pairs_concise, pairs_standard) if c == 1 and s == 1)

    b = n10
    c = n01
    discordant = b + c

    if discordant == 0:
        p_val = 1.0
        p_two_sided = 1.0
    else:
        binom = stats.binomtest(b, n=discordant, p=0.5, alternative=alternative)
        p_val = binom.pvalue
        binom_2s = stats.binomtest(b, n=discordant, p=0.5, alternative="two-sided")
        p_two_sided = binom_2s.pvalue

    odds_ratio = b / c if c > 0 else (float("inf") if b > 0 else 1.0)

    return {
        "n": n,
        "table": {
            "n00": n00,
            "n01_standard_only": n01,
            "n10_concise_only": n10,
            "n11_both": n11,
        },
        "discordant_pairs": discordant,
        "odds_ratio": odds_ratio,
        "p_value": p_val,
        "p_value_two_sided": p_two_sided,
        "alternative": alternative,
    }


def holm_bonferroni(p_values: List[float], alpha: float = 0.05) -> List[Dict[str, Any]]:
    """Apply Holm-Bonferroni step-down correction to a list of p-values."""
    m = len(p_values)
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])

    results = [None] * m
    reject = True

    for rank, (orig_idx, p) in enumerate(indexed):
        divisor = m - rank
        thresh = alpha / divisor
        adjusted_p = min(1.0, p * divisor)

        # Enforce monotonicity of adjusted p-values
        if rank > 0:
            prev_adj = results[indexed[rank - 1][0]]["adjusted_p"]
            adjusted_p = max(adjusted_p, prev_adj)

        if p > thresh:
            reject = False

        results[orig_idx] = {
            "raw_p": p,
            "rank": rank + 1,
            "threshold": thresh,
            "adjusted_p": adjusted_p,
            "significant": reject,
        }

    return results


def bootstrap_interaction(
    concise_precis: List[int],
    standard_precis: List[int],
    concise_naive: List[int],
    standard_naive: List[int],
    n_resamples: int = 10000,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Model-separated retrieval x prompt interaction via paired bootstrap.
    For question i:
      diff_precis(i) = concise_precis(i) - standard_precis(i)
      diff_naive(i) = concise_naive(i) - standard_naive(i)
      interaction(i) = diff_precis(i) - diff_naive(i)
    Delta_prompt_diff = mean(interaction(i))
    """
    n = len(concise_precis)
    deltas = np.array([
        (cp - sp) - (cn - sn)
        for cp, sp, cn, sn in zip(concise_precis, standard_precis, concise_naive, standard_naive)
    ], dtype=float)

    point_estimate = float(np.mean(deltas))

    precis_prompt_gain = float(np.mean(concise_precis)) - float(np.mean(standard_precis))
    naive_prompt_gain = float(np.mean(concise_naive)) - float(np.mean(standard_naive))

    rng = np.random.default_rng(seed)
    indices = rng.integers(0, n, size=(n_resamples, n))
    bootstrap_samples = deltas[indices]
    bootstrap_means = np.mean(bootstrap_samples, axis=1)

    ci_lower = float(np.percentile(bootstrap_means, 2.5))
    ci_upper = float(np.percentile(bootstrap_means, 97.5))
    std_err = float(np.std(bootstrap_means))

    if ci_lower > 0.0:
        classification = "POSITIVE_INTERACTION"  # Concise benefits Précis more than Naive
    elif ci_upper < 0.0:
        classification = "NEGATIVE_INTERACTION"  # Concise benefits Naive more than Précis
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
        "precis_prompt_gain": precis_prompt_gain,
        "naive_prompt_gain": naive_prompt_gain,
    }


def generate_blinded_review_sheet(
    records: List[Dict[str, Any]],
    cached_contexts: List[Dict[str, Any]],
    output_jsonl: Path,
    output_md: Path,
    sample_size: int = 30,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Prespecify a fixed-seed random sample of 30 cohort questions.
    Generates blinded review sheet with condition labels hidden.
    """
    # Filter records to qwen3.5:4b under precis_full
    p_records = [
        r for r in records
        if r.get("model") == "qwen3.5:4b" and r.get("condition") == "precis_full"
    ]

    sample_ids = sorted(list({r["sample_id"] for r in p_records}))
    rng = random.Random(seed)
    selected_sids = rng.sample(sample_ids, sample_size)

    # Context map
    ctx_map = {c["sample_id"]: c for c in cached_contexts}

    # Group by sample_id
    rec_by_sid_prompt = {}
    for r in p_records:
        rec_by_sid_prompt[(r["sample_id"], r["prompt_mode"])] = r

    review_records = []
    condition_key_map = {}

    for idx, sid in enumerate(selected_sids):
        std_rec = rec_by_sid_prompt.get((sid, "standard"), {})
        con_rec = rec_by_sid_prompt.get((sid, "concise"), {})
        ctx_item = ctx_map.get(sid, {})
        precis_ctx = ctx_item.get("precis_v3", {}).get("context_text", "")

        # Randomize assignment of Output A and Output B to blind raters
        # Seed per sample ensures reproducibility
        flip = rng.random() < 0.5
        if flip:
            out_a, out_b = std_rec.get("predicted_answer", ""), con_rec.get("predicted_answer", "")
            ans_a_mode, ans_b_mode = "standard", "concise"
            em_a, em_b = std_rec.get("exact_match", False), con_rec.get("exact_match", False)
        else:
            out_a, out_b = con_rec.get("predicted_answer", ""), std_rec.get("predicted_answer", "")
            ans_a_mode, ans_b_mode = "concise", "standard"
            em_a, em_b = con_rec.get("exact_match", False), std_rec.get("exact_match", False)

        # Transition status
        std_em = std_rec.get("exact_match", False)
        con_em = con_rec.get("exact_match", False)
        if not std_em and con_em:
            transition = "Prompt-Correction"
        elif std_em and not con_em:
            transition = "Prompt-Degradation"
        elif not std_em and not con_em:
            transition = "Persistent-Error"
        else:
            transition = "Persistent-Success"

        item = {
            "review_id": f"REV_{idx + 1:02d}",
            "sample_id": sid,
            "question": std_rec.get("question", ""),
            "gold_answer": std_rec.get("gold_answer", ""),
            "precis_evidence_context": precis_ctx,
            "output_a": out_a,
            "output_b": out_b,
            "transition_status": transition,
            "_blinded_mapping": {
                "output_a_prompt": ans_a_mode,
                "output_b_prompt": ans_b_mode,
                "output_a_em": em_a,
                "output_b_em": em_b,
            }
        }
        review_records.append(item)

    # Write review JSONL
    with open(output_jsonl, "w", encoding="utf-8") as f:
        for r in review_records:
            f.write(json.dumps(r) + "\n")

    # Write human Markdown sheet
    with open(output_md, "w", encoding="utf-8") as f:
        f.write("# Précis Confirmatory Experiment: Blinded Error Analysis Review Sheet\n\n")
        f.write("**Review Sample:** 30 questions randomly sampled (Seed: 42) from confirmatory cohort.\n")
        f.write("**Task:** Evaluate `Output A` and `Output B` without knowledge of prompt condition.\n")
        f.write("\n### Coding Taxonomy Guide:\n")
        f.write("- **Primary Categories:**\n")
        f.write("  1. `Conversational Mismatch`: Full gold entity present in text, but conversational preamble caused exact match failure.\n")
        f.write("  2. `Incomplete Entity`: Partial entity returned (omitted date, unit, or qualifier).\n")
        f.write("  3. `Hallucination`: Asserted facts absent from or contradicting evidence context.\n")
        f.write("  4. `Evidence Insufficiency`: Evidence context lacked the necessary facts to answer question.\n")
        f.write("  5. `Other`: Unclassified or refusal.\n\n")
        f.write("---\n\n")

        for r in review_records:
            f.write(f"## {r['review_id']} (Sample `{r['sample_id'][:8]}`)\n")
            f.write(f"**Question:** {r['question']}\n\n")
            f.write(f"**Gold Answer:** `{r['gold_answer']}`\n\n")
            f.write(f"<details><summary>Click to view Evidence Context ({len(r['precis_evidence_context'].split())} words)</summary>\n\n```\n")
            f.write(r['precis_evidence_context'])
            f.write("\n```\n</details>\n\n")
            f.write(f"- **Output A:** `{r['output_a']}`\n")
            f.write(f"- **Output B:** `{r['output_b']}`\n\n")
            f.write(f"**Transition Status:** `{r['transition_status']}`\n\n")
            f.write("**Human Auditor Coding:**\n")
            f.write("- Output A Error Mode: `[                      ]`\n")
            f.write("- Output B Error Mode: `[                      ]`\n")
            f.write("- Secondary Tags: `[                      ]`\n\n")
            f.write("---\n\n")

    return {
        "sample_size": sample_size,
        "seed": seed,
        "output_jsonl": str(output_jsonl),
        "output_md": str(output_md),
    }


def main():
    parser = argparse.ArgumentParser(description="Analyze prompt validation results.")
    parser.add_argument("--raw-file", type=str, default="experiments/prompt_validation/raw_outputs/eval_records.jsonl")
    parser.add_argument("--output-json", type=str, default="experiments/prompt_validation/results.json")
    args = parser.parse_args()

    raw_file = PROJECT_ROOT / args.raw_file
    out_json = PROJECT_ROOT / args.output_json
    contexts_path = EXP_DIR / "cached_contexts.jsonl"

    if not raw_file.exists():
        print(f"Error: Raw file {raw_file} not found.")
        sys.exit(1)

    records = load_jsonl(raw_file)
    print(f"\n=======================================================")
    print("STEP 1: VALIDATING RESULT LEDGER")
    print("=======================================================")
    ledger_val = validate_ledger(records, expected_samples=100)
    print(json.dumps(ledger_val, indent=2))
    if not ledger_val["valid"]:
        print(f"Warning: Result ledger validation failed! Total records: {ledger_val['total_records']}/800")

    # Index records: map (sample_id, model, condition, prompt_mode) -> record
    rec_map = {}
    for r in records:
        key = (r["sample_id"], r["model"], r["condition"], r["prompt_mode"])
        rec_map[key] = r

    sample_ids = sorted(list({r["sample_id"] for r in records}))
    n_samples = len(sample_ids)

    # Condition summaries
    conditions_summary = {}
    models = ["qwen2.5-coder:7b", "qwen3.5:4b"]
    retrievals = ["naive_rag", "precis_full"]
    prompts = ["standard", "concise"]

    for m in models:
        for r_cond in retrievals:
            for p_mode in prompts:
                subset = [
                    rec_map[(sid, m, r_cond, p_mode)]
                    for sid in sample_ids
                    if (sid, m, r_cond, p_mode) in rec_map
                ]
                conditions_summary[f"{m}__{r_cond}__{p_mode}"] = compute_metrics_summary(subset)

    # ---------------------------------------------------------
    # PRIMARY HYPOTHESIS H1: qwen3.5:4b under precis_full (concise vs standard)
    # ---------------------------------------------------------
    print(f"\n=======================================================")
    print("STEP 2: TESTING PRIMARY HYPOTHESIS H1")
    print("=======================================================")
    q35_p_concise_em = [rec_map[(sid, "qwen3.5:4b", "precis_full", "concise")]["exact_match"] for sid in sample_ids]
    q35_p_standard_em = [rec_map[(sid, "qwen3.5:4b", "precis_full", "standard")]["exact_match"] for sid in sample_ids]
    q35_p_concise_cont = [rec_map[(sid, "qwen3.5:4b", "precis_full", "concise")]["containment_correct"] for sid in sample_ids]
    q35_p_standard_cont = [rec_map[(sid, "qwen3.5:4b", "precis_full", "standard")]["containment_correct"] for sid in sample_ids]

    h1_mcnemar = mcnemar_paired_test(
        pairs_concise=[1 if x else 0 for x in q35_p_concise_em],
        pairs_standard=[1 if x else 0 for x in q35_p_standard_em],
        alternative="greater",
    )

    cont_std_rate = float(np.mean(q35_p_standard_cont))
    cont_con_rate = float(np.mean(q35_p_concise_cont))
    delta_cont = cont_con_rate - cont_std_rate

    # Guardrails: drop <= 0.25 (delta_cont >= -0.25) AND cont_con >= 0.40
    guardrail_passed = (delta_cont >= -0.2500) and (cont_con_rate >= 0.4000)
    h1_em_improved = sum(q35_p_concise_em) > sum(q35_p_standard_em)
    h1_supported = bool(h1_mcnemar["p_value"] < 0.05 and h1_em_improved and guardrail_passed)

    print(f"Précis Standard EM: {sum(q35_p_standard_em)}/{n_samples} ({np.mean(q35_p_standard_em):.4f})")
    print(f"Précis Concise EM:  {sum(q35_p_concise_em)}/{n_samples} ({np.mean(q35_p_concise_em):.4f})")
    print(f"Discordant pairs: {h1_mcnemar['discordant_pairs']} (Concise-only: {h1_mcnemar['table']['n10_concise_only']}, Standard-only: {h1_mcnemar['table']['n01_standard_only']})")
    print(f"McNemar one-sided p-value: {h1_mcnemar['p_value']:.4e}")
    print(f"Précis Standard Containment: {cont_std_rate:.4f}")
    print(f"Précis Concise Containment:  {cont_con_rate:.4f} (Delta: {delta_cont:+.4f})")
    print(f"Containment Guardrail Passed: {guardrail_passed}")
    print(f"--> H1 Supported: {h1_supported}")

    # ---------------------------------------------------------
    # SECONDARY PROMPT FAMILY H2 (H2a, H2b, H2c) WITH HOLM-BONFERRONI
    # ---------------------------------------------------------
    print(f"\n=======================================================")
    print("STEP 3: TESTING SECONDARY PROMPT FAMILY H2")
    print("=======================================================")
    # H2a: qwen3.5:4b Naive RAG (concise vs standard)
    q35_n_c = [1 if rec_map[(sid, "qwen3.5:4b", "naive_rag", "concise")]["exact_match"] else 0 for sid in sample_ids]
    q35_n_s = [1 if rec_map[(sid, "qwen3.5:4b", "naive_rag", "standard")]["exact_match"] else 0 for sid in sample_ids]
    h2a_test = mcnemar_paired_test(q35_n_c, q35_n_s, alternative="greater")

    # H2b: qwen2.5-coder:7b Precis Full (concise vs standard)
    q25_p_c = [1 if rec_map[(sid, "qwen2.5-coder:7b", "precis_full", "concise")]["exact_match"] else 0 for sid in sample_ids]
    q25_p_s = [1 if rec_map[(sid, "qwen2.5-coder:7b", "precis_full", "standard")]["exact_match"] else 0 for sid in sample_ids]
    h2b_test = mcnemar_paired_test(q25_p_c, q25_p_s, alternative="greater")

    # H2c: qwen2.5-coder:7b Naive RAG (concise vs standard)
    q25_n_c = [1 if rec_map[(sid, "qwen2.5-coder:7b", "naive_rag", "concise")]["exact_match"] else 0 for sid in sample_ids]
    q25_n_s = [1 if rec_map[(sid, "qwen2.5-coder:7b", "naive_rag", "standard")]["exact_match"] else 0 for sid in sample_ids]
    h2c_test = mcnemar_paired_test(q25_n_c, q25_n_s, alternative="greater")

    h2_raw_p = [h2a_test["p_value"], h2b_test["p_value"], h2c_test["p_value"]]
    h2_holm = holm_bonferroni(h2_raw_p, alpha=0.05)

    h2_results = {
        "H2a_qwen35_naive": {**h2a_test, "holm": h2_holm[0]},
        "H2b_qwen25_precis": {**h2b_test, "holm": h2_holm[1]},
        "H2c_qwen25_naive": {**h2c_test, "holm": h2_holm[2]},
    }
    for test_id, res in h2_results.items():
        print(f"  {test_id}: raw p={res['p_value']:.4e}, adj p={res['holm']['adjusted_p']:.4e}, sig={res['holm']['significant']}")

    # ---------------------------------------------------------
    # INTERACTION ANALYSIS H3 (RETRIEVAL x PROMPT)
    # ---------------------------------------------------------
    print(f"\n=======================================================")
    print("STEP 4: TESTING RETRIEVAL x PROMPT INTERACTION H3")
    print("=======================================================")
    # Primary target: qwen3.5:4b
    q35_interaction = bootstrap_interaction(
        concise_precis=[1 if x else 0 for x in q35_p_concise_em],
        standard_precis=[1 if x else 0 for x in q35_p_standard_em],
        concise_naive=q35_n_c,
        standard_naive=q35_n_s,
        n_resamples=10000,
        seed=42,
    )
    # Secondary target: qwen2.5-coder:7b
    q25_interaction = bootstrap_interaction(
        concise_precis=q25_p_c,
        standard_precis=q25_p_s,
        concise_naive=q25_n_c,
        standard_naive=q25_n_s,
        n_resamples=10000,
        seed=42,
    )
    print(f"qwen3.5:4b Interaction: point={q35_interaction['point_estimate']:+.4f}, 95% CI=[{q35_interaction['ci_lower']:+.4f}, {q35_interaction['ci_upper']:+.4f}], Class={q35_interaction['classification']}")
    print(f"qwen2.5-coder:7b Interaction: point={q25_interaction['point_estimate']:+.4f}, 95% CI=[{q25_interaction['ci_lower']:+.4f}, {q25_interaction['ci_upper']:+.4f}], Class={q25_interaction['classification']}")

    # ---------------------------------------------------------
    # CROSS-MODEL TESTING FAMILY H4 (qwen3.5:4b vs qwen2.5-coder:7b)
    # ---------------------------------------------------------
    print(f"\n=======================================================")
    print("STEP 5: TESTING CROSS-MODEL FAMILY H4")
    print("=======================================================")
    # Four conditions:
    # 1. Naive RAG + Standard
    h4a_test = mcnemar_paired_test(q35_n_s, q25_n_s, alternative="two-sided")
    # 2. Naive RAG + Concise
    h4b_test = mcnemar_paired_test(q35_n_c, q25_n_c, alternative="two-sided")
    # 3. Precis Full + Standard
    h4c_test = mcnemar_paired_test([1 if x else 0 for x in q35_p_standard_em], q25_p_s, alternative="two-sided")
    # 4. Precis Full + Concise
    h4d_test = mcnemar_paired_test([1 if x else 0 for x in q35_p_concise_em], q25_p_c, alternative="two-sided")

    h4_raw_p = [h4a_test["p_value_two_sided"], h4b_test["p_value_two_sided"], h4c_test["p_value_two_sided"], h4d_test["p_value_two_sided"]]
    h4_holm = holm_bonferroni(h4_raw_p, alpha=0.05)

    h4_results = {
        "H4a_naive_standard": {**h4a_test, "holm": h4_holm[0]},
        "H4b_naive_concise": {**h4b_test, "holm": h4_holm[1]},
        "H4c_precis_standard": {**h4c_test, "holm": h4_holm[2]},
        "H4d_precis_concise": {**h4d_test, "holm": h4_holm[3]},
    }
    for test_id, res in h4_results.items():
        print(f"  {test_id}: raw p={res['p_value_two_sided']:.4e}, adj p={res['holm']['adjusted_p']:.4e}, sig={res['holm']['significant']}")

    # ---------------------------------------------------------
    # STEP 6: BLINDED REVIEW SHEET GENERATION (SEED 42, N=30)
    # ---------------------------------------------------------
    print(f"\n=======================================================")
    print("STEP 6: GENERATING BLINDED HUMAN REVIEW SHEET (N=30)")
    print("=======================================================")
    cached_contexts = []
    if contexts_path.exists():
        with open(contexts_path, "r", encoding="utf-8") as f:
            cached_contexts = [json.loads(line) for line in f if line.strip()]

    review_sheet_info = generate_blinded_review_sheet(
        records=records,
        cached_contexts=cached_contexts,
        output_jsonl=EXP_DIR / "human_review_sheet.jsonl",
        output_md=EXP_DIR / "human_review_sheet.md",
        sample_size=30,
        seed=42,
    )
    print(f"Review sheet generated at: {review_sheet_info['output_md']}")

    # Consolidate complete results
    final_output = {
        "ledger_validation": ledger_val,
        "conditions_summary": conditions_summary,
        "h1_primary_hypothesis": {
            "description": "H1: Concise prompt increases Précis EM for qwen3.5:4b compared with standard prompt.",
            "mcnemar": h1_mcnemar,
            "containment": {
                "standard": cont_std_rate,
                "concise": cont_con_rate,
                "delta": delta_cont,
                "guardrail_passed": guardrail_passed,
            },
            "supported": h1_supported,
        },
        "h2_secondary_prompt_family": {
            "correction_method": "Holm-Bonferroni",
            "family_alpha": 0.05,
            "tests": h2_results,
        },
        "h3_interaction_analysis": {
            "primary_target_qwen35": q35_interaction,
            "secondary_target_qwen25": q25_interaction,
        },
        "h4_cross_model_family": {
            "correction_method": "Holm-Bonferroni",
            "family_alpha": 0.05,
            "tests": h4_results,
        },
        "human_review_sample": review_sheet_info,
    }

    out_json.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(make_serializable(final_output), f, indent=2)

    print(f"\n[DONE] Full statistical analysis exported to {out_json}")


if __name__ == "__main__":
    main()
