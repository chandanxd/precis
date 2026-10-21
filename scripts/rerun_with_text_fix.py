"""Measure the effect of the doubled negation marker by re-generating answers on the STORED contexts.

The current extractor/packer cannot reproduce the stored F contexts byte-for-byte (production now always
applies guarded structural priority and extraction changed), so the fix is applied at text level to the
stored contexts: a "NOT " marker directly before a verb phrase that already contains a negation cue
(not / never / n't within the next three tokens) is removed, which is what the code fix in
packer._render_fact_parts does. Each affected context is generated twice (stored text as a control,
fixed text) with the original model, prompt and decoding settings; stored records are not modified.

  PYTHONPATH=backend/src backend/venv/bin/python scripts/rerun_with_text_fix.py
Writes results/paper_checks/negation_fix_rerun/{table_cohort_F,confirmatory_precis}.jsonl and summary.json
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend/src")); sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "experiments/prompt_validation"))
from precis.pipeline.inference import generate_answer
from eval_table_selection_v2 import check_containment, check_exact_match
import run_experiment as rx  # templates + call_ollama_chat + scoring helpers

OUTD = ROOT / "results/paper_checks/negation_fix_rerun"; OUTD.mkdir(parents=True, exist_ok=True)
FIX = re.compile(r"(?<=\s)NOT (?=(?:\S+ ){0,2}(?:[Nn]ot|NOT|[Nn]ever|n't|N'T)(?=\s|$))")  # case-sensitive marker
fix = lambda t: FIX.sub("", t)
BASE = "http://127.0.0.1:11434"
summary = {}

# ---- table-bearing cohort, variant F (qwen2.5-coder:7b, concise prompt) ----
rows = [json.loads(l) for l in open(ROOT / "results/diagnostic_experiment_4_v1/experiment_4_8_0_final_confirmatory_20261011/eval_records.jsonl")][1:]
out = []
for r in rows:
    ctx = r["cond_f"]["context"]; new = fix(ctx)
    if new == ctx: continue
    ans = eval(r["answers"]) if isinstance(r["answers"], str) else r["answers"]
    rec = {"case_id": r["case_id"], "stored_em": r["cond_f"]["exact_match"], "stored_cont": r["cond_f"]["containment"],
           "g_em": r["cond_g"]["exact_match"]}
    for tag, c in (("control_stored_text", ctx), ("fixed_text", new)):
        res = generate_answer(query=r["question"], context=c, model="qwen2.5-coder:7b", temperature=0.0, top_p=0.9,
                              max_tokens=512, prompt_style="concise", base_url=BASE)
        p = (res.answer or "").strip()
        rec[tag] = {"pred": p, "em": check_exact_match(p, r["gold_answer"], ans) if p else None,
                    "cont": check_containment(p, r["gold_answer"], ans) if p else None}
    out.append(rec); print("F", r["case_id"][:8], rec["stored_em"], rec["control_stored_text"]["em"], rec["fixed_text"]["em"], flush=True)
(OUTD / "table_cohort_F.jsonl").write_text("\n".join(json.dumps(o) for o in out) + "\n")
summary["table_F"] = {"affected_contexts": len(out),
    "stored_em_correct": sum(bool(o["stored_em"]) for o in out),
    "control_regen_em_correct": sum(bool(o["control_stored_text"]["em"]) for o in out),
    "fixed_em_correct": sum(bool(o["fixed_text"]["em"]) for o in out),
    "control_vs_stored_em_identical": sum(bool(o["control_stored_text"]["em"]) == bool(o["stored_em"]) for o in out),
    "fixed_cont_correct": sum(bool(o["fixed_text"]["cont"]) for o in out),
    "control_cont_correct": sum(bool(o["control_stored_text"]["cont"]) for o in out),
    "f_em_total_stored": sum(bool(r["cond_f"]["exact_match"]) for r in rows)}

# ---- confirmatory experiment, Precis v3 contexts, 2 models x 2 prompts ----
D = ROOT / "experiments/prompt_validation"
cc = [json.loads(l) for l in open(D / "cached_contexts.jsonl")]
raw = {}
for l in open(D / "raw_outputs/eval_records.jsonl"):
    x = json.loads(l); raw[(x["sample_id"], x["model"], x["condition"], x["prompt_mode"])] = x
templates = {"standard": rx.STANDARD_PROMPT_TEMPLATE, "concise": rx.CONCISE_PROMPT_TEMPLATE}
out2 = []
for s in cc:
    ctx = s["precis_v3"]["context_text"]; new = fix(ctx)
    if new == ctx: continue
    for m in ("qwen2.5-coder:7b", "qwen3.5:4b"):
        for pm in ("standard", "concise"):
            rec = {"sample_id": s["sample_id"], "model": m, "prompt": pm,
                   "stored_em": str(raw[(s["sample_id"], m, "precis_full", pm)]["exact_match"]) == "True",
                   "stored_cont": str(raw[(s["sample_id"], m, "precis_full", pm)]["containment_correct"]) == "True"}
            for tag, c in (("control_stored_text", ctx), ("fixed_text", new)):
                a, *_ = rx.call_ollama_chat(BASE, m, templates[pm].format(context=c, query=s["question"]),
                                            temperature=0.0, top_p=0.9, seed=42, max_tokens=512)
                rec[tag] = {"pred": a, "em": rx.compute_exact_match(a, s["gold_answer"]), "cont": rx.contains_answer(a, s["gold_answer"])}
            out2.append(rec); print("C", s["sample_id"][:8], m, pm, rec["stored_em"], rec["control_stored_text"]["em"], rec["fixed_text"]["em"], flush=True)
(OUTD / "confirmatory_precis.jsonl").write_text("\n".join(json.dumps(o) for o in out2) + "\n")
cells = {}
for o in out2:
    c = cells.setdefault(f'{o["model"]}|{o["prompt"]}', {"n": 0, "stored_em": 0, "control_em": 0, "fixed_em": 0, "stored_cont": 0, "control_cont": 0, "fixed_cont": 0})
    c["n"] += 1; c["stored_em"] += o["stored_em"]; c["control_em"] += bool(o["control_stored_text"]["em"]); c["fixed_em"] += bool(o["fixed_text"]["em"])
    c["stored_cont"] += o["stored_cont"]; c["control_cont"] += bool(o["control_stored_text"]["cont"]); c["fixed_cont"] += bool(o["fixed_text"]["cont"])
summary["confirmatory_precis"] = {"affected_contexts": len({o["sample_id"] for o in out2}), "cells": cells}
(OUTD / "summary.json").write_text(json.dumps(summary, indent=1)); print(json.dumps(summary, indent=1))
