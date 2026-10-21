"""Compare the blind second rater with the first rater's stored information. Run after labelling.
python3 second_audit/compare_raters.py  -> second_audit/comparison.json"""
import json, re, collections, math
from pathlib import Path
D = Path(__file__).resolve().parent.parent
sheet = {s["review_id"]: s for s in map(json.loads, open(D / "human_review_sheet.jsonl"))}
lab = {(l["review_id"], l["output"]): l for l in json.load(open(D / "second_audit/second_rater_labels.json"))["labels"]}
ea = json.load(open(D / "error_analysis.json"))

def norm(t):
    t = t.lower(); t = re.sub(r"[^\w\s]", " ", t); t = re.sub(r"\b(a|an|the)\b", " ", t); return " ".join(t.split())
out = {"n_labels": len(lab)}
# prompt condition of each output (unblinded only after labelling)
rows = []
for rid, s in sheet.items():
    mp = s["_blinded_mapping"]
    for o in ("A", "B"):
        txt = s["output_" + o.lower()]; prompt = mp[f"output_{o.lower()}_prompt"]
        em = norm(txt) == norm(s["gold_answer"])
        rows.append({"rid": rid, "sid": s["sample_id"][:8], "output": o, "prompt": prompt, "em": em,
                     "label": lab[(rid, o)]["label"], "border": lab[(rid, o)]["borderline"], "trans": s["transition_status"]})
# 1. objective check of the Pass label
out["pass_vs_exact_match"] = {"label_pass_and_em": sum(r["label"] == "Pass" and r["em"] for r in rows),
                              "label_pass_not_em": sum(r["label"] == "Pass" and not r["em"] for r in rows),
                              "em_not_pass": sum(r["label"] != "Pass" and r["em"] for r in rows)}
# 2. distribution by prompt vs paper Table 7
tab = collections.defaultdict(lambda: collections.Counter())
for r in rows: tab[r["prompt"]][r["label"]] += 1
out["second_rater_by_prompt"] = {p: dict(c) for p, c in tab.items()}
out["second_rater_total"] = dict(collections.Counter(r["label"] for r in rows))
out["paper_table7"] = {"standard": {"Evidence Insufficiency": 14, "Conversational Mismatch": 14, "Hallucination": 1, "Incomplete Entity": 0, "Pass": 1},
                       "concise": {"Evidence Insufficiency": 5, "Conversational Mismatch": 3, "Hallucination": 5, "Incomplete Entity": 4, "Pass": 13},
                       "total": {"Evidence Insufficiency": 19, "Conversational Mismatch": 17, "Hallucination": 6, "Incomplete Entity": 4, "Pass": 14}}
out["borderline_labels"] = sum(r["border"] for r in rows)
# 3. correction mechanism on the 12 prompt-correction items (standard output)
corr = [r for r in rows if r["trans"] == "Prompt-Correction" and r["prompt"] == "standard"]
out["corrections_standard_output_labels"] = dict(collections.Counter(r["label"] for r in corr))
# 4. persistent errors: first-rater categories exist per sample id
first = {}
for cat, v in ea["failure_mode_breakdown_persistent_errors"]["categories"].items():
    for sid in v["sample_ids"]: first[sid] = cat
cm = {"Evidence Insufficiency": "ES", "Incomplete or Extended Entity": "FORM", "Factually Ungrounded / Misaligned Context": "UNGR"}
sm = {"Evidence Insufficiency": "ES", "Incomplete Entity": "FORM", "Conversational Mismatch": "FORM", "Hallucination": "UNGR", "Other": "UNGR", "Pass": "PASS"}
pairs = []
for sid, cat in first.items():
    items = [r for r in rows if r["sid"] == sid]
    for r in items:
        if r["prompt"] == "concise": pairs.append((sid, cm[cat], sm[r["label"]], r["label"]))
out["persistent_errors_n"] = len(pairs)
agree = sum(a == b for _, a, b, _ in pairs)
out["persistent_errors_concise_agreement_mapped3"] = agree
ca = collections.Counter(a for _, a, _, _ in pairs); cb = collections.Counter(b for _, _, b, _ in pairs); n = len(pairs)
pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / n ** 2
out["persistent_errors_cohens_kappa_mapped3"] = (agree / n - pe) / (1 - pe) if pe < 1 else None
out["persistent_errors_crosstab"] = collections.Counter((a, b) for _, a, b, _ in pairs).most_common()
out["persistent_errors_detail"] = [(sid, a, lbl) for sid, a, _, lbl in pairs]
(D / "second_audit/comparison.json").write_text(json.dumps(out, indent=1, default=str)); print(json.dumps(out, indent=1, default=str))
