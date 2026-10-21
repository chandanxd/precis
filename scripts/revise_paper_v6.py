"""Build Precis_paper_clean_plane_revised_v6.docx from v5: the Stage 2.5 integrity corrections
(paper/INTEGRITY_v5_stage2_5.md, C1-C8) and the Stage 3 quick-review author items (paper/REVIEW_v5_quick.md, K3).
No content is cut (author decision: the J.UCS version may run to about 28-30 pages).

  backend/venv/bin/python scripts/revise_paper_v6.py
Numbers quoted below are checked against the stored analyses so the text cannot drift from the records. v5 is left untouched.
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from docx_tools import Doc, NS, q

SRC = ROOT / "paper/research-paper/Precis_paper_clean_plane_revised_v5.docx"
DST = ROOT / "paper/research-paper/Precis_paper_clean_plane_revised_v6.docx"
V4 = json.loads((ROOT / "results/paper_checks/v4_reanalysis.json").read_text())
TAB = json.loads((ROOT / "results/paper_checks/table_cohort_checks.json").read_text())
FU = json.loads((ROOT / "experiments/prompt_validation/followup/analysis.json").read_text())
d = Doc(SRC)
P = d.orig                      # handles by v5 body index


def rep(i, old, new):
    d.replace(P[i], old, new)


# ------------------------------------------------------------------ checks against the records
ni = V4["noninferiority"]
nb = {a: ni[a]["newcombe_0.99286"][0] for a in ("N_raw", "W", "TC")}
assert round(nb["N_raw"], 1) == -5.1 and round(nb["TC"], 1) == -5.1 and -5.0 < nb["W"] < -4.9, nb
lo, hi = sorted(-x for x in TAB["pairs"]["b-d:exact_match"]["cluster_boot95_pp"])
assert (round(lo, 1), round(hi, 1)) == (27.3, 43.9), (lo, hi)
cells = FU["cells"]


def main_effect(metric, plus, minus):
    """Mean of two prompts minus mean of the other two, per model-retrieval cell."""
    out = []
    for k, v in cells.items():
        out.append((v[plus[0]][metric] + v[plus[1]][metric]) / 2 - (v[minus[0]][metric] + v[minus[1]][metric]) / 2)
    return out


fmt_em = main_effect("em", ("short_explicit", "concise"), ("standard", "sent_token"))
fmt_judge = main_effect("judge", ("short_explicit", "concise"), ("standard", "sent_token"))
assert (min(fmt_em), max(fmt_em)) == (25.0, 36.5), fmt_em
assert (min(fmt_judge), max(fmt_judge)) == (1.5, 12.0), fmt_judge
tok_judge = [(v["sent_token"]["judge"] + v["concise"]["judge"]) / 2 - (v["standard"]["judge"] + v["short_explicit"]["judge"]) / 2
             for k, v in cells.items() if k.startswith("qwen2.5")]
assert sorted(tok_judge) == [-29.0, -21.5], tok_judge

# ------------------------------------------------------------------ C6: corresponding-author e-mail
rep(3, "[to be added]", "chandanxdev@gmail.com")

# ------------------------------------------------------------------ C4: abstract ranges stated exactly
rep(4, "raised EM by 25 to 37 points", "raised EM by 25.0 to 36.5 points")
rep(4, "saw gains of 2 to 12 points", "saw gains of 1.5 to 12.0 points")
rep(4, "cost the code-specialised generator 22 to 29 points", "cost the code-specialised generator 21.5 to 29.0 points")

# ------------------------------------------------------------------ C5: hardware rule as implemented (hardware.py)
rep(48, "3,072 (VRAM ≥ 2 GB)", "3,072 (RAM ≥ 8 GB and VRAM ≥ 2 GB)")

# ------------------------------------------------------------------ C2: D vs B question-level interval
rep(67, "+27.4 to +43.9", "+27.3 to +43.9")

# ------------------------------------------------------------------ C1: Newcombe bounds at the Bonferroni level
rep(74, "the Newcombe lower bounds against N_raw, W and TC (−5.1, −5.0 and −5.1) reach the 5-point margin",
        "the Newcombe lower bounds against N_raw and TC (−5.1) cross the 5-point margin and that against W (−4.95) "
        "just meets it")

# ------------------------------------------------------------------ C7: CRediT roles describe authors only
tbl = P[118]
for tr in tbl.findall("w:tr", NS):
    if d.text(tr.findall("w:tc", NS)[0]) == "Supervision":
        tbl.remove(tr)
        break
else:
    raise KeyError("Supervision row")

# ------------------------------------------------------------------ C8 + K3: AI-use statement with versions
rep(125, "used ChatGPT (OpenAI) and Claude (Anthropic)", "used ChatGPT (OpenAI, GPT-5) and Claude (Anthropic, Claude Opus 5.5 "
         "and Claude Sonnet 5.5)")
rep(125, "Claude Code (Anthropic; Claude Sonnet and Opus models)", "Claude Code (Anthropic; Claude Opus 5.5 and Claude Sonnet 5.5)")
rep(125, "computed the re-analyses added in this version (scripts/paper_checks_v4.py)",
         "computed the re-analyses added in the last two versions (scripts/paper_checks_v4.py and scripts/paper_checks_v5.py)")

# ------------------------------------------------------------------ C3: test-suite count (pytest collection, 2026-10-19)
rep(202, "503 tests in 20 modules", "503 tests in 17 modules")

# ------------------------------------------------------------------ Figure 2: the v5 image said "rank by ρ(e, q)" and
# "(Eq. 6 packing)"; the text defines σ(e, q) in Eq. (4) and fact packing in Eq. (3). Redrawn in TikZ
# (paper/venues/common/fig2_flow.tex, rendered to fig2_flow.png) and shared with the venue LaTeX builds.
FIG2 = ROOT / "paper/venues/common/fig2_flow.png"
d.parts["word/media/image3.png"] = FIG2.read_bytes()
WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
blip = [b for b in d.body.iter(A + "blip") if b.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed") == "rId13"]
assert len(blip) == 1
drawing = next(a for a in blip[0].iterancestors() if a.tag == q("drawing"))
w_px, h_px = (int.from_bytes(FIG2.read_bytes()[16:20], "big"), int.from_bytes(FIG2.read_bytes()[20:24], "big"))
for ext in list(drawing.iter(WP + "extent")) + list(drawing.iter(A + "ext")):
    ext.set("cy", str(round(int(ext.get("cx")) * h_px / w_px)))

d.save(DST)
print("wrote", DST)
