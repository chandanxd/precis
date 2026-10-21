"""Build Precis_paper_clean_plane_revised_v5.docx from v4 in response to the simulated five-seat review of v4
(paper/REVIEW_v4_EL_JUCS.md): the fact-only configuration reported as a negative result instead of "untested" (DA C1),
abstention against answerability, stored generation latency, the placeholder-header defect, wording fixes, the gemma4
reference, and the college-template front matter removed so the text can be set in the Engineering Letters or J.UCS
template.

  backend/venv/bin/python scripts/revise_paper_v5.py
New numbers come from results/paper_checks/v5_reanalysis.json (scripts/paper_checks_v5.py). v4 is left untouched.
"""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from docx_tools import Doc, NS, q

SRC = ROOT / "paper/research-paper/Precis_paper_clean_plane_revised_v4.docx"
DST = ROOT / "paper/research-paper/Precis_paper_clean_plane_revised_v5.docx"
V5 = json.loads((ROOT / "results/paper_checks/v5_reanalysis.json").read_text())
d = Doc(SRC)
P = d.orig                      # handles by v4 body index


def setp(i, text, lead=None):
    d.set_text(P[i], text, lead=lead); return P[i]


def rep(i, old, new):
    d.replace(P[i], old, new)


# numbers quoted below, checked against the re-analysis so the text cannot drift from the records
ab = V5["abstention_vs_answerability_2x2"]
assert ab["qwen2.5-coder:7b|naive_rag|standard"]["answer_in_ctx"] == 100
assert ab["qwen2.5-coder:7b|precis_full|standard"]["answer_in_ctx"] == 79
assert (ab["qwen2.5-coder:7b|precis_full|sent_token"]["abst"], ab["qwen2.5-coder:7b|precis_full|sent_token"]["abst_answer_in_ctx"]) == (60, 46)
assert all(v["abst"] == v["abst_answer_in_ctx"] for k, v in ab.items() if "|naive_rag|" in k)
assert (V5["fresh_abstention_vs_answerability"]["G"]["abstained"], V5["fresh_abstention_vs_answerability"]["G"]["abstained_answer_in_ctx"]) == (38, 37)
tr = V5["g_table_rendering_defect"]
assert (tr["cases"], tr["by_kind"]["placeholder_header"], tr["g_em_defective"], tr["G_vs_N_raw_discordant"]) == (108, 103, 53, [5, 5])
assert round(tr["g_em_rate_other_table_contexts"] * tr["n_other_table_contexts"]) == 24 and tr["n_other_table_contexts"] == 55
lat = V5["generation_latency_ms"]
med = [v["median"] for v in lat.values()]; p90 = [v["p90"] for v in lat.values()]; mx = max(v["max"] for v in lat.values())
assert (round(min(med) / 1000, 2), round(max(med) / 1000, 2), round(min(p90) / 1000, 1), round(max(p90) / 1000, 1), round(mx / 1000, 1)) == (0.22, 0.93, 0.6, 1.9, 11.5)
cut = [1 - lat[f"{m}|{c}|concise"]["median"] / lat[f"{m}|{c}|standard"]["median"]
       for m in ("qwen2.5-coder:7b", "qwen3.5:4b") for c in ("naive_rag", "precis_full")]
assert (round(min(cut) * 100), round(max(cut) * 100)) == (41, 63), cut

# ================================================================== front matter: drop the college template
setp(0, "KEEPING TABLES INTACT UNDER A TOKEN BUDGET: STRUCTURE, SIMPLE BASELINES AND ANSWER FORMAT IN LOCAL "
        "RETRIEVAL-AUGMENTED QUESTION ANSWERING")
setp(1, "Chandan D, M P Jeevan Gowda, Bhimsen and Chandu S")          # one shared affiliation: no superscripts
setp(2, "Corresponding author: Chandan D, e-mail: [to be added]")
d.move_after(P[3], [P[2]])                                            # affiliation first, then the contact line
ABSTRACT = (
    "Retrieval-augmented generation on local hardware must fit evidence into a small context, and documents whose answers sit "
    "in tables raise the question of how much of their structure to keep. We study it with Précis, an offline pipeline that "
    "keeps HTML tables and lists in native form and packs them under an estimated-token ceiling with a guarded "
    "structural-priority rule (G). On a 200-case table-bearing cohort on which G was designed, rewriting tables as extracted "
    "sentences cut exact match (EM) to 14.0%, against 49.5% for native tables. On a fresh protocol-first cohort of 200 "
    "questions, the arms that kept table and list markup, G (48.0% EM), raw-markup chunks (47.0%), table-aware chunks (48.0%), "
    "whole-document Markdown (49.0%) and hybrid table-aware retrieval (49.0%), were within 2 points of one another; G's "
    "non-inferiority depends on a margin chosen after the results, and G lost when the ceiling was cut to 256 tokens. The "
    "system's fact-only configuration trailed plain chunks wherever the two were compared, and its contexts lacked the answer "
    "in 21 of 100 cases against none for chunks. In a 2×2 prompt experiment a short-answer format raised EM by 25 to 37 "
    "points while an LLM judge (92% agreement with one human labeller on 90 outputs) saw gains of 2 to 12 points, and in this "
    "exploratory follow-up an “Insufficient information” line cost the code-specialised generator 22 to 29 points of "
    "judged-correct answers, mostly through abstentions on contexts that held the answer. On such documents keeping "
    "structure matters, simple structure-keeping baselines are hard to beat, and strict-match comparisons conflate answer "
    "format with accuracy.")
KEYWORDS = ("Retrieval-Augmented Generation, Table Question Answering, Context Budget, Non-inferiority, Answer-Format "
            "Sensitivity, Evaluation Methodology.")
kw = d.clone_after(P[2], P[8], [("Keywords: ", {"bold": True}), (KEYWORDS, {"bold": False})])
d.clone_after(P[2], P[8], [("Abstract: ", {"bold": True}), (ABSTRACT, {"bold": False})])
for i in (4, 5, 6): d.delete(P[i])           # supervisor line, ARTICLE INFO box, college copyright line
for i in (24, 29, 51, 67, 72, 80, 87, 97, 103, 113, 118, 132):
    assert d.text(P[i]).strip() == "Source: Authors, (2026).", i
    d.delete(P[i])
rep(44, "Source: Authors, (2026). ", "")

# ================================================================== DA C1: the fact layer is tested where it is the whole context
rep(9, "The fact layer is part of the released system but is not what the experiments test: it contributed 111 facts to 200 "
       "contexts of G, and an audit (Section 6.8) found its negation flag unreliable.",
    "No experiment isolates the fact layer's contribution inside G, to which it added only 111 facts over 200 contexts; where "
    "the fact-only configuration (Précis v3) was compared with plain chunks (Sections 6.6 and 6.7) it was behind, and an audit "
    "(Section 6.8) found its negation flag unreliable.")
rep(11, "(v) a negative result on the fact layer's negation labels.",
    "(v) negative results on the fact layer: its fact-only contexts trail plain chunks and its negation labels are unreliable.")
rep(99, "The chunked baseline was numerically ahead of Précis v3 in all eight model–prompt cells of Table 7",
    "The chunked baseline was numerically ahead of Précis v3, the fact-only configuration, in exact match and in containment "
    "in all four model–prompt cells of Table 7")
rep(99, "only one difference remains below 0.05.",
    "only one difference remains below 0.05. Context coverage accounts for part of the gap: an answer string occurred in all "
    "100 chunked contexts but in only 79 of the 100 fact-only contexts, so the fact layer lost the answer before generation in "
    "21 cases.")
rep(115, "The SVOA fact layer was not part of any accuracy experiment above. In the 200 contexts of G on the original cohort only "
         "111 facts were packed in total, none with a negation marker, so in these cohorts the fact layer contributes little to "
         "what G packs, and no ablation shows what it adds.",
    "No experiment above isolates the SVOA fact layer's contribution to G. In the 200 contexts of G on the original cohort only "
    "111 facts were packed in total, none with a negation marker, so in these cohorts it contributes little to what G packs; "
    "where it formed the whole context (Précis v3, Sections 6.6 and 6.7) it trailed plain chunks.")
rep(201, "none of the experiments of Section VI tests its effect on answers.",
    "Section VI compares the fact-only configuration with chunks (Sections 6.6 and 6.7) but does not isolate the layer's "
    "contribution inside G.")
rep(121, "For short documents, passing the document as Markdown or using table-aware chunks serves as well as G.",
    "For short documents, passing the document as Markdown or using table-aware chunks serves as well as G. Rewriting prose as "
    "extracted facts did not help either: the fact-only configuration trailed plain chunks in both settings where the two were "
    "compared.")
rep(125, "(7) The fact layer's effect on answers is untested and its negation flag is unreliable.",
    "(7) The fact layer's contribution inside G is not isolated, its fact-only contexts trail chunks, and its negation flag is "
    "unreliable.")
rep(127, "its smaller context holds only against the authors' own earlier pipeline.",
    "its smaller context holds only against the authors' own earlier pipeline. The fact-only configuration trailed plain "
    "chunks and lost the answer string before generation in 21 of 100 contexts.")

# ================================================================== abstention against answerability (R1 W1, DA M1)
rep(104, "(55 to 45 and 43 to 35; p = 0.006 and 0.021).",
    "(55 to 45 and 43 to 35; p = 0.006 and 0.021). These abstentions were mostly false: every abstention on a chunked context, "
    "and 46 of the 60 sentence-format abstentions on Précis v3 contexts, came from a context that contained an answer string.")
rep(104, "for the code-specialised generator, lowers answer quality.",
    "for the code-specialised generator, causes abstentions on answerable contexts.")
rep(105, "(95% intervals +6.5 to +18.0 and +3.5 to +18.5).",
    "(95% intervals +6.5 to +18.0 and +3.5 to +18.5), so a short answer helped the judged score mainly on fact contexts, whose "
    "sentence fragments a sentence answer tends to restate.")
rep(110, "and the remaining loss was at generation (abstentions and wrong answers) and at exact matching.",
    "and the remaining loss was at generation (abstentions and wrong answers) and at exact matching; 37 of G's 38 abstentions "
    "came from a context that held an answer string.")

# ================================================================== wording fixes (R1 W3-W5)
rep(40, "a packed subset of facts that maximises Σ π(t,q)", "a packed subset of facts chosen greedily for a high Σ π(t,q)")
rep(107, "chunked retrieval scored higher than the fact-only Précis v3", "chunked retrieval was numerically ahead of the fact-only Précis v3")
rep(108, "The extraction rules were revised four times after inspecting failures on this split",
    "The extraction rules were revised over successive versions (v1, v1.5, v2 and v3) after inspecting failures on this split")
rep(69, "a 100-case prose-only stratum that is not analysed here.", "a 100-case prose-only stratum, which was never run.")

# ================================================================== stored generation latency (R3 W1)
rep(123, "Ingestion and query timings were not measured, so no speed claim is made,",
    "Only generation time was logged: in the main prompt experiment on the RTX 4060 host the median wall-clock time per answer "
    "was 0.22 to 0.93 s across the eight model, retrieval and prompt cells (90th percentiles 0.6 to 1.9 s; single calls up to "
    "11.5 s, consistent with model loading), and the concise prompt lowered the median by 41 to 63%. Ingestion, retrieval and "
    "CPU-only timings were not measured, so no end-to-end speed claim is made,")
rep(125, "(5) Ingestion and query latency, memory use and CPU-only operation were not measured,",
    "(5) Ingestion and retrieval latency, memory use and CPU-only operation were not measured (only GPU generation time was "
    "logged),")
rep(52, "CPU-only operation, latency and memory use were not measured.",
    "CPU-only operation, memory use and ingestion and retrieval latency were not measured; generation time is reported in "
    "Section 6.9.")

# ================================================================== placeholder-header defect (R2 W1)
rep(214, "Other observed defects are",
    "The table renderer gives header cells that are empty in the source a generated name (Col_n, as in Appendix A.3) and can "
    "leave row labels "
    "empty when a source table spans cells; such a header or an empty label column occurs in 108 of the 200 G contexts of the "
    "fresh cohort, where G's exact match (53 of 108) was no lower than on its other table contexts (24 of 55) and equal to "
    "N_raw's (5 against 5 discordant cases). Other observed defects are")

# ================================================================== acknowledgements: supervisor moves here from the title block
rep(134, "The authors acknowledge", "The authors thank Dr Kaipaa Sandhya for supervising this work, and acknowledge")
rep(134, "Ollama and the Qwen models.", "Ollama and the Qwen and Gemma models.")

# ================================================================== references: gemma4 judge, complete [8]
for tr_ in P[65 + 0].iter(q("tr")):
    cells = list(tr_.iter(q("tc")))
    if d.text(cells[0]).startswith("Replay generator"):
        d.replace(cells[1].find("w:p", NS), "gemma4:12b (Ollama)", "gemma4:12b [53] (Ollama)")
rep(147, "P. Xu, W. Ping, et al.", "P. Xu, W. Ping, X. Wu, L. McAfee, C. Zhu, Z. Liu, S. Subramanian, E. Bakhturina, M. Shoeybi, "
                                  "and B. Catanzaro")
d.clone_after(P[191], P[191], [("[53]Google DeepMind, “Gemma 4”, model, Ollama library. [Online]. Available: "
                                "https://ollama.com/library/gemma4 (accessed Oct. 19, 2026).", {})])

# ================================================================== references: renumber by first appearance (IEEE), as in v4
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
assert sorted(order) == sorted(nums), (sorted(set(nums) - set(order)), sorted(set(order) - set(nums)))
NEW = {old: k + 1 for k, old in enumerate(order)}
cite_rx = re.compile(r"\[(\d+)\]")
for el in d.body.iter(q("t")):
    if el.text and cite_rx.search(el.text):
        el.text = cite_rx.sub(lambda m: "[%d]" % NEW[int(m[1])] if int(m[1]) in NEW else m[0], el.text)
by_new = sorted(ref_els, key=lambda el: int(re.match(r"\[(\d+)\]", d.text(el))[1]))
for el in by_new: d.body.remove(el)
d.move_after(body[ref_head], by_new)

left = [d.text(p)[:60] for p in d.body.iter(q("p")) if "Source: Authors" in d.text(p) or "Impact College of Engineering and Applied Sciences (AI" in d.text(p)]
assert not left, left
d.save(DST); print("saved", DST, "| renumbered:", {k: v for k, v in NEW.items() if k != v})
