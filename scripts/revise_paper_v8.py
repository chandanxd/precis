"""Build Precis_paper_clean_plane_revised_v8.docx from v7: the response to the v7 full review (paper/ars_v7_review).

  backend/venv/bin/python scripts/revise_paper_v8.py
Changes (roadmap items of paper/ars_v7_review/editorial_decision.md):
  R1  structure claim narrowed; the ten structure-keeping vs tag-stripped contrasts of the protocol-first cohorts reported
  R2  related work: HtmlRAG described accurately, element-based chunking [37], long context inside RAG [36], LLM-judge bias
      [38]; old [36]-[53] renumbered to [39]-[56]; the gap statement narrowed and the added contribution stated
  R3  the released application's default configuration and where G2 lives
  R4  factual corrections: two model families, author labellers, the NI referent of G2, the RQ3 sentence
  S1-S14 the should-fix items (fact-only wording, interruptions, noise and detectable difference, mechanism wording, G2/TC
      context, weighted judge agreement, audit anchoring, budget premise, ingestion cost, Section IV, scope, Li et al.,
      abstract) and the Stage 2.5 items I-2 (shards) and I-4 (thousands separators).
Every new number is computed here from the stored records and asserted. v7 is left untouched.
"""
import json, math, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from docx_tools import Doc, NS, q

SRC = ROOT / "paper/research-paper/Precis_paper_clean_plane_revised_v7.docx"
DST = ROOT / "paper/research-paper/Precis_paper_clean_plane_revised_v8.docx"
d = Doc(SRC)
P = d.orig                      # handles by v7 body index
E = ROOT / "experiments"


def setp(i, text, lead=None):
    d.set_text(P[i], text, lead=lead); return P[i]


def rep(i, old, new):
    d.replace(P[i], old, new)


def tcell_rep(tbl_i, old, new):
    for p in P[tbl_i].iter(q("p")):
        if old in d.text(p):
            d.replace(p, old, new); return
    raise KeyError((tbl_i, old))


def mc(b, c):
    m = b + c
    return 1.0 if m == 0 else min(1.0, 2 * sum(math.comb(m, i) for i in range(min(b, c) + 1)) / 2 ** m)


def jl(path):
    return [json.loads(l) for l in open(path)]


# ------------------------------------------------------------------ checks: structure-keeping arms vs tag-stripped chunks
fresh = {r["sample_id"]: r for r in jl(E / "fresh_table_cohort/records.jsonl")}
single = {r["sample_id"]: r for r in jl(E / "baseline_budget/single_records.jsonl")}
ids = [i for i in fresh if i in single]
assert len(ids) == 200
fem = lambda i, a: single[i]["e1"][a]["em"] if a in ("W", "TC", "H") else fresh[i][a]["em"]
L1 = jl(E / "long_doc_cohort/records.jsonl"); L2 = jl(E / "long_doc_fixed_g/records.jsonl")
l1 = lambda r, a: r["ceil"]["2048"][a]["em"]; l2 = lambda r, a: r["arms"][a]["em"]


def contrast(rows, get, a, b):
    x = sum(1 for r in rows if get(r, a) and not get(r, b)); y = sum(1 for r in rows if get(r, b) and not get(r, a))
    return round(100 * (x - y) / len(rows), 1), mc(x, y)


# inclusion rule: every cheap structure-keeping baseline (N_raw, W, TC, H) that was run on a protocol-first cohort, at the
# 2,048 ceiling, against that cohort's tag-stripped chunks (N_clean on the fresh cohort, N on the long-document draws)
CHEAP = ("N_raw", "W", "TC", "H")
S = {("fresh", a): contrast(ids, fem, a, "N_clean") for a in CHEAP}
S.update({("long1", a): contrast(L1, l1, a, "N") for a in CHEAP})
S.update({("long2", a): contrast(L2, l2, a, "N") for a in CHEAP if a in L2[0]["arms"]})
assert len(S) == 10 and set(L2[0]["arms"]) == {"G", "G2", "TC", "W", "N"}
assert {k: v[0] for k, v in S.items()} == {("fresh", "N_raw"): 3.0, ("fresh", "W"): 5.0, ("fresh", "TC"): 4.0,
                                         ("fresh", "H"): 5.0, ("long1", "N_raw"): -2.5, ("long1", "W"): 2.0,
                                         ("long1", "TC"): 6.0, ("long1", "H"): 2.5, ("long2", "W"): 4.0,
                                         ("long2", "TC"): 1.0}
assert round(min(v[1] for v in S.values()), 3) == 0.076 and all(v[1] > 0.05 for v in S.values())
l1k = lambda r, a: r["ceil"]["1024"][a]["em"]
assert contrast(L1, l1k, "N_raw", "N")[0] == -10.0 and contrast(L1, l1k, "N_raw", "N")[1] < 0.002
assert contrast(ids, fem, "G", "N_clean")[0] == 4.0 and contrast(ids, fem, "D", "N_clean")[0] == -4.5
assert (contrast(L1, l1, "G", "N")[0], contrast(L2, l2, "G", "N")[0]) == (-13.5, -13.0)
SW = jl(E / "baseline_budget/single_records.jsonl"); MU = jl(E / "baseline_budget/multi_records.jsonl")
SWEEP = {("single", c, a): contrast(SW, lambda r, a, c=c: r["e2"][c][a]["em"], a, "N") for c in ("256", "512", "1024")
         for a in ("H", "W")}
SWEEP.update({("multi", c, a): contrast(MU, lambda r, a, c=c: r["e3"][c][a]["em"], a, "N") for c in ("1024", "2048")
              for a in ("H", "W")})
assert (min(v[0] for v in SWEEP.values()), max(v[0] for v in SWEEP.values())) == (-5.5, 8.5)
assert sorted(k for k, v in SWEEP.items() if v[1] < 0.05) == [("multi", "1024", "H"), ("single", "1024", "W")]
assert round(min(v[1] for v in SWEEP.values()), 4) == 0.0095
assert (SWEEP[("multi", "1024", "H")][0], SWEEP[("single", "1024", "W")][0]) == (8.5, 5.5)
ps = sorted(v[1] for v in SWEEP.values())
assert min(min(1.0, p_ * (len(ps) - k)) for k, p_ in enumerate(ps)) > 0.05      # Holm over the ten: none survives

# ------------------------------------------------------------------ checks: G2 vs TC context, draw-to-draw swing
F2d = json.loads((E / "long_doc_fixed_g/analysis.json").read_text())
LD = json.loads((E / "long_doc_cohort/analysis.json").read_text())
assert (round(F2d["arms"]["G2"]["mean_tokens"]), round(F2d["arms"]["TC"]["mean_tokens"])) == (1958, 939)
assert (LD["2048"]["arms"]["TC"]["em"], F2d["arms"]["TC"]["em"]) == (83, 63)
hdr = json.loads((E / "long_doc_cohort/manifest.jsonl").open().readline())
assert hdr["counts"]["examples"] == 3357
assert "validation-0000{0,1,2}-of-00007.parquet" in (E / "long_doc_cohort/PROTOCOL.md").read_text()

# ------------------------------------------------------------------ checks: verdict-weighted judge agreement
import csv
FU = E / "prompt_validation/followup"
key = json.loads((FU / "judge_validation_key.json").read_text())
jr = jl(FU / "judge_records.jsonl")
pc = sum(r["judge"] for r in jr) / len(jr)
assert (sum(r["judge"] for r in jr), len(jr)) == (1079, 1600)


def weighted(sheet, col):
    agree = {True: [0, 0], False: [0, 0]}
    for r in csv.DictReader(open(FU / sheet)):
        lab = r[col].strip().upper()
        if lab not in ("CORRECT", "INCORRECT"): continue
        j = key[r["item"]]["judge"]; agree[j][1] += 1; agree[j][0] += (lab == "CORRECT") == j
    return round(100 * (pc * agree[True][0] / agree[True][1] + (1 - pc) * agree[False][0] / agree[False][1]), 1)


assert weighted("judge_validation_sheet.csv", "human_label(CORRECT/INCORRECT)") == 92.6
assert weighted("judge_validation_sheet_B.csv", "label_B(CORRECT/INCORRECT/HARD)") == 97.6

# ------------------------------------------------------------------ checks: detectable difference at n = 200
mdd = lambda pd: 100 * math.sqrt((1.959964 + 0.841621) ** 2 * pd / 200)
assert (round(mdd(0.10)), round(mdd(0.20))) == (6, 9)
assert 0.10 <= 20 / 200 and 40 / 200 <= 0.20      # G vs N_raw (11 + 9) and long-document TC vs N (26 + 14) discordant
assert 'PRECIS_ENABLE_LIST_EXTRACTION (default: False)' in (ROOT / "backend/src/precis/pipeline/structural.py").read_text()

# ------------------------------------------------------------------ R2 (first): renumber [36]-[53] -> [39]-[56]
paras = list(d.body.iter(q("p")))
for n in range(53, 35, -1):
    for p in paras:
        while "[%d]" % n in d.text(p):
            d.replace(p, "[%d]" % n, "[%d]" % (n + 3))
NEW_REFS = [
    "[36]B. Jin, J. Yoon, J. Han, and S. O. Arik, “Long-context LLMs meet RAG: Overcoming challenges for long inputs in "
    "RAG”, in Proc. 13th Int. Conf. on Learning Representations (ICLR 2025), 2025. arXiv:2410.05983.",
    "[37]A. Jimeno Yepes, Y. You, J. Milczek, S. Laverde, and R. Li, “Financial report chunking for effective retrieval "
    "augmented generation”, arXiv preprint arXiv:2402.05131, 2024.",
    "[38]L. Zheng, W.-L. Chiang, Y. Sheng, S. Zhuang, Z. Wu, Y. Zhuang, Z. Lin, Z. Li, D. Li, E. P. Xing, H. Zhang, "
    "J. E. Gonzalez, and I. Stoica, “Judging LLM-as-a-judge with MT-Bench and Chatbot Arena”, in Advances in Neural "
    "Information Processing Systems (NeurIPS 2023), Datasets and Benchmarks Track, vol. 36, 2023. arXiv:2306.05685.",
]
ref = P[167]
assert d.text(ref).startswith("[35]")
for t in NEW_REFS:
    ref = d.clone_after(ref, P[167], [(t, {})])

# ------------------------------------------------------------------ abstract (R1, R4, S4, S14)
setp(4, "Retrieval-augmented generation on local hardware must fit evidence into a small context, and pages whose "
        "answers sit in tables raise the question of how much of their structure to keep. We study it with Précis, an "
        "offline pipeline that keeps HTML tables and lists in native form and packs them first under an estimated-token "
        "ceiling with a guarded structural-priority rule (G), against cheap baselines on table-bearing Natural Questions "
        "pages. On short pages, the system's own rewrite of tables as extracted sentences cut exact match (EM) to 14.0%, "
        "against 49.5% for native tables (in-sample); against tag-stripped chunks, the cheap "
        "structure-keeping baselines were never significantly ahead (−2.5 to +6.0 points at the 2,048 ceiling on the protocol-first cohorts). On a fresh cohort G (48.0% EM) was level with "
        "raw-markup, table-aware and hybrid chunks and whole-document Markdown (47.0 to 49.0%), with three generators from "
        "two model families. On 200 full Wikipedia pages, where the 2,048-token ceiling binds, G was the worst arm (22.0% "
        "EM against 33.0 to 41.5%): same-document fact suppression removed every prose fact, leaving lists and "
        "reference text in half-filled contexts; a repaired rule (G2) raised EM on a fresh draw from 17.5% to 33.5%, non-inferior to table-aware chunking. "
        "A short-answer prompt format raised EM by 25.0 to 36.5 points, but an LLM judge, checked against two blind author "
        "labellers (92% and 97% agreement), saw gains of 1.5 to 12.0 points. Native structure should be kept but not at "
        "the expense of prose, and strict-match comparisons conflate answer format with accuracy.", lead="Abstract: ")

# ------------------------------------------------------------------ Section I (S8, S11, R1, R2)
rep(7, "On local hardware, memory, latency and model size limit the context a generator can use, and long contexts are "
       "used unevenly [3], so evidence has to be selected under a budget.",
       "On local hardware, small generators and limited memory favour short prompts, and long contexts are used unevenly "
       "[3], so evidence has to be selected under a budget; this paper treats that budget as a design parameter (2,048 "
       "estimated tokens in most experiments), not as a measured hardware limit.")
rep(9, "for documents whose answers depend on tables and lists,", "for table- and list-bearing pages,")
rep(10, "(i) an ablation showing that rewriting tables as extracted sentences is the main source of loss on a "
        "table-bearing cohort, with the caveat that G was designed on it;",
        "(i) an ablation showing that the system's own rewrite of tables as extracted sentences is the main source of loss "
        "on a table-bearing cohort (in-sample for G), and no significant advantage of the cheap structure-keeping "
        "baselines over tag-stripped chunks on the protocol-first cohorts;")
rep(10, "The pipeline, protocols, per-case records and scripts are released (Section X).",
        "Extending [24] and HtmlRAG [25], the study sets a structure-first rule against table-aware, hybrid and whole-document "
        "baselines on the same table-bearing questions under one budget, including full pages, and separates answer format "
        "from abstention wording. The pipeline, protocols, per-case records and scripts are "
        "released (Section X).")

# ------------------------------------------------------------------ Section II (R2, S12, S13)
rep(14, "Long-context models can match RAG when resources allow, at a higher cost [7], and retrieval helps even models "
        "with extended windows [8];",
        "Long-context models outperform RAG on average when well resourced, at a much higher cost [7], retrieval helps even "
        "models with extended windows [8], and adding retrieved passages to a long-context model can lower its accuracy "
        "[36];")
rep(16, "Open information extraction supplies",
        "Element-based chunking, which splits a document at its titles, tables and list items, improved RAG on financial "
        "reports [37]; the table-aware baseline TC of Section 6.3 follows that idea. Open information extraction supplies")
rep(17, "and HtmlRAG keeps cleaned and pruned HTML instead of plain text for retrieved web pages [25].",
        "and HtmlRAG keeps cleaned and pruned HTML for retrieved web pages and, under a fixed context window, finds it better "
        "than plain-text and Markdown conversions and than chunk-based refiners on several question-answering sets, Natural "
        "Questions among them [25].")
rep(17, "Among the studies reviewed here, none compares table-preserving packing with chunked, whole-document and hybrid "
        "structure-keeping baselines on the same questions under one token budget.",
        "None of them compares a structure-first packing rule with table-aware and hybrid chunking and whole-document "
        "Markdown on the same table-bearing questions under one token budget, or examines such a rule on long pages where "
        "that budget binds.")
rep(20, "model-judged answer equivalence tracks human judgement more closely [34],",
        "model-judged answer equivalence tracks human judgement more closely [34], although language-model judges have "
        "known position and verbosity biases [38],")

# ------------------------------------------------------------------ Sections IV-V (R3, S10)
rep(42, "with token streaming, JSON Web Token authentication, per-client rate limiting, input limits and a basic "
        "prompt-injection pattern filter, and a deterministic intent router decides whether a question concerns the "
        "uploaded documents.",
        "with token streaming, authentication, rate limiting, input limits, a basic prompt-injection filter and a "
        "rule-based intent router; none of these service features was evaluated.")
rep(43, "and a bounded in-memory session store (at most 1,000 sessions, 20 turns each, four-hour expiry)",
        "and a bounded in-memory session store")
rep(49, "When the feature flag PRECIS_ENABLE_LIST_EXTRACTION is on, HTML tables and lists are separated from prose.",
        "When the feature flag PRECIS_ENABLE_LIST_EXTRACTION is on, HTML tables and lists are separated from prose; the "
        "flag is off by default, so the released application answers with the fact-only configuration (Précis v3 below) "
        "unless it is set, and with G when it is.")

# ------------------------------------------------------------------ Section 6.1 (S3)
rep(60, "which is the size of the smallest differences reported.",
        "which is the size of the smallest differences reported, so non-inferiority verdicts that rest on one or two cases "
        "are within that noise. With the observed 10 to 20% discordant pairs, a paired comparison of 200 cases detects a "
        "difference of about 6 to 9 points with 80% power at a two-sided 5% level; smaller true differences can go "
        "undetected.")

# ------------------------------------------------------------------ Section 6.2-6.3 (R1, S9)
rep(68, "The large structure effect of Table 4 is therefore a loss from destroying structure, not a gain over cheap "
        "structure-keeping alternatives.",
        "The large structure effect of Table 4 is therefore a loss from this conversion, not a gain over cheap "
        "structure-keeping alternatives. Taking every cheap structure-keeping baseline (N_raw, W, TC and H) that was run on a "
        "protocol-first cohort, at the 2,048 ceiling and against that cohort's tag-stripped chunks, gives ten comparisons: "
        "+3.0 to +5.0 points on the fresh cohort, and −2.5 (N_raw) to +6.0 (TC) on the two long-document draws; none is "
        "significant (smallest p = 0.076). At 1,024 tokens on long pages raw-markup chunks were behind (−10.0 points, "
        "p = 0.001), and D, which keeps tables but not lists, was behind on the whole fresh cohort (−4.5). In the exploratory "
        "sweeps (Table 6) H and W against budgeted stripped chunks ranged from −5.5 to +8.5 points, none significant after "
        "Holm correction over these ten (smallest unadjusted p = 0.0095). Keeping structure was therefore never "
        "shown to beat stripping it at the main ceiling, and keeping raw markup can cost accuracy on long pages.")
rep(74, "102 smaller than N_raw's and 122 larger than N_clean's.",
        "102 smaller than N_raw's and 122 larger than N_clean's. These counts cover the context only: G also needs "
        "coreference resolution, parsing and SDH scoring at ingestion, whereas W and TC need only an HTML conversion.")

# ------------------------------------------------------------------ Section 6.4 (I-2, I-4, S2, S4, S5, R3)
rep(77, "mean 1523 estimated tokens", "mean 1,523 estimated tokens")
tcell_rep(78, "923 / 1000", "923 / 1,000")
tcell_rep(78, "1654 / 1440", "1,654 / 1,440")
rep(82, "(902 eligible questions among 3,357 examples; seed 42)",
        "(902 eligible questions among the 3,357 examples of the first three of the seven development shards, as the "
        "protocol fixed; seed 42)")
rep(82, "Table 7 gives the results.",
        "Table 7 gives the results. A GPU out-of-memory error stopped the run once; a retry was added, the completed cases "
        "were kept and none was regenerated (as for the other interrupted runs, logged in the repository).")
rep(86, "Structure-first packing with same-document suppression is therefore unsuitable for long single documents,",
        "Same-document suppression and unfiltered reference lists, rather than the order of packing as such, are the likely "
        "reasons (a reading made after the results) that G is unsuitable for long single documents,")
rep(87, "and G2 used nearly the whole budget (1,958 estimated tokens on average).",
        "and G2 used nearly the whole budget (1,958 estimated tokens on average, against 939 for table-aware chunks, so its "
        "parity comes at about twice their context). Table-aware chunks scored 63 on this draw against 83 on the first, so "
        "differences between draws are as large as the margin.")
rep(87, "so it is a repaired variant, not a separately tuned method.",
        "so it is a repaired variant, not a separately tuned method; it still packs structure first, its two changes were "
        "not tested separately, and it is implemented in the experiment script (scripts/run_long_doc_fixed_g.py), not yet "
        "in the released pipeline.")

# ------------------------------------------------------------------ Section 6.6 (R4, S6, S13)
rep(99, "The judge agreed with two independent human labellers on 92% and 97% of the outputs each could label",
        "The judge agreed with two human labellers (authors, labelling blind) on 92% and 97% of the outputs each could label")
rep(101, "Cohen's κ = 0.84, which the verdict-balanced sample pushes upwards)",
         "Cohen's κ = 0.84, which the verdict-balanced sample pushes upwards; 92.6% when the two verdicts are weighted by "
         "their frequency among the 1,600 outputs)")
rep(101, "so agreement does not differ visibly between the formats being compared.",
         "so agreement does not differ visibly between the formats being compared, which is where a verbosity bias of the "
         "judge [38] would show.")
rep(101, "(96.5%, Wilson 95% interval 90–99%; κ = 0.93)", "(96.5%, Wilson 95% interval 90–99%; κ = 0.93; 97.6% weighted)")

# ------------------------------------------------------------------ Sections 6.9-6.10 (R1, S1, S4, S7, S14, R4)
rep(115, "Structure matters; structure-first packing does not help.", "Keep structure, but not at the expense of prose.")
rep(115, "Rewriting prose as extracted facts did not help either: the fact-only configuration trailed plain chunks in both "
         "settings where the two were compared.",
         "Rewriting prose as extracted facts did not help either: the fact-only configuration was behind plain chunks in "
         "both settings where the two were compared, although the question-level interval of Section 6.7 includes zero and "
         "only one of the eight Holm-adjusted tests of Section 6.6 is below 0.05.")
rep(115, "Rewriting tables as extracted sentences was the weakest variant,",
         "The system's rewrite of tables as extracted sentences was the weakest variant, the cheap "
         "structure-keeping baselines were never significantly ahead of tag-stripped chunks at the 2,048 ceiling,")
rep(116, "Concise prompting raised exact match by 17 to 40 points;",
         "The concise prompt raised exact match by 17 to 40 points (Table 8);")
rep(119, "all but one use MRQA's extracts of at most 800 words", "all but the two long-document draws use MRQA's extracts of "
         "at most 800 words")
rep(119, "(two general-purpose generators from two other model families, answering",
         "(a general-purpose Qwen generator and a Gemma generator, answering")
rep(119, "The equivalence judge is a single local model checked by two labellers on 100 outputs",
         "The equivalence judge is a single local model checked by two author labellers on 100 outputs")
rep(119, "its negation flag is unreliable.",
         "its negation flag is unreliable; the fact-level audit showed the stored labels to the annotators, which may have "
         "anchored their judgements.")

# ------------------------------------------------------------------ Section VII (R1, R4, S1, S4, S5)
setp(121, "This paper evaluated how much a structure-aware packing rule adds to local RAG over table-bearing pages and how "
          "much of a measured difference comes from answer format. The system's own rewrite of tables as extracted "
          "sentences cost most of the accuracy on a table-bearing cohort (14.0% against 49.5% exact match for native "
          "tables, in-sample), but against tag-stripped chunks the cheap structure-keeping baselines were never significantly "
          "ahead (−2.5 to +6.0 points at the 2,048 ceiling on the protocol-first cohorts). On a fresh protocol-first "
          "cohort the guarded structural-priority rule G (48.0%) was not distinguishable from cheap structure-keeping "
          "baselines, its non-inferiority depended on a post hoc margin, it was not shown to match hybrid table-aware "
          "retrieval, and it lost when the ceiling was cut to 256 tokens; its smaller context holds only against the "
          "authors' own earlier pipeline. On full Wikipedia pages, where the ceiling binds, it was the worst arm (22.0% EM "
          "against 33.0 to 41.5%), because same-document suppression dropped every prose fact and left lists and "
          "unfiltered reference text in contexts that used about half the budget; table-aware chunking was best, and a repaired rule that keeps prose (G2) gained 16.0 "
          "points over G on a fresh draw and was non-inferior to table-aware chunking, with about twice its context. The "
          "fact-only configuration was numerically behind plain chunks and lost the answer string before generation in 21 "
          "of 100 contexts. A concise-answer prompt raised exact match in every model–retrieval combination, but a 2×2 "
          "decomposition attributes the gain mainly to answer format, shows that the abstention wording interacts with the "
          "generator, and an equivalence judge sees much smaller differences. On short pages at the 2,048 ceiling the "
          "answer string survived retrieval and packing in nearly every context and most loss arose at generation and "
          "strict matching; on full pages G lost it in packing (84 of 200 "
          "contexts against 140 to 172 for the baselines). Native structure should be kept but not at the expense "
          "of prose, and strict-match comparisons need an equivalence measure and controlled prompts.")
rep(122, "(i) table-and-text benchmarks such as NQ-Tables [21] and OTT-QA [22], same-domain distractors",
         "(i) table-and-text benchmarks such as NQ-Tables [21] and OTT-QA [22], a header-aware row-linearisation baseline, "
         "same-domain distractors")

# ------------------------------------------------------------------ Section X (R5 note, S2)
rep(129, "(author-held files, not an external registry).",
         "(author-held files, not an external registry); operational interruptions of the runs and the retries added are "
         "logged in each experiment's DEVIATIONS.md, and no completed case was regenerated.")

rep(10, "its fact-only contexts trail plain chunks", "its fact-only contexts are behind plain chunks")
rep(119, "its fact-only contexts trail chunks", "its fact-only contexts are behind chunks")


def table1_row(after_first, cells):
    """Insert a Table 1 row (cloned from the row whose first cell is after_first) after that row."""
    import copy
    for tr in P[21].findall("w:tr", NS):
        tcs = tr.findall("w:tc", NS)
        if d.text(tcs[0]) == after_first:
            new = copy.deepcopy(tr)
            for tc, txt in zip(new.findall("w:tc", NS), cells):
                d.set_runs(tc.find("w:p", NS), [(txt, {})])
            tr.addnext(new); return
    raise KeyError(after_first)


table1_row("Sclar et al. [35]", ["Zheng et al. [38]", "LLM-as-a-judge", "Agreement and bias analysis of LLM judges"])
table1_row("Sclar et al. [35]", ["Jimeno Yepes et al. [37]", "Chunking for RAG", "Element-type chunking"])
table1_row("Sclar et al. [35]", ["Jin et al. [36]", "Long-context models in RAG", "Effect of more retrieved passages"])

rep(115, "for long ones, table-aware chunks or the repaired G2 are clearly better than G.",
         "for long ones, table-aware chunks or the repaired G2 (at about twice their context) are clearly better than G.")

# ------------------------------------------------------------------ length: compressions that keep every result (J.UCS 25 pp)
assert d.text(P[91]).startswith("A staged prompt comparison") and d.text(P[91]).endswith("it is not counted as evidence.")
rep(92, "the guardrails were fixed after the exploratory prompt comparison had shown 48% containment",
        "the guardrails were fixed after an earlier exploratory prompt comparison (on 101 and 100 other samples, not "
        "counted as evidence) had shown 48% containment")
d.delete(P[91])
rep(80, "The curves are not monotone (G scores 90 at 1,024 and 86 at 2,048 on the corpora, and the chunk arm 89, 87 and 87 "
        "across the single-document ceilings), which is consistent with noise of several cases.",
        "The curves are not monotone, which is consistent with noise of several cases.")
rep(129, "The generators were run through Ollama (qwen2.5-coder:7b and qwen3.5:4b, Q4_K_M quantisation, plus qwen3.5:9b "
         "and gemma4:e4b for the second and third generator and gemma4:12b for the equivalence judge)",
         "The generators and the judge of Table 3 were run through Ollama (the two main generators with Q4_K_M "
         "quantisation)")
rep(131, "computed the re-analyses added in the last three versions (scripts/paper_checks_v4.py, scripts/paper_checks_v5.py "
         "and the analysis scripts of the generator-family and long-document experiments)",
         "computed the re-analyses of the later versions (scripts/paper_checks_v4.py, scripts/paper_checks_v5.py, the "
         "experiment analysis scripts and scripts/revise_paper_v8.py)")
rep(60, "With the observed 10 to 20% discordant pairs, a paired comparison of 200 cases detects a difference of about 6 to 9 "
        "points with 80% power at a two-sided 5% level; smaller true differences can go undetected.",
        "With 10 to 20% discordant pairs, 200 paired cases detect about 6 to 9 points at 80% power (two-sided 5% level).")

B2_OLD = d.text(P[201])
assert B2_OLD.startswith("B.2 Negation-rendering defect and other implementation notes. ")
for keep in ("9 of 200 stored contexts of F", "4 of the 100 Précis contexts", "11 of 200 contexts of A", "9 of 200 of E",
             "7 of 200 benchmark samples", "9 of 9 F contexts", "16 of 16 prompt-experiment generations", "141 becomes 142",
             "159 for chunks", "108 of the 200 G contexts", "53 of 108", "24 of 55", "5 against 5", "503 tests in 17 modules",
             "Python 3.12.3, spaCy 3.8.14"):
    assert keep in B2_OLD, keep
setp(201, "An earlier context renderer inserted a NOT marker for every negated fact even when the verb phrase already carried "
          "the negation word (“The framework NOT does NOT subsidize …”); stored polarity was correct. The doubled marker "
          "occurs in 9 of 200 stored contexts of F, none of G's and 4 of the 100 Précis contexts of the prompt experiment "
          "(with the current extractor, in 11 of 200 contexts of A, 9 of 200 of E and 7 of 200 benchmark samples). "
          "Regenerating each affected context with the original model, prompt and decoding reproduced every stored outcome "
          "(9 of 9 F contexts, 16 of 16 prompt-experiment generations), and removing the marker changed no exact-match "
          "outcome and one benchmark containment outcome (Précis v3: 141 becomes 142 of 200, against 159 for chunks). The "
          "renderer no longer adds the marker when the verb phrase carries a negation cue; NOT markers from negation words in "
          "table cells or titles are not addressed. The table renderer gives empty header cells a generated name (Col_n, as in Appendix A.3) "
          "and can leave row labels empty when a source table spans cells; this occurs in 108 of the 200 G contexts of the "
          "fresh cohort, where G's exact match (53 of 108) was no lower than on its other table contexts (24 of 55) and equal "
          "to N_raw's (5 against 5 discordant cases). Other observed defects are heuristic adjunct typing (“to the "
          "warehouse” typed as both time and recipient), some empty objects, duplicated coordination facts and closed "
          "reporting-verb lists (“hypothesized that …” is typed asserted). The test suite has 503 tests in 17 modules, all "
          "passing (Python 3.12.3, spaCy 3.8.14).", lead="B.2 Negation-rendering defect and other implementation notes. ")

IP_OLD = d.text(P[60])
for keep in ("10,000 resamples", "3 to 7 points", "Holm over their 15 contrasts", "187 distinct questions", "benchmark 74",
             "3 of 200 exact-match outcomes", "97.5% interval", "seven comparisons"):
    assert keep in IP_OLD, keep
setp(60, "Each analysis has one declared status. (a) The original table cohort (Table 4) is in-sample, because G was "
         "designed on it, and descriptive (unadjusted exact McNemar tests, question-level bootstrap intervals). (b) On the "
         "fresh cohort the primary family (exact match; G against D, F2, N_raw and N_clean; two-sided exact McNemar, Holm "
         "over four contrasts) was fixed in a protocol before any model call. (c) Baseline adequacy (Section 6.3) compares "
         "G with seven arms by the lower bound of a 99% question-level bootstrap interval (10,000 resamples); because the "
         "5-point non-inferiority margin was chosen after the fresh-cohort results (and before W, TC and H were run), "
         "verdicts are given for margins of 3 to 7 points, with Newcombe paired score intervals and a Bonferroni level for "
         "seven comparisons as checks. (d) In the prompt experiment (Section 6.6) the primary test is one-sided McNemar for "
         "qwen3.5:4b with Précis v3. (e) On the long-document cohort (Section 6.4) the primary family (exact match at the "
         "2,048 ceiling; G against N, N_raw, W, TC and H; non-inferiority at 5 points by 99% bootstrap intervals; two-sided "
         "exact McNemar with Holm) and the margin were fixed before the draw, and G2 was tested on a second, fresh draw "
         "under its own protocol (G2 against G, and non-inferiority to TC at 5 points by a 97.5% interval; Holm over the "
         "two). Everything else (the ceiling sweeps, with Holm over their 15 contrasts, the threshold sensitivity, the "
         "strata and the 2×2 follow-up) is exploratory. The protocols are author-held files whose SHA-256 hashes and time "
         "stamps were written before the model calls; they were neither registered externally nor under version control "
         "during the runs, so their order relative to the data cannot be verified independently, and they are called "
         "protocol-first below. Clustering is handled by resampling questions (187 distinct questions in the 200 cases of "
         "the original cohort, 74 in the 200-sample benchmark, distinct by construction elsewhere). Each case is a single "
         "greedy generation; repeating identical contexts changed 3 of 200 exact-match outcomes (Section 6.5), the size of "
         "the smallest differences reported, so verdicts that rest on one or two cases are within that noise. With 10 to "
         "20% discordant pairs, 200 paired cases detect about 6 to 9 points at 80% power (two-sided 5% level). A "
         "non-significant difference is never read as equivalence.", lead="Inference plan. ")
rep(110, "where it formed the whole context (Précis v3, Sections 6.6 and 6.7) it trailed plain chunks.",
         "where it formed the whole context (Précis v3, Sections 6.6 and 6.7) it was behind plain chunks.")

rep(115, "structure-first packing was clearly harmful, and a repaired variant",
         "G's structure-first packing with same-document suppression was clearly harmful, and a repaired variant")

# ------------------------------------------------------------------ consistency checks on the result
full = "\n".join(d.text(p) for p in d.body.iter(q("p")))
for bad in ("trail", "ten comparisons on the protocol-first cohorts (N_raw, W, TC, H and G", "filled the context", "filled its contexts", "three model families", "independent human labellers", "non-inferior to it.", "1523", "923 / 1000"):
    assert bad not in full, bad
cited = set()
body_txt = full.split("XII. REFERENCES")[0] + full.split("APPENDIX A.")[1]
for m in re.finditer(r"\[(\d+)\](?:\s*[–-]\s*\[(\d+)\])?", body_txt):
    a = int(m.group(1)); cited |= set(range(a, int(m.group(2) or a) + 1))
listed = {int(x) for x in re.findall(r"^\[(\d+)\]", full.split("XII. REFERENCES")[1].split("APPENDIX A.")[0], re.M)}
assert listed == set(range(1, 57)) and cited == listed, (sorted(listed - cited), sorted(cited - listed))
d.save(DST)
print("wrote", DST)
