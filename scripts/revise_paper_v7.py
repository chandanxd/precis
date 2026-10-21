"""Build Precis_paper_clean_plane_revised_v7.docx from v6: the reviewer-defence revision.

  backend/venv/bin/python scripts/revise_paper_v7.py
Changes: (1) the generator-replay wording (contexts are generator-independent, so a replay is a full run) and the third
generator family, gemma4:e4b (experiments/generator_family); (2) Appendix B compressed: the four SDH term definitions are
summarised in one paragraph and the exact piecewise formulas are left to backend/src/precis/pipeline/sdh.py;
(3) the long-document cohort (experiments/long_doc_cohort) and the narrowed framing; (4) the second judge labeller;
(5) the repaired rule G2 on a fresh long-document draw (experiments/long_doc_fixed_g). Numbers quoted below are asserted against the stored analyses. v6 is left untouched.
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from docx_tools import Doc, NS, q

SRC = ROOT / "paper/research-paper/Precis_paper_clean_plane_revised_v6.docx"
DST = ROOT / "paper/research-paper/Precis_paper_clean_plane_revised_v7.docx"
GF = json.loads((ROOT / "experiments/generator_family/analysis.json").read_text())
d = Doc(SRC)
P = d.orig                      # handles by v6 body index


def setp(i, text, lead=None):
    d.set_text(P[i], text, lead=lead); return P[i]


def rep(i, old, new):
    d.replace(P[i], old, new)


def cell_rep(tbl_i, first_cell, old, new):
    for tr in P[tbl_i].findall("w:tr", NS):
        tcs = tr.findall("w:tc", NS)
        if d.text(tcs[0]) == first_cell:
            for p in tcs[1].findall("w:p", NS):
                if old in d.text(p):
                    d.replace(p, old, new); return
    raise KeyError((tbl_i, first_cell, old))


# ------------------------------------------------------------------ checks: generator family
gm, qw = GF["gemma4:e4b"], GF["qwen3.5:9b"]
r1 = lambda x: round(x, 1)
assert gm["n"] == 200 and gm["em"]["G"] == 78
g = {a: (r1(v["diff_pp"]), round(v["p_mcnemar"], 3)) for a, v in gm["G_vs"].items()}
assert g == {"N_raw": (1.0, 0.791), "N_clean": (1.0, 0.86), "W": (-2.0, 0.219), "TC": (-2.5, 0.267), "H": (0.0, 1.0),
             "D": (6.5, 0.002), "F2": (-1.5, 0.581)}, g
q9 = {a: (r1(v["diff_pp"]), round(v["p_mcnemar"], 3)) for a, v in qw["G_vs"].items()}
assert q9["D"] == (7.0, 0.004) and q9["F2"] == (6.5, 0.004) and q9["N_clean"] == (-4.0, 0.185) and qw["em"]["G"] == 98

# ------------------------------------------------------------------ (1) generator wording and the third family
rep(71, "The last column replays the fixed contexts through a general-purpose generator, qwen3.5:9b, because "
        "qwen2.5-coder is a code model.",
        "The last column gives exact match when the same contexts are answered by a general-purpose generator, qwen3.5:9b, "
        "because qwen2.5-coder is a code model.")
setp(75, "Retrieval and packing make no model call, so each arm's context is the same whichever generator answers it, "
         "and answering the stored contexts with another generator is equivalent to running the whole pipeline with it. "
         "With qwen3.5:9b, G was +7.0 points above D (p = 0.004) and +6.5 above F2 (p = 0.004), and was not "
         "distinguishable from N_raw (−0.5, p = 1.00), N_clean (−4.0, p = 0.18), W (−1.0), TC (+0.0) or H (+0.0). A "
         "third generator from another family, gemma4:e4b (exploratory, protocol-first), had lower exact match throughout "
         "(78 for G) and put G in the same position relative to the structure-keeping baselines: not distinguishable "
         "from N_raw (+1.0), N_clean (+1.0), W (−2.0, p = 0.22), TC (−2.5, p = 0.27) or H (0.0), and above D (+6.5, "
         "p = 0.002); only its lead over F2 was not reproduced (−1.5, p = 0.58). The position of G relative to the "
         "baselines therefore does not depend on the code-specialised generator.")
rep(113, "the primary generator is code-specialised (the 9b replay changes the generator but not the contexts)",
         "the primary generator is code-specialised (two general-purpose generators from two other model families, "
         "answering the same generator-independent contexts, leave G's position relative to the baselines unchanged)")
cell_rep(61, "Replay generator and judge", "qwen3.5:9b [50] (thinking off) replayed on fixed contexts",
         "qwen3.5:9b [50] and gemma4:e4b [51] (thinking off) on the stored, generator-independent contexts")
rep(123, "plus qwen3.5:9b for the replay and gemma4:12b for the equivalence judge",
         "plus qwen3.5:9b and gemma4:e4b for the second and third generator and gemma4:12b for the equivalence judge")
rep(123, "the protocols of the fresh-cohort, baseline and follow-up experiments",
         "the protocols of the fresh-cohort, baseline, follow-up, generator-family and long-document experiments")
rep(125, "ran the experiments of Sections 6.3–6.6 and the regeneration checks of Appendix B.2",
         "ran the experiments of Sections 6.3–6.6, the third-generator runs, the long-document cohort and the "
         "regeneration checks of Appendix B.2")
rep(125, "computed the re-analyses added in the last two versions (scripts/paper_checks_v4.py and scripts/paper_checks_v5.py)",
         "computed the re-analyses added in the last three versions (scripts/paper_checks_v4.py, scripts/paper_checks_v5.py "
         "and the analysis scripts of the generator-family and long-document experiments)")

# ------------------------------------------------------------------ (2) Appendix B: one paragraph for the four terms
rep(27, "(Appendix B, Eqs. (B1)–(B5))", "(Appendix B, Eq. (B1))")
rep(191, "scored with Eqs. (B1)–(B5)", "scored with Eq. (B1)")
setp(192, "The Semantic Density Heuristic combines four terms, each bounded in [0, 1], with equal weights "
          "(α = β = γ = δ = 0.25):")
SDH_TERMS = ("Entity relatedness E maps the cosine similarity of the subject and object embeddings, clipped at zero, "
             "piecewise-linearly onto [0.20, 1.0] (an affine map from [0.15, 0.85]) and multiplies it by 0.7 for each "
             "generic-pronoun slot. Verb informativeness I gives the head lemma a fixed tier (0.20 for be, 0.25 for have "
             "and do, 0.32 for other light verbs, 0.35 for other stop words, 0.50 for common reporting or perception verbs, "
             "0.85 for out-of-vocabulary verbs) and otherwise grows with the rarity of the lemma in the spaCy vocabulary, "
             "from 0.58 to 0.98, in the spirit of the frequency–rank law [52]. Uniqueness U is 1 when the largest cosine "
             "similarity m between the fact and any stored fact is at most 0.60, decreases smoothly up to m = 0.92 and is "
             "close to zero for near duplicates, with the same purpose as the redundancy term of maximal marginal "
             "relevance [53]. Adjunct density A rises from 0.20 for a fact without adjuncts to 1 for three weighted "
             "qualifiers (weights 1.2 for cause, 1.0 for time, 0.9 for location and 0.8 for other types). The exact "
             "piecewise definitions are in backend/src/precis/pipeline/sdh.py; the constants were set by hand and were "
             "neither tuned nor ablated.")
setp(194, SDH_TERMS)
for i in range(195, 202):                       # Eqs. (B2)-(B5) and their lead paragraphs
    d.delete(P[i])


# ------------------------------------------------------------------ (3) long-document cohort and narrowed framing
def long_doc_edits():
    import re
    LD = json.loads((ROOT / "experiments/long_doc_cohort/analysis.json").read_text())
    DG = json.loads((ROOT / "experiments/long_doc_cohort/g_context_diagnostic.json").read_text())
    hdr = json.loads((ROOT / "experiments/long_doc_cohort/manifest.jsonl").open().readline())
    man = [json.loads(l) for l in (ROOT / "experiments/long_doc_cohort/manifest.jsonl").open()][1:]
    A2, A1 = LD["2048"], LD["1024"]
    em2 = {a: v["em"] for a, v in A2["arms"].items()}; em1 = {a: v["em"] for a, v in A1["arms"].items()}
    aic = {a: v["answer_in_context"] for a, v in A2["arms"].items()}
    tok = {a: round(v["mean_tokens"]) for a, v in A2["arms"].items()}
    assert em2 == {"G": 44, "N": 71, "N_raw": 66, "W": 75, "TC": 83, "H": 76}, em2
    assert em1 == {"G": 43, "N": 75, "N_raw": 55, "W": 78, "TC": 79, "H": 76}, em1
    assert aic == {"G": 84, "N": 172, "N_raw": 140, "W": 168, "TC": 158, "H": 152}, aic
    assert (tok["G"], tok["TC"], tok["H"]) == (1049, 989, 1141), tok
    gv = A2["G_vs"]
    ci = {k: (r1(v["diff_pp"]), r1(v["ci99_pp"][0]), r1(v["ci99_pp"][1])) for k, v in gv.items()}
    assert ci == {"N": (-13.5, -23.0, -4.0), "N_raw": (-11.0, -20.0, -2.5), "W": (-15.5, -24.5, -6.5),
                  "TC": (-19.5, -28.5, -10.5), "H": (-16.0, -25.0, -7.0)}, ci
    assert max(v["p_holm5"] for v in gv.values()) < 0.0025 and not any(v["non_inferior_at_5pp"] for v in gv.values())
    assert r1(A1["G_vs"]["N_raw"]["diff_pp"]) == -6.0 and round(A1["G_vs"]["N_raw"]["p_mcnemar"], 2) == 0.10
    assert (hdr["pool"], hdr["counts"]["examples"], LD["doc_words_median"], LD["doc_est_tokens_median"]) == (902, 3357, 7093.0, 9625.0)
    assert sum(m["answer_in_table"] for m in man) == 33 and sum(m["answer_word_offset"] > 1575 for m in man) == 57
    st = A2["strata"]["answer_in_table"]["em"]
    assert (st["G"], min(v for k, v in st.items() if k != "G"), max(st.values())) == (7, 9, 14), st
    dg = DG["2048"]
    assert (dg["with_fact"], dg["with_table"], dg["lists_only"], dg["with_reference_or_navigation_boilerplate"]) == (0, 118, 82, 107)
    holm = lambda p: "< 0.001" if p < 0.001 else "%.3f" % p

    # ---- renumber Tables 7-11 -> 8-12 (a new Table 7 follows Table 6)
    paras = list(d.body.iter(q("p")))
    for n in (11, 10, 9, 8, 7):
        for p in paras:
            while re.search(r"\bTable %d\b" % n, d.text(p)):
                d.replace(p, "Table %d" % n, "Table %d" % (n + 1))

    # ---- Section 6.4: the long-document cohort, new Table 7
    rep(77, "Two exploratory experiments therefore make the ceiling bind.",
            "Two exploratory experiments therefore make the ceiling bind, and a third, protocol-first cohort uses full pages "
            "(below).")
    body_t, cap_t = P[80], P[79]
    p1 = d.clone_after(P[81], body_t, [("Long documents. ", {"bold": True}), (
        "Because MRQA cuts every page to at most 800 words, a third cohort was drawn under a protocol fixed before the "
        "draw, with the primary family and a 5-point non-inferiority margin stated in advance: 200 questions from the full "
        "development pages of Natural Questions v1.0 [44] whose page contains a table and at least 3,000 words of text, "
        "excluding every question used before (902 eligible questions among 3,357 examples; seed 42). The median page had "
        "7,093 words (9,625 estimated tokens), so the 2,048 ceiling covered about a fifth of it; the answer lay inside a "
        "table for 33 questions and beyond the first 1,575 words, which whole-document truncation can reach, for 57. "
        "Arms G, N, N_raw, W, TC and H were run as before with qwen2.5-coder:7b and the concise prompt at ceilings of "
        "2,048 (primary) and 1,024 estimated tokens. Table 7 gives the results.", {"bold": False})])
    rows = [["G (guarded priority)", "44", "84", "1,049", "reference", "—", "43"]]
    names = {"N": "N (chunks, stripped)", "N_raw": "N_raw (chunks, markup)", "W": "W (whole doc, truncated)",
             "TC": "TC (table-aware chunks)", "H": "H (hybrid, table-aware)"}
    for a in ("N", "N_raw", "W", "TC", "H"):
        d_, lo, hi = ci[a]
        rows.append([names[a], str(em2[a]), str(aic[a]), "{:,}".format(tok[a]),
                     "%+.1f [%.1f, %.1f]" % (d_, lo, hi), holm(gv[a]["p_holm5"]), str(em1[a])])
    rows = [[c.replace("-", "−") if re.match(r"^[+\-\[]", c) or "[" in c else c for c in r] for r in rows]
    tbl = d.make_table(P[78], ["Arm (long documents)", "EM /200 at 2,048", "Answer in context", "Mean tokens",
                               "G − arm, EM pp [99% CI]", "Holm p", "EM /200 at 1,024"],
                       rows, [2600, 1050, 1050, 950, 1900, 850, 1050])
    p1.addnext(tbl)
    cap = d.clone_after(tbl, cap_t, [("Table 7: ", {"bold": True}), (
        "Long-document cohort (N = 200 full Natural Questions pages, median 7,093 words): exact match, contexts containing "
        "an answer string and mean estimated tokens at the 2,048 ceiling, the exact-match difference of G from each arm "
        "with its 99% bootstrap interval and Holm-adjusted McNemar p, and exact match at 1,024. qwen2.5-coder:7b, concise "
        "prompt.", {"bold": False})])
    p2 = d.clone_after(cap, body_t, [(
        "When the ceiling bound on long pages, G was the worst arm: 44 of 200 exact matches against 66 to 83 for the five "
        "baselines, 11.0 to 19.5 points behind each of them (Holm p ≤ 0.002), so non-inferiority failed against all five at "
        "the pre-specified margin. At 1,024 the picture was the same (43 against 55 to 79), except that the gap to "
        "raw-markup chunks was not significant (−6.0 points, p = 0.10). Table-aware chunks were best (83 at 2,048, with a "
        "smaller context than G's). The loss arose before generation: an answer string was in only 84 of G's 200 contexts, "
        "against 140 to 172 for the baselines, and G was behind even on the 33 questions whose answer lay in a table "
        "(7 correct against 9 to 14).", {})])
    d.clone_after(p2, body_t, [("Why G fails on full pages. ", {"bold": True}), (
        "A descriptive look at G's contexts, made after the results were known, shows the mechanism. None of G's 200 "
        "contexts contained a prose fact: on a single document, packing any table or list suppresses every fact of that "
        "document (Section III), and full pages offer many lists. 82 contexts held lists only, and 107 contained "
        "reference-list, category or media-link text that the navigation filter, designed on MRQA's extracts, did not "
        "remove; G also left about half of the budget unused (1,049 estimated tokens on average). Structure-first packing "
        "with same-document suppression is therefore unsuitable for long single documents, and table-aware chunking keeps "
        "the benefit of native tables without that failure. The replays through other generators that the protocol listed "
        "as exploratory were not run, because the deficit lies in what the contexts contain, which does not depend on the "
        "generator.", {"bold": False})])

    # ---- framing: abstract, contributions, inference plan, stage loss, discussion, limitations, conclusions
    setp(4, "Retrieval-augmented generation on local hardware must fit evidence into a small context, and documents whose "
            "answers sit in tables raise the question of how much of their structure to keep. We study it with Précis, an "
            "offline pipeline that keeps HTML tables and lists in native form and packs them under an estimated-token "
            "ceiling with a guarded structural-priority rule (G). On short table-bearing pages (MRQA Natural Questions), "
            "rewriting tables as extracted sentences cut exact match (EM) to 14.0%, against 49.5% for native tables, but on "
            "a fresh protocol-first cohort G (48.0% EM) was only level with cheap structure-keeping baselines (raw-markup, "
            "table-aware and hybrid chunks and whole-document Markdown, 47.0 to 49.0%), with each of three generators from "
            "three model families. On 200 full Wikipedia pages (median 7,093 words), where the 2,048-token ceiling binds, G "
            "was the worst arm (22.0% EM against 33.0 to 41.5%, every difference significant): structure-first packing "
            "filled the context with lists, suppressed every prose fact, and let the answer reach only 84 of 200 contexts. "
            "The system's fact-only configuration also trailed plain chunks. In a 2×2 prompt experiment a short-answer "
            "format raised EM by 25.0 to 36.5 points while an LLM judge (92% and 97% agreement with two independent "
            "human labellers) saw gains of 1.5 to 12.0 points, and an “Insufficient information” line made the code-specialised "
            "generator abstain on answerable contexts. Keeping table structure matters, table-aware chunking is the robust "
            "way to keep it, and strict-match comparisons conflate answer format with accuracy.", lead="Abstract: ")
    rep(10, "and exploratory ceiling sweeps over single documents and five-document corpora;",
            "exploratory ceiling sweeps over single documents and five-document corpora, and a protocol-first cohort of "
            "full Wikipedia pages on which the ceiling binds;")
    rep(60, "Everything else, namely the ceiling sweeps",
            "(e) On the long-document cohort (Section 6.4) the primary family (exact match at the 2,048 ceiling; G against "
            "N, N_raw, W, TC and H; non-inferiority at a 5-point margin by 99% bootstrap intervals, and two-sided exact "
            "McNemar with Holm) and the margin were fixed in a protocol before the cohort was drawn. Everything else, "
            "namely the ceiling sweeps")
    rep(100, "and that is where packing, not generation, decides the outcome.",
             "and that is where packing, not generation, decides the outcome. On full pages the same holds at 2,048: an "
             "answer string reached 84 of G's contexts against 140 to 172 for the other arms (Table 7).")
    rep(109, "the packing rule matters less.", "structure-first packing does not help.")
    rep(109, "its lead over plain chunking did not survive correction.",
             "its lead over plain chunking did not survive correction. On full pages, where the ceiling bound throughout, "
             "structure-first packing was clearly harmful (Section 6.4).")
    rep(109, "For short documents, passing the document as Markdown or using table-aware chunks serves as well as G.",
             "For short documents, passing the document as Markdown or using table-aware chunks serves as well as G; for "
             "long ones, table-aware chunks are clearly better.")
    rep(113, "(1) All cohorts come from one source, MRQA Natural Questions, whose documents are short (at most 800 words) "
             "and largely Wikipedia pages with short answers; the ceiling rarely binds, no long or multi-row-reasoning "
             "documents were tested, and the five-document corpora use random distractors.",
             "(1) All cohorts come from Natural Questions (Wikipedia pages with short answers); all but one use MRQA's "
             "extracts of at most 800 words, on which the ceiling rarely binds; the long-document cohort has a single "
             "generator, no multi-row-reasoning questions were tested, and the five-document corpora use random "
             "distractors.")
    rep(113, "(3) The non-inferiority margin was chosen after the fresh-cohort results,",
             "(3) The non-inferiority margin of Section 6.3 was chosen after the fresh-cohort results (that of the "
             "long-document cohort was fixed before it was drawn),")
    rep(115, "and it lost when the ceiling was cut to 256 tokens; its smaller context holds only against the authors' own "
             "earlier pipeline.",
             "and it lost when the ceiling was cut to 256 tokens; its smaller context holds only against the authors' own "
             "earlier pipeline. On full Wikipedia pages, where the ceiling binds, it was the worst arm (22.0% EM against "
             "33.0 to 41.5%), because structure-first packing with same-document suppression filled the context with lists "
             "and dropped every prose fact; table-aware chunking was best.")
    rep(115, "On documents of this kind keeping structure matters, simple structure-keeping baselines are hard to beat, and "
             "strict-match comparisons need an equivalence measure and controlled prompts.",
             "Keeping table structure matters, table-aware chunking is the robust way to keep it, and strict-match "
             "comparisons need an equivalence measure and controlled prompts.")
    rep(116, "(i) long, table-heavy documents and table-and-text benchmarks such as NQ-Tables [21] and OTT-QA [22], with "
             "same-domain distractors and a cross-encoder reranker; (ii) row-level truncation for G under small ceilings and "
             "a token estimate calibrated against the generator's tokenizer;",
             "(i) table-and-text benchmarks such as NQ-Tables [21] and OTT-QA [22], same-domain distractors and a "
             "cross-encoder reranker; (ii) for G, a boilerplate-aware structural filter, per-element rather than "
             "per-document fact suppression and row-level truncation, tested on full pages, and a token estimate calibrated "
             "against the generator's tokenizer;")
    cell_rep(61, "Data source", "MRQA 2019 [43] version of Natural Questions [44], development split",
             "MRQA 2019 [43] version of Natural Questions [44], development split; full NQ v1.0 development pages for the "
             "long-document cohort")
    rep(123, "development split. The generators",
             "development split, and, for the long-document cohort, from the full Natural Questions v1.0 development pages "
             "(Hugging Face release google-research-datasets/natural_questions). The generators")


def labeller_edits():
    """Second, independent labeller of the answer-equivalence judge (scripts/score_judge_validation_B.py)."""
    JB = json.loads((ROOT / "experiments/prompt_validation/followup/judge_validation_B.json").read_text())
    jb, ab, ja = JB["judge_vs_B"], JB["A_vs_B"], JB["judge_vs_A"]
    assert (jb["agree"], jb["n"], round(100 * jb["agreement"], 1), round(jb["cohen_kappa"], 2)) == (83, 86, 96.5, 0.93), jb
    assert [round(100 * x) for x in jb["wilson95"]] == [90, 99] and JB["B_hard"] == 14
    assert (ab["agree"], ab["n"]) == (76, 76) and (ja["agree"], ja["n"]) == (83, 90)
    rep(95, "With one labeller and 90 outputs the judged counts are a supporting measure,",
            "A second author, who saw neither the first labels nor the verdicts, labelled the same 100 outputs (14 marked hard "
            "to tell): the judge agreed with this labeller on 83 of 86 (96.5%, Wilson 95% interval 90–99%; κ = 0.93), and the "
            "two labellers agreed on all 76 outputs that both labelled. With two labellers and at most 90 scored outputs each, "
            "the judged counts are a supporting measure,")
    rep(93, "The judge agreed with a human label on 92% of 90 audited outputs (Section 6.6).",
            "The judge agreed with two independent human labellers on 92% and 97% of the outputs each could label "
            "(Section 6.6).")
    rep(113, "The equivalence judge is a single local model checked by one labeller on 90 outputs",
             "The equivalence judge is a single local model checked by two labellers on 100 outputs")
    rep(116, "a larger, multi-labeller validation of the equivalence judge", "a larger validation of the equivalence judge")


def g2_edits():
    """Repaired rule G2 on a fresh long-document draw (experiments/long_doc_fixed_g)."""
    F = json.loads((ROOT / "experiments/long_doc_fixed_g/analysis.json").read_text())
    em = {a: v["em"] for a, v in F["arms"].items()}; aic = {a: v["answer_in_context"] for a, v in F["arms"].items()}
    h1, h2, sec = F["H1_G2_vs_G"], F["H2_G2_vs_TC"], F["secondary"]
    assert em == {"G": 35, "G2": 67, "TC": 63, "W": 69, "N": 61}, em
    assert (aic["G"], aic["G2"], round(F["arms"]["G2"]["mean_tokens"])) == (70, 158, 1958)
    assert (r1(h1["diff_pp"]), h1["x_only"], h1["y_only"], [r1(x) for x in h1["ci_pp"]]) == (16.0, 38, 6, [10.0, 22.5]) and h1["p_holm2"] < 0.001
    assert (r1(h2["diff_pp"]), [r1(x) for x in h2["ci_pp"]], h2["non_inferior_at_5pp"]) == (2.0, [-4.5, 9.0], True)
    assert (r1(sec["W"]["diff_pp"]), round(sec["W"]["p_mcnemar"], 2), r1(sec["N"]["diff_pp"]), round(sec["N"]["p_mcnemar"], 2)) == (-1.0, 0.88, 3.0, 0.45)
    assert (F["g2_contexts_with_fact"], F["g_contexts_with_fact"]) == (200, 0)
    why = next(p for p in d.body.iter(q("p")) if d.text(p).startswith("Why G fails on full pages."))
    d.clone_after(why, P[80], [("Repair on a fresh draw. ", {"bold": True}), (
        "The diagnostic points to two changes, which were tested on questions not used to design them, under a protocol "
        "written before a second draw of 200 eligible full pages (none shared with the first; seed 43). The repaired rule G2 "
        "suppresses only facts whose subject and object both occur in the packed structural text, not every fact of the page, "
        "and skips a structural candidate when at least 30% of its lines are references or media and external links. On this "
        "draw G2 had 67 exact matches against 35 for G (+16.0 points, 38 against 6 discordant cases, Holm p < 0.001, 95% "
        "interval +10.0 to +22.5) and was non-inferior to table-aware chunks at the 5-point margin (63; +2.0 points, 97.5% "
        "interval −4.5 to +9.0); it was level with whole-document Markdown (69; −1.0, p = 0.88) and stripped chunks (61; +3.0, "
        "p = 0.45). Every G2 context contained prose facts (none of G's did), an answer string reached 158 of its contexts "
        "against 70 for G, and G2 used nearly the whole budget (1,958 estimated tokens on average). G2 was designed after the "
        "first long-document results and is tested on one further draw from the same source, so it is a repaired variant, not a "
        "separately tuned method.", {"bold": False})])
    rep(4, "and let the answer reach only 84 of 200 contexts.",
           "and let the answer reach only 84 of 200 contexts; two changes suggested by this failure (per-element instead of "
           "per-document fact suppression, and a reference-list filter) raised EM on a fresh draw of 200 pages from 17.5% to "
           "33.5%, non-inferior to table-aware chunking.")
    rep(4, "Keeping table structure matters, table-aware chunking is the robust way to keep it,",
           "Keeping table structure matters, packing it first must not crowd out prose,")
    rep(60, "and the margin were fixed in a protocol before the cohort was drawn.",
            "and the margin were fixed in a protocol before the cohort was drawn; the repaired rule G2 was tested on a second, "
            "fresh draw under its own protocol (G2 against G, and non-inferiority to TC at 5 points by a 97.5% interval, Holm "
            "over the two).")
    rep(109, "structure-first packing was clearly harmful (Section 6.4).",
             "structure-first packing was clearly harmful, and a repaired variant that keeps prose facts (G2) restored parity "
             "with table-aware chunks on a fresh draw (Section 6.4).")
    rep(109, "for long ones, table-aware chunks are clearly better.",
             "for long ones, table-aware chunks or the repaired G2 are clearly better than G.")
    rep(113, "the long-document cohort has a single generator,",
             "the long-document cohorts have a single generator, G2 was designed after the first of them and checked on one "
             "further draw from the same source,")
    rep(115, "and dropped every prose fact; table-aware chunking was best.",
             "and dropped every prose fact; table-aware chunking was best, and a repaired rule that keeps prose (G2) gained "
             "16.0 points over G on a fresh draw and was non-inferior to it.")
    rep(115, "Keeping table structure matters, table-aware chunking is the robust way to keep it,",
             "Keeping table structure matters, packing it first must not crowd out prose,")
    rep(116, "(ii) for G, a boilerplate-aware structural filter, per-element rather than per-document fact suppression and "
             "row-level truncation, tested on full pages, and a token estimate",
             "(ii) testing the repaired rule G2 on other sources and refining its reference-list filter, row-level truncation "
             "for small ceilings, and a token estimate")
    rep(123, "generator-family and long-document experiments", "generator-family, long-document and repaired-G experiments")
    rep(125, "the long-document cohort and the", "the long-document and repaired-G cohorts and the")


long_doc_edits()
labeller_edits()
g2_edits()
d.save(DST)
print("wrote", DST)
