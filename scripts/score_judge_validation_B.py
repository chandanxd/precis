"""Score the second labeller of the answer-equivalence judge (instructions: experiments/prompt_validation/followup/
JUDGE_VALIDATION_B_INSTRUCTIONS.md).

  backend/venv/bin/python scripts/score_judge_validation_B.py
Reads judge_validation_sheet.csv (labeller A), judge_validation_sheet_B.csv (labeller B) and judge_validation_key.json (the
judge's verdicts); writes experiments/prompt_validation/followup/judge_validation_B.json.
"""
import csv, json, math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FU = ROOT / "experiments/prompt_validation/followup"
key = json.load(open(FU / "judge_validation_key.json"))
A = {r["item"]: (r["human_label(CORRECT/INCORRECT)"] or "").strip().upper() for r in csv.DictReader(open(FU / "judge_validation_sheet.csv"))}
B = {r["item"]: (r["label_B(CORRECT/INCORRECT/HARD)"] or "").strip().upper() for r in csv.DictReader(open(FU / "judge_validation_sheet_B.csv"))}
J = {it: ("CORRECT" if k["judge"] else "INCORRECT") for it, k in key.items()}
assert set(A) == set(B) == set(J), "the three files must cover the same items"
missing = [it for it, v in B.items() if v not in ("CORRECT", "INCORRECT", "HARD")]
assert not missing, "labeller B has not labelled items %s" % ", ".join(missing[:10])


def wilson(k, n, z=1.96):
    if n == 0: return None
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 4), round(c + h, 4)]


def kappa(x, y):
    n = len(x)
    po = sum(a == b for a, b in zip(x, y)) / n
    pc = sum((x.count(c) / n) * (y.count(c) / n) for c in ("CORRECT", "INCORRECT"))
    return round((po - pc) / (1 - pc), 4) if pc < 1 else None


def pair(p, q, name):
    its = [it for it in key if p[it] in ("CORRECT", "INCORRECT") and q[it] in ("CORRECT", "INCORRECT")]
    x, y = [p[i] for i in its], [q[i] for i in its]
    agree = sum(a == b for a, b in zip(x, y))
    return {"pair": name, "n": len(its), "agree": agree, "agreement": round(agree / len(its), 4) if its else None,
            "wilson95": wilson(agree, len(its)), "cohen_kappa": kappa(x, y)}


both = [it for it in key if A[it] in ("CORRECT", "INCORRECT") and B[it] in ("CORRECT", "INCORRECT") and A[it] == B[it]]
res = {"B_hard": sum(v == "HARD" for v in B.values()),
       "judge_vs_B": pair(J, B, "judge-B"), "judge_vs_A": pair(J, A, "judge-A"), "A_vs_B": pair(A, B, "A-B"),
       "judge_vs_consensus": {"n": len(both), "agree": sum(J[i] == A[i] for i in both),
                              "wilson95": wilson(sum(J[i] == A[i] for i in both), len(both))}}
(FU / "judge_validation_B.json").write_text(json.dumps(res, indent=1))
print(json.dumps(res, indent=1))
