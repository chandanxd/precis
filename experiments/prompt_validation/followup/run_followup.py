"""RQ2 follow-up (protocol: followup/PROTOCOL.md). Runs the two new prompts on the cached confirmatory contexts.

  PYTHONPATH=backend/src backend/venv/bin/python experiments/prompt_validation/followup/run_followup.py gen
  PYTHONPATH=backend/src backend/venv/bin/python experiments/prompt_validation/followup/run_followup.py judge
"""
import hashlib, json, re, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "backend/src")); sys.path.insert(0, str(HERE.parent))
import run_experiment as R  # existing templates and chat helper

STD_ABST = '- If the provided facts do not contain enough information to answer the question, say so explicitly.'
CON_ABST = '- If the provided facts do not contain enough information to answer the question, output "Insufficient information".'
assert STD_ABST in R.STANDARD_PROMPT_TEMPLATE and CON_ABST in R.CONCISE_PROMPT_TEMPLATE
PROMPTS = {
    "standard": R.STANDARD_PROMPT_TEMPLATE,
    "concise": R.CONCISE_PROMPT_TEMPLATE,
    "short_explicit": R.CONCISE_PROMPT_TEMPLATE.replace(CON_ABST, STD_ABST),
    "sent_token": R.STANDARD_PROMPT_TEMPLATE.replace(STD_ABST, CON_ABST),
}
OUT = HERE / "followup_records.jsonl"
JOUT = HERE / "judge_records.jsonl"
sha = lambda t: hashlib.sha256(t.encode()).hexdigest()


def gen():
    ctxs = [json.loads(l) for l in (HERE.parent / "cached_contexts.jsonl").open() if l.strip()]
    done = {(r["sample_id"], r["model"], r["condition"], r["prompt_mode"]) for r in map(json.loads, OUT.open())} if OUT.exists() else set()
    json.dump({k: sha(v) for k, v in PROMPTS.items()}, open(HERE / "prompt_hashes.json", "w"), indent=1)
    with OUT.open("a") as fo:
        for m in ("qwen2.5-coder:7b", "qwen3.5:4b"):
            for pm in ("short_explicit", "sent_token"):
                for s in ctxs:
                    for cond in ("naive_rag", "precis_full"):
                        if (s["sample_id"], m, cond, pm) in done: continue
                        info = s.get(cond) or s.get("precis_v3")
                        assert sha(info["context_text"]) == info["sha256"]
                        ans, lat, ev, pe = R.call_ollama_chat("http://localhost:11434", m, PROMPTS[pm].format(context=info["context_text"], query=s["question"]))
                        fo.write(json.dumps({"sample_id": s["sample_id"], "model": m, "condition": cond, "prompt_mode": pm,
                                             "question": s["question"], "gold_answer": s["gold_answer"], "predicted_answer": ans,
                                             "exact_match": R.compute_exact_match(ans, s["gold_answer"]),
                                             "containment_correct": R.contains_answer(ans, s["gold_answer"]),
                                             "prompt_tokens": pe, "generated_tokens": ev}) + "\n"); fo.flush()
                print(m, pm, "done", flush=True)


RUBRIC = ("Question: {q}\nReference answer: {g}\nCandidate answer: {a}\n\n"
          "Does the candidate give the same answer as the reference (same entity, number or date; extra correct detail is "
          "allowed; an abstention is incorrect)? Reply with exactly CORRECT or INCORRECT.")


def judge():
    recs = [json.loads(l) for l in (HERE.parent / "raw_outputs/eval_records.jsonl").open()] + [json.loads(l) for l in OUT.open()]
    done = {(r["sample_id"], r["model"], r["condition"], r["prompt_mode"]) for r in map(json.loads, JOUT.open())} if JOUT.exists() else set()
    with JOUT.open("a") as fo:
        for n, r in enumerate(recs, 1):
            k = (r["sample_id"], r["model"], r["condition"], r["prompt_mode"])
            if k in done: continue
            ans, *_ = R.call_ollama_chat("http://localhost:11434", "gemma4:12b",
                                         RUBRIC.format(q=r["question"], g=r["gold_answer"], a=r["predicted_answer"]), max_tokens=8)
            fo.write(json.dumps({"sample_id": k[0], "model": k[1], "condition": k[2], "prompt_mode": k[3],
                                 "judge": ans.strip().upper().startswith("CORRECT")  and not ans.strip().upper().startswith("INCORRECT"),
                                 "judge_raw": ans.strip()[:40]}) + "\n"); fo.flush()
            if n % 200 == 0: print(n, "/", len(recs), flush=True)


if __name__ == "__main__":
    {"gen": gen, "judge": judge}[sys.argv[1]]()
