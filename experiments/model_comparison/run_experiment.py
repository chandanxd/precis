#!/usr/bin/env python3
"""
Experiment execution harness for Précis model selection.
Executes Stage A, Stage B, and Stage C runs sequentially with:
- Full resumability (skips completed samples)
- Immediate per-sample disk flushing
- Exact decoding configurations
- Offline metric computation (EM, Containment, ROUGE-L, BERTScore, MiniLM)
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import requests

os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend" / "src"))

from precis.evaluation.metrics import (
    compute_exact_match,
    compute_minilm_cosine,
    compute_rouge_l,
    normalize_answer,
)

_GLOBAL_BERT_SCORER = None


def get_bert_scorer(device: str = "cpu"):
    global _GLOBAL_BERT_SCORER
    if _GLOBAL_BERT_SCORER is None:
        from bert_score import BERTScorer
        _GLOBAL_BERT_SCORER = BERTScorer(
            model_type="microsoft/deberta-large-mnli",
            device=device,
        )
    return _GLOBAL_BERT_SCORER


STANDARD_PROMPT_TEMPLATE = """You are a precise document question-answering assistant.

Answer the question using ONLY the facts provided below.
Do not use outside knowledge, assumptions, or unstated information.

GROUNDING RULES:
- Treat each fact as information extracted from the source document.
- A fact containing "NOT" represents a negated claim. Preserve that negation in your answer.
- [attributed to X] means the claim is attributed to X. Do not present it as independently established.
- [conditional] means the claim depends on a condition. Do not present it as unconditional.
- [hypothetical] means the claim is hypothetical. Do not present it as an established event.
- Do not infer missing relationships, causes, dates, identities, or conclusions.
- If the provided facts do not contain enough information to answer the question, say so explicitly.
- Be concise and answer the question directly.
- Do not repeat facts unnecessarily.

FACTS FROM DOCUMENT:
{context}

QUESTION:
{query}

ANSWER:"""

CONCISE_PROMPT_TEMPLATE = """You are a precise document question-answering assistant.

Answer the question using ONLY the facts provided below.
Provide ONLY the shortest complete answer supported by the supplied evidence. Do not include full sentences, explanations, conversational filler, or introductory phrases.

GROUNDING RULES:
- Treat each fact as information extracted from the source document.
- A fact containing "NOT" represents a negated claim. Preserve that negation in your answer.
- [attributed to X] means the claim is attributed to X. Do not present it as independently established.
- [conditional] means the claim depends on a condition. Do not present it as unconditional.
- [hypothetical] means the claim is hypothetical. Do not present it as an established event.
- Do not infer missing relationships, causes, dates, identities, or conclusions.
- If the provided facts do not contain enough information to answer the question, output "Insufficient information".
- Give only the entity, name, date, number, or exact phrase that directly answers the question.

FACTS FROM DOCUMENT:
{context}

QUESTION:
{query}

ANSWER:"""


def contains_answer(text: str, answer: str) -> bool:
    """Exact word-boundary normalized string containment match."""
    import re
    norm_ans = normalize_answer(answer)
    if not norm_ans:
        return False
    norm_text = normalize_answer(text)
    if not norm_text:
        return False
    pattern = r"(?:\b|^)" + re.escape(norm_ans) + r"(?:\b|$)"
    return re.search(pattern, norm_text) is not None


def call_ollama_chat(
    base_url: str,
    model: str,
    prompt: str,
    temperature: float = 0.0,
    top_p: float = 0.9,
    seed: int = 42,
    max_tokens: int = 512,
    think: bool = False,
    timeout: int = 120,
) -> Tuple[str, int, int, int]:
    """Call Ollama /api/chat. Returns (answer, latency_ms, eval_count, prompt_eval_count)."""
    endpoint = f"{base_url.rstrip('/')}/api/chat"

    payload: Dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {
            "temperature": temperature,
            "top_p": top_p,
            "seed": seed,
            "num_predict": max_tokens,
        },
    }

    # Only include think: false if not in native thinking mode
    if not think:
        payload["think"] = False

    t0 = time.perf_counter()
    resp = requests.post(endpoint, json=payload, timeout=timeout)
    resp.raise_for_status()
    latency_ms = int((time.perf_counter() - t0) * 1000)

    data = resp.json()
    msg = data.get("message", {})
    answer = msg.get("content", "").strip()

    eval_count = data.get("eval_count", len(answer.split()))
    prompt_eval_count = data.get("prompt_eval_count", 0)

    return answer, latency_ms, eval_count, prompt_eval_count


def load_completed_keys(output_file: Path) -> Set[Tuple[str, str]]:
    """Load set of already completed (sample_id, condition) tuples."""
    completed = set()
    if output_file.exists():
        with open(output_file, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    d = json.loads(line_str)
                    completed.add((d["sample_id"], d["condition"]))
                except Exception:
                    pass
    return completed


def evaluate_model_on_cohort(
    cohort_name: str,
    model_tag: str,
    output_file: Path,
    cached_contexts: List[Dict[str, Any]],
    base_url: str = "http://localhost:11434",
    prompt_mode: str = "standard",
    is_reasoning_mode: bool = False,
    use_bertscore: bool = True,
    bertscore_device: str = "cuda",
) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    completed = load_completed_keys(output_file)
    print(f"\n--- Running {model_tag} on {cohort_name} (Prompt: {prompt_mode}) ---")
    print(f"Output path: {output_file} (Already completed: {len(completed)} evaluations)")

    template = CONCISE_PROMPT_TEMPLATE if prompt_mode == "concise" else STANDARD_PROMPT_TEMPLATE

    # Filter contexts for this cohort (support stage_b_eval / stage_b_heldout alias)
    cohort_contexts = [
        c for c in cached_contexts
        if c["cohort"] == cohort_name or (cohort_name in ("stage_b_heldout", "stage_b_eval") and c["cohort"] in ("stage_b_heldout", "stage_b_eval"))
    ]
    print(f"Total samples in cohort: {len(cohort_contexts)}")

    conditions = ["naive_rag", "precis_full"]

    with open(output_file, "a", encoding="utf-8") as out_f:
        for idx, item in enumerate(cohort_contexts):
            sid = item["sample_id"]
            q = item["question"]
            gold = item["gold_answer"]

            for cond in conditions:
                if (sid, cond) in completed:
                    continue

                ctx_info = item.get(cond) or item.get("precis_v3" if cond == "precis_full" else cond)
                ctx_text = ctx_info["context_text"]
                ctx_words = ctx_info["context_words"]
                ctx_tokens = ctx_info["context_tokens_est"]
                ctx_sha256 = ctx_info["sha256"]

                prompt = template.format(context=ctx_text, query=q)

                try:
                    ans, latency_ms, eval_count, prompt_cnt = call_ollama_chat(
                        base_url=base_url,
                        model=model_tag,
                        prompt=prompt,
                        temperature=0.0,
                        top_p=0.9,
                        seed=42,
                        max_tokens=512,
                        think=is_reasoning_mode,
                    )
                except Exception as exc:
                    print(f"  [ERROR] Sample {sid} ({cond}) failed: {exc}")
                    continue

                em = compute_exact_match(ans, gold)
                cont = contains_answer(ans, gold)
                rouge_l = compute_rouge_l(ans, gold)
                minilm = compute_minilm_cosine(ans, gold)

                bert_score = None
                if use_bertscore:
                    try:
                        scorer = get_bert_scorer(device=bertscore_device)
                        _, _, f1 = scorer.score([ans.strip()], [gold.strip()])
                        bert_score = round(float(f1[0].item()), 4)
                    except Exception as b_exc:
                        print(f"  [WARN] BERTScore failed: {b_exc}")

                record = {
                    "sample_id": sid,
                    "cohort": cohort_name,
                    "condition": cond,
                    "question": q,
                    "gold_answer": gold,
                    "predicted_answer": ans,
                    "exact_match": em,
                    "containment_correct": cont,
                    "rouge_l": rouge_l,
                    "bert_score": bert_score,
                    "minilm_cosine": minilm,
                    "context_words": ctx_words,
                    "context_tokens_est": ctx_tokens,
                    "context_sha256": ctx_sha256,
                    "generated_tokens": eval_count,
                    "prompt_tokens": prompt_cnt,
                    "latency_ms": latency_ms,
                    "model": model_tag,
                    "prompt_mode": prompt_mode,
                    "temperature": 0.0,
                    "top_p": 0.9,
                    "seed": 42,
                    "max_tokens": 512,
                    "timestamp": time.time(),
                }

                out_f.write(json.dumps(record) + "\n")
                out_f.flush()
                completed.add((sid, cond))

            if (idx + 1) % 10 == 0 or idx == len(cohort_contexts) - 1:
                print(f"  [{idx + 1}/{len(cohort_contexts)}] Evaluated sample {sid}")


def main():
    parser = argparse.ArgumentParser(description="Précis model comparison runner.")
    parser.add_argument("--stage", choices=["a", "b", "c", "all"], default="a", help="Stage to execute.")
    parser.add_argument("--model", type=str, default=None, help="Specific model tag to run (or runs all models in stage).")
    parser.add_argument("--base-url", type=str, default="http://localhost:11434", help="Ollama API base URL.")
    parser.add_argument("--use-bertscore", action="store_true", default=True, help="Compute DeBERTa BERTScore.")
    parser.add_argument("--device", type=str, default="cpu", help="Device for metric computation (default cpu to avoid VRAM contention with Ollama).")
    args = parser.parse_args()

    contexts_path = Path("experiments/model_comparison/cached_contexts.jsonl")
    if not contexts_path.exists():
        print(f"Error: Cached contexts not found at {contexts_path}. Run prepare_data.py first.")
        sys.exit(1)

    with open(contexts_path, "r", encoding="utf-8") as f:
        cached_contexts = [json.loads(line) for line in f if line.strip()]

    print(f"Loaded {len(cached_contexts)} cached context records.")

    raw_dir = Path("experiments/model_comparison/raw_outputs")

    # Models for Stage A
    controlled_models = [
        "qwen2.5-coder:7b",
        "qwen3.5:4b",
        "qwen3.5:9b",
        "gemma4:e2b",
        "gemma4:e4b",
        "gemma4:12b",
    ]
    exploratory_models = [
        "deepseek-r1:8b",
    ]

    if args.stage in ["a", "all"]:
        print("\n=======================================================")
        print("STAGE A: DEVELOPMENT SCREENING (101 SAMPLES)")
        print("=======================================================")
        models_to_run = [args.model] if args.model else controlled_models

        for m in models_to_run:
            safe_name = m.replace(":", "_").replace(".", "_")
            out_file = raw_dir / f"stage_a_{safe_name}.jsonl"
            evaluate_model_on_cohort(
                cohort_name="stage_a_dev",
                model_tag=m,
                output_file=out_file,
                cached_contexts=cached_contexts,
                base_url=args.base_url,
                prompt_mode="standard",
                is_reasoning_mode=False,
                use_bertscore=args.use_bertscore,
                bertscore_device=args.device,
            )

        # Also run exploratory model if not running a specific other model
        if args.model is None or args.model == "deepseek-r1:8b":
            for m in exploratory_models:
                safe_name = m.replace(":", "_").replace(".", "_")
                out_file = raw_dir / f"stage_a_{safe_name}_exploratory.jsonl"
                evaluate_model_on_cohort(
                    cohort_name="stage_a_dev",
                    model_tag=m,
                    output_file=out_file,
                    cached_contexts=cached_contexts,
                    base_url=args.base_url,
                    prompt_mode="standard",
                    is_reasoning_mode=True,
                    use_bertscore=args.use_bertscore,
                    bertscore_device=args.device,
                )

    if args.stage in ["b", "all"]:
        print("\n=======================================================")
        print("STAGE B: HELD-OUT EVALUATION (100 SAMPLES)")
        print("=======================================================")
        if not args.model:
            print("Error: For Stage B, specify --model <model_tag> (e.g. qwen2.5-coder:7b or selected candidate).")
            if args.stage == "b":
                sys.exit(1)
        else:
            safe_name = args.model.replace(":", "_").replace(".", "_")
            out_file = raw_dir / f"stage_b_{safe_name}.jsonl"
            evaluate_model_on_cohort(
                cohort_name="stage_b_heldout",
                model_tag=args.model,
                output_file=out_file,
                cached_contexts=cached_contexts,
                base_url=args.base_url,
                prompt_mode="standard",
                is_reasoning_mode=False,
                use_bertscore=args.use_bertscore,
                bertscore_device=args.device,
            )

    if args.stage == "c":
        print("\n=======================================================")
        print("STAGE C: CONCISE ANSWER PROMPT EXPERIMENT (100 SAMPLES)")
        print("=======================================================")
        if not args.model:
            print("Error: For Stage C, specify --model <model_tag>.")
            sys.exit(1)
        safe_name = args.model.replace(":", "_").replace(".", "_")
        out_file = raw_dir / f"stage_c_{safe_name}_concise.jsonl"
        evaluate_model_on_cohort(
            cohort_name="stage_b_heldout",
            model_tag=args.model,
            output_file=out_file,
            cached_contexts=cached_contexts,
            base_url=args.base_url,
            prompt_mode="concise",
            is_reasoning_mode=False,
            use_bertscore=args.use_bertscore,
            bertscore_device=args.device,
        )


if __name__ == "__main__":
    main()
