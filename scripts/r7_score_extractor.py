"""R7 + judge validation: score the completed annotation sheets. No model calls.

  backend/venv/bin/python scripts/r7_score_extractor.py
Rules (fixed before looking at any score):
 - Fact rows where annotator A wrote 'ambiguous' / 'hard to tell' (or a compound label) as the true modality are unscorable:
   they are excluded from every precision and agreement figure and counted separately.
 - Sentence rows where either annotator wrote 'ambiguous' are excluded the same way.
 - Sentence rows whose text was split over two CSV cells by the spreadsheet are re-joined before scoring.
 - Judge rows with a blank human label are excluded and counted.
"""
import csv, json, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "experiments/extractor_eval"; PV = ROOT / "experiments/prompt_validation/followup"
MOD = {"asserted", "attributed", "conditional", "hypothetical"}


def kappa(a, b):
    n = len(a)
    if not n: return None
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = collections.Counter(a), collections.Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / n ** 2
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


yn = lambda v: v.strip().upper()[:1]
out = {}

# ------------------------------------------------------------ facts
F = list(csv.DictReader(open(D / "facts_to_annotate.csv", encoding="utf-8-sig")))
tk = "A_true_modality(asserted/attributed/conditional/hypothetical)"; bk = "B_true_modality(asserted/attributed/conditional/hypothetical)"
unscor = [r for r in F if r[tk].strip().lower() not in MOD and r[tk].strip()]
use = [r for r in F if r not in unscor and yn(r["A_polarity_correct(Y/N)"]) in "YN" and yn(r["B_polarity_correct(Y/N)"]) in "YN"]
out["facts"] = {"rows": len(F), "unscorable_ambiguous": len(unscor), "scored": len(use)}


def prec(rows, col, cls_fn):
    by = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        k = cls_fn(r); by[k][1] += 1; by[k][0] += yn(r[col]) == "Y"
    return {k: {"correct": v[0], "n": v[1], "precision": round(v[0] / v[1], 3)} for k, v in sorted(by.items())}


negc = lambda r: "negated" if r["stored_negated"] == "1" else "not_negated"
modc = lambda r: r["stored_modality"]
for who in ("A", "B"):
    out["facts"][f"{who}_polarity_precision"] = prec(use, f"{who}_polarity_correct(Y/N)", negc)
    out["facts"][f"{who}_modality_precision"] = prec(use, f"{who}_modality_correct(Y/N)", modc)
agp = [r for r in use if yn(r["A_polarity_correct(Y/N)"]) == yn(r["B_polarity_correct(Y/N)"])]
agm = [r for r in use if yn(r["A_modality_correct(Y/N)"]) == yn(r["B_modality_correct(Y/N)"])]
out["facts"]["kappa_polarity"] = kappa([yn(r["A_polarity_correct(Y/N)"]) for r in use], [yn(r["B_polarity_correct(Y/N)"]) for r in use])
out["facts"]["kappa_modality_correct"] = kappa([yn(r["A_modality_correct(Y/N)"]) for r in use], [yn(r["B_modality_correct(Y/N)"]) for r in use])
out["facts"]["raw_agreement_polarity"] = round(len(agp) / len(use), 3); out["facts"]["raw_agreement_modality"] = round(len(agm) / len(use), 3)
out["facts"]["agreed_polarity_precision"] = prec([r for r in agp], "A_polarity_correct(Y/N)", negc)
out["facts"]["agreed_modality_precision"] = prec([r for r in agm], "A_modality_correct(Y/N)", modc)
# A's corrected modality when the stored one is wrong
conf = collections.Counter((r["stored_modality"], r[tk].strip().lower()) for r in use if yn(r["A_modality_correct(Y/N)"]) == "N")
out["facts"]["A_modality_errors_stored_to_true"] = {f"{a}->{b}": n for (a, b), n in conf.most_common()}

import re
_cue = re.compile(r"\b(not|n't|no|never|neither|nor|none|nothing|nobody|without|cannot|unable)\b", re.I)
wrong = [r for r in use if r["stored_negated"] == "1" and yn(r["A_polarity_correct(Y/N)"]) == "N"]
loc = collections.Counter("in_fact_fields" if any(_cue.search(r[k]) for k in ("subject", "verb", "object")) else "elsewhere_in_sentence" for r in wrong)
out["facts"]["negated_but_wrong_by_A"] = {"n": len(wrong), **dict(loc), "note": "automatic check of whether a negation cue occurs in the fact's subject, verb or object"}

# ------------------------------------------------------------ sentences
raw = list(csv.reader(open(D / "sentences_to_annotate.csv", encoding="utf-8-sig")))[1:]
ext = json.load(open(D / "sentences_extractor_output.json"))
S = []
for r in raw:
    if r[3].strip().upper()[:1] not in ("Y", "N") and r[3].strip().lower() != "ambiguous":   # split sentence cell
        r = r[:2] + [r[2] + r[3]] + r[4:]
    S.append({"item": r[0], "sentence": r[2], "A_neg": r[3].strip(), "A_mod": r[4].strip().lower(), "B_neg": r[5].strip(), "B_mod": r[6].strip().lower()})
sus = [s for s in S if s["A_neg"].lower() == "ambiguous" or s["A_mod"] == "ambiguous"]
su = [s for s in S if s not in sus and s["A_neg"] in ("Y", "N") and s["B_neg"] in ("Y", "N") and s["A_mod"] in MOD and s["B_mod"] in MOD]
out["sentences"] = {"rows": len(S), "unscorable_ambiguous": len(sus), "scored": len(su)}
out["sentences"]["kappa_negation"] = kappa([s["A_neg"] for s in su], [s["B_neg"] for s in su])
out["sentences"]["kappa_modality"] = kappa([s["A_mod"] for s in su], [s["B_mod"] for s in su])
out["sentences"]["raw_agreement_negation"] = round(sum(s["A_neg"] == s["B_neg"] for s in su) / len(su), 3)
out["sentences"]["raw_agreement_modality"] = round(sum(s["A_mod"] == s["B_mod"] for s in su) / len(su), 3)


def neg_scores(rows, label):
    tp = fp = fn = tn = 0
    for s in rows:
        truth = label(s) == "Y"; pred = any(f["negated"] for f in ext[s["item"]])
        tp += truth and pred; fp += (not truth) and pred; fn += truth and not pred; tn += (not truth) and not pred
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "n": len(rows), "precision": round(tp / (tp + fp), 3) if tp + fp else None,
            "recall": round(tp / (tp + fn), 3) if tp + fn else None}


def nonasserted_scores(rows, label):
    tp = fp = fn = tn = 0
    for s in rows:
        truth = label(s) != "asserted"; pred = any(f["modality"] != "asserted" for f in ext[s["item"]])
        tp += truth and pred; fp += (not truth) and pred; fn += truth and not pred; tn += (not truth) and not pred
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "n": len(rows), "precision": round(tp / (tp + fp), 3) if tp + fp else None,
            "recall": round(tp / (tp + fn), 3) if tp + fn else None}


out["sentences"]["negation_vs_A"] = neg_scores(su, lambda s: s["A_neg"])
out["sentences"]["negation_vs_B"] = neg_scores(su, lambda s: s["B_neg"])
agn = [s for s in su if s["A_neg"] == s["B_neg"]]
out["sentences"]["negation_vs_agreed"] = neg_scores(agn, lambda s: s["A_neg"])
out["sentences"]["nonasserted_vs_A"] = nonasserted_scores(su, lambda s: s["A_mod"])
out["sentences"]["nonasserted_vs_B"] = nonasserted_scores(su, lambda s: s["B_mod"])
agm2 = [s for s in su if s["A_mod"] == s["B_mod"]]
out["sentences"]["nonasserted_vs_agreed"] = nonasserted_scores(agm2, lambda s: s["A_mod"])
out["sentences"]["note"] = "extractor was run on the single sentence (no coreference); 'predicted negated' = any fact of the sentence negated"

# ------------------------------------------------------------ judge validation
J = list(csv.DictReader(open(PV / "judge_validation_sheet.csv", encoding="utf-8-sig")))
key = json.load(open(PV / "judge_validation_key.json"))
lab = [(key[r["item"]]["judge"], r["human_label(CORRECT/INCORRECT)"].strip().upper()) for r in J]
blank = [x for x in lab if x[1] not in ("CORRECT", "INCORRECT")]
lab = [(j, h == "CORRECT") for j, h in lab if h in ("CORRECT", "INCORRECT")]
tp = sum(j and h for j, h in lab); tn = sum((not j) and (not h) for j, h in lab); fp = sum(j and not h for j, h in lab); fn = sum((not j) and h for j, h in lab)
n_pos = sum(j for j, _ in lab); n_neg = len(lab) - n_pos
sens = tp / (tp + fn) if tp + fn else None; spec = tn / (tn + fp) if tn + fp else None
ppv = tp / (tp + fp) if tp + fp else None; npv = tn / (tn + fn) if tn + fn else None
w = 1079 / 1600           # share of judge-CORRECT outputs among all 1,600 judged outputs
out["judge"] = {"items": len(J), "blank_hard_to_tell": len(blank), "scored": len(lab), "judge_correct_items": n_pos, "judge_incorrect_items": n_neg,
                "human_agrees_when_judge_CORRECT_(precision)": round(ppv, 3), "human_agrees_when_judge_INCORRECT_(npv)": round(npv, 3),
                "kappa": kappa([j for j, _ in lab], [h for _, h in lab]),
                "raw_agreement_in_stratified_sample": round((tp + tn) / len(lab), 3),
                "population_weighted_agreement": round(w * ppv + (1 - w) * npv, 3),
                "confusion": {"judge_correct_human_correct": tp, "judge_correct_human_incorrect": fp, "judge_incorrect_human_correct": fn, "judge_incorrect_human_incorrect": tn},
                "note": "sample was stratified 50 judge-CORRECT / 50 judge-INCORRECT; population weights use the 1,079/521 split of all 1,600 outputs"}
(D / "extractor_scores.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
