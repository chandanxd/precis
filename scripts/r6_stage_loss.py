"""R6: stage-loss decomposition. No model calls.

(1) Fresh table cohort: where does answer-bearing evidence disappear for each arm (document -> context -> output -> exact match)?
(2) 200-sample NQ benchmark (v3): decomposition of the 88.5% coverage -> 19% EM gap into generation failure/abstention and
    exact-match strictness, using stored outputs and MRQA aliases.
Run: PYTHONPATH=backend/src backend/venv/bin/python scripts/r6_stage_loss.py
"""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend/src")); sys.path.insert(0, str(ROOT / "scripts"))
from precis.api.security import sanitize_document
from precis.evaluation.metrics import normalize_answer
from eval_table_selection_v2 import check_containment, check_exact_match

ABST = re.compile(r"(insufficient information|not (?:enough|sufficient)|does not (?:contain|provide|specify|mention|state)|do not (?:contain|provide)|no information|cannot be (?:determined|answered)|not (?:specified|mentioned|provided|stated))", re.I)
nq = {}
for l in (ROOT / "backend/data/nq_subset/nq_dev.jsonl").open():
    r = json.loads(l); nq[r["doc_id"]] = r


def present(text, answers):
    t = normalize_answer(text)
    return any(normalize_answer(a) and normalize_answer(a) in t for a in answers)


# ---- (1) fresh cohort
rows = [json.loads(l) for l in (ROOT / "experiments/fresh_table_cohort/records.jsonl").open()]
man = {m["sample_id"]: m for m in map(json.loads, (ROOT / "experiments/fresh_table_cohort/manifest.jsonl").open()) if "sample_id" in m}
out1 = {"n": len(rows), "arms": {}}
for arm in ("N_raw", "N_clean", "D", "F2", "G"):
    c = dict(in_context=0, in_context_and_em=0, in_context_and_contains=0, in_context_abstained=0, in_context_wrong=0,
             in_context_contains_not_em=0, not_in_context=0, not_in_context_but_em=0)
    for r in rows:
        ans = man[r["sample_id"]]["answers"]; a = r[arm]; ctxp = present(a["context"], ans)
        if ctxp:
            c["in_context"] += 1; c["in_context_and_em"] += a["em"]; c["in_context_and_contains"] += a["cont"]
            c["in_context_contains_not_em"] += (a["cont"] and not a["em"])
            if not a["cont"]:
                if ABST.search(a["pred"] or "") or a["status"] != "ok": c["in_context_abstained"] += 1
                else: c["in_context_wrong"] += 1
        else:
            c["not_in_context"] += 1; c["not_in_context_but_em"] += a["em"]
    out1["arms"][arm] = c
out1["document_has_answer"] = sum(present(sanitize_document(nq[r["sample_id"]]["document"]), man[r["sample_id"]]["answers"]) for r in rows)
out1["raw_document_has_answer"] = sum(present(nq[r["sample_id"]]["document"], man[r["sample_id"]]["answers"]) for r in rows)

# ---- (2) NQ-200 v3
rec = [json.loads(l) for l in (ROOT / "results/nq_benchmark_svoa_enhanced_v3/per_question_results.jsonl").open()]
p = [r for r in rec if r["condition"] == "precis_full"]
n = len(p); cont = em = ab = cont_not_em = nocont_nonabst = 0
for r in p:
    ans = nq[r["sample_id"]]["answers"] or [r["gold_answer"]]
    c = check_containment(r["predicted_answer"], r["gold_answer"], ans); e = bool(r["exact_match"])
    cont += c; em += e; cont_not_em += (c and not e)
    if not c:
        if ABST.search(r["predicted_answer"] or ""): ab += 1
        else: nocont_nonabst += 1
out2 = {"n": n, "coverage_reported": 177, "containment_with_aliases": cont, "exact_match": em,
        "contained_but_not_exact": cont_not_em, "not_contained_abstained": ab, "not_contained_other_wrong": nocont_nonabst,
        "gap_coverage_to_em": 177 - em, "lost_generation_or_abstention_upper": 177 - cont, "lost_exact_match_strictness": cont_not_em,
        "note": "per-case coverage flags were not stored, so the split uses the reported 177 as a ceiling; containment is an upper bound for correct answers"}
res = {"fresh_table_cohort": out1, "nq200_v3": out2}
(ROOT / "results/paper_checks/r6_stage_loss.json").write_text(json.dumps(res, indent=1))
print(json.dumps(res, indent=1))
