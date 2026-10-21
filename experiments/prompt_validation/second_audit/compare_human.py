"""Compare the human second rater with the LLM second rater, the objective exact-match check and Table 7."""
import csv, json, re, collections
from pathlib import Path
D = Path(__file__).resolve().parent.parent
canon = {"pass": "Pass", "conversational mismatch": "Conversational Mismatch", "incomplete entity": "Incomplete Entity",
         "hallucination": "Hallucination", "evidence insufficiency": "Evidence Insufficiency", "other": "Other"}
H = {(r["review_id"], r["output"].strip().upper()): canon[r["label"].strip().lower()] for r in csv.DictReader(open(D / "second_audit/human_rater_labels.csv"))}
Hb = {(r["review_id"], r["output"].strip().upper()): r["borderline"].strip().lower() for r in csv.DictReader(open(D / "second_audit/human_rater_labels.csv"))}
L = {(l["review_id"], l["output"]): l["label"] for l in json.load(open(D / "second_audit/second_rater_labels.json"))["labels"]}
sheet = {s["review_id"]: s for s in map(json.loads, open(D / "human_review_sheet.jsonl"))}
def norm(t):
    t = re.sub(r"[^\w\s]", " ", t.lower()); t = re.sub(r"\b(a|an|the)\b", " ", t); return " ".join(t.split())
rows = []
for rid, s in sheet.items():
    for o in "AB":
        rows.append({"rid": rid, "o": o, "prompt": s["_blinded_mapping"][f"output_{o.lower()}_prompt"], "em": norm(s[f"output_{o.lower()}"]) == norm(s["gold_answer"]),
                     "h": H[(rid, o)], "l": L[(rid, o)], "trans": s["transition_status"], "out": s[f"output_{o.lower()}"], "gold": s["gold_answer"]})
n = len(rows); out = {"n": n}
out["human_counts"] = dict(collections.Counter(r["h"] for r in rows))
out["human_by_prompt"] = {p: dict(collections.Counter(r["h"] for r in rows if r["prompt"] == p)) for p in ("standard", "concise")}
out["human_pass_vs_exact_match"] = {"pass_and_em": sum(r["h"] == "Pass" and r["em"] for r in rows), "pass_not_em": sum(r["h"] == "Pass" and not r["em"] for r in rows), "em_not_pass": sum(r["h"] != "Pass" and r["em"] for r in rows)}
out["human_pass_but_not_em_cases"] = [(r["rid"], r["o"], r["out"][:60], r["gold"]) for r in rows if r["h"] == "Pass" and not r["em"]]
def kappa(a, b):
    labs = sorted(set(a) | set(b)); po = sum(x == y for x, y in zip(a, b)) / len(a)
    ca, cb = collections.Counter(a), collections.Counter(b); pe = sum(ca[k] * cb[k] for k in labs) / len(a) ** 2
    return po, (po - pe) / (1 - pe)
po, k = kappa([r["h"] for r in rows], [r["l"] for r in rows]); out["human_vs_llm"] = {"agreement": po, "kappa": k}
out["human_vs_llm_crosstab"] = collections.Counter((r["h"], r["l"]) for r in rows if r["h"] != r["l"]).most_common()
# agreement after folding the objective Pass out (error-mode only, items both raters called an error)
err = [r for r in rows if r["h"] != "Pass" and r["l"] != "Pass"]
po2, k2 = kappa([r["h"] for r in err], [r["l"] for r in err]); out["error_items_only"] = {"n": len(err), "agreement": po2, "kappa": k2}
corr = [r for r in rows if r["trans"] == "Prompt-Correction" and r["prompt"] == "standard"]
out["human_corrections_standard_labels"] = dict(collections.Counter(r["h"] for r in corr))
fold = lambda x: "ES/Other" if x in ("Evidence Insufficiency", "Other") else x
po3, k3 = kappa([fold(r["h"]) for r in rows], [fold(r["l"]) for r in rows])
out["folded_ES_Other"] = {"agreement": po3, "agreed_labels": round(po3 * n), "kappa": k3}
out["exact_agreed_labels"] = sum(r["h"] == r["l"] for r in rows)
out["error_items_only"]["agreed_labels"] = round(out["error_items_only"]["agreement"] * out["error_items_only"]["n"])
out["table7_total"] = {"Evidence Insufficiency": 19, "Conversational Mismatch": 17, "Hallucination": 6, "Incomplete Entity": 4, "Pass(Other exact-match pass)": 14}
out["llm_counts"] = dict(collections.Counter(r["l"] for r in rows))
out["human_borderline_flags"] = dict(collections.Counter(Hb.values()))
(D / "second_audit/comparison_human.json").write_text(json.dumps(out, indent=1, default=str)); print(json.dumps(out, indent=1, default=str))
