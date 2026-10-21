"""Measure (not bound) the effect of the doubled negation marker on variants A and E and on the NQ-200 benchmark.

A and E contexts were never stored and extraction has changed, so they are REBUILT with the current extractor and the
PRE-FIX renderer (as in measure_negation_exposure.py). For every context that contains a doubled marker the answer is
generated twice with the original model, prompt style and decoding settings: control (doubled marker kept) and fixed
(marker removed, which is what packer._render_fact_parts now does). The control-vs-fixed difference isolates the marker.
NQ-200 (v3): the stored packed facts of the 7 affected samples are re-rendered (control reproduces the stored answers
or not is recorded), then generated with the marker removed. Stored records are never modified.
  PYTHONPATH=backend/src backend/venv/bin/python scripts/rerun_negation_AE_NQ.py
Writes results/paper_checks/negation_AE_NQ_rerun/{A,E,nq200}.jsonl and summary.json. Needs Ollama (qwen2.5-coder:7b).
"""
import json, re, sys, uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend/src")); sys.path.insert(0, str(ROOT / "scripts"))
from precis.pipeline import packer
import eval_structural_decompilation_v3 as sd
import eval_table_extraction_prototype as proto
from precis.graph.store import FactStore
from precis.pipeline.coref import resolve_coreferences
from precis.pipeline.inference import generate_answer
from precis.pipeline.packer import pack_context, render_context
from precis.pipeline.sdh import score_facts_with_store
from precis.pipeline.svoa import extract_facts
from scoring import em, cont  # gold answer or any MRQA alternative

OUTD = ROOT / "results/paper_checks/negation_AE_NQ_rerun"; OUTD.mkdir(parents=True, exist_ok=True)
BASE = "http://127.0.0.1:11434"; MODEL = "qwen2.5-coder:7b"
packer._VERB_ALREADY_NEGATED = re.compile(r"(?!x)x")  # pre-fix renderer
DBL = re.compile(r"(?<=\s)NOT (?=(?:\S+ ){0,2}(?:[Nn]ot|NOT|[Nn]ever|n't|N'T)(?=\s|$))")
fix = lambda t: DBL.sub("", t)
captured = {}
sd.generate_answer = lambda **kw: (captured.__setitem__("ctx", kw["context"]) or type("R", (), {"answer": "x", "prompt_tokens": 0, "tokens_generated": 0, "latency_ms": 0})())
runner = next(f for n, f in vars(sd).items() if callable(f) and getattr(f, "__doc__", None) and "Execute pipeline ingestion, packing" in f.__doc__)


def gen(q, ctx, style):
    kw = dict(query=q, context=ctx, model=MODEL, temperature=0.0, top_p=0.9, max_tokens=512, base_url=BASE)
    if style: kw["prompt_style"] = style
    return (generate_answer(**kw).answer or "").strip()


summary = {}
# ------------------------------------------------------------------ A and E on the table cohort (concise prompt)
recs = [json.loads(l) for l in open(ROOT / "results/diagnostic_experiment_4_v1/experiment_4_8_0_final_confirmatory_20261011/eval_records.jsonl")][1:]
ids = {x["case_id"] for x in recs}
docs = {}
for l in open(ROOT / "backend/data/nq_subset/nq_dev.jsonl"):
    r = json.loads(l)
    if r["doc_id"] in ids: docs[r["doc_id"]] = r["document"]
rows = {"A": [], "E": []}
for i, r in enumerate(recs, 1):
    sid, q = r["case_id"], r["question"]; bc = {}
    ctxs = {}
    runner(q, docs[sid], sid, "cond_a", base_svoa_cache=bc); ctxs["A"] = captured["ctx"]
    st = FactStore(in_memory=True, collection_name=f"e_{uuid.uuid4().hex[:8]}")
    facts = extract_facts(resolve_coreferences(docs[sid]), source_doc=sid) + proto.extract_table_list_facts(docs[sid], source_doc=sid)
    st.add_facts(score_facts_with_store(facts, st))
    ctxs["E"] = render_context(pack_context(q, st, token_ceiling=2048).packed_facts)
    for tag, ctx in ctxs.items():
        if not DBL.search(ctx): continue
        o = {"case_id": sid, "variant": tag, "stored_em": bool(r["cond_" + tag.lower()]["exact_match"]),
             "g_em": bool(r["cond_g"]["exact_match"])}
        for k, c in (("control", ctx), ("fixed", fix(ctx))):
            p = gen(q, c, "concise"); o[k] = {"pred": p, "em": em(sid, p) if p else False, "cont": cont(sid, p) if p else False}
        rows[tag].append(o); print(tag, sid[:8], o["stored_em"], o["control"]["em"], o["fixed"]["em"], flush=True)
    if i % 25 == 0: print("built", i, {t: len(v) for t, v in rows.items()}, flush=True)
for tag in "AE":
    (OUTD / f"{tag}.jsonl").write_text("\n".join(json.dumps(o) for o in rows[tag]) + "\n")
    rs = rows[tag]
    summary[tag] = {"affected_contexts": len(rs), "stored_em_correct": sum(o["stored_em"] for o in rs),
                    "control_em_correct": sum(o["control"]["em"] for o in rs), "fixed_em_correct": sum(o["fixed"]["em"] for o in rs),
                    "control_cont_correct": sum(o["control"]["cont"] for o in rs), "fixed_cont_correct": sum(o["fixed"]["cont"] for o in rs),
                    "em_outcome_changes_fixed_vs_control": sum(o["control"]["em"] != o["fixed"]["em"] for o in rs),
                    "gained_by_fix": sum((not o["control"]["em"]) and o["fixed"]["em"] for o in rs),
                    "lost_by_fix": sum(o["control"]["em"] and not o["fixed"]["em"] for o in rs)}

# ------------------------------------------------------------------ NQ-200 v3, standard prompt, stored packed facts
cache = json.load(open(ROOT / "backend/data/nq_subset/reconstructed_facts_cache_v3.json"))
stored = {}
for l in open(ROOT / "results/nq_benchmark_svoa_enhanced_v3/per_question_results.jsonl"):
    x = json.loads(l)
    if x["condition"] == "precis_full": stored[x["sample_id"]] = x
nq = []
for sid, v in cache.items():
    if not any(DBL.search(" " + f["rendered"] + " ") for f in v["packed_facts"]): continue
    ctx = "\n".join(f"Fact {i}: {f['rendered']}" for i, f in enumerate(v["packed_facts"], 1))
    q = stored[sid]["question"]
    o = {"sample_id": sid, "question": q, "stored_pred": stored[sid]["predicted_answer"], "stored_em": em(sid, stored[sid]["predicted_answer"]),
         "stored_cont": cont(sid, stored[sid]["predicted_answer"])}
    for k, c in (("control", ctx), ("fixed", fix(ctx))):
        p = gen(q, c, None); o[k] = {"pred": p, "em": em(sid, p) if p else False, "cont": cont(sid, p) if p else False}
    nq.append(o); print("NQ", sid[:8], o["stored_em"], o["control"]["em"], o["fixed"]["em"], flush=True)
(OUTD / "nq200.jsonl").write_text("\n".join(json.dumps(o) for o in nq) + "\n")
summary["nq200_v3"] = {"affected_samples": len(nq), "stored_em_correct": sum(o["stored_em"] for o in nq),
    "control_em_correct": sum(o["control"]["em"] for o in nq), "fixed_em_correct": sum(o["fixed"]["em"] for o in nq),
    "control_reproduces_stored_em": sum(o["control"]["em"] == o["stored_em"] for o in nq),
    "control_reproduces_stored_pred": sum(o["control"]["pred"] == o["stored_pred"] for o in nq),
    "stored_cont_correct": sum(o["stored_cont"] for o in nq), "fixed_cont_correct": sum(o["fixed"]["cont"] for o in nq),
    "control_cont_correct": sum(o["control"]["cont"] for o in nq)}
(OUTD / "summary.json").write_text(json.dumps(summary, indent=1)); print(json.dumps(summary, indent=1))
