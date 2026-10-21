"""Build Precis_paper_clean_plane_revised_v3.docx from v2: one scoring rule for every cohort, held-out coverage reported
under identical conditions, stage naming, and (if present) the measured negation-marker effects.

  backend/venv/bin/python scripts/revise_paper_v3.py
Numbers come from results/paper_checks/unified_scoring.json, experiments/prompt_validation/followup/analysis.json and
results/paper_checks/negation_AE_NQ_rerun/summary.json. v2 is left untouched.
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from docx_tools import Doc, NS, q

SRC = ROOT / "paper/research-paper/Precis_paper_clean_plane_revised_v2.docx"
DST = ROOT / "paper/research-paper/Precis_paper_clean_plane_revised_v3.docx"
d = Doc(SRC)
paras = [p for p in d.body.iter(q("p"))]


def find(text):
    hits = [p for p in paras if text in d.text(p)]
    if len(hits) != 1:
        raise KeyError("%d paragraphs contain %r" % (len(hits), text))
    return hits[0]


def rep(old, new, anchor=None):
    d.replace(find(anchor or old), old, new)


def cell(old, new, anchor):
    """Replace a whole table-cell text; `anchor` is a text unique to the row (any cell) used to locate the row."""
    row = None
    for tr in d.body.iter(q("tr")):
        if anchor in " | ".join(d.text(tc) for tc in tr.iter(q("tc"))):
            row = tr; break
    assert row is not None, anchor
    for tc in row.iter(q("tc")):
        if d.text(tc) == old:
            d.replace(tc.find("w:p", NS), old, new); return
    raise KeyError((old, anchor))


# ------------------------------------------------------------------ 6.1 scoring rule (item 4)
p = find("Scoring rules differ by cohort and are not interchangeable.")
d.set_text(p, "Scoring is the same in every cohort. A prediction is correct for exact match if its normalised text equals the gold "
    "answer or any alternative answer that MRQA lists, and correct for containment if a normalised answer occurs in it at word "
    "boundaries (any match counts). The rule is implemented once (scripts/scoring.py). The 200-sample benchmark of Section 6.7 and "
    "the confirmatory and follow-up experiments of Section 6.6 were first scored against the single gold answer and have been "
    "recomputed with it: in the confirmatory experiment 3 of 800 exact-match outcomes and 9 of 800 containment outcomes changed, "
    "and in the benchmark the exact-match count of Précis v1 changed by one case (the table-bearing cohorts already used the rule "
    "and reproduce exactly). ROUGE-L, MiniLM cosine and BERTScore, and the reference answer shown to the equivalence judge, still "
    "use the single gold answer. Absolute values still differ between cohorts because documents, prompts and generators differ.")
rep("Exact match (EM), word-boundary containment,", "Exact match (EM) and word-boundary containment (gold answer or any MRQA alternative),")

# ------------------------------------------------------------------ 6.6 stage naming (item 15)
rep("A staged investigation preceded the pre-specified test.", "A staged prompt-comparison investigation preceded the pre-specified test (its Stages A–C are unrelated to the stages of the table-decompilation runs in the project records).")
rep("the exploratory Stage C result (containment 48%)", "the exploratory prompt-comparison Stage C result (containment 48%)")

# ------------------------------------------------------------------ 6.6 confirmatory tables recomputed
U = json.load(open(ROOT / "results/paper_checks/unified_scoring.json"))
C = U["confirmatory_cells"]
cell("21 → 44", "21 → 45", "qwen2.5-coder:7b / Naive RAG | 21")
cell("0.67 → 0.50", "0.68 → 0.51", "qwen2.5-coder:7b / Naive RAG | 21")
cell("0.52 → 0.40", "0.53 → 0.41", "qwen2.5-coder:7b / Précis v3 | 18")
cell("11 → 49", "11 → 51", "qwen3.5:4b / Naive RAG | 11")
cell("0.74 → 0.64", "0.75 → 0.66", "qwen3.5:4b / Naive RAG | 11")
cell("0.60 → 0.52", "0.61 → 0.53", "qwen3.5:4b / Précis v3 | 6")
rep("(N = 100 per cell; EM in correct answers out of 100).", "(N = 100 per cell; EM in correct answers out of 100). EM and containment use the gold answer or any MRQA alternative; ROUGE-L, MiniLM and BERTScore use the single gold answer.")
rep("Containment moved from 0.60 to 0.52", "Containment moved from 0.61 to 0.53")
rep("11% to 49%, adjusted p = 1.09 × 10⁻¹¹", "11% to 51%, adjusted p = 2.73 × 10⁻¹²")
rep("21% to 44%, p = 5.65 × 10⁻⁶", "21% to 45%, p = 8.05 × 10⁻⁷")
rep("−0.01 with a 95% bootstrap interval of [−0.10, +0.08] for qwen3.5:4b and −0.06 with [−0.15, +0.03] for qwen2.5-coder:7b",
    "−0.03 with a 95% bootstrap interval of [−0.13, +0.07] for qwen3.5:4b and −0.07 with [−0.15, +0.01] for qwen2.5-coder:7b")
rep("adjusted p = 0.052, 0.359, 0.052 and 0.193", "adjusted p = 0.052, 0.286, 0.052 and 0.193")
rep("(for example 49 against 43 correct answers for qwen3.5:4b under the concise prompt)", "(for example 51 against 43 correct answers for qwen3.5:4b under the concise prompt)")
rep("(22 against 7, 16 against 6, 18 against 4 and 17 against 5 discordant questions; exact McNemar p = 0.008, 0.053, 0.004 and 0.017,",
    "(23 against 8, 16 against 6, 18 against 4 and 18 against 5 discordant questions; exact McNemar p = 0.011, 0.052, 0.004 and 0.011,")
rep("(9 against 6, 13 against 4, 8 against 3 and 13 against 7; p = 0.61, 0.049, 0.23 and 0.26)", "(9 against 6, 13 against 3, 8 against 3 and 15 against 7; p = 0.61, 0.021, 0.23 and 0.13)")
# Table 9 EM entries (first number of each cell)
cell("21 / 84 / 2", "21 / 84 / 2", "qwen2.5-coder:7b / Naive RAG | 21 / 84")
cell("23 / 56 / 36", "24 / 56 / 36", "qwen2.5-coder:7b / Naive RAG | 21 / 84")
cell("53 / 79 / 4", "55 / 79 / 4", "qwen2.5-coder:7b / Naive RAG | 21 / 84")
cell("44 / 64 / 22", "45 / 64 / 22", "qwen2.5-coder:7b / Naive RAG | 21 / 84")
cell("49 / 81 / 3", "51 / 81 / 3", "qwen3.5:4b / Naive RAG | 11 / 77")
cell("49 / 78 / 9", "51 / 78 / 9", "qwen3.5:4b / Naive RAG | 11 / 77")
rep("raised exact match by 21 to 38 points in all eight contrasts", "raised exact match by 21 to 40 points in all eight contrasts")
rep("from 53 to 44 with Naive RAG and from 43 to 35 with Précis v3 (unadjusted exploratory p = 0.012 and 0.021; Holm p = 0.08 and 0.11)",
    "from 55 to 45 with Naive RAG and from 43 to 35 with Précis v3 (unadjusted exploratory p = 0.006 and 0.021; Holm p = 0.044 and 0.11)")
rep("Concise prompting raised exact match by 17 to 38 points", "Concise prompting raised exact match by 17 to 40 points")
rep("which is the abstention confound that the follow-up above separates.", "which is the abstention confound that the follow-up above separates. The 60 audited generations are all from qwen3.5:4b with Précis v3, whose exact-match outcomes are identical under the scoring rule of Section 6.1.")

# ------------------------------------------------------------------ 6.7 benchmark: v1 exact match under the unified rule
rep("also raised exact match from 14.0% to 18.0% (question-level 95% interval for the exact-match gain +1.0 to +7.7 points; McNemar p = 0.0078)",
    "also raised exact match from 14.5% to 18.0% (+3.5 points, 8 cases gained and 1 lost; question-level 95% interval +0.5 to +7.4 points; exact McNemar p = 0.039)")
cell("0.140", "0.145", "v1 (initial baseline)")

# ------------------------------------------------------------------ 6.7 held-out coverage under identical conditions (item 7)
p = find("To check whether the level of coverage is specific to the development cases")
d.set_text(p, "To check whether the level of coverage is specific to the development cases, the current extractor was run without the "
    "coreference stage, under one procedure, on the 200 development documents and on documents from the same development file that "
    "were not among them (their questions and documents excluded): one random record per distinct question, seed 42, and a case "
    "counts as covered when any extracted fact contains any MRQA answer alias (scripts/paper_checks_heldout_coverage.py). Coverage "
    "was 182/200 (91.0%; question-level 95% interval 85.6–95.5%) on the development documents, 175/200 (87.5%; 83.0–92.0%) on 200 "
    "held-out documents and 866/1,000 (86.6%; 84.4–88.7%) on 1,000 held-out documents. The held-out level of about 87% is therefore "
    "stable, and the gap between development and held-out documents under identical conditions is about 4 points. These figures are "
    "not directly comparable with the 177/200 (88.5%) of Table 11, which is the frozen v3 extractor with the coreference stage. "
    "Versions v1 to v2 were not re-run on the held-out documents, so this check supports the level of v3 coverage and not the size "
    "of the improvement over v1.")

# ------------------------------------------------------------------ availability + AI-use statements
rep("The annotation sheets, labels and scoring script of Sections 6.6 and 6.8 are in the repository.",
    "The annotation sheets, labels and scoring script of Sections 6.6 and 6.8 are in the repository, and the exact-match and containment rule used in every table is implemented once in scripts/scoring.py.")
rep("to run the additional experiments of Sections 6.3–6.6", "to run the additional experiments of Sections 6.3–6.6 and the regeneration checks of Appendix B.4, to re-score every cohort under one scoring rule")

# Figure 6 regenerated under the unified scoring rule (scripts/plot_figure_6_prompt_effect.py)
d.parts["word/media/image6.png"] = (ROOT / "paper/figures/figure_6_prompt_effect.png").read_bytes()

exec(open(ROOT / "scripts/revise_paper_v3_negation.py").read()) if (ROOT / "results/paper_checks/negation_AE_NQ_rerun/summary.json").exists() and (ROOT / "scripts/revise_paper_v3_negation.py").exists() else None
d.save(DST); print("saved", DST)
