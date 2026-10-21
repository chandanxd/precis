"""Build Precis_paper_clean_plane_revised_v4.docx from v3 in response to the simulated five-seat review of v3:
evaluation framing, margin-sensitivity and strata re-analyses, Holm over the ceiling sweeps, the 2x2 decomposition with
interaction terms, interval reporting for the judge and the extractor audit, the fact-layer specification moved to
Appendix B, and cuts (Figs. 2, 4, 5, 6, Tables 3, 10, 11, B1, B2, Figs. B1, B2) to bring the paper to about 17 pages.

  backend/venv/bin/python scripts/revise_paper_v4.py
Numbers come from results/paper_checks/v4_reanalysis.json (scripts/paper_checks_v4.py) and the stored analysis files
already cited by v3. v3 is left untouched.
"""
import re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from docx_tools import Doc, NS, q

SRC = ROOT / "paper/research-paper/Precis_paper_clean_plane_revised_v3.docx"
DST = ROOT / "paper/research-paper/Precis_paper_clean_plane_revised_v4.docx"
d = Doc(SRC)
P = d.orig                      # handles by v3 body index (see the structure dump in the commit message)
DONE = set()                    # paragraphs whose text is written here with v4 numbering (skipped by the renumbering)


def setp(i_or_el, text, lead=None):
    el = P[i_or_el] if isinstance(i_or_el, int) else i_or_el
    d.set_text(el, text, lead=lead); DONE.add(el); return el


def rep(i, old, new):
    d.replace(P[i], old, new)


def drop(*idx):
    for i in idx: d.delete(P[i])


def row_of(tbl, anchor):
    for tr in tbl.iter(q("tr")):
        if anchor in " | ".join(d.text(tc) for tc in tr.iter(q("tc"))): return tr
    raise KeyError(anchor)


def setrow(tbl, anchor, cells):
    tr = row_of(tbl, anchor)
    for tc, txt in zip(tr.iter(q("tc")), cells):
        if txt is None: continue
        p = tc.find("w:p", NS); d.set_runs(p, [(txt, {})]); DONE.add(p)


# ================================================================== title, keywords, abstract
setp(0, "KEEPING TABLES INTACT UNDER A TOKEN BUDGET: STRUCTURE PRESERVATION, SIMPLE BASELINES AND ANSWER-FORMAT "
        "SENSITIVITY IN LOCAL RETRIEVAL-AUGMENTED QUESTION ANSWERING")
info = list(P[5].iter(q("p")))
for p, kw in zip(info[2:8], ["Retrieval-Augmented Generation,", "Table Question Answering,", "Context Budget,",
                             "Non-inferiority,", "Answer-Format Sensitivity,", "Evaluation Methodology."]):
    d.set_runs(p, [(kw, {})]); DONE.add(p)
setp(info[9], "Retrieval-augmented generation on local hardware must fit evidence into a small context, and documents whose "
    "answers sit in tables raise the question of how much of their structure to keep. We study it with Précis, an offline "
    "pipeline that keeps HTML tables and lists in native form and packs them under an estimated-token ceiling with a guarded "
    "structural-priority rule (G). On a 200-case table-bearing cohort on which G was designed, rewriting tables as extracted "
    "sentences cut exact match (EM) to 14.0%, against 49.5% for native tables. On a fresh protocol-first cohort of 200 "
    "questions, the arms that kept table and list markup, G (48.0% EM), raw-markup chunks (47.0%), table-aware chunks (48.0%), "
    "whole-document Markdown (49.0%) and hybrid table-aware retrieval (49.0%), were within 2 points of one another; G's "
    "non-inferiority depends on a margin chosen after the results, and G lost when the ceiling was cut to 256 tokens. In a 2×2 "
    "prompt experiment a short-answer format raised EM by 25 to 37 points, an LLM judge (92% agreement with one human labeller "
    "on 90 outputs) saw gains of 2 to 12 points, and an “Insufficient information” abstention line cost the "
    "code-specialised generator 22 to 29 points of judged-correct answers. On such documents keeping structure matters, simple "
    "structure-keeping baselines are hard to beat, and strict-match comparisons conflate answer format with accuracy.")

# ================================================================== I. Introduction
setp(8, "Retrieval-augmented generation (RAG) systems retrieve text passages and place them in a language-model prompt [1], "
    "[2]. On local hardware, memory, latency and model size limit the context a generator can use, and long contexts are used "
    "unevenly [3], so evidence has to be selected under a budget. Documents whose answers live in tables and lists make the "
    "selection harder: a table cell has meaning only through its row and column headers, and chunking, stripping markup or "
    "rewriting a table as sentences can sever those links.")
setp(9, "This paper asks how much a structure-aware packing rule adds over simple baselines that also keep structure, and how "
    "much of a measured difference between such systems is an artefact of answer format. The testbed is Précis, an offline "
    "pipeline that keeps HTML tables and lists in native form, packs them first under an estimated-token ceiling with a guarded "
    "structural-priority rule (Candidate G), and fills any remaining budget with subject–verb–object–adjunct (SVOA) facts "
    "extracted from prose. The fact layer is part of the released system but is not what the experiments test: it contributed "
    "111 facts to 200 contexts of G, and an audit (Section 6.8) found its negation flag unreliable. Its specification is in "
    "Appendix B.")
setp(10, "Three research questions guide the evaluation. RQ1 (structure and baselines): for documents whose answers depend on "
    "tables and lists, how does native-structure packing compare with structure-destroying conversion and with cheap "
    "structure-keeping baselines, and what happens when the ceiling binds? RQ2 (answer format): how much of a strict-match "
    "difference between prompts comes from answer format and how much from the abstention instruction, and does an "
    "answer-equivalence measure change the conclusion? RQ3 (information loss): at which stage is answer-bearing evidence lost?")
setp(11, "The contributions are evaluative: (i) an ablation showing that rewriting tables as extracted sentences is the main "
    "source of loss on a table-bearing cohort, with the caveat that G was designed on it; (ii) a protocol-first comparison on a "
    "fresh cohort against five simple baselines, with non-inferiority verdicts over margins of 3 to 7 points, table and list "
    "strata, and exploratory ceiling sweeps over single documents and five-document corpora; (iii) a 2×2 decomposition of a "
    "concise-answer prompt into answer format and abstention wording, scored by exact match and by an answer-equivalence judge "
    "checked against human labels; (iv) a stage-loss trace on two cohorts; and (v) a negative result on the fact layer's "
    "negation labels. The pipeline, protocols, per-case records and scripts are released (Section X).")
setp(12, "Section II reviews related work, Section III formulates the packing problem, Sections IV and V describe the system, "
    "Section VI reports results, discussion and limitations, and Section VII concludes. Appendix A gives the prompt templates and "
    "Appendix B the fact-layer specification and implementation notes.")

# ================================================================== II. Related work (new refs [47]-[52], renumbered at the end)
setp(14, "Related work is grouped into seven themes: retrieval-augmented generation and its context limits, context compression, "
    "retrieval granularity, tables and HTML as evidence, epistemic status in text, hierarchical and hybrid retrieval, and answer "
    "evaluation and prompt sensitivity. Table 1 summarises the studies reviewed.")
rep(15, "such systems assume a model that can be fine-tuned or a window that is generous.",
    "such systems assume a model that can be fine-tuned or a window that is generous. Long-context models can match RAG when "
    "resources allow, at a higher cost [50], and retrieval helps even models with extended windows [51]; whole-document input is "
    "therefore one of the baselines here.")
rep(16, "All three need an additional neural model at inference time, and none represents negation or attribution explicitly: "
    "a deleted “not” is simply a deleted token.",
    "All three need an additional neural model at inference time, and none treats a table as a unit to be kept or dropped whole.")
setp(18, "Tables are a third kind of evidence. Table question answering is usually studied with semantic parsers or "
    "table-pretrained encoders [17], [18], which presuppose a clean table; open-domain question answering over tables, and over "
    "tables and text, adds table retrieval [20], [49], and TableRAG retrieves schema and cell information so that a model can "
    "reason over very large tables [48]. Sui et al. benchmark how the serialisation of a table in the prompt, including "
    "markup-based formats, changes what language models can answer [19], and HtmlRAG keeps cleaned and pruned HTML instead of "
    "plain text for retrieved web pages [47]. A general RAG pipeline receives HTML in which tables and prose are mixed, and what "
    "it does with a table before prompting decides what the generator can use. Among the studies reviewed here, none compares "
    "table-preserving packing with chunked, whole-document and hybrid structure-keeping baselines on the same questions under one "
    "token budget. Précis addresses that preprocessing and packing step rather than the table-reading model.")
rep(20, "BM25 [25] fused with a dense ranking by reciprocal rank fusion [26].",
    "BM25 [25] fused with a dense ranking by reciprocal rank fusion [26]; a cross-encoder reranker [52] is a stronger and costlier "
    "second stage that is not evaluated here.")
T1 = P[22]
setrow(T1, "Edge et al. [12]", ["Tan et al. [47]", "HTML as retrieved knowledge", "HTML cleaning and block-tree pruning"])
setrow(T1, "Fader et al. [14]", ["Chen et al. [48]", "Very large tables", "Schema and cell retrieval"])
setrow(T1, "Herzig et al. [18]", ["Pasupat & Liang [17]; Herzig et al. [18]", None, "Semantic parsing; table-pretrained encoder"])
setrow(T1, "This work", [None, "Structure-preserving local RAG under a budget",
                         "Native tables and lists, guarded packing; format–abstention decomposition"])

# ================================================================== III. Problem formulation: SDH moves to Appendix B
setp(26, "A document is split into prose and structural elements. A structural element e is a table or list rendered in native "
    "form, with its own embedding and source document d(e). Each prose sentence yields zero or more facts t = (s, v, o, X, n, μ, "
    "a): subject, verb phrase, object, a set of typed adjuncts, a negation flag n, an epistemic modality μ ∈ {asserted, "
    "attributed, conditional, hypothetical} and, for attributed facts, the source a. Facts and elements are embedded into "
    "384-dimensional unit vectors, and facts are stored in a set G. Table 2 lists the notation.")
T2 = P[27]
setrow(T2, "SDH terms", ["SDH(t)", "Semantic Density Heuristic score of fact t (Appendix B)"])
d.delete(row_of(T2, "SDH term weights"))
sdh_block = [P[i] for i in range(30, 40)]            # SDH intro, Eqs. (1)-(5) and their definitions -> Appendix B.1
setp(40, "Each fact carries an intrinsic score SDH(t) ∈ [0, 1], an equally weighted sum of entity relatedness, verb "
    "informativeness, uniqueness and adjunct density (Appendix B, Eqs. (B1)–(B5)); its constants were set by hand and were "
    "neither tuned nor ablated. At query time a fact is ranked by the product of this score and its relevance to the question:")
setp(44, "Selecting the fact context is a 0/1 knapsack problem over the candidates C, which the system solves greedily in "
    "descending order of π (not of the value density π/τ, which was not evaluated):")

# ================================================================== IV-V. System: trim, drop Fig. 2, Table 3, complexity
setp(55, "Fig. 1 shows the data flow of Précis from ingestion to local generation. A browser interface lets a user upload "
    "documents, ask questions and inspect the packed context, the pipeline trace and the hardware profile. A FastAPI service "
    "exposes ingestion, query and inspection endpoints with token streaming, JSON Web Token authentication, per-client rate "
    "limiting, input limits and a basic prompt-injection pattern filter, and a deterministic intent router decides whether a "
    "question concerns the uploaded documents.")
rep(58, "(Figs. 2 and 3)", "(Fig. 2)"); DONE.add(P[58])
drop(59, 60, 61)
setp(65, "The profiler reads CPU cores, RAM and GPU memory and selects a token ceiling of 4,096 "
    "(RAM ≥ 8 GB and VRAM ≥ 6 GB), 3,072 (VRAM ≥ 2 GB), 2,048 (RAM ≥ 16 GB without a qualifying GPU) or 1,024 (other hosts), "
    "with a default model per mode (hardware.py). These rules were not evaluated: in the experiments the ceiling was fixed at "
    "2,048 estimated tokens unless Section 6.4 varies it, and the generator was fixed per experiment. The evaluation host was an "
    "AMD Ryzen 9 8945HS laptop with 16 GB RAM and an NVIDIA RTX 4060 Laptop GPU (8 GB VRAM); CPU-only operation, latency and "
    "memory use were not measured.", lead="Stage 0: Hardware profiling. ")
drop(66, 67, 68)
setp(70, "F-coref [37] replaces pronouns with their referents, a spaCy dependency parse [38] yields SVOA "
    "facts with rule-based negation and modality labels, and the facts are scored with SDH and written to ChromaDB with their "
    "modality, adjuncts, attribution, source document and sentence index (Appendix B.1).", lead="Stages 1–3: Fact layer. ")
stage_block = [P[71], P[72]]                         # extraction and scoring details -> Appendix B.1
drop(78)

# ================================================================== 6.1 setup
setp(81, "All results come from the authors' harness on the evaluation host of Table 3, and the cohorts are analysed separately "
    "and never pooled.")
setp(82, "Scoring is the same in every cohort. A prediction is correct for exact match if its normalised text equals the gold "
    "answer or any alternative answer that MRQA lists, and correct for containment if a normalised answer occurs in it at word "
    "boundaries. The rule is implemented once (scripts/scoring.py); re-scoring the prompt experiment, which was first scored "
    "against the single gold answer, changed 3 of 800 exact-match and 9 of 800 containment outcomes and left the primary test of "
    "Section 6.6 unchanged. ROUGE-L, MiniLM cosine and BERTScore, and the reference shown to the equivalence judge, use the single "
    "gold answer.")
setp(83, "Each analysis has one declared status. (a) The original table cohort (Table 4) is in-sample, because G was designed on "
    "it, and is descriptive: unadjusted exact McNemar tests and question-level bootstrap intervals. (b) On the fresh cohort the "
    "primary family (exact match; G against D, F2, N_raw and N_clean; two-sided exact McNemar, Holm over four contrasts) was "
    "written into a protocol before any model call. (c) Baseline adequacy (Section 6.3) compares G with seven arms by the lower "
    "bound of a 99% question-level bootstrap interval (10,000 resamples) for the exact-match difference; because the 5-point "
    "non-inferiority margin was chosen after the fresh-cohort results were known (and before W, TC and H were run), verdicts are "
    "given for margins of 3 to 7 points, with Newcombe paired score intervals and a Bonferroni level for seven comparisons as "
    "checks. (d) In the prompt experiment of Section 6.6 the primary test is one-sided McNemar for qwen3.5:4b with Précis v3. "
    "Everything else, namely the ceiling sweeps (Holm over their 15 contrasts), the threshold sensitivity, the strata and the 2×2 "
    "follow-up, is exploratory. The protocols are author-held files with SHA-256 hashes and time stamps written before the model "
    "calls; they are not entries in an external registry and were not under version control during the runs, so their order "
    "relative to the data cannot be verified independently, and they are called protocol-first below. Clustering is handled by "
    "resampling questions: the original table cohort holds 187 distinct questions in 200 cases and the 200-sample benchmark 74, "
    "whereas the other cohorts have distinct questions by construction. Each case is a single greedy generation, and repeating "
    "identical contexts changed 3 of 200 exact-match outcomes (Section 6.5), which is the size of the smallest differences "
    "reported. A non-significant difference is never read as equivalence.", lead="Inference plan. ")
T4 = P[84]
setrow(T4, "Statistics", [None, "Exact McNemar (paired binary), Holm / Bonferroni / Benjamini–Hochberg, question-level bootstrap "
                                "(10,000 resamples), Newcombe paired score intervals, Wilson intervals"])
setrow(T4, "Context ceiling", [None, "2,048 estimated tokens (word-count proxy, Eq. (2))"])

# ================================================================== 6.2 structure
rep(88, "B, decompiled prose, in which tables are converted into sentences",
    "B, SVOA-decompiled prose, in which the system's own extractor rewrites tables as sentences")
setrow(P[89], "Decompiled prose", [None, "SVOA-decompiled prose"])
drop(92, 93, 94)                                     # Fig. 4 duplicates Table 5
setp(95, "Table 4 gives the results. Rewriting tables as extracted sentences (B, 14.0% EM) was the weakest variant and fell below "
    "the prose baseline (A, 32.0%), whereas retaining tables in native form (D) reached 49.5%; D beat B in 79 cases against 8 "
    "(exact McNemar p = 8 × 10⁻¹⁶; question-level 95% interval +27.4 to +43.9 points). B measures the cost of this extractor's "
    "conversion, which has the defects reported in Section 6.8, not the cost of every tables-to-text method. Candidate G had the "
    "highest exact match (110/200, 55.0%) and, with E, the highest containment (137/200). Its leads over F (+2.5 points, 15 "
    "against 10 discordant pairs, p = 0.42; 95% interval −2.5 to +7.7) and E (+1.0, p = 0.73) are not distinguishable from zero, "
    "and its lead over D (+5.5, p = 0.019) does not survive Holm or Bonferroni correction over the four G contrasts (0.058 and "
    "0.077). Because G was designed on this cohort, these results are descriptive.")
drop(96)
setp(97, "A second table- or list-bearing cohort was drawn under a protocol-first design: 200 distinct questions from the "
    "Natural Questions development file whose documents contain table or list markup, excluding every identifier and question "
    "used before (1,425 candidate records, 748 distinct questions; seed 42). Five arms were run with qwen2.5-coder:7b, the "
    "concise prompt and the 2,048 ceiling: chunked passage retrieval on the raw document (N_raw) and on tag-stripped text "
    "(N_clean), table retention alone (D), a reconstruction of F without same-document fact suppression (F2; the frozen F cannot "
    "be regenerated by the current code) and G. Exact match was 96/200 (48.0%) for G, 94 for N_raw, 89 for F2, 88 for N_clean and "
    "79 for D. In the primary family G exceeded D (20 against 3 discordant cases, Holm p = 0.002) but not F2 (13 against 6, Holm "
    "p = 0.50), N_raw (11 against 9, p = 0.82) or N_clean (18 against 10, p = 0.50). The lead over D is confined to the 32 "
    "list-only documents, where D has no evidence by construction (G 18 correct, D 0), so it is a mechanism check. On the 168 "
    "documents with a table, G, D and N_raw (and W, TC and H of Section 6.3) scored 76 to 79 correct, against 71 for tag-stripped "
    "chunks and for F2; native tables beat stripped chunks (D against N_clean) by 4.8 points (17 against 9, p = 0.17, 95% "
    "interval −1.2 to +10.7), which has the expected sign but is not significant at this size. The large structure effect of "
    "Table 4 is therefore a loss from destroying structure, not a gain over cheap structure-keeping alternatives.",
    lead="Fresh cohort. ")
drop(98, 99, 100)                                    # Fig. 5: efficiency against F is not a point in G's favour
setp(101, "Against the authors' own pipelines G's packed context was smaller: 56.2% fewer estimated tokens than F2 on the fresh "
    "cohort (401.8 against 917.9; paired mean difference −516 tokens, 95% interval −573 to −461) and 53.2% fewer than F on the "
    "original cohort (365.8 against 781.1), or 43 to 46% fewer model-reported prompt tokens. Against external baselines it is not "
    "smaller (Section 6.3). The estimate understates native length: native prompt tokens ran at about 1.24 per estimated context "
    "token, and at the 2,048 ceiling the full native prompt exceeded 2,048 tokens in 41 F cases and 1 G case.",
    lead="Context size. ")

# ================================================================== 6.3 baselines
rep(103, "and the non-inferiority verdict at the 5-point margin.",
    "and the smallest margin, among 3 to 7 points, at which G is non-inferior.")
T6 = P[104]
for anchor, v in (("N_raw (chunks", "5"), ("N_clean (chunks", "3"), ("W (whole doc", "5"), ("TC (table-aware", "5"),
                  ("H (hybrid", "7"), ("F2 (F without", "3")):
    setrow(T6, anchor, [None] * 6 + [v])
setrow(T6, "Arm", [None] * 6 + ["Smallest NI margin met (pp)"])
rep(105, "G − arm is positive when G is ahead.",
    "G − arm is positive when G is ahead. The margin column uses the 99% bootstrap lower bound; Newcombe paired intervals give "
    "the same values except 6 for H.")
setp(107, "G was not distinguishable from any structure-keeping baseline: its exact-match differences from N_raw, W, TC and H "
    "lay between −1.0 and +1.0 points. Whether this counts as non-inferiority depends on a margin chosen after the fresh-cohort "
    "results were known. At 5 points G is non-inferior to N_raw, N_clean, W, TC and F2 but not to H; at 4 points only N_clean and "
    "F2 remain; and at a Bonferroni level for seven comparisons (99.3%) the Newcombe lower bounds against N_raw, W and TC (−5.1, "
    "−5.0 and −5.1) reach the 5-point margin. The verdicts against N_raw, W and TC therefore rest on one or two cases, and "
    "non-inferiority to TC with its absence for H is not itself a supported difference. Efficiency does not favour G either: per "
    "100 estimated tokens the order was N_clean (15.7), W (12.6), G (11.9), H (11.7), TC (11.4), D (11.3), N_raw (9.3) and F2 "
    "(4.8), and G's context was 13.5 tokens larger than W's (paired 95% interval +1.0 to +29.9), about 18 tokens smaller than "
    "TC's and H's, 102 smaller than N_raw's and 122 larger than N_clean's.")

# ================================================================== 6.4 ceiling
setp(114, "With a single document and a 256-token ceiling the budget binds and G loses: exact match 67 against 89 for chunks "
    "(−11.0 points, 11 against 33 discordant cases, Holm p = 0.018 over the 15 contrasts of Table 6) and 87 for W (Holm p = "
    "0.008), with only 150 of 200 G contexts still containing an answer string against 191 for chunks. The likely cause is that G "
    "packs a structural element first and truncates one that does not fit, which was not examined separately; row-level "
    "truncation with repeated headers, as in TC, is the obvious remedy. At 512 and 1,024 tokens G was level with chunks and H. In "
    "five-document corpora at a 1,024 ceiling G was ahead of budgeted chunks (90 against 74; unadjusted p = 0.014, Holm 0.17) and "
    "of truncated Markdown (71; Holm 0.056) and level with H (91); at 2,048 tokens G (86) was not distinguishable from chunks "
    "(81), H (92) or W (91). The curves are not monotone (G scores 90 at 1,024 and 86 at 2,048 on the corpora, and the chunk arm "
    "89, 87 and 87 across the single-document ceilings), which is consistent with noise of several cases. The sweeps show a clear "
    "disadvantage of G at a very small ceiling and no advantage over hybrid table-aware retrieval in any setting.")
setp(115, "B applies to the word-count estimate of Eq. (2), not to the generator's tokens; the generator was given a context "
    "window large enough for every prompt, so nothing was truncated by the model server.", lead="What the ceiling bounds. ")

# ================================================================== 6.5 thresholds
setp(117, "The thresholds of Eq. (4) and the cap of three elements were set on the original cohort. Perturbing each in turn on "
    "the fresh cohort (relevance 0.20 and 0.30, keyword-assisted 0.10 and 0.20, eligibility 0.30 and 0.50, cap two and four) "
    "changed 0 to 8 of 200 contexts and moved exact match by at most 1 point from the rerun of G (95 correct; the stored G has "
    "96, and the rerun differed from it in 3 of 200 outcomes on identical contexts, which is the decoding noise of the local "
    "server at temperature 0). Because so few contexts change, this shows how rarely the cohort exercises the thresholds, not "
    "that they carry over to other data.")

# ================================================================== 6.6 prompts
setp(119, "A staged prompt comparison (screening of generators on 101 samples, then model and prompt comparisons on 100 held-out "
    "pairs) preceded and motivated the main experiment; it is not counted as evidence.")
setp(120, "The main prompt experiment used 100 new question–document pairs from the same MRQA source, selected deterministically "
    "from an eligible pool of 3,904 by sorting SHA-256 hashes of normalised questions after removing overlaps with earlier "
    "cohorts. It crossed two generators (qwen2.5-coder:7b and qwen3.5:4b), two retrieval conditions (the chunked baseline, here "
    "“Naive RAG”, and Précis v3, the fact-only pipeline without the structural packing of G) and two prompts (standard and "
    "concise), giving 800 evaluations on contexts cached once per question and condition and checked by SHA-256 parity. "
    "Hypotheses, guardrails and tests were written into protocol files time-stamped before the first model output; the "
    "guardrails were fixed after the exploratory prompt comparison had shown 48% containment. Runs used Ollama 0.35.1, Q4_K_M "
    "quantisation and the templates of Appendix A. The primary hypothesis was that the concise prompt raises Précis exact match "
    "for qwen3.5:4b (one-sided exact McNemar, α = 0.05), with guardrails of a containment change of at least −0.25 and concise "
    "containment of at least 0.40; three secondary prompt effects used Holm-corrected one-sided tests.")
drop(124, 125, 126)                                  # Fig. 6 duplicates Table 8
setp(127, "The primary hypothesis was supported: for qwen3.5:4b with Précis v3 exact match rose from 6/100 to 43/100 (37 "
    "concise-only against 0 standard-only correct answers; one-sided p = 7.3 × 10⁻¹², identical under single-gold and alias "
    "scoring), and containment moved from 0.61 to 0.53, within both guardrails. The three secondary effects were also significant "
    "after Holm correction (11 to 51, 18 to 35 and 21 to 45 correct). Containment fell in all four conditions. A gain this large "
    "under strict matching is expected when one prompt asks for a bare span [27], [29]; the follow-up below asks what it consists "
    "of.")
setp(128, "The retrieval-by-prompt interaction was −0.03 (95% interval −0.13 to +0.07) for qwen3.5:4b and −0.07 (−0.15 to +0.01) "
    "for qwen2.5-coder:7b, so the prompt effect is not shown to differ between retrieval methods. The chunked baseline was "
    "numerically ahead of Précis v3 in all eight model–prompt cells of Table 7 (for example 51 against 43 correct for qwen3.5:4b "
    "under the concise prompt), in the same direction as the benchmark of Section 6.7; in exploratory paired tests it was ahead in "
    "containment in all four model–prompt strata (unadjusted p = 0.004 to 0.052), but after Holm correction over the eight tests "
    "only one difference remains below 0.05.")
setp(129, "The concise prompt differs from the standard one in its answer-format instructions (a short span instead of a "
    "sentence) and in its abstention line (output “Insufficient information” instead of saying so explicitly). In a blinded "
    "30-question pilot error audit (60 outputs labelled by one author and one language-model rater; κ = 0.70 on merged labels), "
    "the concise prompt corrected 12 answers and degraded none; 7 corrections unwrapped a correct entity from a sentence and 5 "
    "replaced an abstention. An exploratory follow-up crossed the two factors on the same 100 cached contexts by adding two "
    "prompts, each built by swapping only the abstention line (Appendix A): the concise prompt with the standard abstention line "
    "(short + explicit) and the standard prompt with the “Insufficient information” line (sentence + token). Table 8 gives, per "
    "cell, exact match, outputs judged equivalent to the gold answer by a local model (gemma4:12b, fixed rubric, temperature 0) "
    "and abstaining outputs.", lead="Separating format from abstention. ")
setp(133, "Averaged over the abstention wording, the short-span format raised exact match by 25.0 to 36.5 points in the four "
    "model–retrieval combinations (95% intervals all above +18), so the large exact-match effect of the concise prompt is mainly a "
    "format effect. The abstention wording is a separate factor whose effect depends on the generator and the format. For "
    "qwen2.5-coder the “Insufficient information” line raised abstention (from 2 to 36 sentence outputs with Naive RAG and from 9 "
    "to 60 with Précis v3), lowered judged-equivalent answers by 21.5 and 29.0 points on average, and lowered exact match in the "
    "short format (55 to 45 and 43 to 35; p = 0.006 and 0.021). For qwen3.5:4b it left judged-equivalent answers almost unchanged "
    "(−3.0 and 0.0 points) and raised exact match in the sentence format (11 to 18 and 6 to 17; p = 0.016 and 0.001) but not in "
    "the short format, where both cells were unchanged; the format-by-abstention interaction for exact match was −11.0 points "
    "(95% interval −18 to −5) for qwen3.5:4b with Précis v3 and −13.0 (−22 to −4) for qwen2.5-coder with Naive RAG. The concise "
    "prompt of the main experiment therefore combines a format instruction that changes strict-match scores with an abstention "
    "instruction that, for the code-specialised generator, lowers answer quality.")
setp(134, "Mostly not. Averaged over the abstention wording, the format effect on judged-equivalent answers was +1.5 and +4.0 "
    "points with Naive RAG (intervals including zero) and +12.0 and +11.0 with Précis v3 (95% intervals +6.5 to +18.0 and +3.5 to "
    "+18.5). The headline cell, qwen3.5:4b with Précis v3, moved from 6 to 43 under exact match but from 56 to 67 under the judge. "
    "Exact match mostly measures whether an answer is a bare span, and many sentence answers of the standard prompt are "
    "equivalent to the gold answer. The retrieval ranking is the same under both measures: the chunked baseline was ahead of "
    "Précis v3 in all eight cells under exact match and by 6 to 24 judged-equivalent answers. The judge was checked by one author, "
    "who labelled 100 outputs sampled equally from its CORRECT and INCORRECT verdicts without seeing the verdict; 10 marked hard "
    "to tell were excluded. On the remaining 90 the two agreed on 83 (92.2%, Wilson 95% interval 85–96%; Cohen's κ = 0.84, which "
    "the verdict-balanced sample pushes upwards), on 46 of 49 sentence-format and 37 of 41 short-format outputs, so agreement does "
    "not differ visibly between the formats being compared. The judge saw the single gold answer whereas exact match accepts MRQA "
    "alternatives, which can only make the judge stricter. With one labeller and 90 outputs the judged counts are a supporting "
    "measure, and the conclusions about format rest on the direction of the differences, not their size.",
    lead="Does the format effect survive an equivalence measure? ")
drop(135, 136, 137, 138)                             # pilot audit condensed into the paragraph above

# ================================================================== 6.7 information loss
setp(140, "On a 200-sample development benchmark of short passages (74 distinct questions; 512-word chunks with 128-word "
    "overlap, standard prompt, qwen2.5-coder:7b, 2,048 ceiling), chunked retrieval scored higher than the fact-only Précis v3: "
    "57 against 38 exact matches (26 against 7 discordant pairs; question-level 95% interval for the difference −0.5 to +19.5 "
    "points) and 159 against 141 containment. 186 of the 200 passages fit in one chunk, so this setting tests extraction rather "
    "than packing, and it does not bear on the table cohorts.", lead="Single-passage benchmark. ")
setp(141, "The extraction rules were revised four times after inspecting failures on this split, raising answer coverage (the "
    "answer string in some extracted fact) from 68.5% (v1) to 88.5% (v3) and exact match from 14.5% to 19.0%; these are in-sample "
    "engineering results. Under one procedure without coreference, the current extractor covered 91.0% of these development "
    "documents and 86.6% of 1,000 held-out documents from the same file (95% interval 84.4–88.7%), so the level of coverage, "
    "though not the size of the improvement, carries over.")
drop(142, 143, 144, 150)
setp(145, "Tracing the answer string through the v3 pipeline gave 200/200 in the source passages, 177/200 in the extracted facts "
    "and 177/177 in both the retrieved candidates and the packed context, so in this setting the loss arose at extraction (23 "
    "cases) and after packing. Of the 177 covered cases, 141 outputs contained an answer string and 38 were exact matches, so at "
    "least 36 covered cases were lost at generation and 103 between containment and exact match. The 177/177 figures are "
    "conditional on extraction, and an answer string in a context shows that the answer was available, not that it was used.")
rep(146, "so retrieval and packing again lost almost nothing; the loss was at generation (abstentions and wrong answers) and at exact matching.",
    "so the answer string survived retrieval and packing in nearly every context, and the remaining loss was at generation "
    "(abstentions and wrong answers) and at exact matching.")

# ================================================================== 6.8 audit
rep(152, "400 facts sampled to include 130 negated, 120 non-asserted and 150 asserted ones",
    "400 facts sampled at random within strata (seed 42) to include 130 of the 184 negated, 120 non-asserted and 150 asserted ones")
rep(152, "For each fact they judged whether the stored negation flag and the stored modality were right;",
    "For each fact they judged, with the stored labels visible, whether the stored negation flag and the stored modality were right;")
rep(152, "0.50 for stored modality, 0.80 for sentence negation and 0.71 for sentence modality.",
    "0.50 for stored modality, 0.80 for sentence negation and 0.71 for sentence modality (prevalence-adjusted agreement, PABAK, "
    "0.92, 0.81, 0.92 and 0.85).")
rep(156, "by annotator A (44.7% by B, 43.5% where both agree), against",
    "by annotator A (Wilson 95% interval 35–53%), 44.7% by B and 43.5% where both agree, against")
rep(156, "Sentence-level recall of negation was about 80% (81.0% by A, 80.0% by B), but sentence-level precision was about 30% in this cue-enriched sample",
    "Sentence-level recall of negation was about 80% (81.0% by A, 95% interval 60–92%, on only 21 negated sentences), but "
    "sentence-level precision was about 30% in this cue-enriched sample")
rep(156, "and the most frequent corrections were attributed facts that were really asserted (17 of the 35 modality errors by A) and the reverse (7).",
    "and A marked 38 stored modalities wrong, 3 of them without naming a different class; among the other 35 the most frequent "
    "corrections were attributed facts that were really asserted (17) and the reverse (7).")
rep(156, "the fact layer's modality labels are usable,", "the fact layer's modality labels are mostly right for asserted facts,")

# ================================================================== 6.9 discussion, 6.10 limitations, VII conclusions
setp(158, "Rewriting tables as extracted sentences was the weakest variant, and on the fresh cohort every arm that kept tables "
    "and lists, including the cheap ones, was within a few points of every other. The evidence supports keeping native structure "
    "and does not separate G from whole-document Markdown, table-aware chunking or hybrid table-aware retrieval on documents of "
    "this length. Where the ceiling bound very tightly G was worse, and where it bound across several documents its lead over "
    "plain chunking did not survive correction. For short documents, passing the document as Markdown or using table-aware chunks "
    "serves as well as G.", lead="Structure matters; the packing rule matters less. ")
setp(159, "Concise prompting raised exact match by 17 to 40 points; the 2×2 follow-up shows that most of the gain is format, that "
    "the abstention wording is a separate factor whose effect depends on the generator, and that an equivalence judge sees far "
    "smaller format effects. For evaluation with small local generators, exact match should be accompanied by an equivalence "
    "measure, and prompt changes should be decomposed before a method comparison is read. With two generators, two prompt "
    "families and N = 100 it is not established that the size of these effects carries over to other models.",
    lead="Answer formatting is a large effect on exact match and a small one on answer quality. ")
setp(162, "(1) All cohorts come from one source, MRQA Natural Questions, whose documents are short (at most 800 words) and largely "
    "Wikipedia pages with short answers; the ceiling rarely binds, no long or multi-row-reasoning documents were tested, and the "
    "five-document corpora use random distractors. (2) The original table cohort is in-sample for G, its variants A–F reuse frozen "
    "predictions under a prompt wording that was not hash-recorded, and F2 is a reconstruction. (3) The non-inferiority margin "
    "was chosen after the fresh-cohort results, and the protocols are author-held, not externally registered. (4) The baselines "
    "omit cross-encoder reranking [52] and row-serialised tables, the primary generator is code-specialised (the 9b replay "
    "changes the generator but not the contexts), and each case is a single greedy generation. (5) Ingestion and query latency, "
    "memory use and CPU-only operation were not measured, and the token estimate is not calibrated against the generator's "
    "tokenizer. (6) The equivalence judge is a single local model checked by one labeller on 90 outputs, and the pilot error "
    "audit has an author and a language model as raters. (7) The fact layer's effect on answers is untested and its negation flag "
    "is unreliable. (8) An earlier renderer doubled the negation marker in 9 of 200 stored F contexts and 4 of 100 prompt-"
    "experiment contexts and in none of G's; regenerating with the marker removed changed no exact-match outcome that could be "
    "tested, and the renderer has been fixed (Appendix B.2). The intent router is a set of English regular expressions, and the "
    "injection filter is a basic pattern list with a development default secret that must be replaced in production.")
drop(163)
setp(165, "This paper evaluated how much a structure-aware packing rule adds to local RAG over table-bearing documents and how "
    "much of a measured difference comes from answer format. Rewriting tables as extracted sentences cost most of the accuracy on "
    "a table-bearing cohort (14.0% against 49.5% exact match for native tables). On a fresh protocol-first cohort the guarded "
    "structural-priority rule G (48.0%) was not distinguishable from cheap structure-keeping baselines, its non-inferiority "
    "depended on a post hoc margin, it was not shown to match hybrid table-aware retrieval, and it lost when the ceiling was cut "
    "to 256 tokens; its smaller context holds only against the authors' own earlier pipeline. A concise-answer prompt raised exact "
    "match in every model–retrieval combination, but a 2×2 decomposition attributes the gain mainly to answer format, shows that "
    "the abstention wording interacts with the generator, and an equivalence judge sees much smaller differences. At the 2,048 "
    "ceiling the answer string survived retrieval and packing in nearly every context, and most loss arose at generation and "
    "strict matching. On documents of this kind keeping structure matters, simple structure-keeping baselines are hard to beat, "
    "and strict-match comparisons need an equivalence measure and controlled prompts.")
setp(166, "Future work has five directions: (i) long, table-heavy documents and table-and-text benchmarks such as NQ-Tables [20] "
    "and OTT-QA [49], with same-domain distractors and a cross-encoder reranker; (ii) row-level truncation for G under small "
    "ceilings and a token estimate calibrated against the generator's tokenizer; (iii) repeated sampling and latency, memory and "
    "CPU-only measurements; (iv) a larger, multi-labeller validation of the equivalence judge and the format–abstention "
    "decomposition with more generator families; and (v) fixing the negation-scope errors of the fact layer and testing its effect "
    "with single-term SDH ablations on a negation-sensitive question set.")

# ================================================================== back matter
setp(172, "The authors acknowledge the open-source software and datasets that supported this research, including the MRQA 2019 "
    "Natural Questions release, spaCy, FastCoref, sentence-transformers, ChromaDB, Ollama and the Qwen models. Competing "
    "interests: none declared. Funding: no specific funding was received for this work.")
rep(50, "(Section 6.4)", "(Section 6.2)")
rep(174, "prompt-template hashes of the pre-specified experiment", "prompt-template hashes of the main prompt experiment")
rep(174, "carry SHA-256 hashes and timestamps written before their model calls.",
    "carry SHA-256 hashes and time stamps written before their model calls (author-held files, not an external registry).")
setp(176, "During the preparation of this manuscript the authors used ChatGPT (OpenAI) and Claude (Anthropic) for language "
    "editing, organisation of existing material and review of analytical summaries. Claude Code (Anthropic; Claude Sonnet and "
    "Opus models) wrote analysis scripts, ran the experiments of Sections 6.3–6.6 and the regeneration checks of Appendix B.2, "
    "re-scored every cohort under one scoring rule, computed the re-analyses added in this version (scripts/paper_checks_v4.py), "
    "and revised the manuscript in response to simulated peer reviews produced with Claude-based tools; those reviews are not "
    "independent of the model that revised the text. A Claude-based subagent acted as the second rater of the pilot error audit "
    "(Section 6.6) and saw only the question, gold answer, evidence context and the two unlabelled outputs. A local model "
    "(gemma4:12b) was the answer-equivalence judge, and a language model reworded the free-text notes of one annotator in the "
    "extractor audit; all other labels were assigned by human annotators. Every reported number is produced by a script in the "
    "repository from the stored per-case records. The authors are responsible for verifying the data, statistical calculations, "
    "references and interpretation, and all authors reviewed and approved the final manuscript.")
REFS = [
    "[47]J. Tan, Z. Dou, W. Wang, M. Wang, W. Chen, and J.-R. Wen, “HtmlRAG: HTML is better than plain text for modeling "
    "retrieved knowledge in RAG systems”, in Proc. ACM Web Conference 2025 (WWW ’25), 2025. doi: 10.1145/3696410.3714546.",
    "[48]S.-A. Chen, L. Miculicich, J. M. Eisenschlos, Z. Wang, Z. Wang, Y. Chen, Y. Fujii, H.-T. Lin, C.-Y. Lee, and T. "
    "Pfister, “TableRAG: Million-token table understanding with language models”, in Advances in Neural Information Processing "
    "Systems (NeurIPS 2024), vol. 37, 2024.",
    "[49]W. Chen, M.-W. Chang, E. Schlinger, W. Wang, and W. W. Cohen, “Open question answering over tables and text”, in Proc. "
    "9th Int. Conf. on Learning Representations (ICLR 2021), 2021. arXiv:2010.10439.",
    "[50]Z. Li, C. Li, M. Zhang, Q. Mei, and M. Bendersky, “Retrieval augmented generation or long-context LLMs? A comprehensive "
    "study and hybrid approach”, in Proc. 2024 Conf. on Empirical Methods in Natural Language Processing: Industry Track, pp. "
    "881–893, 2024. doi: 10.18653/v1/2024.emnlp-industry.66.",
    "[51]P. Xu, W. Ping, et al., “Retrieval meets long context large language models”, in Proc. 12th Int. Conf. on Learning "
    "Representations (ICLR 2024), 2024. arXiv:2310.03025.",
    "[52]R. Nogueira and K. Cho, “Passage re-ranking with BERT”, arXiv preprint arXiv:1901.04085, 2019.",
]
last = P[223]
for r in REFS:
    last = d.clone_after(last, P[223], [(r, {})])

# ================================================================== Appendix A: the two follow-up prompts
d.clone_after(P[227], P[225], [(
    "Follow-up prompts (Section 6.6). Each changes only the abstention line. SHORT + EXPLICIT is CONCISE with the line “- If "
    "the provided facts do not contain enough information to answer the question, output \"Insufficient information\".” replaced "
    "by the STANDARD line “- If the provided facts do not contain enough information to answer the question, say so explicitly.” "
    "(sha256 055fe3eb608fa4438d7f602b20b514ede588a8d793c29ef80209630b41eaa524); SENTENCE + TOKEN is STANDARD with the reverse "
    "replacement (sha256 7758ebdb2bfa180152825ae285ef3ecf058a659b1d04119232d883783f84a209). The format factor of Table 8 is "
    "therefore every other difference between STANDARD and CONCISE.", {})])

# ================================================================== Appendix B: fact-layer specification
setp(231, "APPENDIX B. FACT-LAYER SPECIFICATION AND IMPLEMENTATION NOTES")
rep(122, "in the confirmatory 2×2×2 experiment", "in the 2×2×2 prompt experiment")
rep(225, "Templates of the confirmatory experiment", "Templates of the main prompt experiment")
lead_p = d.clone_after(P[231], P[232], [("B.1 Extraction and scoring. ", {"bold": True}),
                                        ("The fact layer is described here for completeness; none of the experiments of "
                                         "Section VI tests its effect on answers.", {"bold": False})])
d.move_after(lead_p, stage_block + sdh_block)
rep(72, "Eqs. (1)–(5)", "Eqs. (B1)–(B5)"); DONE.add(P[72])
for i in range(232, 252): d.delete(P[i])          # B.1-B.3: demonstration tables, figures and worked example
setp(252, "An earlier context renderer inserted a NOT marker for every negated fact even when the verb phrase already carried the "
    "negation word (“The framework NOT does NOT subsidize …”); stored polarity was correct. The doubled marker occurs in 9 of 200 "
    "stored contexts of F, none of G's and 4 of the 100 Précis contexts of the prompt experiment; rebuilt with the current "
    "extractor it appears in 11 of 200 contexts of A, 9 of 200 of E and 7 of 200 benchmark samples. Each affected context was "
    "generated again with the original model, prompt and decoding settings, with the marker kept and removed. Generating again on "
    "unchanged text reproduced every stored exact-match and containment outcome (9 of 9 F contexts, 16 of 16 prompt-experiment "
    "generations), and removing the marker changed no exact-match outcome in any of these sets and one benchmark containment "
    "outcome (Précis v3 containment 141 becomes 142 of 200, against 159 for chunks). The renderer no longer adds the marker when "
    "the verb phrase carries a negation cue; NOT markers that come from negation words in table cells or titles are not "
    "addressed. Other observed defects are heuristic adjunct typing (for example “to the warehouse” typed as both time and "
    "recipient), some empty objects, duplicated coordination facts and closed reporting-verb lists, so that “hypothesized that …” "
    "is typed asserted. The test suite has 503 tests in 20 modules, all passing in the project environment (Python 3.12.3, "
    "spaCy 3.8.14).", lead="B.2 Negation-rendering defect and other implementation notes. ")

# ================================================================== renumbering: equations, tables, figures, appendix refs
EQ = {6: "1", 7: "2", 8: "3", 9: "4", 10: "5", 1: "B1", 2: "B2", 3: "B3", 4: "B4", 5: "B5"}
TB = {1: 1, 2: 2, 4: 3, 5: 4, 6: 5, 7: 6, 8: 7, 9: 8, 12: 9, 13: 10, 14: 11}
FG = {1: 1, 3: 2}
for i, old in ((31, 1), (33, 2), (35, 3), (37, 4), (39, 5), (41, 6), (43, 7), (45, 8), (47, 9), (49, 10)):
    for t in P[i].iter(q("t")):
        if t.text and t.text.strip() == "(%d)" % old: t.text = t.text.replace("(%d)" % old, "(%s)" % EQ[old])
    DONE.add(P[i])
SUBS = [
    (re.compile(r"Eqs\. \((\d+)\)–\((\d+)\)"), lambda m: "Eqs. (%s)–(%s)" % (EQ[int(m[1])], EQ[int(m[2])])),
    (re.compile(r"Eq\. \((\d+)\)"), lambda m: "Eq. (%s)" % EQ[int(m[1])]),
    (re.compile(r"Eq\. (\d+)\b"), lambda m: "Eq. (%s)" % EQ[int(m[1])]),
    (re.compile(r"\bTable (\d+)\b"), lambda m: "Table %d" % TB[int(m[1])]),
    (re.compile(r"\bFig\. (\d+)\b"), lambda m: "Fig. %d" % FG[int(m[1])]),
    (re.compile(r"\bFigure (\d+)\b"), lambda m: "Figure %d" % FG[int(m[1])]),
    (re.compile(r"Appendix B\.4"), lambda m: "Appendix B.2"),
]
bad = []
for p in d.body.iter(q("p")):
    if p in DONE: continue
    full = d.text(p); want = full
    for rx, f in SUBS: want = rx.sub(f, want)
    if want == full: continue
    for t in p.iter(q("t")):
        if t.text:
            for rx, f in SUBS: t.text = rx.sub(f, t.text)
    if d.text(p) != want: bad.append(want[:80])
assert not bad, bad

# ================================================================== references: renumber by first appearance (IEEE)
body = list(d.body)
ref_head = next(i for i, el in enumerate(body) if el.tag == q("p") and d.text(el).strip() == "XII. REFERENCES")
ref_els = [el for el in body[ref_head + 1:] if el.tag == q("p") and re.match(r"\[\d+\]", d.text(el))]
CIT = re.compile(r"\[(\d+)\](?:–\[(\d+)\])?")
order = []
for el in body[:ref_head] + body[ref_head + 1 + len(ref_els):]:
    for p in ([el] if el.tag == q("p") else list(el.iter(q("p")))):
        for m in CIT.finditer(d.text(p)):
            a, b = int(m[1]), int(m[2] or m[1])
            for n in range(a, b + 1):
                if n not in order: order.append(n)
nums = [int(re.match(r"\[(\d+)\]", d.text(el))[1]) for el in ref_els]
order += [n for n in nums if n not in order]           # uncited entries (none expected) keep their place at the end
assert sorted(order) == sorted(nums), (sorted(set(nums) - set(order)), sorted(set(order) - set(nums)))
NEW = {old: k + 1 for k, old in enumerate(order)}
cite_rx = re.compile(r"\[(\d+)\]")
for el in d.body.iter(q("t")):
    if el.text and cite_rx.search(el.text):
        el.text = cite_rx.sub(lambda m: "[%d]" % NEW[int(m[1])] if int(m[1]) in NEW else m[0], el.text)
by_new = sorted(ref_els, key=lambda el: int(re.match(r"\[(\d+)\]", d.text(el))[1]))
anchor = body[ref_head]
for el in by_new: d.body.remove(el)
d.move_after(anchor, by_new)

d.save(DST); print("saved", DST)
print("uncited:", [n for n in nums if n not in order[:len(order)]] or "none")
