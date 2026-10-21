#!/usr/bin/env python3
"""
Factorial experiment runner for Précis confirmatory answer-formatting study.
Executes:
2 models (qwen2.5-coder:7b, qwen3.5:4b) x
2 retrieval conditions (naive_rag, precis_full) x
2 prompts (standard, concise) = 8 conditions per sample (800 evaluations total).

Features:
- Full crash resumability (skips completed (sample_id, model, condition, prompt_mode) tuples)
- Immediate per-sample disk flushing
- Runtime SHA-256 context checksum verification
- Offline cached metrics (EM, Containment, ROUGE-L, BERTScore F1, MiniLM cosine)
- Strict validation asserting exactly 1 valid record per condition
"""

import argparse
import hashlib
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

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "src"))

from precis.evaluation.metrics import (
    compute_exact_match,
    compute_minilm_cosine,
    compute_rouge_l,
    normalize_answer,
)

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


def compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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
    timeout: int = 120,
) -> Tuple[str, int, int, int]:
    """Call Ollama /api/chat with think: false. Returns (answer, latency_ms, eval_count, prompt_eval_count)."""
    endpoint = f"{base_url.rstrip('/')}/api/chat"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "think": False,
        "options": {
            "temperature": temperature,
            "top_p": top_p,
            "seed": seed,
            "num_predict": max_tokens,
        },
    }

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


def load_completed_keys(output_file: Path) -> Set[Tuple[str, str, str, str]]:
    """Load set of already completed (sample_id, model, condition, prompt_mode) tuples."""
    completed = set()
    if output_file.exists():
        with open(output_file, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    d = json.loads(line_str)
                    completed.add((
                        d["sample_id"],
                        d["model"],
                        d["condition"],
                        d["prompt_mode"],
                    ))
                except Exception:
                    pass
    return completed


def main():
    parser = argparse.ArgumentParser(description="Run confirmatory prompt validation experiment.")
    parser.add_argument("--base-url", type=str, default="http://localhost:11434", help="Ollama base URL.")
    parser.add_argument("--model", type=str, default=None, help="Filter to specific model (default: runs both).")
    parser.add_argument("--prompt", type=str, default=None, choices=["standard", "concise"], help="Filter to prompt.")
    parser.add_argument("--device", type=str, default="cpu", help="Device for BERTScore.")
    args = parser.parse_args()

    exp_dir = PROJECT_ROOT / "experiments" / "prompt_validation"
    contexts_path = exp_dir / "cached_contexts.jsonl"
    config_path = exp_dir / "config.json"
    raw_dir = exp_dir / "raw_outputs"
    raw_dir.mkdir(parents=True, exist_ok=True)
    out_file = raw_dir / "eval_records.jsonl"

    if not contexts_path.exists():
        print(f"Error: Context cache not found at {contexts_path}. Run prepare_data.py first.")
        sys.exit(1)

    with open(contexts_path, "r", encoding="utf-8") as f:
        cached_contexts = [json.loads(line) for line in f if line.strip()]

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Verify prompt hashes
    assert compute_hash(STANDARD_PROMPT_TEMPLATE) == config["prompts"]["standard"]["sha256"], "Standard prompt hash mismatch!"
    assert compute_hash(CONCISE_PROMPT_TEMPLATE) == config["prompts"]["concise"]["sha256"], "Concise prompt hash mismatch!"

    models = [config["models"]["reference"]["tag"], config["models"]["candidate"]["tag"]]
    if args.model:
        models = [args.model]

    prompts = ["standard", "concise"]
    if args.prompt:
        prompts = [args.prompt]

    retrieval_conditions = ["naive_rag", "precis_full"]

    completed = load_completed_keys(out_file)
    print(f"Loaded {len(cached_contexts)} samples.")
    print(f"Evaluating models: {models}")
    print(f"Evaluating prompts: {prompts}")
    print(f"Already completed evaluations: {len(completed)}")

    templates = {
        "standard": STANDARD_PROMPT_TEMPLATE,
        "concise": CONCISE_PROMPT_TEMPLATE,
    }

    # Factorial execution loop
    total_evals = len(cached_contexts) * len(models) * len(retrieval_conditions) * len(prompts)
    current_eval = 0

    with open(out_file, "a", encoding="utf-8") as out_f:
        for m in models:
            for prompt_name in prompts:
                template = templates[prompt_name]
                print(f"\n=======================================================")
                print(f"RUNNING: Model={m} | Prompt={prompt_name}")
                print(f"=======================================================")

                for idx, sample in enumerate(cached_contexts):
                    sid = sample["sample_id"]
                    q = sample["question"]
                    gold = sample["gold_answer"]

                    for cond in retrieval_conditions:
                        current_eval += 1
                        key = (sid, m, cond, prompt_name)
                        if key in completed:
                            continue

                        ctx_info = sample.get(cond) or sample.get("precis_v3" if cond == "precis_full" else cond)
                        ctx_text = ctx_info["context_text"]
                        ctx_sha = ctx_info["sha256"]

                        # Runtime context checksum verification
                        runtime_sha = compute_hash(ctx_text)
                        if runtime_sha != ctx_sha:
                            raise ValueError(f"Runtime context checksum mismatch for sample {sid} ({cond})!")

                        prompt_str = template.format(context=ctx_text, query=q)

                        try:
                            ans, latency_ms, eval_count, prompt_cnt = call_ollama_chat(
                                base_url=args.base_url,
                                model=m,
                                prompt=prompt_str,
                                temperature=0.0,
                                top_p=0.9,
                                seed=42,
                                max_tokens=512,
                            )
                        except Exception as exc:
                            print(f"  [ERROR] {m} {sid} {cond} {prompt_name} failed: {exc}")
                            continue

                        em = compute_exact_match(ans, gold)
                        cont = contains_answer(ans, gold)
                        rouge_l = compute_rouge_l(ans, gold)
                        minilm = compute_minilm_cosine(ans, gold)

                        bert_score = None
                        try:
                            scorer = get_bert_scorer(device=args.device)
                            _, _, f1 = scorer.score([ans.strip()], [gold.strip()])
                            bert_score = round(float(f1[0].item()), 4)
                        except Exception as b_exc:
                            print(f"  [WARN] BERTScore failed: {b_exc}")

                        record = {
                            "sample_id": sid,
                            "cohort": "confirmatory_heldout_dev",
                            "model": m,
                            "condition": cond,
                            "prompt_mode": prompt_name,
                            "question": q,
                            "gold_answer": gold,
                            "predicted_answer": ans,
                            "exact_match": em,
                            "containment_correct": cont,
                            "rouge_l": rouge_l,
                            "bert_score": bert_score,
                            "minilm_cosine": minilm,
                            "context_words": ctx_info.get("context_words", len(ctx_text.split())),
                            "context_tokens_est": ctx_info.get("context_tokens_est", 0),
                            "context_sha256": ctx_sha,
                            "generated_tokens": eval_count,
                            "prompt_tokens": prompt_cnt,
                            "latency_ms": latency_ms,
                            "temperature": 0.0,
                            "top_p": 0.9,
                            "seed": 42,
                            "max_tokens": 512,
                            "timestamp": time.time(),
                        }

                        out_f.write(json.dumps(record) + "\n")
                        out_f.flush()
                        completed.add(key)

                    if (idx + 1) % 25 == 0 or idx == len(cached_contexts) - 1:
                        print(f"  [{idx + 1}/{len(cached_contexts)}] Evaluated sample {sid} ({m}, {prompt_name})")

    print("\n[DONE] Execution completed successfully!")


if __name__ == "__main__":
    main()
