"""S6: replay the fixed fresh-cohort contexts (all arms) through a general-purpose generator.

  PYTHONPATH=backend/src backend/venv/bin/python scripts/run_generator_replay.py [model]
Contexts are taken unchanged from experiments/fresh_table_cohort/records.jsonl (N_raw, N_clean, D, F2, G) and
experiments/baseline_budget/single_records.jsonl (TC, H, W at 2,048). Pipeline concise prompt, temperature 0, top-p 0.9,
seed 42, 512 new tokens, thinking disabled (/api/chat, think false). Writes experiments/baseline_budget/replay_<model>.jsonl.
"""
import json, sys, time
from pathlib import Path
import requests
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend/src")); sys.path.insert(0, str(ROOT / "scripts"))
from precis.pipeline.inference import build_prompt, strip_thinking_tags
from eval_table_selection_v2 import check_containment, check_exact_match

MODEL = sys.argv[1] if len(sys.argv) > 1 else "qwen3.5:9b"
OUT_DIR = ROOT / (sys.argv[2] if len(sys.argv) > 2 else "experiments/baseline_budget")   # e.g. experiments/generator_family
OUT = OUT_DIR / f"replay_{MODEL.replace(':', '_').replace('.', '_')}.jsonl"
fresh = {r["sample_id"]: r for r in map(json.loads, (ROOT / "experiments/fresh_table_cohort/records.jsonl").open())}
single = {r["sample_id"]: r for r in map(json.loads, (ROOT / "experiments/baseline_budget/single_records.jsonl").open())}
man = {m["sample_id"]: m for m in map(json.loads, (ROOT / "experiments/fresh_table_cohort/manifest.jsonl").open()) if "sample_id" in m}
done = {(r["sample_id"], r["arm"]) for r in map(json.loads, OUT.open())} if OUT.exists() else set()
with OUT.open("a") as fo:
    for sid, fr in fresh.items():
        m = man[sid]
        ctxs = {a: fr[a]["context"] for a in ("N_raw", "N_clean", "D", "F2", "G")}
        if sid in single:
            for a in ("TC", "H", "W"): ctxs[a] = single[sid]["e1"][a]["context"]
        for arm, ctx in ctxs.items():
            if (sid, arm) in done: continue
            if not ctx.strip():
                rec = {"pred": "", "em": False, "cont": False}
            else:
                prompt = build_prompt(ctx, m["question"], "concise")
                r = requests.post("http://localhost:11434/api/chat", json={
                    "model": MODEL, "messages": [{"role": "user", "content": prompt}], "stream": False, "think": False,
                    "options": {"temperature": 0.0, "top_p": 0.9, "seed": 42, "num_predict": 512, "num_ctx": 8192}}, timeout=300)
                r.raise_for_status()
                p = strip_thinking_tags(r.json()["message"]["content"]).strip()
                rec = {"pred": p, "em": check_exact_match(p, m["gold_answer"], m["answers"]) if p else False,
                       "cont": check_containment(p, m["gold_answer"], m["answers"]) if p else False}
            fo.write(json.dumps({"sample_id": sid, "arm": arm, "model": MODEL, **rec}) + "\n"); fo.flush()
        print(sid[:8], flush=True)
