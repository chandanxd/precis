"""Estimate exposure of variants A-E (table cohort) and the NQ-200 benchmark to the doubled negation marker.

Contexts of A-E were not stored, so they are REBUILT with the current extractor and the PRE-FIX renderer and
scanned. Estimates only: extraction has changed since the original runs. D contains Markdown tables only (no facts).
The NQ-200 count scans the packed facts stored in backend/data/nq_subset/reconstructed_facts_cache_v3.json.
  PYTHONPATH=backend/src backend/venv/bin/python scripts/measure_negation_exposure.py
Writes results/paper_checks/negation_exposure_AE.json
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
from precis.pipeline.packer import pack_context, render_context
from precis.pipeline.sdh import score_facts_with_store
from precis.pipeline.svoa import extract_facts

packer._VERB_ALREADY_NEGATED = re.compile(r"(?!x)x")  # pre-fix renderer
DBL = re.compile(r"(?<=\s)NOT (?=(?:\S+ ){0,2}(?:[Nn]ot|NOT|[Nn]ever|n't|N'T)(?=\s|$))")
NOT = re.compile(r"\bNOT\b")
captured = {}
sd.generate_answer = lambda **kw: (captured.__setitem__("ctx", kw["context"]) or type("R", (), {"answer": "x", "prompt_tokens": 0, "tokens_generated": 0, "latency_ms": 0})())
runner = next(f for n, f in vars(sd).items() if callable(f) and getattr(f, "__doc__", None) and "Execute pipeline ingestion, packing" in f.__doc__)

recs = [json.loads(l) for l in open(ROOT / "results/diagnostic_experiment_4_v1/experiment_4_8_0_final_confirmatory_20261011/eval_records.jsonl")][1:]
docs = {}
for l in open(ROOT / "backend/data/nq_subset/nq_dev.jsonl"):
    r = json.loads(l)
    if r["doc_id"] in {x["case_id"] for x in recs}: docs[r["doc_id"]] = r["document"]

out = {c: {"contexts": 0, "with_NOT": 0, "doubled": 0, "doubled_and_stored_em_wrong": 0} for c in "ABCE"}
errors = {}
for i, r in enumerate(recs, 1):
    sid, q = r["case_id"], r["question"]; raw = docs[sid]; bc = {}
    # signature of the runner: (raw_doc, q, sid, condition, model, base_svoa_cache)
    ctxs = {}
    for cond, tag in (("cond_a", "A"), ("cond_b", "B"), ("cond_c", "C")):
        try:
            runner(q, raw, sid, cond, base_svoa_cache=bc)
            ctxs[tag] = captured["ctx"]
        except Exception as e:
            errors[tag] = errors.get(tag, 0) + 1; ctxs[tag] = ""
    # E: base SVOA + table/list facts
    st = FactStore(in_memory=True, collection_name=f"e_{uuid.uuid4().hex[:8]}")
    facts = extract_facts(resolve_coreferences(raw), source_doc=sid) + proto.extract_table_list_facts(raw, source_doc=sid)
    st.add_facts(score_facts_with_store(facts, st))
    ctxs["E"] = render_context(pack_context(q, st, token_ceiling=2048).packed_facts)
    for tag, ctx in ctxs.items():
        o = out[tag]; o["contexts"] += 1
        has_n = bool(NOT.search(ctx)); has_d = bool(DBL.search(ctx))
        o["with_NOT"] += has_n; o["doubled"] += has_d
        o["doubled_and_stored_em_wrong"] += (has_d and not r["cond_" + tag.lower()]["exact_match"])
    if i % 20 == 0: print(i, {t: (v["with_NOT"], v["doubled"]) for t, v in out.items()}, flush=True)

# NQ-200 v3: scan stored packed facts
cache = json.load(open(ROOT / "backend/data/nq_subset/reconstructed_facts_cache_v3.json"))
nq = {"samples": len(cache), "samples_with_NOT": 0, "samples_doubled": 0, "packed_facts": 0, "facts_with_NOT": 0, "facts_doubled": 0}
for k, v in cache.items():
    flag_n = flag_d = False
    for f in v["packed_facts"]:
        nq["packed_facts"] += 1
        t = " " + f["rendered"] + " "
        if NOT.search(t): nq["facts_with_NOT"] += 1; flag_n = True
        if DBL.search(t): nq["facts_doubled"] += 1; flag_d = True
    nq["samples_with_NOT"] += flag_n; nq["samples_doubled"] += flag_d
res = {"runner_errors": errors, "table_cohort_rebuilt_estimates": out, "D": "tables only, no facts: no exposure by construction", "nq200_v3_packed_fact_scan": nq}
(ROOT / "results/paper_checks/negation_exposure_AE.json").write_text(json.dumps(res, indent=1))
print(json.dumps(res, indent=1))
