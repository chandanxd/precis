"""Rebuild second_audit/table7_merged_counts.json (Table 7 of the paper) from the two raters' labels.
Pass is defined by exact match; evidence insufficiency + other are merged. Re-run after editing human_rater_labels.csv."""
import collections, json
from pathlib import Path
D = Path(__file__).resolve().parent.parent
exec((D / "second_audit/compare_human.py").read_text().split('out = {"n": n}')[0].replace("Path(__file__).resolve().parent.parent", f'Path(r"{D}")'))
fold = lambda x: "Refusal / insufficient" if x in ("Evidence Insufficiency", "Other") else x
tab = {}
for who, key in (("H", "h"), ("L", "l")):
    for p in ("standard", "concise"):
        c = collections.Counter()
        for r in rows:
            if r["prompt"] == p and not r["em"]:
                c["Not labelled (human Pass on a non-exact match)" if r[key] == "Pass" else fold(r[key])] += 1
        tab[f"{who}|{p}"] = dict(c)
(D / "second_audit/table7_merged_counts.json").write_text(json.dumps(tab, indent=1)); print(tab)
