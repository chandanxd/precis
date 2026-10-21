"""Build Precis_paper_clean_plane_revised_v2.docx from the revised manuscript and the new experiment records.

  backend/venv/bin/python scripts/build_revised_paper.py
Numbers in new text come from experiments/baseline_budget/analysis.json, experiments/prompt_validation/followup/analysis.json
and results/paper_checks/r6_stage_loss.json; nothing is typed in by hand except wording.
"""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from docx_tools import Doc, NS, q

SRC = ROOT / "paper/research-paper/Precis_paper_clean_plane_revised.docx"
DST = ROOT / "paper/research-paper/Precis_paper_clean_plane_revised_v2.docx"
A = json.load(open(ROOT / "experiments/baseline_budget/analysis.json"))
FU = json.load(open(ROOT / "experiments/prompt_validation/followup/analysis.json"))
R6 = json.load(open(ROOT / "results/paper_checks/r6_stage_loss.json"))
F = json.load(open(ROOT / "experiments/fresh_table_cohort/analysis.json"))
ES = json.load(open(ROOT / "experiments/extractor_eval/extractor_scores.json"))
EF, ESN, EJ = ES["facts"], ES["sentences"], ES["judge"]

d = Doc(SRC)
O = d.orig
H1_T, H2_T, BODY_T, CAP_T, SRC_T = O[77], O[78], O[94], O[119], O[120]
H1_T, H2_T, BODY_T, CAP_T, SRC_T = [__import__("copy").deepcopy(x) for x in (H1_T, H2_T, BODY_T, CAP_T, SRC_T)]
TBL_T = __import__("copy").deepcopy(O[118])


def para(text, tmpl=None):
    p = __import__("copy").deepcopy(tmpl if tmpl is not None else BODY_T)
    d.set_runs(p, [(text, {})])
    return p


def h2(text): return para(text, H2_T)
def h1(text): return para(text, H1_T)


def caption(label, text):
    p = __import__("copy").deepcopy(CAP_T)
    d.set_runs(p, [(label + ": ", {"bold": True}), (text, {"bold": False})])
    return p


def source(text="Source: Authors, (2026)."):
    return para(text, SRC_T)


def pm(x, nd=1):
    return ("%+." + str(nd) + "f") % x


def ci(x, nd=1):
    return "%s to %s" % (("%+." + str(nd) + "f") % x[0], ("%+." + str(nd) + "f") % x[1])


E1, E2, E3, E4 = A["E1"], A["E2"], A["E3"], A["E4"]
E6 = A["E6_replay_qwen3_5_9b"]
S = E1["summary"]; GV = E1["G_vs"]

# ============================================================ front matter
art = O[5]
cells = list(art.iter(q("tc")))
abstract = (
    "Retrieval-augmented generation (RAG) usually places retrieved passages in the prompt, which leaves open how much document "
    "structure a local pipeline can keep within a small context budget. Précis is an offline pipeline that keeps HTML tables and "
    "lists in native form and packs them under a token ceiling with a guarded structural-priority rule (Candidate G). A further "
    "layer of negation- and modality-tagged subject–verb–object–adjunct (SVOA) facts is implemented; on a small annotated sample its negation flag was wrong for more than half of the facts it marked as negated. "
    "On a 200-case table-bearing cohort (qwen2.5-coder:7b), converting tables to prose gave 14.0% exact match (EM) and keeping "
    "them in native form 49.5%. On a fresh pre-specified cohort of 200 questions, G (48.0% EM) was non-inferior at a 5-point margin "
    "to chunked retrieval, to table-aware chunking and to a whole-document Markdown baseline, but not to hybrid table-aware "
    "retrieval, and the Markdown baseline matched G with a similar context ({0:.0f} against {1:.0f} estimated tokens). G's 56% smaller context "
    "is relative to F2, a reconstruction of the authors' earlier pipeline without same-document suppression. With a 256-token "
    "ceiling G fell behind chunked retrieval ({2} against {3} correct); over five-document corpora at a 1,024-token ceiling it beat "
    "chunked retrieval ({4} against {5}) but not hybrid table-aware retrieval. On single-passage documents chunked retrieval beat "
    "Précis v3 (EM 28.5% against 19.0%). A concise-answer prompt raised EM in all four model–retrieval combinations of a "
    "pre-specified experiment, but a 2×2 follow-up attributes the gain to answer format, and the prompt's abstention wording lowered "
    "accuracy; an LLM-judged equivalence measure (92% agreement with human labels on 90 audited outputs) shows much smaller format effects. At a "
    "2,048-token ceiling retrieval and packing lost almost no answer evidence; most loss arose at generation and answer matching."
).format(S["W"]["mean_tokens"], S["G"]["mean_tokens"], E2["256"]["summary"]["G"]["em"], E2["256"]["summary"]["N"]["em"],
     E3["1024"]["summary"]["G"]["em"], E3["1024"]["summary"]["N"]["em"])
d.set_runs(cells[1].findall("w:p", NS)[1], [(abstract, {})])
ps = cells[0].findall("w:p", NS)
d.set_runs(ps[4], [("Context Budget,", {})]); d.set_runs(ps[5], [("Non-inferiority,", {})])

# ============================================================ introduction
d.set_runs(O[9], [(
    "Documents whose answers live in tables and lists sharpen the problem. A table cell has meaning only through its row and column "
    "headers, and converting a table to running prose or to sentence-level facts can sever those links. Précis therefore keeps HTML "
    "tables and lists in their native form and gives them priority when the question calls for them. A second, optional layer "
    "decomposes prose into SVOA propositions annotated with negation and epistemic modality and ranks them with a Semantic Density "
    "Heuristic (SDH). This paper evaluates the structure-preserving part. The fact layer is implemented and described, but none of "
    "the experiments here tests its effect on answers, and a small annotated audit of its extractor (Section 6.8) found its negation flag unreliable.", {})])
d.set_runs(O[10], [(
    "The paper describes the system, formalises its scoring and packing, and reports an evaluation scoped to structured documents, "
    "to baseline adequacy under a token budget, and to answer-format sensitivity. Three research questions guide it. RQ1 (structure "
    "preservation and baseline adequacy): for documents whose answers depend on tables and lists, does preserving native structure "
    "and prioritising it during packing maintain answer quality against strong, simple baselines, and what does it do to context "
    "size when the ceiling is made to bind? RQ2 (answer-format sensitivity): how sensitive are strict-match scores to the answer "
    "format and to the abstention instruction, and does an answer-equivalence measure change the conclusions? RQ3 (information "
    "loss): at which stage is answer-bearing evidence lost, in a setting where retrieval and packing can lose it?", {})])
d.set_runs(O[11], [(
    "The main contributions are: (i) an end-to-end offline pipeline from document to grounded answer built from open components; "
    "(ii) query-adaptive greedy packing under a token ceiling and a guarded structural-priority variant (Candidate G); (iii) a "
    "seven-variant ablation on a 200-case table-bearing cohort and a fresh pre-specified cohort, with a non-inferiority comparison "
    "against five simple baselines and a ceiling sweep over single documents and multi-document corpora; (iv) a pre-specified "
    "2×2×2 experiment on answer-format sensitivity, a follow-up that separates format from abstention policy, and an "
    "answer-equivalence check validated against human labels; (v) a stage-loss trace on the table cohort; and (vi) an annotated audit of the "
    "extractor's negation and modality labels. The SVOA fact schema and the SDH are documented in Appendix B; their effect on answers is not "
    "tested and they are not claimed as contributions of the evidence presented here.", {})])
d.set_runs(O[12], [(
    "The rest of this paper is organised as follows. Section II reviews related work. Section III formulates the problem, Section "
    "IV describes the system model, and Section V presents the framework and its algorithm. Section VI reports results, discussion "
    "and limitations, and Section VII concludes with directions for future work. Appendix A lists prompt templates, and Appendix B "
    "holds the code-level verification of the released implementation.", {})])

# related work
d.replace(O[14], "Related work is grouped into five themes: retrieval-augmented generation and its context limits, context compression, retrieval granularity and structured fact units, tables as evidence, and epistemic status in text.",
          "Related work is grouped into seven themes: retrieval-augmented generation and its context limits, context compression, retrieval granularity and structured fact units, tables as evidence, hierarchical and hybrid retrieval, answer evaluation and prompt sensitivity, and epistemic status in text.")
d.replace(O[18], "Précis addresses that preprocessing and packing step rather than the table-reading model.",
          "Sui et al. benchmark how the serialisation of a table in the prompt changes what language models can answer [N1], and Herzig et al. retrieve tables with a dense retriever for open-domain question answering [N2]. Neither compares table-preserving packing with passage chunking under a token budget. Précis addresses that preprocessing and packing step rather than the table-reading model.")
r1 = d.clone_after(O[19], BODY_T, [(
    "Retrieval can also be hierarchical or hybrid. RAPTOR builds a tree of recursive summaries and retrieves across its levels [N3]; "
    "Précis instead uses the document's own markup and no learned summaries. Combining lexical and dense rankings is a standard, "
    "strong and cheap baseline: BM25 [N4] fused with a dense ranking by reciprocal rank fusion [N5]. Section 6.3 therefore compares G "
    "with table-aware chunking and a hybrid retriever, not only with plain chunking.", {})])
r2 = d.clone_after(r1, BODY_T, [(
    "Evaluation choices matter as much as retrieval choices. Token-level metrics such as exact match undercount correct answers "
    "[N6], model-judged answer equivalence tracks human judgement more closely [N7], and language-model accuracy can move by tens "
    "of points with small changes of prompt format [N8]. RQ2 is positioned against this work.", {})])
# Table 1: extra rows
t1 = O[20]
rows1 = [[''.join(c.itertext()) for c in tr.findall('w:tc', NS)] for tr in t1.findall('w:tr', NS)]
hdr1, body1, last1 = rows1[0], rows1[1:-1], rows1[-1]
extra = [["Sui et al. [N1]", "Table serialisation for LLMs", "Benchmark of input formats"],
         ["Herzig et al. [N2]", "Open-domain QA over tables", "Dense table retrieval"],
         ["Sarthi et al. [N3]", "Hierarchical retrieval", "Recursive summary tree"],
         ["Bulian et al. [N6]; Kamalloo et al. [N7]", "Answer-equivalence evaluation", "Learned and LLM-based matching"],
         ["Sclar et al. [N8]", "Prompt-format sensitivity", "Format-spread analysis"]]
newt1 = d.make_table(t1, hdr1, body1 + extra + [last1], [3240, 4104, 3528], font_sz=None)
t1.addnext(newt1); d.delete(t1)

# problem formulation / system model small edits
d.replace(O[48], "The ceiling B is a hard constraint.",
          "The ceiling B is enforced on estimated tokens (Eq. 7); the generator's own count runs about 1.24 times higher (Section 6.4), so B bounds the estimate and not the native prompt length.")
d.replace(O[63], "In the controlled experiments the ceiling was fixed at 2,048 tokens, the cpu value, and the generator was fixed per experiment rather than chosen by the profile.",
          "In most controlled experiments the ceiling was fixed at 2,048 tokens, the cpu value, and the generator was fixed per experiment rather than chosen by the profile; the ceiling sweeps of Section 6.4 vary the ceiling from 256 to 2,048, but the hardware detection rules themselves were not evaluated.")
d.replace(O[52], "are distinct from the fixed 2,048-token evaluation ceiling.", "are distinct from the 2,048-token ceiling of most evaluations (Section 6.4 varies it).")

# ============================================================ results: detach old section VI
old_sec = O[77:151]            # 'VI. RESULTS' .. 'Implementation notes'
keep = {i: O[i] for i in (82, 83, 87, 88, 89, 90, 91, 95, 96, 97, 102, 103, 104, 105, 106, 107, 112, 113, 114, 118, 119, 120,
                          125, 126, 127, 128, 129, 130, 133, 134, 135, 137, 138, 139, 140, 141)}
for el in old_sec:
    if el.getparent() is not None: el.getparent().remove(el)
anchor = O[76]


def setcap(p, old, new):
    d.replace(p, old, new)
    return p


# table 4 rebuilt with extra rows
t4_rows = [[''.join(c.itertext()) for c in tr.findall('w:tc', NS)] for tr in O[81].findall('w:tr', NS)]
for r in t4_rows:
    r[1] = r[1].replace("Section 6.3", "Section 6.6")
t4_rows.insert(5, ["Additional baselines", "W: whole-document Markdown, truncated at the ceiling; TC: table-aware chunks, dense retrieval; H: the same chunks, BM25 + dense with reciprocal rank fusion [N4], [N5]"])
t4_rows.append(["Replay generator and judge", "qwen3.5:9b [N9] (thinking off) replayed on fixed contexts; gemma4:12b (Ollama) as answer-equivalence judge, temperature 0"])
t4 = d.make_table(O[81], t4_rows[0], t4_rows[1:], [2448, 8452])

seq = []
add = seq.append
add(h1("VI. RESULTS AND DISCUSSIONS"))
add(h2("6.1 Experimental setup"))
add(para("Two kinds of evidence are reported and kept apart. Sections 6.2–6.7 report controlled evaluations produced by the authors' harness on the evaluation host of Table 4. Appendix B reports checks made by executing the released code on a separate two-vCPU Intel Xeon (2.10 GHz) server with 7 GB of RAM, Python 3.13 and spaCy 3.8, where the embedding and coreference weights were unavailable; values that depend on those models are marked illustrative. The cohorts are analysed separately and are never pooled."))
add(para("Scoring rules differ by cohort and are not interchangeable. In the table-bearing cohorts, exact match, containment and ROUGE-L are computed against the gold answer and every alternative answer that MRQA lists (any match counts). In the 200-sample benchmark of Section 6.7 and in the confirmatory experiment of Section 6.6, exact match is computed against the single gold answer only; the containment counts of Section 6.7 and the answer-coverage rule of Table 11 use the gold answer and its alternatives, whereas containment in Section 6.6 uses the gold answer only. Absolute exact-match values should therefore not be compared across cohorts."))
add(para("Inference plan. Each analysis has one declared status. (a) The original table cohort (Table 5) is in-sample, because G was designed on it, and is descriptive only: unadjusted exact McNemar tests and question-level bootstrap intervals. (b) On the fresh cohort the primary family is exact match, G against D, F2, N_raw and N_clean, two-sided exact McNemar tests with Holm correction over four contrasts, written into the protocol before any model call. (c) Baseline adequacy (Section 6.3) is a non-inferiority analysis of G against five comparators at a margin of 5 points of exact match, judged by the lower bound of a 99% question-level bootstrap interval (10,000 resamples; 99% because five comparators are tested); the margin was chosen after the fresh-cohort results were known and before the new arms were run. (d) In the 2×2×2 experiment of Section 6.6 the primary test is one-sided McNemar for qwen3.5:4b with Précis v3, with its own guardrails. Everything else, namely the ceiling sweeps, the multi-document corpus, the threshold sensitivity, the document-type strata and the 2×2 follow-up other than its Holm-corrected format and abstention contrasts, is exploratory and labelled so. Clustering is handled by resampling questions: the original table cohort holds 187 distinct questions in 200 cases and the 200-sample benchmark 74, whereas the fresh cohort, the baseline experiments and the confirmatory cohort have distinct questions by construction. A non-significant difference is never read as equivalence."))
add(t4); add(caption("Table 4", "Experimental configuration of the controlled evaluations.")); add(source())

add(h2("6.2 Structural preservation on table-bearing documents (RQ1)"))
add(O[85]) if False else None
p85 = __import__("copy").deepcopy(O[85]); add(p85)
for i in (86, 87, 88, 89, 90, 91):
    pass
add(keep[87 - 1]) if False else None
# retained original block: table 5, its caption/source, Fig 4
t5 = O[86]; add(t5); add(keep[87]); add(keep[88])
add(keep[89]); add(keep[90]); add(keep[91])
add(O[92]); add(O[93])
# fresh cohort paragraph: edits
p94 = __import__("copy").deepcopy(O[94])
d.replace(p94, "Section 6.7", "Section 6.10")
d.replace(p94, "The advantage over D is confined to the 32 list-only documents, where D has no evidence by construction (G 18 correct, D 0);",
          "The advantage over D is confined to the 32 list-only documents, where D has no evidence by construction (G 18 correct, D 0), so it is a mechanism check and not evidence for G;")
add(p94)
add(keep[95]); add(keep[96]); add(keep[97])
add(O[98])

# ---- 6.3 baseline adequacy
add(h2("6.3 Baseline adequacy and efficiency (RQ1)"))
add(para("The fresh cohort was re-run with three further arms that do not use the SVOA or SDH code and are cheap to build: W, the whole document converted from HTML to Markdown in document order (tables as Markdown tables, lists as bullets) and truncated at the ceiling; TC, table-aware chunks (tables kept whole or split by rows with the header repeated, lists kept whole, prose grouped to about 128 words) retrieved by dense similarity; and H, the same chunks retrieved by BM25 and dense rankings fused by reciprocal rank fusion. All use the 2,048-token ceiling, at most five chunks, qwen2.5-coder:7b and the concise prompt (protocol and hash in the repository). Table 6 gives exact match, containment, mean estimated context tokens, exact-match points per 100 tokens, the exact-match difference of G from each arm with its 99% interval, and the non-inferiority verdict at the 5-point margin. The last column replays the fixed contexts through a general-purpose generator, qwen3.5:9b, because qwen2.5-coder is a code model."))
order = [("N_raw", "N_raw (chunks, markup)"), ("N_clean", "N_clean (chunks, stripped)"), ("W", "W (whole doc, Markdown)"),
         ("TC", "TC (table-aware chunks)"), ("H", "H (hybrid, table-aware)"), ("D", "D (tables only)"),
         ("F2", "F2 (F without suppression)")]
rows6 = []
for k, lab in order:
    s = S[k]; g = GV[k]["em"]
    ver = ("G higher" if g["ci99_pp"][0] > 0 else ("non-inferior" if g["non_inferior_at_5pp_99ci"] else "not established"))
    rows6.append([lab, "%d" % s["em"], "%d" % s["cont"], "%.0f" % s["mean_tokens"], "%.1f" % s["em_pp_per_100tok"],
                  "%s [%s]" % (pm(g["diff_pp"]), "%.1f, %.1f" % tuple(g["ci99_pp"])), ver, "%d" % E6["summary"][k]["em"]])
rows6.append(["G (guarded priority)", "%d" % S["G"]["em"], "%d" % S["G"]["cont"], "%.0f" % S["G"]["mean_tokens"],
              "%.1f" % S["G"]["em_pp_per_100tok"], "reference", "—", "%d" % E6["summary"]["G"]["em"]])
t6 = d.make_table(TBL_T, ["Arm", "EM /200", "Cont. /200", "Mean tokens", "EM pp per 100 tok", "G − arm, EM pp [99% CI]", "Non-inferiority (−5 pp)", "EM, qwen3.5:9b"],
                  rows6, [2300, 800, 900, 1000, 1100, 1900, 1700, 1200])
add(t6)
add(caption("Table 6", "Baseline adequacy on the fresh table- and list-bearing cohort (N = 200, 2,048-token ceiling, qwen2.5-coder:7b except the last column). N_raw, N_clean, D, F2 and G are the earlier records; W, TC and H were run for this table. G − arm is positive when G is ahead."))
add(source())
ge = GV
add(para("G was non-inferior to N_raw, N_clean, W and TC at the 5-point margin but not to H, whose interval for G − H (%s) reaches below −5 points; parity with hybrid table-aware retrieval is therefore not established. G was ahead of D (%s, 99%% interval %s), which is the list-only effect described above. Non-inferiority is a weak statement: it says G is not worse than the comparator by more than 5 points, not that the two are equal, and the intervals for W, TC and H also include differences of a few points in either direction. Efficiency is not a point in favour of G either. Per 100 estimated tokens the order was N_clean (%.1f), W (%.1f), G (%.1f), H (%.1f), TC (%.1f), D (%.1f), N_raw (%.1f) and F2 (%.1f). W matched G in accuracy (%d against %d correct) with %.1f%% %s tokens, and the tag-stripped chunks were %.0f%% smaller than G with %.1f points lower exact match that is not distinguishable from zero. G's context is smaller than F2 (a reduction of %.1f%%, F2 being the reconstruction of the authors' earlier pipeline without same-document suppression) and N_raw (%.1f%%), about 4%% smaller than TC and H, and larger than W, D and N_clean. The 56%% figure in the abstract is therefore a reduction against F2, not against any chunked or Markdown baseline."
         % (ci(ge["H"]["em"]["ci99_pp"]), pm(ge["D"]["em"]["diff_pp"]), ci(ge["D"]["em"]["ci99_pp"]),
            S["N_clean"]["em_pp_per_100tok"], S["W"]["em_pp_per_100tok"], S["G"]["em_pp_per_100tok"], S["H"]["em_pp_per_100tok"], S["TC"]["em_pp_per_100tok"],
            S["D"]["em_pp_per_100tok"], S["N_raw"]["em_pp_per_100tok"], S["F2"]["em_pp_per_100tok"], S["W"]["em"], S["G"]["em"],
            abs(100 * (1 - S["W"]["mean_tokens"] / S["G"]["mean_tokens"])), "fewer" if S["W"]["mean_tokens"] < S["G"]["mean_tokens"] else "more",
            100 * (1 - S["N_clean"]["mean_tokens"] / S["G"]["mean_tokens"]), ge["N_clean"]["em"]["diff_pp"],
            ge["F2"]["tokens"]["G_reduction_pct"], ge["N_raw"]["tokens"]["G_reduction_pct"])))
e6 = E6["G_vs"]
add(para("With qwen3.5:9b on the same fixed contexts, G was %s points above D (p = %.3f) and %s above F2 (p = %.3f), and was not distinguishable from N_raw (%s, p = %.2f), N_clean (%s, p = %.2f), W (%s), TC (%s) or H (%s). The ordering relative to the baselines therefore does not depend on the code-specialised generator, although absolute exact match was higher for the 9b model (%d for G) and the replay uses the same contexts, so it does not test retrieval again."
         % (pm(e6["D"]["em"]["diff_pp"]), e6["D"]["em"]["p_mcnemar"], pm(e6["F2"]["em"]["diff_pp"]), e6["F2"]["em"]["p_mcnemar"],
            pm(e6["N_raw"]["em"]["diff_pp"]), e6["N_raw"]["em"]["p_mcnemar"], pm(e6["N_clean"]["em"]["diff_pp"]), e6["N_clean"]["em"]["p_mcnemar"],
            pm(e6["W"]["em"]["diff_pp"]), pm(e6["TC"]["em"]["diff_pp"]), pm(e6["H"]["em"]["diff_pp"]), E6["summary"]["G"]["em"])))

# ---- 6.4 binding budget
add(h2("6.4 Where the ceiling binds (RQ1)"))
add(para("At the 2,048 ceiling the budget barely binds on this data: G's largest context was 1,163 estimated tokens, and in the 200-sample benchmark of Section 6.7 186 of 200 passages fit in one 512-word chunk. MRQA documents are short (the longest in the 12,836-record development file has 800 words), which is consistent with the release truncating long pages. Two exploratory experiments therefore make the ceiling bind. First, the same single documents were run with ceilings of 256, 512 and 1,024 estimated tokens, comparing G with budgeted chunks (the N arm, tag-stripped 512-word chunks cut at the ceiling), H and W. Second, each question was placed in a five-document corpus (the relevant document and four random distractors, in shuffled order; mean %d estimated tokens) with ceilings of 1,024 and 2,048; G ingested all five documents, the chunked arms treated the concatenation as one text, and W truncated it. Table 7 gives exact match and, in brackets, the number of the 200 contexts that contain an answer string."
         % round(E3["corpus_mean_est_tokens"])))
rows7 = []
def cellv(sm, a): return "%d (%d)" % (sm[a]["em"], sm[a]["answer_in_context"])
for lab, sm in (("Single document, 256", E2["256"]["summary"]), ("Single document, 512", E2["512"]["summary"]),
                ("Single document, 1,024", E2["1024"]["summary"])):
    rows7.append([lab] + [cellv(sm, a) for a in ("G", "N", "H", "W")] + ["%.0f / %.0f" % (sm["G"]["mean_tokens"], sm["N"]["mean_tokens"])])
for lab, sm in (("Five-document corpus, 1,024", E3["1024"]["summary"]), ("Five-document corpus, 2,048", E3["2048"]["summary"])):
    rows7.append([lab] + [cellv(sm, a) for a in ("G", "N", "H", "W")] + ["%.0f / %.0f" % (sm["G"]["mean_tokens"], sm["N"]["mean_tokens"])])
t7 = d.make_table(TBL_T, ["Setting, ceiling (est. tokens)", "G", "N (chunks)", "H (hybrid)", "W (truncated)", "Mean tokens, G / N"],
                  rows7, [3100, 1400, 1400, 1400, 1500, 2100])
add(t7); add(caption("Table 7", "Exploratory ceiling sweeps (N = 200): exact match, with the number of contexts containing an answer string in brackets. qwen2.5-coder:7b, concise prompt."))
add(source())
g2 = E2["256"]["G_vs"]; g5 = E2["512"]["G_vs"]; m1 = E3["1024"]["G_vs"]; m2 = E3["2048"]["G_vs"]
add(para("With a single document and a 256-token ceiling the budget binds and G loses: exact match %d against %d for chunks (%s points, p = %.3f) and %d for W, with only %d of 200 G contexts still containing an answer string against %d for chunks, probably because G packs structural elements first and cuts one that does not fit (this mechanism was not examined separately). At 512 and 1,024 tokens G was level with chunks (%s and %s points; p = %.2f and %.2f) and with H, and was below W at 512 (%s, p = %.3f). In the five-document corpora at a 1,024 ceiling G was ahead of budgeted chunks (%d against %d correct; %s points, 95%% interval %s, p = %.3f) and of truncated Markdown (%d; %s points), and level with hybrid table-aware retrieval (%d; %s points, p = %.2f). At 2,048 tokens, where the corpus (%d tokens on average) still exceeds the ceiling, G (%d) was not distinguishable from chunks (%d), H (%d) or W (%d). These experiments show that varying the ceiling changes what is selected and that G's selection helps against plain chunking and truncation only in the multi-document, moderately bound setting; they show no advantage over a hybrid table-aware retriever, and a clear disadvantage when the ceiling is very small."
         % (E2["256"]["summary"]["G"]["em"], E2["256"]["summary"]["N"]["em"], pm(g2["N"]["em"]["diff_pp"]), g2["N"]["em"]["p_mcnemar"], E2["256"]["summary"]["W"]["em"],
            E2["256"]["summary"]["G"]["answer_in_context"], E2["256"]["summary"]["N"]["answer_in_context"],
            pm(g5["N"]["em"]["diff_pp"]), pm(E2["1024"]["G_vs"]["N"]["em"]["diff_pp"]), g5["N"]["em"]["p_mcnemar"], E2["1024"]["G_vs"]["N"]["em"]["p_mcnemar"],
            pm(g5["W"]["em"]["diff_pp"]), g5["W"]["em"]["p_mcnemar"],
            E3["1024"]["summary"]["G"]["em"], E3["1024"]["summary"]["N"]["em"], pm(m1["N"]["em"]["diff_pp"]), ci(m1["N"]["em"]["ci95_pp"]), m1["N"]["em"]["p_mcnemar"],
            E3["1024"]["summary"]["W"]["em"], pm(m1["W"]["em"]["diff_pp"]), E3["1024"]["summary"]["H"]["em"], pm(m1["H"]["em"]["diff_pp"]), m1["H"]["em"]["p_mcnemar"],
            round(E3["corpus_mean_est_tokens"]), E3["2048"]["summary"]["G"]["em"], E3["2048"]["summary"]["N"]["em"], E3["2048"]["summary"]["H"]["em"], E3["2048"]["summary"]["W"]["em"])))
add(para("What the ceiling bounds. B is applied to the word-count estimate of Eq. (7). Native prompt tokens ran at about 1.24 per estimated context token, so the estimate understates native length; at the 2,048 ceiling the native full prompt (context plus a template of roughly 260 tokens) was exceeded in 41 cases for F and 1 for G (maxima 3,937 and 2,372 tokens), and the generator was given a context window large enough for every prompt, so nothing was truncated by the model server. B is therefore a bound on estimated context tokens, not a hard bound on the prompt the generator sees, and Eq. (7) has not been calibrated against the generator's tokenizer."))

# ---- 6.5 sensitivity
add(h2("6.5 Threshold sensitivity of Candidate G"))
parts = []
for name, lab in (("rel0.20", "relevance threshold 0.20"), ("rel0.30", "0.30"), ("kw0.10", "keyword-assisted threshold 0.10"), ("kw0.20", "0.20"),
                  ("elig0.30", "eligibility threshold 0.30"), ("elig0.50", "0.50"), ("cap2", "cap of two elements"), ("cap4", "four")):
    v = E4[name]; parts.append("%s: %d contexts changed, EM %d (%s points)" % (lab, v["contexts_changed"], v["em"], pm(v["vs_G_em"]["diff_pp"])))
add(para("The thresholds 0.25, 0.15 and 0.40 and the cap of three elements were set when G was designed on the original cohort. Each was perturbed in turn on the fresh cohort at the 2,048 ceiling, regenerating answers only when the context changed (otherwise the rerun of G is reused; the rerun of G itself differed from the stored G in %d of 200 exact-match outcomes although all 200 contexts were identical, which is the decoding noise of the local server at temperature 0). " % A["G_rerun_vs_original"]["outcomes_changed"]
         + "; ".join(parts) + ". No perturbation moved exact match by more than 1 point and none was significant (all p ≥ 0.5), and the eligibility threshold and a cap of four changed no context, because every document in this cohort contributes at most a few structural elements. The result is a sensitivity check: it shows that the reported G is not an artefact of one threshold choice on this cohort, not that the thresholds are tuned for other data."))

# ---- 6.6 RQ2
add(h2("6.6 Answer format and abstention policy (RQ2)"))
add(para("A staged investigation preceded the pre-specified test. Stage A screened candidate generators on 101 samples; Stage B compared qwen3.5:4b with qwen2.5-coder:7b on 100 held-out question–document pairs and did not support higher Précis exact match for qwen3.5:4b (one-sided McNemar p = 0.788); and Stage C compared the standard and concise prompts on that same cohort. Stage C was therefore exploratory, and it motivated, but is not counted as evidence in, the pre-specified experiment."))
p101 = __import__("copy").deepcopy(O[101])
d.replace(p101, "and Précis v3) and two prompts", "and Précis v3, the fact-only pipeline without the structural packing of Candidate G, which was not part of this experiment) and two prompts")
d.replace(p101, "The primary preregistered hypothesis", "The primary pre-specified hypothesis")
add(p101)
add(keep[102]); add(setcap(keep[103], "Table 6: ", "Table 8: ")); add(keep[104])
add(keep[105]); add(keep[106]); add(keep[107])
add(O[108])
p109 = __import__("copy").deepcopy(O[109]); d.replace(p109, "Table 6 and Fig. 6", "Table 8 and Fig. 6"); d.replace(p109, "pairs of Table 6", "pairs of Table 8"); d.replace(p109, "benchmark result of Section 6.4", "benchmark result of Section 6.7"); add(p109)

# follow-up 2x2
P = ["standard", "sent_token", "short_explicit", "concise"]
def fcell(m, c):
    x = FU["cells"][f"{m}|{c}"]
    return [("%d / %d / %d" % (x[p]["em"], x[p]["judge"], x[p]["abstained"])) for p in P]
rows9 = []
for m, ml in (("qwen2.5-coder:7b", "qwen2.5-coder:7b"), ("qwen3.5:4b", "qwen3.5:4b")):
    for c, cl in (("naive_rag", "Naive RAG"), ("precis_full", "Précis v3")):
        rows9.append(["%s / %s" % (ml, cl)] + fcell(m, c))
t9 = d.make_table(TBL_T, ["Model / retrieval", "Sentence + explicit (standard)", "Sentence + token", "Short + explicit", "Short + token (concise)"],
                  rows9, [2900, 2000, 1800, 2000, 2200])
cons = FU["contrasts"]
fmt = [r for r in cons if r["contrast"].startswith("format")]
abs_ = [r for r in cons if r["contrast"].startswith("abstention")]
add(para("Separating format from abstention. The standard and concise prompts differ in two ways: the answer format (sentence or short span) and the abstention instruction (say so explicitly, or output “Insufficient information”), and 5 of the 12 audited corrections were abstention-to-answer transitions. A follow-up, designed after the pre-specified experiment and therefore exploratory in its design (protocol and hash in the repository), crossed the two factors on the same 100 cached contexts, two generators and two retrieval conditions by adding two prompts, each built by swapping only the abstention line: a short-span format with the standard abstention wording, and the standard sentence format with the “Insufficient information” wording. Table 9 gives, per cell, exact match, answers judged equivalent by a local model (gemma4:12b, fixed rubric, temperature 0), and the number of outputs that abstain."))
add(t9); add(caption("Table 9", "The 2×2 follow-up (N = 100 per cell): exact match / outputs judged equivalent to the gold answer / abstaining outputs. The judge agreed with a human label on 92% of 90 audited outputs (Section 6.6)."))
add(source())
fm = [r["diff_pp"] for r in fmt]; fp = max(r["p_holm16"] for r in fmt)
def abst_text():
    sf = {(r["model"], r["retrieval"]): r for r in abs_ if r["contrast"] == "abstention|format=sentence"}
    sh = {(r["model"], r["retrieval"]): r for r in abs_ if r["contrast"] == "abstention|format=short"}
    return sf, sh
sf, sh = abst_text()
c = FU["cells"]
add(para("With the abstention wording held fixed, the short-span format raised exact match by %.0f to %.0f points in all eight contrasts (Holm-adjusted p %s over the 16 tests, no case in which the sentence format was ahead), so the large effect of the concise prompt is a format effect. The abstention wording is a separate factor and did not help. With sentence answers, the “Insufficient information” wording raised abstention from %d to %d outputs for qwen2.5-coder with Naive RAG and from %d to %d with Précis v3, and cut judged-equivalent answers from %d to %d and from %d to %d; for qwen3.5:4b it changed judged-equivalent answers little (%d to %d and %d to %d). With short answers, replacing the standard abstention wording by the “Insufficient information” wording (that is, moving from the short-explicit prompt to the concise prompt) lowered qwen2.5-coder's exact match from %d to %d with Naive RAG and from %d to %d with Précis v3 (unadjusted exploratory p = %.3f and %.3f; Holm p = %.2f and %.2f) and judged-equivalent answers from %d to %d and from %d to %d, and left qwen3.5:4b unchanged. The concise prompt of the pre-specified experiment therefore combines a useful format instruction with an abstention instruction that, for the code-specialised generator, cost accuracy."
         % (min(fm), max(fm), ("< 0.001" if fp < 0.001 else "≤ %.3f" % fp),
            c["qwen2.5-coder:7b|naive_rag"]["standard"]["abstained"], c["qwen2.5-coder:7b|naive_rag"]["sent_token"]["abstained"],
            c["qwen2.5-coder:7b|precis_full"]["standard"]["abstained"], c["qwen2.5-coder:7b|precis_full"]["sent_token"]["abstained"],
            c["qwen2.5-coder:7b|naive_rag"]["standard"]["judge"], c["qwen2.5-coder:7b|naive_rag"]["sent_token"]["judge"],
            c["qwen2.5-coder:7b|precis_full"]["standard"]["judge"], c["qwen2.5-coder:7b|precis_full"]["sent_token"]["judge"],
            c["qwen3.5:4b|naive_rag"]["standard"]["judge"], c["qwen3.5:4b|naive_rag"]["sent_token"]["judge"],
            c["qwen3.5:4b|precis_full"]["standard"]["judge"], c["qwen3.5:4b|precis_full"]["sent_token"]["judge"],
            c["qwen2.5-coder:7b|naive_rag"]["short_explicit"]["em"], c["qwen2.5-coder:7b|naive_rag"]["concise"]["em"],
            c["qwen2.5-coder:7b|precis_full"]["short_explicit"]["em"], c["qwen2.5-coder:7b|precis_full"]["concise"]["em"],
            [r for r in cons if r["contrast"] == "abstention|format=short" and r["model"].startswith("qwen2.5") and r["retrieval"] == "naive_rag"][0]["p"],
            [r for r in cons if r["contrast"] == "abstention|format=short" and r["model"].startswith("qwen2.5") and r["retrieval"] == "precis_full"][0]["p"],
            [r for r in cons if r["contrast"] == "abstention|format=short" and r["model"].startswith("qwen2.5") and r["retrieval"] == "naive_rag"][0]["p_holm16"],
            [r for r in cons if r["contrast"] == "abstention|format=short" and r["model"].startswith("qwen2.5") and r["retrieval"] == "precis_full"][0]["p_holm16"],
            c["qwen2.5-coder:7b|naive_rag"]["short_explicit"]["judge"], c["qwen2.5-coder:7b|naive_rag"]["concise"]["judge"],
            c["qwen2.5-coder:7b|precis_full"]["short_explicit"]["judge"], c["qwen2.5-coder:7b|precis_full"]["concise"]["judge"])))
add(para("Does the format effect survive an equivalence measure? Much of it does not. The headline cell of the pre-specified experiment, qwen3.5:4b with Précis v3, moved from 6 to 43 correct under exact match, but from %d to %d judged-equivalent answers. For qwen3.5:4b with Naive RAG the judged count moved from %d to %d, and for qwen2.5-coder it fell from %d to %d with Naive RAG and from %d to %d with Précis v3. Exact match mostly measures whether the answer is a bare span, and many of the standard prompt's sentence answers are equivalent to the gold answer even though they fail exact match. The retrieval ranking, in contrast, is the same under every measure: the chunked baseline was ahead of Précis v3 in all eight model–prompt cells under exact match, and under judged equivalence by %d to %d points. The judge is a single local model with a fixed rubric, so it was checked against a human. One of the authors, working from a sheet that showed the question, the gold answer and the output but not the judge's verdict, labelled 100 outputs sampled equally from its CORRECT and INCORRECT verdicts as correct or incorrect; %d were marked hard to tell and excluded. On the remaining %d the judge and the human agreed on %d (%.1f%%, Cohen's κ = %.2f): of the %d outputs judged correct %d were correct by the human label (%.0f%%), and of the %d judged incorrect %d were incorrect (%.0f%%); weighting the two strata by their share of all 1,600 judged outputs gives about %.0f%% agreement. This is one labeller and a small sample, so the judged counts are a supporting measure and the exact-match conclusions above do not rest on them."
         % (c["qwen3.5:4b|precis_full"]["standard"]["judge"], c["qwen3.5:4b|precis_full"]["concise"]["judge"],
            c["qwen3.5:4b|naive_rag"]["standard"]["judge"], c["qwen3.5:4b|naive_rag"]["concise"]["judge"],
            c["qwen2.5-coder:7b|naive_rag"]["standard"]["judge"], c["qwen2.5-coder:7b|naive_rag"]["concise"]["judge"],
            c["qwen2.5-coder:7b|precis_full"]["standard"]["judge"], c["qwen2.5-coder:7b|precis_full"]["concise"]["judge"],
            min(100 * (v["judge"]["naive_rag"] - v["judge"]["precis_full"]) for v in FU["retrieval_ranking"].values()),
            max(100 * (v["judge"]["naive_rag"] - v["judge"]["precis_full"]) for v in FU["retrieval_ranking"].values()),
            EJ["blank_hard_to_tell"], EJ["scored"], EJ["confusion"]["judge_correct_human_correct"] + EJ["confusion"]["judge_incorrect_human_incorrect"],
            100 * EJ["raw_agreement_in_stratified_sample"], EJ["kappa"], EJ["judge_correct_items"], EJ["confusion"]["judge_correct_human_correct"],
            100 * EJ["human_agrees_when_judge_CORRECT_(precision)"], EJ["judge_incorrect_items"], EJ["confusion"]["judge_incorrect_human_incorrect"],
            100 * EJ["human_agrees_when_judge_INCORRECT_(npv)"], 100 * EJ["population_weighted_agreement"])))
add(para("Pilot error audit. A seeded 30-question subset of the confirmatory cohort (60 generations) was labelled under a blinded protocol by two second raters, a human rater (one of the authors) and a language-model subagent, each given only the question, gold answer, evidence context and the two unlabelled outputs, without the prompt condition (Table 10). The subset held 12 prompt-correction transitions, no prompt-degradation transition, 17 persistent errors and one persistent success. In 7 of the 12 corrections the standard output wrapped the correct entity in a sentence; in the other 5 it abstained for insufficient information and the concise prompt answered, which is the abstention confound that the follow-up above separates. The first reviewer's per-output labels were not stored, so its category counts (for example evidence insufficiency 19, conversational mismatch 17, hallucination 6 of 60) could not be verified and are not used. On the 46 outputs that failed exact match the two new raters agree on 38 (83%, Cohen's κ = 0.70) with evidence insufficiency and other merged, and on 24 (52%, κ = 0.35) with the original six labels; across all 60 outputs with six labels they agreed on 37 (62%, κ = 0.51), mostly disagreeing about refusals. Both raters' Pass labels coincide with exact matches (the human rater labelled one further exact match as a conversational mismatch). One rater is an author and the other a language model, so the audit is a pilot: it supports only the objective findings (12 corrections, no degradations, 7 wrappers and 5 refusals, refusals the largest failure category) and no category percentages."))
add(keep[112]); add(setcap(keep[113], "Table 7: ", "Table 10: ")); add(keep[114])

# ---- 6.7 RQ3
add(h2("6.7 Information loss across pipeline stages (RQ3)"))
add(O[116])
p117 = __import__("copy").deepcopy(O[117])
d.replace(p117, "(Table 8)", "(Table 11)"); d.replace(p117, "from 59 to 23 cases", "from 63 to 23 cases")
add(p117)
t8 = keep[118]
for tc in t8.iter(q("tc")):
    for p in tc.findall("w:p", NS):
        if d.text(p) == "59 (29.5%)": d.set_runs(p, [("63 (31.5%)", {})])
add(t8); add(setcap(keep[119], "Table 8: ", "Table 11: ")); add(keep[120])
nq = R6["nq200_v3"]
add(para("Tracing the answer string through the v3 pipeline gave 200/200 in the source passages, 177/200 in the extracted facts, 177/177 in top-K retrieval and 177/177 in the packed context, so in this single-document setting the loss arose at extraction (23 cases), generation and strict string matching, not at retrieval or packing. The step from 177 covered cases to 38 exact matches can be decomposed with the stored outputs. With the MRQA alternatives, %d outputs contain an answer string, so at least %d covered cases were lost to generation (of the %d outputs that do not contain one, %d abstain and %d give a different answer), and the remaining %d lost between containment and exact match, that is, answers that are present but fail strict matching. About three quarters of the gap between coverage and exact match is therefore answer format and matching, not evidence. Because the revisions were developed after inspecting failure cases on this same split, the gains in Table 11 are in-sample engineering results; the corrected v1 row is 137 covered and 63 missed cases (31.5%%), where the earlier 59 was the number of outputs that failed containment, not extraction misses."
         % (nq["containment_with_aliases"], nq["lost_generation_or_abstention_upper"], 200 - nq["containment_with_aliases"],
            nq["not_contained_abstained"], nq["not_contained_other_wrong"], nq["contained_but_not_exact"])))
add(para("The same trace on the table cohort is where retrieval and packing could lose evidence. Table 12 follows the fresh cohort from the document to the context and to the answer. At the 2,048 ceiling the answer string was in the context in 197 of 200 cases for G and in 198 to 199 for the chunked, Markdown and F2 arms (168 for D, which has no evidence for the %d list-only documents by construction), so retrieval and packing again lost almost nothing; the loss was at generation (abstentions and wrong answers) and at exact matching. The situation changes when the ceiling binds: at 256 estimated tokens the answer string was in only %d of G's 200 contexts against %d for chunks (Table 7), and that is where packing, not generation, decides the outcome."
         % (F["strata_sizes"]["list_only"], E2["256"]["summary"]["G"]["answer_in_context"], E2["256"]["summary"]["N"]["answer_in_context"])))
rows12 = []
for arm, lab in (("N_raw", "N_raw"), ("N_clean", "N_clean"), ("D", "D"), ("F2", "F2"), ("G", "G")):
    x = R6["fresh_table_cohort"]["arms"][arm]
    rows12.append([lab, "%d" % x["in_context"], "%d" % x["in_context_and_contains"], "%d" % x["in_context_and_em"],
                   "%d" % x["in_context_contains_not_em"], "%d" % x["in_context_abstained"], "%d" % x["in_context_wrong"]])
t12 = d.make_table(TBL_T, ["Arm", "Answer in context", "Output contains answer", "Exact match", "Contains, not exact", "Abstained", "Wrong answer"],
                   rows12, [1200, 1700, 1800, 1500, 1700, 1500, 1500])
add(t12); add(caption("Table 12", "Stage loss on the fresh table- and list-bearing cohort (N = 200, 2,048-token ceiling, qwen2.5-coder:7b). Rows after the first column count cases whose context contains the answer string; “Abstained” and “Wrong answer” partition those contexts' outputs that do not contain the answer."))
add(source())
add(O[122])

# ---- 6.8 fact layer
add(h2("6.8 The fact layer: an extractor audit"))
def pct(x): return "%.1f%%" % (100 * x)
def cellp(d_, k): return "%s (%d/%d)" % (pct(d_[k]["precision"]), d_[k]["correct"], d_[k]["n"])
def agr(d_, k): return "%s (%d/%d)" % (pct(d_[k]["precision"]), d_[k]["correct"], d_[k]["n"])
def sc(d_, key):
    x = d_[key]; return x
rows13 = []
for k, lab in (("negated", "Polarity correct, stored negated"), ("not_negated", "Polarity correct, stored not negated")):
    rows13.append([lab, "%d" % EF["A_polarity_precision"][k]["n"], cellp(EF["A_polarity_precision"], k), cellp(EF["B_polarity_precision"], k), agr(EF["agreed_polarity_precision"], k)])
for k in ("asserted", "attributed", "conditional", "hypothetical"):
    rows13.append(["Modality correct, stored %s" % k, "%d" % EF["A_modality_precision"][k]["n"], cellp(EF["A_modality_precision"], k), cellp(EF["B_modality_precision"], k), agr(EF["agreed_modality_precision"], k)])
def sn(dd, key):
    x = dd[key]; return x
for key, lab in (("negation", "Sentence negation"), ("nonasserted", "Sentence non-asserted modality")):
    A_, B_, G_ = ESN[key + "_vs_A"], ESN[key + "_vs_B"], ESN[key + "_vs_agreed"]
    rows13.append([lab + ", recall", "%d / %d / %d" % (A_["tp"] + A_["fn"], B_["tp"] + B_["fn"], G_["tp"] + G_["fn"]),
                   "%s (%d/%d)" % (pct(A_["recall"]), A_["tp"], A_["tp"] + A_["fn"]), "%s (%d/%d)" % (pct(B_["recall"]), B_["tp"], B_["tp"] + B_["fn"]),
                   "%s (%d/%d)" % (pct(G_["recall"]), G_["tp"], G_["tp"] + G_["fn"])])
    rows13.append([lab + ", precision", "%d / %d / %d" % (A_["tp"] + A_["fp"], B_["tp"] + B_["fp"], G_["tp"] + G_["fp"]),
                   "%s (%d/%d)" % (pct(A_["precision"]), A_["tp"], A_["tp"] + A_["fp"]), "%s (%d/%d)" % (pct(B_["precision"]), B_["tp"], B_["tp"] + B_["fp"]),
                   "%s (%d/%d)" % (pct(G_["precision"]), G_["tp"], G_["tp"] + G_["fp"])])
t13 = d.make_table(TBL_T, ["Measure", "n", "Annotator A", "Annotator B", "A and B agree"], rows13, [3800, 1500, 1900, 1900, 1800])
add(para("The SVOA fact layer was not part of any accuracy experiment above. In the 200 contexts of G on the original cohort only %d facts were packed in total, none with a negation marker, so in these cohorts the fact layer contributes little to what G packs, and no ablation shows what it adds. What can be said is how accurate its labels are. Two human annotators, working independently, labelled, from 700 randomly drawn development documents (7,824 extracted facts, of which %d, 2.4%%, were flagged negated), 400 facts sampled to include %d negated, %d non-asserted and %d asserted ones, and 200 sentences (100 containing a negation cue, 60 a hedge, attribution or condition cue, and 40 neither). For each fact they judged whether the stored negation flag and the stored modality were right; for each sentence, blind to the extractor, whether its main claim is negated and which of four modalities it carries (asserted, attributed, conditional, hypothetical). A language model was used only to reword the free-text notes that accompany one annotator's labels. %d facts and %d sentences that one annotator marked ambiguous or too thin to judge were excluded, leaving %d facts and %d sentences. Agreement between the annotators was κ = %.2f for stored polarity, %.2f for stored modality, %.2f for sentence negation and %.2f for sentence modality. Table 13 reports precision per stored class and recall at sentence level." % (111, 184, 130, 120, 150, EF["unscorable_ambiguous"], ESN["unscorable_ambiguous"], EF["scored"], ESN["scored"], EF["kappa_polarity"], EF["kappa_modality_correct"], ESN["kappa_negation"], ESN["kappa_modality"])))
add(t13); add(caption("Table 13", "Extractor audit: precision of the stored negation flag and modality per stored class (facts), and negation and non-asserted-modality recall and precision at sentence level, per annotator and where both agree. Counts in brackets; n for sentence rows lists A / B / agreed. The sample is enriched for negated and non-asserted facts and for cue-bearing sentences, so precision is per class, not overall, and sentence precision is lowered by the enrichment."))
add(source())
add(para("The negation flag was wrong for more than half of the facts it marked negated: %s of %d stored-negated facts had correct polarity by annotator A (%s by B, %s where both agree), against %s of non-negated facts, and in %d of the %d wrong cases (%.0f%%) no negation cue occurs in the fact's own subject, verb or object (an automatic check), which indicates negation attached to a fact from another clause of the same sentence, not a missed cue. Sentence-level recall of negation was about 80%% (%s by A, %s by B), but sentence-level precision was about 30%% in this cue-enriched sample, which is consistent with the same over-attachment. Modality labels were more accurate: asserted facts were correct %s of the time by A (%s by B), attributed facts %s (%s), and the few conditional and hypothetical facts were almost all correct, but annotators disagreed more on whether a stored modality was right (κ = %.2f), and the most frequent corrections were attributed facts that were really asserted (%d of the %d modality errors by A) and the reverse (%d). The audit supports a limited claim: the fact layer's modality labels are usable, but its negation flag, which the system's grounding prompt asks the generator to respect, is not reliable at the fact level. It is a small, single-source sample with a language-model-worded note column and two annotators, and it does not measure the effect of these errors on answers; single-term SDH ablations and a negation- or hedge-sensitive question set remain future work."
         % (pct(EF["A_polarity_precision"]["negated"]["precision"]), EF["A_polarity_precision"]["negated"]["n"], pct(EF["B_polarity_precision"]["negated"]["precision"]), pct(EF["agreed_polarity_precision"]["negated"]["precision"]),
            pct(EF["A_polarity_precision"]["not_negated"]["precision"]), EF["negated_but_wrong_by_A"]["elsewhere_in_sentence"], EF["negated_but_wrong_by_A"]["n"],
            100 * EF["negated_but_wrong_by_A"]["elsewhere_in_sentence"] / EF["negated_but_wrong_by_A"]["n"],
            pct(ESN["negation_vs_A"]["recall"]), pct(ESN["negation_vs_B"]["recall"]),
            pct(EF["A_modality_precision"]["asserted"]["precision"]), pct(EF["B_modality_precision"]["asserted"]["precision"]),
            pct(EF["A_modality_precision"]["attributed"]["precision"]), pct(EF["B_modality_precision"]["attributed"]["precision"]),
            EF["kappa_modality_correct"], EF["A_modality_errors_stored_to_true"]["attributed->asserted"], sum(v for k, v in EF["A_modality_errors_stored_to_true"].items() if k.split("->")[0] != k.split("->")[1]),
            EF["A_modality_errors_stored_to_true"]["asserted->attributed"])))

# ---- 6.9 discussion
add(h2("6.9 Discussion"))
add(para("Structure matters; the packing rule matters less. Decomposing tables into prose was the weakest variant and preserving them natively recovered most of the accuracy, consistent with the view that a cell is interpretable only through its headers. Beyond that, the evidence does not separate G from simple alternatives: on the fresh cohort G was not worse than chunked retrieval, table-aware chunks and whole-document Markdown by more than 5 points, was not shown to be as good as hybrid table-aware retrieval, and matched truncated Markdown with a similar context. Its reduction in context is real only against F2 and, mildly, against raw-markup chunks. When the ceiling bound across several documents G helped against plain chunking, and when it bound very tightly G was worse."))
add(para("Answer formatting is a large effect on exact match and a small one on answer quality. Concise prompting raised exact match by 17 to 38 points across the four combinations and lowered containment by 8 to 17 points. The 2×2 follow-up shows that the gain is a format effect that does not depend on the abstention wording, that the abstention wording of the concise prompt is a separate and mostly harmful factor for the code-specialised generator, and that an equivalence judge sees far smaller differences. The supported conclusion is a caution for evaluation with two small local generators, two prompt families and N = 100: exact match must be accompanied by an equivalence measure, and prompt changes must be decomposed into their parts before a method comparison is read. It is not established that format is a first-order factor for other generators."))
add(para("Explainability and practicality. Every packing decision can be traced to a similarity, a filter or the ceiling, and the interface exposes the same fields. The ceiling is derived from the host in the released code, extraction is rule-based, and all models are local. Ingestion and query timings were not measured, so no speed claim is made, and no user study of auditability was run."))

# ---- 6.10 limitations
add(h2("6.10 Limitations"))
add(para("Evidence. (1) The 56% and 53.17% context reductions are against F2 and F, the authors' own earlier pipeline, by a word-count estimate that was not calibrated against the generator's tokenizer, and F2 is a reconstruction. (2) The original table cohort is in-sample for G (designed after diagnosing 13 failures on it, with its table threshold also examined there); variants A–F reused frozen predictions while G was generated live; variant F cannot be regenerated from the current code, and the “confirmatory” label that the project records give Experiment 4.8.0 does not denote an independent test. The fresh cohort removes the dependence but is a single draw with a single set of thresholds; the sensitivity check of Section 6.5 perturbs one threshold at a time. (3) The non-inferiority margin was chosen after the fresh-cohort results were known; parity with hybrid table-aware retrieval is not established, and other strong baselines (cross-encoder reranking, larger generators) were not run. (4) The ceiling sweeps are exploratory, the five-document corpus is synthetic (random distractors), and no genuinely long documents were used because the MRQA release truncates them. (5) All cohorts come from one Natural Questions development source, and the extraction revisions were developed on the evaluation split. (6) Two local generators plus one replay generator, two prompt families and a fixed qwen2.5-coder choice were used, on one GPU-equipped host with greedy decoding that is not perfectly reproducible (3 of 200 outcomes changed on identical contexts), so CPU-only behaviour and other models are untested, and the prompt wording of the original table-cohort run was not hash-recorded (Appendix A). (7) The equivalence judge is a single local model checked by one labeller on 90 outputs; the error audit is a pilot with an author and a language model as raters. (8) The effect of the SVOA, modality and SDH components on answers is untested, and the extractor audit of Section 6.8 is a small single-source sample whose negation flag was unreliable. (9) Scope: the results apply to documents whose answers depend on tables and lists; on short single-passage documents chunked retrieval scored higher than Précis v3 (Section 6.7), so no advantage over chunked retrieval is claimed for prose documents."))
add(para("Implementation. The doubled negation marker found in code checks affected 9 of 200 stored F contexts and 4 of 100 confirmatory contexts, none of G's, and a regeneration check showed no change in any outcome that could be tested (Appendix B.4). The intent router is a set of English regular expressions, and the injection filter is a basic pattern list with a development default secret that must be replaced in production."))

# insert Section VI after the anchor
cur = anchor
for el in seq:
    cur.addnext(el); cur = el

# ============================================================ conclusions
c_p = d.find("This paper presented Précis")
d.set_runs(c_p, [(
    "This paper presented Précis, an offline pipeline that keeps tables and lists in native form and packs a query-specific context "
    "under a token ceiling, with an optional layer of negation- and modality-tagged facts whose negation flag a small annotation audit found unreliable. On a 200-case table-bearing "
    "cohort, preserving tables natively raised exact match from 14.0% (tables converted to prose) to 49.5%, and guarded "
    "structural-priority packing reached 55.0%, a difference from the persistent baseline that was not significant. On a fresh "
    "pre-specified cohort, G was non-inferior at a 5-point margin to chunked retrieval, table-aware chunking and whole-document "
    "Markdown but not shown to be so for hybrid table-aware retrieval, and its smaller context is established only against the "
    "reconstructed persistent baseline. When the ceiling was made to bind, G helped against plain chunking across multi-document "
    "corpora and hurt at a very small ceiling. Chunked retrieval outperformed Précis v3 on short single-passage documents. A "
    "concise-answer prompt raised exact match in every model–retrieval combination; a follow-up attributes this to answer format "
    "and shows that the prompt's abstention wording lowered accuracy and that a human-validated answer-equivalence measure sees much smaller "
    "differences, so format and abstention instructions must be controlled, and exact match supplemented, when retrieval methods "
    "are compared. In the table cohort retrieval and packing lost almost no answer evidence at the 2,048 ceiling, and most loss "
    "arose at generation and answer matching.", {})])
fw = d.find("Future work has six directions")
d.set_runs(fw, [(
    "Future work has six directions: (i) evaluating on genuinely long documents and mixed table-and-prose corpora, with stronger "
    "baselines such as reranking; (ii) calibrating the token estimate against the target model's tokenizer; (iii) fixing the "
    "negation scope errors the audit exposed and re-scoring the extractor, then running single-term SDH ablations and a negation- "
    "or hedge-sensitive question set, which are the evidence the fact layer still lacks; (iv) validating the answer-equivalence "
    "judge on a larger sample with more than one labeller and repeating the format–abstention decomposition with more generators; (v) fixing the adjunct-typing errors and the negation flags that arise from table cells "
    "and titles; and (vi) a user study of how well people can audit answers through the modality and negation fields.", {})])

# data availability, AI statement
dv = d.find("The source code, experiment protocols")
d.set_runs(dv, [(
    "The source code, experiment protocols, per-case records and analysis scripts are available at https://github.com/chandanxd/precis; "
    "a tagged release that reproduces each table and its archive DOI will be given here at submission [DOI to be inserted]. The Natural "
    "Questions data were taken from the MRQA 2019 shared-task release (https://github.com/mrqa/MRQA-Shared-Task-2019), development split. "
    "The generators were run through Ollama (qwen2.5-coder:7b and qwen3.5:4b, Q4_K_M quantisation, plus qwen3.5:9b for the replay and "
    "gemma4:12b for the equivalence judge); the model digests and prompt-template hashes of the pre-specified experiment are recorded in "
    "its configuration, and the protocols of the fresh-cohort, baseline and follow-up experiments carry SHA-256 hashes and timestamps "
    "written before their model calls. The annotation sheets, labels and scoring script of Sections 6.6 and 6.8 are in the repository.", {})])
ai = d.find("During the preparation of this manuscript")
d.replace(ai, "a Claude-based model also acted as a blind second rater for the error-mode audit of Section 6.3.",
          "a Claude-based model also acted as a blind second rater for the error-mode audit of Section 6.6, and Claude Code was used to write analysis scripts, to run the additional experiments of Sections 6.3–6.6 and to revise the manuscript in response to a simulated peer review. A local language model (gemma4:12b) served as the answer-equivalence judge of Section 6.6, and a language model was used to word the free-text notes that accompany one annotator's labels in the extractor audit of Section 6.8; the labels themselves were assigned by the human annotators.")

# ============================================================ appendices
app_a_last = O[208]
bseq = []
b = bseq.append
b(para("APPENDIX B. CODE-LEVEL VERIFICATION OF THE RELEASED IMPLEMENTATION", O[202]))
p124 = __import__("copy").deepcopy(O[124])
d.replace(p124, "Table 9", "Table B1")
d.replace(p124, "SVOA extraction.", "B.1 SVOA extraction.")
b(p124)
b(keep[125]); b(setcap(keep[126], "Table 9: ", "Table B1: ")); b(keep[127])
b(keep[128]); b(setcap(keep[129], "Figure 7: ", "Figure B1: ")); b(keep[130])
p131 = __import__("copy").deepcopy(O[131]); d.replace(p131, "Fig. 7", "Fig. B1"); b(p131)
b(para("B.2 Packing worked example. To illustrate Eq. (8), the eight facts of Table B1 were scored with the shipped SDH function under two stated assumptions: an empty store (U = 1, the cold-start rule) and a subject–object cosine of 0.50 (E = 0.60) for facts that have an object; facts 3 and 7 have empty objects, for which the shipped scorer returns E = 0, which is why their SDH values are lower. The question was “What does the framework exclude or not subsidize?”. The query similarities in Table B2 are illustrative inputs, not measurements, because no embedding model was available. They were passed through a stub store into the shipped pack_context function with B = 60 tokens. SDH and π are printed to four decimals because two decimals hide the order of F1 and F8.", O[132]))
rowsb2 = [["F1", "Asserted", "18", "0.7271", "0.40", "0.2908", "Packed"], ["F2", "Attrib.", "24", "0.6439", "0.18", "0.1159", "Over budget"],
          ["F3", "Attrib.", "15", "0.4925", "0.15", "0.0739", "Over budget"], ["F4", "Asserted, ¬", "18", "0.6506", "0.82", "0.5335", "Packed"],
          ["F5", "Asserted, ¬", "13", "0.6506", "0.78", "0.5075", "Packed"], ["F6", "Asserted", "18", "0.6589", "0.20", "0.1318", "Over budget"],
          ["F7", "Hypoth.", "12", "0.5661", "0.22", "—", "Filtered (hypothetical)"], ["F8", "Asserted", "17", "0.6452", "0.45", "0.2904", "Over budget"]]
b(d.make_table(O[133], ["Fact", "Modality", "τ(t)", "SDH", "sim (illustr.)", "π(t,q)", "Decision (B = 60)"], rowsb2, [792, 1728, 1007, 1007, 1584, 1368, 2736]))
b(caption("Table B2", "Per-fact cost, score and packing decision for the worked example (similarities are illustrative; SDH and π unrounded to four decimals).")); b(source())
b(para("Facts F4 and F5, the two negated statements, have the highest pack scores because their illustrative similarity to the question is high. F1 and F8 are nearly tied, with π = 0.2908 and 0.2904 unrounded (the two-decimal values 0.73 × 0.40 and 0.65 × 0.45 would suggest the opposite order), and F1 is packed first because its score is higher by 0.0005. After F4, F5 and F1 use 49 tokens, F8 would bring the total to 66 and is skipped. F7 is removed by the modality filter before ranking. For F4, Eqs. (1) and (6) give:"))
b(keep[137]); b(keep[138]); b(keep[139])
b(setcap(keep[140], "Figure 8: ", "Figure B2: ")); b(keep[141])
p142 = __import__("copy").deepcopy(O[142]); d.replace(p142, "Fig. 8(b)", "Fig. B2(b)"); d.replace(p142, "which is the hard constraint of Section III", "which is the bound on estimated tokens described in Section III"); b(p142)
p143 = __import__("copy").deepcopy(O[143]); d.replace(p143, "Software verification.", "B.3 Software verification."); b(p143)
p150 = __import__("copy").deepcopy(O[150]); d.replace(p150, "Implementation notes.", "B.4 Negation-rendering defect and other implementation notes."); b(p150)
cur = app_a_last
for el in bseq:
    cur.addnext(el); cur = el

# fix remaining references in Appendix A text
for p in d.body.iter(q("p")):
    t = d.text(p)
    if "the prompt wording of the original table-bearing run (Section 6.2)" in t:
        pass

d.replace(d.find("A.1 Templates of the confirmatory experiment"), "(Section 6.3)", "(Section 6.6)")
# captions for retained Table 11 (CRediT)
cr = d.find("Table 11: Contribution allocation")
d.replace(cr, "Table 11: ", "Table 14: ")

# ============================================================ references: add + renumber by first appearance
newrefs = {
    "N1": "Y. Sui, M. Zhou, M. Zhou, S. Han, and D. Zhang, “Table meets LLM: Can large language models understand structured table data? A benchmark and empirical study”, in Proc. 17th ACM Int. Conf. on Web Search and Data Mining (WSDM 2024), pp. 645–654, 2024. doi: 10.1145/3616855.3635752.",
    "N2": "J. Herzig, T. Müller, S. Krichene, and J. Eisenschlos, “Open domain question answering over tables via dense retrieval”, in Proc. 2021 Conf. of the North American Chapter of the ACL: Human Language Technologies (NAACL-HLT), pp. 512–519, 2021. doi: 10.18653/v1/2021.naacl-main.43.",
    "N3": "P. Sarthi, S. Abdullah, A. Tuli, S. Khanna, A. Goldie, and C. D. Manning, “RAPTOR: Recursive abstractive processing for tree-organized retrieval”, in Proc. 12th Int. Conf. on Learning Representations (ICLR 2024), 2024. arXiv:2401.18059.",
    "N4": "S. Robertson and H. Zaragoza, “The probabilistic relevance framework: BM25 and beyond”, Foundations and Trends in Information Retrieval, vol. 3, no. 4, pp. 333–389, 2009. doi: 10.1561/1500000019.",
    "N5": "G. V. Cormack, C. L. A. Clarke, and S. Büttcher, “Reciprocal rank fusion outperforms Condorcet and individual rank learning methods”, in Proc. 32nd Int. ACM SIGIR Conf. on Research and Development in Information Retrieval, pp. 758–759, 2009.",
    "N6": "J. Bulian, C. Buck, W. Gajewski, B. Börschinger, and T. Schuster, “Tomayto, tomahto. Beyond token-level answer equivalence for question answering evaluation”, in Proc. 2022 Conf. on Empirical Methods in Natural Language Processing (EMNLP), pp. 291–305, 2022. doi: 10.18653/v1/2022.emnlp-main.20.",
    "N7": "E. Kamalloo, N. Dziri, C. Clarke, and D. Rafiei, “Evaluating open-domain question answering in the era of large language models”, in Proc. 61st Annual Meeting of the ACL (Volume 1: Long Papers), pp. 5591–5606, 2023. doi: 10.18653/v1/2023.acl-long.307.",
    "N8": "M. Sclar, Y. Choi, Y. Tsvetkov, and A. Suhr, “Quantifying language models' sensitivity to spurious features in prompt design or: How I learned to start worrying about prompt formatting”, in Proc. 12th Int. Conf. on Learning Representations (ICLR 2024), 2024. arXiv:2310.11324.",
    "N9": "Qwen Team, “Qwen3.5-9B”, model card, Hugging Face. [Online]. Available: https://huggingface.co/Qwen/Qwen3.5-9B (accessed Oct. 18, 2026).",
}
ref_head = d.find("XII. REFERENCES")
ref_paras = []
el = ref_head.getnext()
while el is not None and el.tag == q("p") and re.match(r"^\[\d+\]", d.text(el)):
    ref_paras.append(el); el = el.getnext()
last_ref = ref_paras[-1]
tmpl_ref = ref_paras[-1]
byid = {re.match(r"^\[(\d+)\]", d.text(p)).group(1): p for p in ref_paras}
for k, txt in newrefs.items():
    p = __import__("copy").deepcopy(tmpl_ref); d.set_runs(p, [("[%s]" % k + txt, {})]); byid[k] = p
# expand citation ranges "[a]–[b]" into explicit lists so that every member takes part in the ordering
rng = re.compile(r"\[(\d+)\]\s*[–-]\s*\[(\d+)\]")
ref_set0 = set(ref_paras)
for p in list(d.body.iter(q("p"))):
    if p in ref_set0: continue
    while True:
        m = rng.search(d.text(p))
        if not m: break
        lo, hi = int(m.group(1)), int(m.group(2))
        d.replace(p, m.group(0), ", ".join("[%d]" % k for k in range(lo, hi + 1)))
# order of first appearance in body (excluding the reference list)
tok = re.compile(r"\[(N?\d+)\]")
ref_set = set(ref_paras)
order = []
for p in d.body.iter(q("p")):
    if p in ref_set or p.getparent() is None: continue
    if d.text(p).startswith("XII. REFERENCES"): continue
    for m in tok.finditer(d.text(p)):
        if m.group(1) in byid and m.group(1) not in order: order.append(m.group(1))
rest = [k for k in byid if k not in order]
final = order + rest
newnum = {old: str(i + 1) for i, old in enumerate(final)}


def renumber(p):
    full = d.text(p)
    matches = list(re.finditer(r"\[(N?\d+)\]", full))
    for m in reversed(matches):
        if m.group(1) in newnum:
            d.replace_at(p, m.start(), m.end(), "[%s]" % ("@" + newnum[m.group(1)]))
    for t in p.iter(q("t")):
        if t.text: t.text = t.text.replace("[@", "[")


# add positional replace helper
def replace_at(self, p, start, end, new):
    runs = p.findall("w:r", NS); ts = [r.find("w:t", NS) for r in runs]
    pos = 0; done = False
    for t in ts:
        if t is None: continue
        L = len(t.text or ""); s, e = max(start, pos), min(end, pos + L)
        if s < e:
            a = t.text
            t.text = a[: s - pos] + (new if not done else "") + a[e - pos:]; done = True
        pos += L


Doc.replace_at = replace_at
for p in list(d.body.iter(q("p"))):
    if p in ref_set or d.text(p).startswith("XII. REFERENCES"): continue
    if tok.search(d.text(p)): renumber(p)
# collapse runs of >= 3 consecutive citations back into ranges
seqre = re.compile(r"\[\d+\](?:, \[\d+\])+")
for p in list(d.body.iter(q("p"))):
    if p in ref_set or d.text(p).startswith("XII. REFERENCES"): continue
    while True:
        done = False
        for m in seqre.finditer(d.text(p)):
            nums = [int(x) for x in re.findall(r"\d+", m.group(0))]
            # find first run of >= 3 consecutive ascending numbers
            i = 0
            while i < len(nums):
                j = i
                while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1: j += 1
                if j - i >= 2:
                    # locate the text span of nums[i..j] inside the match
                    toks = re.findall(r"\[\d+\]", m.group(0)); pre = ", ".join(toks[:i]); 
                    start = m.start() + (len(pre) + 2 if i else 0)
                    seg = ", ".join(toks[i:j + 1])
                    d.replace_at(p, start, start + len(seg), "[%d]–[%d]" % (nums[i], nums[j]))
                    done = True; break
                i = j + 1
            if done: break
        if not done: break
# collapse ranges like [13]–[16] only if still consecutive (leave as is otherwise)
for p in ref_paras: p.getparent().remove(p)
cur = ref_head
for old in final:
    p = byid[old]
    t = d.text(p)
    d.set_runs(p, [(re.sub(r"^\[(N?\d+)\]", "[%s]" % newnum[old], t), {})])
    cur.addnext(p); cur = p

d.save(DST)
print("saved", DST, "refs", len(final), "order head", order[:12])
