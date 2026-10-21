"""Generate the venue LaTeX sources of the Précis paper from the shared Word text (v6).

  backend/venv/bin/python scripts/build_venue_latex.py          # writes paper/venues/{el,jucs}/precis_*.tex
  (cd paper/venues/el && pdflatex precis_el && pdflatex precis_el)
  (cd paper/venues/jucs && pdflatex precis_jucs && pdflatex precis_jucs)

Body paragraphs, tables and captions are converted from the DOCX runs, so the venue text cannot drift from the Word
version; only the equations, Algorithm 1, Figures 1 and 2 (TikZ, paper/venues/common/fig{1_arch,2_flow}.tex, drawn at print size
with 8 pt labels and placed at 100%) and the J.UCS reference
entries are set by hand. Venue differences:
  EL   IAENGtran (IEEE two-column), numeric citations, Roman sections, table captions above, AI statement as a section.
  JUCS jucs2e (one column), [Name year] citations, Arabic sections, captions below, Key Words + Category, AI-use
       disclosure moved into the Methods subsection as J.UCS requires.
"""
import re, shutil, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from docx_tools import Doc, NS, q

SRC = ROOT / "paper/research-paper/Precis_paper_clean_plane_revised_v9.docx"
OUT = ROOT / "paper/venues"
d = Doc(SRC)
B = [el for el in d.body if el.tag in (q("p"), q("tbl"))]
M = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"


def find(prefix, start=0):
    """Index of the first body element whose text starts with prefix (all structure is located by text, not position)."""
    for i in range(start, len(B)):
        if d.text(B[i]).strip().startswith(prefix):
            return i
    raise KeyError(prefix)


I_REFS = find("XII. REFERENCES")
REF = {int(re.match(r"\[(\d+)\]", d.text(B[i])).group(1)): i
       for i in range(I_REFS + 1, find("APPENDIX A.")) if re.match(r"\[\d+\]", d.text(B[i]))}
assert sorted(REF) == list(range(1, 57)), sorted(REF)

# ================================================================== references
# key -> (J.UCS label, J.UCS entry). The EL entries are the manuscript's reference paragraphs themselves.
JUCS_REFS = {
 1: ("Lewis et al. 2020", "Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M., Yih, W.-t., Rocktäschel, T., Riedel, S., Kiela, D.: ``Retrieval-augmented generation for knowledge-intensive NLP tasks''; Advances in Neural Information Processing Systems 33 (NeurIPS 2020), 9459--9474."),
 2: ("Gao et al. 2024", "Gao, Y., Xiong, Y., Gao, X., Jia, K., Pan, J., Bi, Y., Dai, Y., Sun, J., Wang, M., Wang, H.: ``Retrieval-augmented generation for large language models: A survey''; arXiv preprint arXiv:2312.10997v5 (2024)."),
 3: ("Liu et al. 2024", "Liu, N. F., Lin, K., Hewitt, J., Paranjape, A., Bevilacqua, M., Petroni, F., Liang, P.: ``Lost in the middle: How language models use long contexts''; Transactions of the Association for Computational Linguistics, 12 (2024), 157--173. doi:10.1162/tacl\\_a\\_00638."),
 4: ("Karpukhin et al. 2020", "Karpukhin, V., Oguz, B., Min, S., Lewis, P., Wu, L., Edunov, S., Chen, D., Yih, W.-t.: ``Dense passage retrieval for open-domain question answering''; Proc. 2020 Conf. on Empirical Methods in Natural Language Processing (EMNLP), ACL (2020), 6769--6781."),
 5: ("Barnett et al. 2024", "Barnett, S., Kurniawan, S., Thudumu, S., Brannelly, Z., Abdelrazek, M.: ``Seven failure points when engineering a retrieval augmented generation system''; Proc. IEEE/ACM 3rd Int. Conf. on AI Engineering -- Software Engineering for AI (CAIN 2024), ACM (2024), 194--199. doi:10.1145/3644815.3644945."),
 6: ("Asai et al. 2024", "Asai, A., Wu, Z., Wang, Y., Sil, A., Hajishirzi, H.: ``Self-RAG: Learning to retrieve, generate, and critique through self-reflection''; Proc. 12th Int. Conf. on Learning Representations (ICLR 2024) (2024). arXiv:2310.11511."),
 7: ("Li et al. 2024", "Li, Z., Li, C., Zhang, M., Mei, Q., Bendersky, M.: ``Retrieval augmented generation or long-context LLMs? A comprehensive study and hybrid approach''; Proc. 2024 Conf. on Empirical Methods in Natural Language Processing: Industry Track, ACL (2024), 881--893. doi:10.18653/v1/2024.emnlp-industry.66."),
 8: ("Xu et al. 2024a", "Xu, P., Ping, W., Wu, X., McAfee, L., Zhu, C., Liu, Z., Subramanian, S., Bakhturina, E., Shoeybi, M., Catanzaro, B.: ``Retrieval meets long context large language models''; Proc. 12th Int. Conf. on Learning Representations (ICLR 2024) (2024). arXiv:2310.03025."),
 9: ("Jiang et al. 2023", "Jiang, H., Wu, Q., Lin, C.-Y., Yang, Y., Qiu, L.: ``LLMLingua: Compressing prompts for accelerated inference of large language models''; Proc. 2023 Conf. on Empirical Methods in Natural Language Processing (EMNLP), ACL (2023), 13358--13376."),
 10: ("Li et al. 2023", "Li, Y., Dong, B., Guerin, F., Lin, C.: ``Compressing context to enhance inference efficiency of large language models''; Proc. 2023 Conf. on Empirical Methods in Natural Language Processing (EMNLP), ACL (2023), 6342--6353."),
 11: ("Xu et al. 2024b", "Xu, F., Shi, W., Choi, E.: ``RECOMP: Improving retrieval-augmented LMs with context compression and selective augmentation''; Proc. 12th Int. Conf. on Learning Representations (ICLR 2024) (2024). arXiv:2310.04408."),
 12: ("Chen et al. 2024a", "Chen, T., Wang, H., Chen, S., Yu, W., Ma, K., Zhao, X., Zhang, H., Yu, D.: ``Dense X Retrieval: What retrieval granularity should we use?''; Proc. 2024 Conf. on Empirical Methods in Natural Language Processing (EMNLP 2024), ACL (2024), 15159--15177. doi:10.18653/v1/2024.emnlp-main.845."),
 13: ("Min et al. 2023", "Min, S., Krishna, K., Lyu, X., Lewis, M., Yih, W.-t., Koh, P. W., Iyyer, M., Zettlemoyer, L., Hajishirzi, H.: ``FActScore: Fine-grained atomic evaluation of factual precision in long form text generation''; Proc. 2023 Conf. on Empirical Methods in Natural Language Processing (EMNLP), ACL (2023), 12076--12100."),
 14: ("Edge et al. 2024", "Edge, D., Trinh, H., Cheng, N., Bradley, J., Chao, A., Mody, A., Truitt, S., Metropolitansky, D., Ness, R. O., Larson, J.: ``From local to global: A graph RAG approach to query-focused summarization''; arXiv preprint arXiv:2404.16130 (2024)."),
 15: ("Banko et al. 2007", "Banko, M., Cafarella, M. J., Soderland, S., Broadhead, M., Etzioni, O.: ``Open information extraction from the web''; Proc. 20th Int. Joint Conf. on Artificial Intelligence (IJCAI-07) (2007), 2670--2676."),
 16: ("Fader et al. 2011", "Fader, A., Soderland, S., Etzioni, O.: ``Identifying relations for open information extraction''; Proc. 2011 Conf. on Empirical Methods in Natural Language Processing (EMNLP), ACL (2011), 1535--1545."),
 17: ("Angeli et al. 2015", "Angeli, G., Johnson Premkumar, M. J., Manning, C. D.: ``Leveraging linguistic structure for open domain information extraction''; Proc. 53rd Annual Meeting of the ACL and 7th Int. Joint Conf. on Natural Language Processing (ACL-IJCNLP), vol. 1, ACL (2015), 344--354."),
 18: ("Kolluru et al. 2020", "Kolluru, K., Adlakha, V., Aggarwal, S., Mausam, Chakrabarti, S.: ``OpenIE6: Iterative grid labeling and coordination analysis for open information extraction''; Proc. 2020 Conf. on Empirical Methods in Natural Language Processing (EMNLP), ACL (2020), 3748--3761."),
 19: ("Pasupat and Liang 2015", "Pasupat, P., Liang, P.: ``Compositional semantic parsing on semi-structured tables''; Proc. 53rd Annual Meeting of the ACL and 7th Int. Joint Conf. on Natural Language Processing (ACL-IJCNLP), vol. 1, ACL (2015), 1470--1480."),
 20: ("Herzig et al. 2020", "Herzig, J., Nowak, P. K., Müller, T., Piccinno, F., Eisenschlos, J.: ``TaPas: Weakly supervised table parsing via pre-training''; Proc. 58th Annual Meeting of the Association for Computational Linguistics (ACL), ACL (2020), 4320--4333."),
 21: ("Herzig et al. 2021", "Herzig, J., Müller, T., Krichene, S., Eisenschlos, J.: ``Open domain question answering over tables via dense retrieval''; Proc. 2021 Conf. of the North American Chapter of the ACL: Human Language Technologies (NAACL-HLT), ACL (2021), 512--519. doi:10.18653/v1/2021.naacl-main.43."),
 22: ("Chen et al. 2021", "Chen, W., Chang, M.-W., Schlinger, E., Wang, W., Cohen, W. W.: ``Open question answering over tables and text''; Proc. 9th Int. Conf. on Learning Representations (ICLR 2021) (2021). arXiv:2010.10439."),
 23: ("Chen et al. 2024b", "Chen, S.-A., Miculicich, L., Eisenschlos, J. M., Wang, Z., Wang, Z., Chen, Y., Fujii, Y., Lin, H.-T., Lee, C.-Y., Pfister, T.: ``TableRAG: Million-token table understanding with language models''; Advances in Neural Information Processing Systems 37 (NeurIPS 2024) (2024)."),
 24: ("Sui et al. 2024", "Sui, Y., Zhou, M., Zhou, M., Han, S., Zhang, D.: ``Table meets LLM: Can large language models understand structured table data? A benchmark and empirical study''; Proc. 17th ACM Int. Conf. on Web Search and Data Mining (WSDM 2024), ACM (2024), 645--654. doi:10.1145/3616855.3635752."),
 25: ("Tan et al. 2025", "Tan, J., Dou, Z., Wang, W., Wang, M., Chen, W., Wen, J.-R.: ``HtmlRAG: HTML is better than plain text for modeling retrieved knowledge in RAG systems''; Proc. ACM Web Conference 2025 (WWW '25), ACM (2025). doi:10.1145/3696410.3714546."),
 26: ("Saurí and Pustejovsky 2009", "Saurí, R., Pustejovsky, J.: ``FactBank: A corpus annotated with event factuality''; Language Resources and Evaluation, 43, 3 (2009), 227--268. doi:10.1007/s10579-009-9089-9."),
 27: ("Chapman et al. 2001", "Chapman, W. W., Bridewell, W., Hanbury, P., Cooper, G. F., Buchanan, B. G.: ``A simple algorithm for identifying negated findings and diseases in discharge summaries''; Journal of Biomedical Informatics, 34, 5 (2001), 301--310."),
 28: ("Morante and Blanco 2012", "Morante, R., Blanco, E.: ``*SEM 2012 Shared Task: Resolving the scope and focus of negation''; Proc. 1st Joint Conf. on Lexical and Computational Semantics (*SEM 2012), ACL (2012), 265--274."),
 29: ("Sarthi et al. 2024", "Sarthi, P., Abdullah, S., Tuli, A., Khanna, S., Goldie, A., Manning, C. D.: ``RAPTOR: Recursive abstractive processing for tree-organized retrieval''; Proc. 12th Int. Conf. on Learning Representations (ICLR 2024) (2024). arXiv:2401.18059."),
 30: ("Robertson and Zaragoza 2009", "Robertson, S., Zaragoza, H.: ``The probabilistic relevance framework: BM25 and beyond''; Foundations and Trends in Information Retrieval, 3, 4 (2009), 333--389. doi:10.1561/1500000019."),
 31: ("Cormack et al. 2009", "Cormack, G. V., Clarke, C. L. A., Büttcher, S.: ``Reciprocal rank fusion outperforms Condorcet and individual rank learning methods''; Proc. 32nd Int. ACM SIGIR Conf. on Research and Development in Information Retrieval, ACM (2009), 758--759."),
 32: ("Nogueira and Cho 2019", "Nogueira, R., Cho, K.: ``Passage re-ranking with BERT''; arXiv preprint arXiv:1901.04085 (2019)."),
 33: ("Bulian et al. 2022", "Bulian, J., Buck, C., Gajewski, W., Börschinger, B., Schuster, T.: ``Tomayto, tomahto. Beyond token-level answer equivalence for question answering evaluation''; Proc. 2022 Conf. on Empirical Methods in Natural Language Processing (EMNLP), ACL (2022), 291--305. doi:10.18653/v1/2022.emnlp-main.20."),
 34: ("Kamalloo et al. 2023", "Kamalloo, E., Dziri, N., Clarke, C., Rafiei, D.: ``Evaluating open-domain question answering in the era of large language models''; Proc. 61st Annual Meeting of the ACL (Volume 1: Long Papers), ACL (2023), 5591--5606. doi:10.18653/v1/2023.acl-long.307."),
 35: ("Sclar et al. 2024", "Sclar, M., Choi, Y., Tsvetkov, Y., Suhr, A.: ``Quantifying language models' sensitivity to spurious features in prompt design or: How I learned to start worrying about prompt formatting''; Proc. 12th Int. Conf. on Learning Representations (ICLR 2024) (2024). arXiv:2310.11324."),
 36: ("Jin et al. 2025", "Jin, B., Yoon, J., Han, J., Arik, S. O.: ``Long-context LLMs meet RAG: Overcoming challenges for long inputs in RAG''; Proc. 13th Int. Conf. on Learning Representations (ICLR 2025) (2025). arXiv:2410.05983."),
 37: ("Jimeno Yepes et al. 2024", "Jimeno Yepes, A., You, Y., Milczek, J., Laverde, S., Li, R.: ``Financial report chunking for effective retrieval augmented generation''; arXiv preprint arXiv:2402.05131 (2024)."),
 38: ("Zheng et al. 2023", "Zheng, L., Chiang, W.-L., Sheng, Y., Zhuang, S., Wu, Z., Zhuang, Y., Lin, Z., Li, Z., Li, D., Xing, E. P., Zhang, H., Gonzalez, J. E., Stoica, I.: ``Judging LLM-as-a-judge with MT-Bench and Chatbot Arena''; Advances in Neural Information Processing Systems 36 (NeurIPS 2023), Datasets and Benchmarks Track (2023). arXiv:2306.05685."),
 39: ("Chroma 2026", "Chroma: ``Chroma: The open-source data infrastructure for AI''; software documentation (accessed Oct. 13, 2026). \\url{https://docs.trychroma.com}"),
 40: ("Malkov and Yashunin 2020", "Malkov, Y. A., Yashunin, D. A.: ``Efficient and robust approximate nearest neighbor search using hierarchical navigable small world graphs''; IEEE Transactions on Pattern Analysis and Machine Intelligence, 42, 4 (2020), 824--836."),
 41: ("Ollama 2026", "Ollama: ``Ollama: Run large language models locally''; software repository, MIT license (accessed Oct. 13, 2026). \\url{https://github.com/ollama/ollama}"),
 42: ("Wang et al. 2020", "Wang, W., Wei, F., Dong, L., Bao, H., Yang, N., Zhou, M.: ``MiniLM: Deep self-attention distillation for task-agnostic compression of pre-trained transformers''; Advances in Neural Information Processing Systems 33 (NeurIPS 2020), 5776--5788."),
 43: ("Reimers and Gurevych 2019", "Reimers, N., Gurevych, I.: ``Sentence-BERT: Sentence embeddings using Siamese BERT-networks''; Proc. 2019 Conf. on Empirical Methods in Natural Language Processing and 9th Int. Joint Conf. on Natural Language Processing (EMNLP-IJCNLP), ACL (2019), 3982--3992. doi:10.18653/v1/D19-1410."),
 44: ("Otmazgin et al. 2022", "Otmazgin, S., Cattan, A., Goldberg, Y.: ``F-coref: Fast, accurate and easy to use coreference resolution''; Proc. 2nd Conf. of the Asia-Pacific Chapter of the ACL and 12th Int. Joint Conf. on Natural Language Processing: System Demonstrations (AACL-IJCNLP 2022), ACL (2022), 48--56. doi:10.18653/v1/2022.aacl-demo.6."),
 45: ("Honnibal et al. 2020", "Honnibal, M., Montani, I., Van Landeghem, S., Boyd, A.: ``spaCy: Industrial-strength Natural Language Processing in Python''; software (2020). doi:10.5281/zenodo.1212303."),
 46: ("Fisch et al. 2019", "Fisch, A., Talmor, A., Jia, R., Seo, M., Choi, E., Chen, D.: ``MRQA 2019 shared task: Evaluating generalization in reading comprehension''; Proc. 2nd Workshop on Machine Reading for Question Answering, ACL (2019), 1--13."),
 47: ("Kwiatkowski et al. 2019", "Kwiatkowski, T., Palomaki, J., Redfield, O., Collins, M., Parikh, A. P., Alberti, C., Epstein, D., Polosukhin, I., Devlin, J., Lee, K., Toutanova, K., Jones, L., Kelcey, M., Chang, M.-W., Dai, A. M., Uszkoreit, J., Le, Q., Petrov, S.: ``Natural Questions: A benchmark for question answering research''; Transactions of the Association for Computational Linguistics, 7 (2019), 452--466. doi:10.1162/tacl\\_a\\_00276."),
 48: ("Hui et al. 2024", "Hui, B., et al.: ``Qwen2.5-Coder technical report''; arXiv preprint arXiv:2409.12186 (2024)."),
 49: ("Qwen Team 2026a", "Qwen Team: ``Qwen3.5-4B''; model card, Hugging Face (accessed Oct. 17, 2026). \\url{https://huggingface.co/Qwen/Qwen3.5-4B}"),
 50: ("Lin 2004", "Lin, C.-Y.: ``ROUGE: A package for automatic evaluation of summaries''; Text Summarization Branches Out: Post-Conference Workshop of ACL 2004, ACL (2004), 74--81."),
 51: ("Zhang et al. 2020", "Zhang, T., Kishore, V., Wu, F., Weinberger, K. Q., Artzi, Y.: ``BERTScore: Evaluating text generation with BERT''; Proc. 8th Int. Conf. on Learning Representations (ICLR 2020) (2020). arXiv:1904.09675."),
 52: ("He et al. 2021", "He, P., Liu, X., Gao, J., Chen, W.: ``DeBERTa: Decoding-enhanced BERT with disentangled attention''; Proc. 9th Int. Conf. on Learning Representations (ICLR 2021) (2021). arXiv:2006.03654."),
 53: ("Qwen Team 2026b", "Qwen Team: ``Qwen3.5-9B''; model card, Hugging Face (accessed Oct. 18, 2026). \\url{https://huggingface.co/Qwen/Qwen3.5-9B}"),
 54: ("Google DeepMind 2026", "Google DeepMind: ``Gemma 4''; model, Ollama library (accessed Oct. 19, 2026). \\url{https://ollama.com/library/gemma4}"),
 55: ("Zipf 1949", "Zipf, G. K.: ``Human Behavior and the Principle of Least Effort''; Addison-Wesley, Cambridge, MA (1949)."),
 56: ("Carbonell and Goldstein 1998", "Carbonell, J., Goldstein, J.: ``The use of MMR, diversity-based reranking for reordering documents and producing summaries''; Proc. 21st Annual Int. ACM SIGIR Conf. on Research and Development in Information Retrieval, ACM (1998), 335--336."),
}

# ================================================================== text conversion
GREEK = {"α": r"\alpha", "β": r"\beta", "γ": r"\gamma", "δ": r"\delta", "λ": r"\lambda", "μ": r"\mu", "π": r"\pi",
         "ρ": r"\rho", "σ": r"\sigma", "τ": r"\tau", "ω": r"\omega", "κ": r"\kappa", "θ": r"\theta", "Δ": r"\Delta", "Σ": r"\Sigma",
         "∈": r"\in", "≥": r"\geq", "≤": r"\leq", "⋅": r"\cdot", "∑": r"\sum", "⌊": r"\lfloor", "⌋": r"\rfloor",
         "′": r"'", "𝒫": r"\mathcal{P}", "∗": r"\ast", "→": r"\rightarrow", "⊆": r"\subseteq", "√": r"\surd"}
SUP = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻", "0123456789-")
ESC = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
       "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}


def esc(s):
    s = "".join(ESC.get(c, c) for c in s)
    s = re.sub(r"[⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+", lambda m: r"\textsuperscript{%s}" % m.group(0).translate(SUP), s)
    s = "".join("$%s$" % GREEK[c] if c in GREEK else c for c in s)
    s = s.replace("$$", "")                       # merge adjacent math glyphs
    s = re.sub(r"[A-Za-z]+(?:\\_[A-Za-z]+){2,}", lambda m: m.group(0).replace("\\_", "\\_\\allowbreak{}"), s)
    s = re.sub(r"\b[0-9a-f]{40,}\b", lambda m: r"\texttt{\seqsplit{%s}}" % m.group(0), s)
    return s


def runs_latex(p, lead_ok=True):
    """Paragraph runs -> LaTeX; a bold run at the start becomes \\leadin{}, italics \\textit{}, sub/sup scripts."""
    out, first = [], True
    for r in p.findall("w:r", NS):
        t = "".join((x.text or "") if x.tag == q("t") else ("\n" if x.tag == q("br") else "") for x in r)
        if not t:
            continue
        rp = r.find("w:rPr", NS)
        get = lambda tag: (rp is not None and rp.find("w:" + tag, NS) is not None and
                           rp.find("w:" + tag, NS).get(q("val")) not in ("0", "false"))
        va = rp.find("w:vertAlign", NS).get(q("val")) if rp is not None and rp.find("w:vertAlign", NS) is not None else None
        s = esc(t)
        if va == "subscript":
            s = r"\textsubscript{%s}" % s
        elif va == "superscript":
            s = r"\textsuperscript{%s}" % s
        if get("b") and first and lead_ok and s.strip():
            s = r"\leadin{%s} " % s.strip()
        elif get("i") and s.strip():
            s = r"\textit{%s}" % s
        out.append(s)
        if t.strip():
            first = False
    return "".join(out).replace("} \\leadin", "}\\leadin")


ROMAN = {"I": "sec:intro", "II": "sec:related", "III": "sec:problem", "IV": "sec:system", "V": "sec:framework",
         "VI": "sec:results", "VII": "sec:conclusions"}


def secref(tok):
    if tok in ROMAN:
        return r"\ref{%s}" % ROMAN[tok]
    return r"\ref{sec:%s}" % tok


def xrefs(s):
    def secs(m):
        word, body = m.group(1), m.group(2)
        body = re.sub(r"\b([IVX]+|\d+\.\d+)\b", lambda k: secref(k.group(1)), body)
        return "%s~%s" % (word, body.replace("–", "--"))
    s = re.sub(r"\b(Sections?) ((?:VII|VI|IV|V|III|II|I|\d+\.\d+)(?:(?:, | and |–)(?:VII|VI|IV|V|III|II|I|\d+\.\d+))*)(?![\w.]*\d)", secs, s)
    s = s.replace("Section~X", "the Data and Code Availability section").replace("(Section X)", "(Data and Code Availability)")
    s = re.sub(r"\bTables? (\d+)(?:–(\d+))?", lambda m: ("Tables~\\ref{tab:%s}--\\ref{tab:%s}" % (m.group(1), m.group(2)))
               if m.group(2) else "Table~\\ref{tab:%s}" % m.group(1), s)
    s = re.sub(r"\bFig\. (\d)", r"Fig.~\\ref{fig:\1}", s)
    s = re.sub(r"\bEqs\. \((B?\d)\)–\((B?\d)\)", r"Eqs.~(\\ref{eq:\1})--(\\ref{eq:\2})", s)
    s = re.sub(r"\bEq\. \((B?\d)\)", r"Eq.~(\\ref{eq:\1})", s)
    return s


def cites(s):
    def grp(m):
        nums = []
        for a, b in re.findall(r"\[(\d+)\](?:–\[(\d+)\])?", m.group(0)):
            nums += list(range(int(a), int(b) + 1)) if b else [int(a)]
        return r"\cite{%s}" % ",".join("r%d" % n for n in nums)
    return re.sub(r"\[\d+\](?:(?:–|, )\[\d+\])*", grp, s)


def conv(p, **kw):
    return cites(xrefs(runs_latex(p, **kw)))


def text(i):
    return d.text(B[i])


# ================================================================== equations (hand-set from the OMML)
EQ_TEX = {
 "1": r"\pi(t,q)=\mathrm{SDH}(t)\cdot \mathrm{sim}(t,q),\qquad \mathrm{sim}(t,q)=1-d_{\cos}(e_t,e_q)",
 "2": r"\tau(t)=\max\bigl(3,\ \lfloor 1.3\,\omega(t)\rfloor+2\bigr)",
 "3": r"\max_{\mathcal{P}\subseteq C}\ \sum_{t\in\mathcal{P}}\pi(t,q)\quad\text{subject to}\quad \sum_{t\in\mathcal{P}}\tau(t)\le B",
 "4": r"\begin{split}\sigma(e,q)=\mathrm{sim}(e,q)\,\bigl(1&+0.15\cdot\mathbf{1}[d(e)\in D_{\mathcal{P}}]\\&+0.10\cdot\mathbf{1}[d(e)=d']\bigr)\end{split}",
 "5": r"\Delta=1-\frac{T_G}{T_F},\qquad T_V=\frac{1}{N}\sum_{i=1}^{N}\tau_V(i)",
 "B1": r"\begin{split}\mathrm{SDH}(t)&=\alpha E(s,o)+\beta I(v)+\gamma U(t,\mathcal{G})+\delta A(t),\\ 1&=\alpha+\beta+\gamma+\delta\end{split}",
 "B2": r"E(s,o)=\lambda\cdot\begin{cases}0.20\,\dfrac{r}{0.15} & r<0.15\\[4pt] 0.20+0.80\min\Bigl(1,\dfrac{r-0.15}{0.70}\Bigr) & r\ge 0.15\end{cases}",
 "B3": r"I(v)=0.58+0.40\sqrt{\rho(v)/R}",
 "B4": r"U(t,\mathcal{G})=\begin{cases}1 & m\le 0.60\\[2pt] 1-0.85\Bigl(\dfrac{m-0.60}{0.32}\Bigr)^{3/2} & 0.60<m<0.92\\[6pt] 0.15\,\dfrac{1-m}{0.08} & m\ge 0.92\end{cases}",
 "B5": r"A(t)=0.20+0.80\min\Bigl(1,\ \frac{1}{3}\sum_k w_k c_k\Bigr)",
}

EQ = {}
for i, el in enumerate(B):
    m = re.fullmatch(r"\((B?\d)\)", d.text(el).strip())
    if m and len(list(el.iter(M + "oMath"))) == 1:
        EQ[i] = (m.group(1), EQ_TEX[m.group(1)])
assert {t for t, _ in EQ.values()} <= set(EQ_TEX) and len(EQ) >= 6, EQ


# ================================================================== tables
# docx index -> (number, EL wide?, EL colspec, JUCS colspec, EL size, JUCS size)
C = lambda w: r">{\centering\arraybackslash}p{%s}" % w
L = lambda w: r">{\raggedright\arraybackslash}p{%s}" % w
TABLE_SPEC = {  # (first header cell, columns) -> (EL wide?, EL spec, J.UCS spec, EL size, J.UCS size)
 ("Study", 3): (True, L("0.22\\textwidth") + L("0.32\\textwidth") + L("0.38\\textwidth"), L("3.1cm") + L("4.2cm") + L("4.5cm"), r"\footnotesize", r"\footnotesize"),
 ("Symbol", 2): (False, L("0.36\\columnwidth") + L("0.58\\columnwidth"), L("3.6cm") + L("8.2cm"), r"\footnotesize", r"\footnotesize"),
 ("Parameter", 2): (True, L("0.17\\textwidth") + L("0.78\\textwidth"), L("2.6cm") + L("9.2cm"), r"\footnotesize", r"\footnotesize"),
 ("Var.", 8): (True, "c" + L("0.2\\textwidth") + "cc" + C("1.5cm") + "c" + C("1.5cm") + "c", "c" + L("2.7cm") + "cc" + C("1.0cm") + "c" + C("1.0cm") + "c", r"\footnotesize", r"\scriptsize"),
 ("Arm", 8): (True, L("0.2\\textwidth") + C("1.0cm") * 4 + C("1.25cm") + C("2.6cm") + C("1.8cm") + C("1.5cm"), L("2.3cm") + C("0.8cm") * 2 + C("0.8cm") + C("1.0cm") + C("2.0cm") + C("1.3cm") + C("1.1cm"), r"\footnotesize", r"\scriptsize"),
 ("Setting, ceiling (est. tokens)", 6): (True, L("0.24\\textwidth") + C("1.6cm") * 4 + C("2.4cm"), L("3.0cm") + C("1.3cm") * 4 + C("1.6cm"), r"\footnotesize", r"\scriptsize"),
 ("Model / retrieval", 7): (True, L("0.22\\textwidth") + C("1.7cm") * 5 + C("1.7cm"), L("2.6cm") + C("1.25cm") * 6, r"\footnotesize", r"\scriptsize"),
 ("Model / retrieval", 5): (True, L("0.22\\textwidth") + C("2.6cm") * 4, L("2.8cm") + C("2.1cm") * 4, r"\footnotesize", r"\scriptsize"),
 ("Arm", 7): (True, "l" + C("1.9cm") * 6, "l" + C("1.45cm") * 6, r"\footnotesize", r"\scriptsize"),
 ("Measure", 5): (True, L("0.3\\textwidth") + C("1.6cm") + C("2.4cm") * 3, L("3.6cm") + C("1.3cm") + C("2.1cm") * 3, r"\footnotesize", r"\scriptsize"),
 ("Arm (long documents)", 7): (True, L("0.2\\textwidth") + C("1.4cm") * 3 + C("2.8cm") + C("1.2cm") + C("1.4cm"), L("2.6cm") + C("1.1cm") * 3 + C("2.3cm") + C("1.0cm") + C("1.1cm"), r"\footnotesize", r"\scriptsize"),
 ("CRediT role", 2): (False, L("0.42\\columnwidth") + L("0.52\\columnwidth"), L("4.2cm") + L("7.4cm"), r"\footnotesize", r"\footnotesize"),
}
TABLES, CAPTION_AFTER = {}, {}
for i, el in enumerate(B):
    m = re.match(r"Table (\d+):", d.text(el).strip())
    if m and B[i - 1].tag == q("tbl"):
        tr = B[i - 1].findall("w:tr", NS)[0]
        sig = (d.text(tr.findall("w:tc", NS)[0]).strip(), len(tr.findall("w:tc", NS)))
        assert sig in TABLE_SPEC, ("no layout for table", m.group(1), sig)
        TABLES[i - 1] = (int(m.group(1)),) + TABLE_SPEC[sig]
        CAPTION_AFTER[i - 1] = i
assert sorted(n for n, *_ in TABLES.values()) == list(range(1, len(TABLES) + 1)), "table numbers must run 1..n"



def cell(tc):
    return r" \newline ".join(conv(p, lead_ok=False) for p in tc.findall("w:p", NS) if d.text(p).strip())


def table_tex(i, venue):
    n, wide, el_spec, ju_spec, el_sz, ju_sz = TABLES[i]
    cap_p = B[CAPTION_AFTER[i]]
    cap = re.sub(r"^\{?Table~\\ref\{tab:\d+\}:\}?\s*", "", conv(cap_p, lead_ok=False))
    assert not cap.startswith(("Table", "{Table")), cap[:40]
    rows = [[cell(tc) for tc in tr.findall("w:tc", NS)] for tr in B[i].findall("w:tr", NS)]
    head = " & ".join(r"\textbf{%s}" % c if venue == "el" else r"\textit{%s}" % c for c in rows[0]) + r" \\"
    body = "\n".join(" & ".join(r) + r" \\" for r in rows[1:])
    spec = el_spec if venue == "el" else ju_spec
    tab = "\\begin{tabular}{%s}\n\\hline\n%s\n\\hline\n%s\n\\hline\n\\end{tabular}" % (spec, head, body)
    if venue == "el":
        env = "table*" if wide else "table"
        return ("\\begin{%s}[!t]\n\\centering\\renewcommand{\\arraystretch}{1.15}%s\n\\caption{%s}\\label{tab:%d}\n"
                "\\begin{adjustbox}{max width=\\%s}\n%s\n\\end{adjustbox}\n\\end{%s}\n"
                % (env, el_sz, cap, n, "textwidth" if wide else "columnwidth", tab, env))
    return ("\\begin{table}[!htbp]\n\\centering\\renewcommand{\\arraystretch}{1.1}%s\n\\begin{adjustbox}{max width=\\textwidth}\n%s\n"
            "\\end{adjustbox}\n\\caption{\\fontsize{10pt}{11pt}\\selectfont\\itshape %s}\\label{tab:%d}\n\\end{table}\n"
            % (ju_sz, tab, cap, n))


# ================================================================== special blocks
def listing(lines, size=r"\footnotesize"):
    body = "\n".join(lines)
    return "\\begin{lstlisting}[basicstyle=%s\\ttfamily,breaklines=true,columns=fullflexible,keepspaces=true,frame=single]\n%s\n\\end{lstlisting}\n" % (size, body)


def algorithm_tex(venue):
    ps = [d.text(p) for p in B[I_ALG].iter(q("p"))]
    title, lines = ps[0], [l.replace("\t", "  ") for l in ps[1:] if l.strip()]
    title = re.sub(r"^Algorithm 1:\s*", "", title)
    cap = "\\leadin{Algorithm 1:} %s" % esc(title)
    blk = listing(lines, r"\scriptsize" if venue == "el" else r"\scriptsize")
    if venue == "el":
        return "\\begin{figure*}[!t]\n\\noindent %s\\par\\vspace{2pt}\n%s\\end{figure*}\n" % (cap, blk)
    return "\\begin{figure}[!htbp]\n\\noindent %s\\par\\vspace{2pt}\n%s\\end{figure}\n" % (cap, blk)


def runs_with_breaks(p):
    return "".join((x.text or "") if x.tag == q("t") else ("\n" if x.tag == q("br") else "") for x in p.iter() if x.tag in (q("t"), q("br")))


def prompt_tex(i):
    raw = runs_with_breaks(B[i])
    head, _, body = raw.partition("\n")
    m = re.match(r"(STANDARD|CONCISE) \(sha256 ([0-9a-f]+)\)", head.strip())
    assert m, head
    return ("\\noindent\\leadin{%s} (sha256 \\texttt{\\seqsplit{%s}})\n%s" % (m.group(1), m.group(2), listing(body.strip("\n").split("\n"), r"\scriptsize")))


def jucs_figure_pair():
    caps = [re.sub(r"^\{?Figure \d+:\}?\s*", "", conv(B[f + 1], lead_ok=False)) for f in FIGS[:2]]
    cap = lambda c, n: "\\caption{\\fontsize{10pt}{11pt}\\selectfont\\itshape %s}\\label{fig:%d}" % (c, n)   # J.UCS: 10 pt
    return ("\\begin{figure}[!htbp]\n\\centering\n"
            "\\begin{minipage}[b]{0.49\\textwidth}\\centering\n\\input{fig1_arch.tex}\n%s\n\\end{minipage}\\hfill\n"
            "\\begin{minipage}[b]{0.49\\textwidth}\\centering\n\\input{fig2_flow.tex}\n%s\n\\end{minipage}\n"
            "\\end{figure}\n" % (cap(caps[0], 1), cap(caps[1], 2)))


RESULT_FIGS = {3: "figure_3_ceiling_sweep.pdf", 4: "figure_4_forest.pdf"}   # plotted by plot_figures_results.py


def figure_tex(n, venue):
    cap = re.sub(r"^\{?Figure \d+:\}?\s*", "", conv(B[FIGS[n - 1] + 1], lead_ok=False))
    if n in RESULT_FIGS:                        # results figures: plotted at each venue's text width, placed at 100%
        if venue == "el":
            return ("\\begin{figure*}[!t]\n\\centering\n\\includegraphics[width=\\textwidth]{%s}\n\\caption{%s}\\label{fig:%d}\n"
                    "\\end{figure*}\n" % (RESULT_FIGS[n], cap, n))
        return ("\\begin{figure}[!htbp]\n\\centering\n\\includegraphics[width=\\textwidth]{%s}\n"
                "\\caption{\\fontsize{10pt}{11pt}\\selectfont\\itshape %s}\\label{fig:%d}\n\\end{figure}\n"
                % (RESULT_FIGS[n].replace(".pdf", "_jucs.pdf"), cap, n))   # plotted at the 12.2 cm J.UCS text width
    if venue == "el":
        inner = "\\input{fig1_arch.tex}" if n == 1 else "\\input{fig2_flow.tex}"     # TikZ at print size
        return "\\begin{figure}[!t]\n\\centering\n%s\n\\caption{%s}\\label{fig:%d}\n\\end{figure}\n" % (inner, cap, n)
    inner = "\\input{fig1_arch.tex}" if n == 1 else "\\input{fig2_flow.tex}"
    return ("\\begin{figure}[!htbp]\n\\centering\n%s\n\\caption{\\fontsize{10pt}{11pt}\\selectfont\\itshape %s}\\label{fig:%d}\n\\end{figure}\n"
            % (inner, cap, n))


# ================================================================== J.UCS length trim (J.UCS maximum 25 pages)
# The J.UCS version omits the related-work summary table (Table 1, which repeats Section 2's prose), the notation table
# (Table 2; every symbol is defined in the text) and Appendix A.2/A.3 (pipeline template wording, example context). All of
# them remain in the full manuscript in the repository, which the J.UCS text points to. From v8 it also omits Algorithm 1,
# which restates Section 5 and Fig. 2 (body_tex), and Table 10 (stage loss), whose key counts are in the text.
# From v9, to make room for Figs. 3 and 4, it omits Table 6 (ceiling sweeps), whose exact-match values Fig. 3 plots and
# whose context counts the text quotes; shortens four passages whose numbers Tables 5 and 7 and Figs. 3 and 4 carry; gives
# the main prompt templates by description and hash (JUCS_A1, appendix_tex); and reduces Appendix B to a pointer (JUCS_B),
# since Limitation (8) states the negation-rendering facts of B.2.
JUCS_DROP_TABLES = {1, 2, 6, 10}
JUCS_TEXT_EDITS = [
    (" Table~\\ref{tab:1} summarises the studies reviewed.", ""),
    (" Table~\\ref{tab:2} lists the notation.", ""),
    (" Table~\\ref{tab:10} follows the fresh cohort from the document to the context and to the answer.",
     " The full manuscript in the repository tabulates it per arm."),
    ("Its specification is in Appendix B.", "Its specification is in the full manuscript in the repository."),
    ("Appendix A gives the prompt templates and Appendix B the fact-layer specification and implementation notes",
     "Appendix A describes the prompt templates, and Appendix B points to the fact-layer specification and "
     "implementation notes in the full manuscript"),
    ("(Appendix B, Eq.~(\\ref{eq:B1}))", "(specified in the full manuscript in the repository)"),
    ("(Appendix B.1)", "(specified in the full manuscript)"),
    ("Table~\\ref{tab:6} gives exact match and, in brackets, the number of the 200 contexts that contain an answer string; "
     "Fig.~\\ref{fig:3} plots the exact-match values.",
     "Fig.~\\ref{fig:3} gives exact match; the full manuscript in the repository also tabulates the number of the 200 "
     "contexts that contain an answer string."),
    ("Exploratory ceiling sweeps of Table~\\ref{tab:6} (", "Exploratory ceiling sweeps ("),
    ("over the 15 contrasts of Table~\\ref{tab:6})", "over the 15 contrasts of Fig.~\\ref{fig:3})"),
    ("against 191 for chunks (Table~\\ref{tab:6})", "against 191 for chunks (Section~\\ref{sec:6.4})"),
    ("Exact match was 96/200 (48.0\\%) for G, 94 for N\\_raw, 89 for F2, 88 for N\\_clean and 79 for D. ", ""),
    ("per 100 estimated tokens the order was N\\_clean (15.7), W (12.6), G (11.9), H (11.7), TC (11.4), D (11.3), "
     "N\\_raw (9.3) and F2 (4.8), and G's",
     "G was third of eight in exact match per 100 estimated tokens (Table~\\ref{tab:5}), and its"),
    ("At 512 and 1,024 tokens G was level with chunks and H. In five-document corpora at a 1,024 ceiling G was ahead of "
     "budgeted chunks (90 against 74; unadjusted p = 0.014, Holm 0.17) and of truncated Markdown (71; Holm 0.056) and level "
     "with H (91); at 2,048 tokens G (86) was not distinguishable from chunks (81), H (92) or W (91). The curves are not "
     "monotone, which is consistent with noise of several cases. ",
     "At 512 tokens and above no contrast survived Holm correction (smallest: G against truncated Markdown in five-document "
     "corpora at 1,024, 90 against 71, Holm p = 0.056), and G was never ahead of H (Fig.~\\ref{fig:3}). "),
    ("G was the worst arm: 44 of 200 exact matches against 66 to 83 for the five baselines, 11.0 to 19.5 points behind each "
     "of them (Holm p $\\leq$ 0.002)",
     "G was the worst arm, 11.0 to 19.5 points behind each of the five baselines (Holm p $\\leq$ 0.002; Table~\\ref{tab:7})"),
    ("and the renderer has been fixed (Appendix B.2).", "and the renderer has been fixed."),
]
JUCS_A1 = ("They were run with qwen2.5-coder:7b and qwen3.5:4b through the Ollama chat interface (thinking disabled; "
           "temperature 0.0, top-p 0.9, seed 42, 512 new tokens) and are given verbatim in the full manuscript in the "
           "repository: STANDARD (sha256 \\texttt{\\seqsplit{%s}}) instructs the model to answer only from the supplied facts, "
           "to preserve negation and not to present attributed, conditional or hypothetical claims as established, and to "
           "say explicitly when the facts do not suffice; CONCISE (sha256 \\texttt{\\seqsplit{%s}}) keeps those rules but asks "
           "for only the shortest complete answer (an entity, name, date, number or exact phrase) and for the output "
           "\"Insufficient information\" instead.")
JUCS_B = ("The fact layer's full specification (extraction rules, modality and negation labels, and the definitions and "
          "constants of the Semantic Density Heuristic) and the implementation notes (the negation-rendering defect "
          "summarised in Section~\\ref{sec:6.10}, table header naming, extractor defects and the test suite) are given in "
          "the full manuscript in the repository; the fact layer is implemented in backend/src/precis/pipeline/svoa.py and "
          "sdh.py.")
FULL_VERSION = ("The pipeline's slightly different template wording, used for the fresh cohort, and an example of a packed "
                "context are given in the full manuscript in the repository (paper/research-paper/).")


# From v9 (per-author blocks with ORCID iDs) the J.UCS Conclusions are condensed; every point dropped is stated in
# Section 6 and the Discussion, and the full paragraph stays in the Word and EL versions.
JUCS_CONCLUSIONS = (
    "This paper evaluated how much a structure-aware packing rule adds to local RAG over table-bearing pages and how much "
    "of a measured difference comes from answer format. Rewriting tables as extracted sentences cost most of the accuracy "
    "(14.0\\% against 49.5\\% exact match for native tables, in-sample), but against tag-stripped chunks the cheap "
    "structure-keeping baselines were never significantly ahead. On a fresh cohort G was not distinguishable from them, "
    "its non-inferiority rested on a post hoc margin, and it lost at a 256-token ceiling; on full Wikipedia pages it was "
    "the worst arm (22.0\\% EM against 33.0 to 41.5\\%) because same-document suppression dropped every prose fact, and "
    "a repaired rule (G2) gained 16.0 points and was non-inferior to table-aware chunking at about twice its context. "
    "A concise-answer prompt raised exact match everywhere, mainly through answer format, and an equivalence judge sees "
    "much smaller differences. Native structure should be kept but not at the expense of prose, and strict-match "
    "comparisons need an equivalence measure and controlled prompts.")


def jucs_trim(tex):
    for old, new in JUCS_TEXT_EDITS:
        assert tex.count(old) == 1, old
        tex = tex.replace(old, new)
    a = tex.index("This paper evaluated how much a structure-aware packing rule")
    assert tex.count("This paper evaluated how much a structure-aware packing rule") == 1
    return tex[:a] + JUCS_CONCLUSIONS + tex[tex.index("\n", a):]


# ================================================================== section map
HEADINGS = [("I. INTRODUCTION", "section", "Introduction", "sec:intro"),
            ("II. RELATED WORKS", "section", "Related Work", "sec:related"),
            ("III. PROBLEM FORMULATION", "section", "Problem Formulation", "sec:problem"),
            ("IV. SYSTEM MODEL", "section", "System Model", "sec:system"),
            ("V. PROPOSED FRAMEWORK", "section", "Proposed Framework", "sec:framework"),
            ("VI. RESULTS AND DISCUSSIONS", "section", "Results and Discussion", "sec:results"),
            ("6.1 Experimental setup", "subsection", "Experimental Setup", "sec:6.1"),
            ("6.2 Structural preservation", "subsection", "Structural Preservation on Table-Bearing Documents (RQ1)", "sec:6.2"),
            ("6.3 Baseline adequacy", "subsection", "Baseline Adequacy and Efficiency (RQ1)", "sec:6.3"),
            ("6.4 Where the ceiling binds", "subsection", "Where the Ceiling Binds (RQ1)", "sec:6.4"),
            ("6.5 Threshold sensitivity", "subsection", "Threshold Sensitivity of Candidate G", "sec:6.5"),
            ("6.6 Answer format", "subsection", "Answer Format and Abstention Policy (RQ2)", "sec:6.6"),
            ("6.7 Information loss", "subsection", "Information Loss across Pipeline Stages (RQ3)", "sec:6.7"),
            ("6.8 The fact layer", "subsection", "The Fact Layer: an Extractor Audit", "sec:6.8"),
            ("6.9 Discussion", "subsection", "Discussion", "sec:6.9"),
            ("6.10 Limitations", "subsection", "Limitations", "sec:6.10"),
            ("VII. CONCLUSIONS AND FUTURE WORKS", "section", "Conclusions and Future Work", "sec:conclusions")]
HEAD = {find(pre): (kind, title, lab) for pre, kind, title, lab in HEADINGS}
FIGS = [i for i, el in enumerate(B) if el.tag == q("p") and el.find(".//w:drawing", NS) is not None]
assert len(FIGS) == 4 and all(d.text(B[f + 1]).startswith("Figure %d:" % (k + 1)) for k, f in enumerate(FIGS)), FIGS
I_ALG = next(i for i, el in enumerate(B) if el.tag == q("tbl") and d.text(el).startswith("Algorithm 1:"))
I_ALG_INTRO = find("The complete procedure is given as Algorithm 1.")
I_AFTER_EQ5 = find("where τ")
I_BODY_START, I_BODY_END = find("I. INTRODUCTION"), find("VIII. AUTHOR")
SKIP = set(CAPTION_AFTER.values()) | {f + 1 for f in FIGS} | {I_ALG_INTRO}


def body_tex(venue, start, stop):
    out = []
    i = start
    while i < stop:
        el = B[i]
        if i in HEAD:
            kind, title, lab = HEAD[i]
            out.append("\\%s{%s}\\label{%s}\n" % (kind, title, lab))
        elif i in SKIP:
            pass
        elif i in TABLES:
            if not (venue == "jucs" and TABLES[i][0] in JUCS_DROP_TABLES):
                out.append(table_tex(i, venue))
        elif i in EQ:
            tag, tex = EQ[i]
            out.append("\\begin{equation}\\label{eq:%s}%s\n%s\n\\end{equation}\n" % (tag, "\\tag{%s}" % tag if tag.startswith("B") else "", tex))
        elif i in FIGS:
            if venue == "jucs" and i in FIGS[:2]:   # J.UCS trim: Figures 1 and 2 side by side in one float
                if i == FIGS[0]:
                    out.append(jucs_figure_pair())
            else:
                out.append(figure_tex(FIGS.index(i) + 1, venue))
        elif i == I_ALG:
            if venue == "jucs":                     # J.UCS trim: Algorithm 1 restates Section 5 and Fig. 2
                out.append("The complete procedure is given as Algorithm 1 in the full manuscript in the repository.\n")
            else:
                out.append("The complete procedure is given as Algorithm 1.\n\n" + algorithm_tex(venue))
        elif el.tag == q("p") and d.text(el).strip():
            s = conv(el)
            if i == I_AFTER_EQ5:                    # continues the sentence after Eq. (5)
                s = "\\noindent " + s
            out.append(s + "\n")
        i += 1
    return "\n".join(out)


def appendix_tex(venue):
    out = []
    a1 = conv(B[find("A.1 Templates")])
    if venue == "jucs":                         # J.UCS trim: templates by description and hash, verbatim in the full text
        sha = lambda pre: re.match(r"\w+ \(sha256 ([0-9a-f]{64})\)", d.text(B[find(pre)]).strip()).group(1)
        k = a1.index("These are the texts run with")
        out.append(a1[:k] + JUCS_A1 % (sha("STANDARD (sha256"), sha("CONCISE (sha256")) + "\n")
    else:
        out.append(a1 + "\n")
        out.append(prompt_tex(find("STANDARD (sha256")))
        out.append(prompt_tex(find("CONCISE (sha256")))
    out.append(conv(B[find("Follow-up prompts")]) + "\n")
    if venue == "jucs":
        out.append(FULL_VERSION + "\n")
    else:
        for pre in ("A.2 Pipeline templates", "A.3 Example"):
            out.append(conv(B[find(pre)]) + "\n")
        out.append(listing(runs_with_breaks(B[find("| Secretary")]).strip("\n").split("\n"), r"\scriptsize"))
    secA = "\\section{Prompt Templates and an Example Context}\\label{app:A}\n"
    secB = "\\section{Fact-Layer Specification and Implementation Notes}\\label{app:B}\n"
    if venue == "jucs":                         # J.UCS trim: Appendix B in the full text; Limitation (8) has B.2's facts
        return secA + "\n".join(out) + secB + JUCS_B + "\n"
    for i in range(find("B.1 Extraction"), len(B)):
        if not d.text(B[i]).strip(): continue
        if i in EQ:
            tag, tex = EQ[i]
            out.append("\\begin{equation}\\label{eq:%s}\\tag{%s}\n%s\n\\end{equation}\n" % (tag, tag, tex))
        else:
            out.append(conv(B[i]) + "\n")
    blk = "\n".join(out)
    k = blk.index(r"\leadin{B.1")
    return secA + blk[:k] + secB + blk[k:]


# ================================================================== front and back matter
TITLE = "Keeping Tables Intact Under a Token Budget: Structure, Simple Baselines and Answer Format in Local Retrieval-Augmented Question Answering"
# (name, e-mail, ORCID iD) in author order; the first author is the corresponding author. All four are final-year
# undergraduate students of the same department. EL asks for each author's affiliation, role, country and e-mail, listed
# one by one; J.UCS gives each author a block with affiliation, ORCID iD and e-mail.
AUTHOR_INFO = [("Chandan D", "chandanxdev@gmail.com", "0009-0004-0814-4356"),
               ("M P Jeevan Gowda", "mpjeevangowda@gmail.com", "0009-0008-6843-7133"),
               ("Bhimsen", "harishbhimsen12396@gmail.com", "0009-0008-0387-931X"),
               ("Chandu S", "kingskingchandu143@gmail.com", "0009-0007-3799-4167")]
AUTHORS = [a[0] for a in AUTHOR_INFO]
AFFIL = "Department of Artificial Intelligence and Machine Learning, Impact College of Engineering and Applied Sciences, Bengaluru, India"
ROLE = "a final-year undergraduate student in the " + AFFIL
EMAIL = AUTHOR_INFO[0][1]
_front = "\n".join(d.text(B[i]) for i in range(find("I. INTRODUCTION")))
assert all(e in _front and o in _front for _, e, o in AUTHOR_INFO), "author e-mails/ORCIDs differ from the Word text"
EL_AUTHOR_NOTE = " ".join("%s is %s (%se-mail: %s)." % (n, ROLE, "corresponding author; " if k == 0 else "", e)
                          for k, (n, e, _) in enumerate(AUTHOR_INFO))
abstract = re.sub(r"^\\leadin\{Abstract:\}\s*", "", conv(B[find("Abstract:")]))
keywords = re.sub(r"^\\leadin\{Keywords:\}\s*", "", conv(B[find("Keywords:")])).rstrip(".")
assert not abstract.startswith("\\leadin") and not keywords.startswith("\\leadin")
contrib_tex = lambda v: table_tex(find("VIII. AUTHOR") + 1, v)


def credit_sentence():
    """The CRediT table as one sentence (J.UCS length trim): roles grouped by author list, in table order."""
    groups = {}
    for tr in B[find("VIII. AUTHOR") + 1].findall("w:tr", NS)[1:]:
        role, who = (d.text(tc).strip() for tc in tr.findall("w:tc", NS))
        groups.setdefault(who, []).append(role)
    return "; ".join("%s: %s" % (", ".join(r[0] + r[1:].lower() if k == 0 else r.lower() for k, r in enumerate(roles)),
                                 "all authors" if who.count(";") == len(AUTHORS) - 1 else who)
                     for who, roles in groups.items()) + "."
ack = conv(B[find("IX. ACKNOWLEDGMENTS") + 1])
ACK_TAIL = "Competing interests: none declared. Funding: no specific funding was received for this work."
assert ack.count(" " + ACK_TAIL) == 1          # EL moves it to the first-page footnote; the ethics sentence stays
EL_FUNDING = "This work received no specific funding; the authors declare no competing interests."
data_av = conv(B[find("X. DATA AND CODE") + 1])
# URLs as \url so long addresses can break at / and . instead of stretching the line
data_av = re.sub(r"(https?://[^\s;,)]+?)([.;,)]?)(?=[\s;,)]|$)", lambda m: r"\url{%s}%s" % (m.group(1).replace(r"\_", "_"), m.group(2)), data_av)
genai = conv(B[find("XI. GENERATIVE AI") + 1])

COMMON_PRE = r"""\usepackage{amsmath,amssymb}
\usepackage{graphicx}
\usepackage{array}
\usepackage{adjustbox}
\usepackage{listings}
\usepackage{seqsplit}
\usepackage{tikz}
\usetikzlibrary{positioning,arrows.meta,shapes.geometric,fit,calc}
\usepackage{url}
\lstset{literate={←}{{$\leftarrow$}}1 {é}{{\'e}}1}
\usepackage{newunicodechar}
\newunicodechar{−}{\textminus}
\newunicodechar{×}{\texttimes}
\newunicodechar{≈}{\ensuremath{\approx}}
\newunicodechar{‑}{-}
\setlength{\emergencystretch}{1.5em}
"""


def el_tex():
    authors = ", ".join(AUTHORS[:-1]) + " and " + AUTHORS[-1]
    return "% Generated by scripts/build_venue_latex.py from " + SRC.name + " -- do not edit by hand.\n" + r"""\documentclass[journal]{IAENGtran}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{mathptmx}
\usepackage{textcomp}
""" + COMMON_PRE + r"""\usepackage{cite}
\newcommand{\leadin}[1]{\textit{#1}}
\hyphenation{Pré-cis}
\begin{document}
\title{""" + TITLE + r"""}
\author{""" + authors + r"""%
\thanks{Manuscript received October 2026. """ + EL_FUNDING + r"""}%
\thanks{""" + EL_AUTHOR_NOTE + r"""}}
\maketitle
\pagestyle{empty}
\thispagestyle{empty}
\begin{abstract}
""" + abstract + r"""
\end{abstract}
\begin{IAENGkeywords}
""" + keywords + r""".
\end{IAENGkeywords}
\IAENGpeerreviewmaketitle

""" + el_style(body_tex("el", I_BODY_START, I_BODY_END)) + r"""
\appendices
""" + el_style(appendix_tex("el")) + r"""
\section*{Author Contributions}
Table~\ref{tab:12} gives each author's roles in the CRediT taxonomy.
""" + contrib_tex("el") + r"""
\section*{Data and Code Availability}
""" + data_av + r"""

\section*{Generative AI Use Statement}
""" + genai + r"""

\section*{Acknowledgment}
""" + ack.replace(" " + ACK_TAIL, "") + r"""

\begin{thebibliography}{99}
""" + "\n".join(r"\bibitem{r%d} %s" % (n, el_ref(n)) for n in range(1, 57)) + r"""
\end{thebibliography}
\end{document}
"""


def el_style(tex):
    """EL (IAENG) house style: refer to "(1)", not "Eq. (1)", except at the start of a sentence ("Equation (1)")."""
    tex = re.sub(r"(^|(?<=[.!?] ))Eqs?\.~\(", lambda m: m.group(1) + ("Equations~(" if "Eqs" in m.group(0) else "Equation~("),
                 tex, flags=re.M)
    tex = re.sub(r"(?<=[(,]) ?Eqs?\.~\(", lambda m: (" " if m.group(0).startswith(" ") else "") + "see~(", tex)
    tex = re.sub(r"\bEqs?\.~\(", "(", tex)
    assert "Eq.~(" not in tex and "Eqs.~(" not in tex
    return tex


def el_ref(n):
    t = d.text(B[REF[n]]).strip()
    t = re.sub(r"^\[%d\]\s*" % n, "", t)
    t = esc(t)
    t = re.sub(r"(https?://\S+?)([).,]?)(?=\s|$)", lambda m: r"\url{%s}%s" % (m.group(1).replace(r"\_", "_"), m.group(2)), t)
    t = re.sub(r"([?!])” ?,", r"\1”", t).replace("”,", ",”")
    return t.replace("“", "``").replace("”", "''")


def jucs_tex():
    authors_tex = "\n   \\and\n   ".join(       # one block per author, as in the J.UCS template
        r"{\bfseries\fontsize{10pt}{10pt}\selectfont{%s}} \\ {\fontsize{9pt}{12pt}\selectfont{(Impact College of "
        r"Engineering and Applied Sciences, Bengaluru, India\\ \orcid{%s}, %s%s)}}" % (n, o, e, "; corresponding author" if k == 0 else "")
        for k, (n, e, o) in enumerate(AUTHOR_INFO))
    body = jucs_trim(body_tex("jucs", I_BODY_START, I_BODY_END) + "\n%%APPX%%\n" + appendix_tex("jucs"))
    body, appx = body.split("\n%%APPX%%\n")
    # J.UCS: AI-tool use is disclosed in the Materials and Methods section
    k = body.index("\\label{sec:6.2}")
    k = body.rindex("\\subsection", 0, k)
    jucs_genai = genai.replace("the regeneration checks of Appendix B.2", "the regeneration checks of Section~\\ref{sec:6.10}")
    assert jucs_genai != genai                  # J.UCS trim: Appendix B is a pointer, Limitation (8) has the checks
    body = body[:k] + "\\leadin{Use of generative AI tools.} " + jucs_genai + "\n\n" + body[k:]
    refs = sorted(JUCS_REFS.items(), key=lambda kv: kv[1][0].lower())
    return "% Generated by scripts/build_venue_latex.py from " + SRC.name + " -- do not edit by hand.\n" + r"""\documentclass[10pt, a4paper, oneside]{article}
\usepackage[hidelinks]{hyperref}
\usepackage{jucs2e}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{mathptmx}
\usepackage{textcomp}
""" + COMMON_PRE + r"""\usepackage{mathtools}
\usepackage{scalerel}
\usepackage{setspace}
\usepackage[strict]{changepage}
\usepackage{caption}
\usepackage{afterpage}
\usepackage{ragged2e}
\usepackage{titlesec}
\titleformat*{\section}{\Large\bfseries}
\titleformat*{\subsection}{\normalsize\bfseries}
\renewcommand{\baselinestretch}{0.9}
\usepackage[textwidth=8cm, margin=0cm, left=4.6cm, right=4.2cm, top=3.9cm, bottom=6.8cm, a4paper, headheight=0.5cm, headsep=0.5cm]{geometry}
\usepackage{fancyhdr}
\usepackage[format=plain, labelfont=it, textfont=it, justification=centering]{caption}
\usepackage{microtype}
\urlstyle{same}
\pagestyle{fancy}
\newcommand{\leadin}[1]{\textit{#1}}
% float placement: let text fill pages around tables and figures (J.UCS length trim)
\setcounter{topnumber}{3}\setcounter{bottomnumber}{2}\setcounter{totalnumber}{5}
\renewcommand{\topfraction}{0.9}\renewcommand{\bottomfraction}{0.6}\renewcommand{\textfraction}{0.08}
\renewcommand{\floatpagefraction}{0.85}
% breakcites (loaded by the J.UCS template, not installed here): let multi-reference citations wrap
\makeatletter
\AtBeginDocument{\def\@citex[#1]#2{\leavevmode\let\@citea\@empty\@cite{\@for\@citeb:=#2\do{\@citea\def\@citea{,\penalty\@m\ }%
  \edef\@citeb{\expandafter\@firstofone\@citeb\@empty}\if@filesw\immediate\write\@auxout{\string\citation{\@citeb}}\fi
  \@ifundefined{b@\@citeb}{\mbox{\reset@font\bfseries ?}\G@refundefinedtrue\@latex@warning{Citation `\@citeb' undefined}}%
  {\csname b@\@citeb\endcsname}}}{#1}}}
\makeatother
\renewcommand{\ttdefault}{pcr}   % Type 1 Courier for \texttt (the default EC typewriter embeds as bitmap Type 3)
\newcommand\jucs{{Journal of Universal Computer Science}}
\newcommand\jucsvol{vol. --, no. -- (2026)}
\newcommand\jucspages{--}
\newcommand\jucssubmitted{--}
\newcommand\jucsaccepted{--}
\newcommand\jucsappeared{--}
\newcommand\jucslicence{ CC BY 4.0}
\newcommand\startingPage{1}
\setcounter{page}{\startingPage}
\newcommand\paperauthor{{Chandan D et al.: }}
\newcommand\papertitle{""" + TITLE + r"""}
\header{\paperauthor \papertitle}
% jucs2e.sty hard-codes the sample running head; restate it with this paper's authors and short title
\fancyhead[OC]{{\ifnum\thepage=\startingPage
  \begin{singlespace}\fontsize{8pt}{5pt}\selectfont{\itshape{\jucs, \jucsvol, \jucspages \\ submitted: \jucssubmitted, accepted: \jucsaccepted, appeared: \jucsappeared \jucslicence}}\vspace{-5mm}\end{singlespace}
  \else {\fontsize{8pt}{5pt}\selectfont{\itshape{Chandan D et al.: Keeping Tables Intact Under a Token Budget}}}\vspace{-0.5mm}\fi}}
\hyphenation{Pré-cis}
\begin{document}
\title{{\fontsize{14pt}{14pt}\selectfont{\vspace*{-3mm}\papertitle\vspace*{-1mm}}}}
\author{""" + authors_tex + r"""}
\label{first}
\maketitle

\begin{abstract}
{\fontsize{9pt}{9pt}\selectfont{\vspace*{-2mm}
""" + abstract + r"""}}
\end{abstract}

\begin{keywords}
{\fontsize{9pt}{9pt}\selectfont{""" + keywords + r"""}}
\end{keywords}

\begin{category}
{\fontsize{9pt}{9pt}\selectfont{H.3.3, I.2.7}}
\end{category}

\begin{doi}
{\fontsize{9pt}{9pt}\selectfont{10.3897/jucs.\textless SubmissionNumber\textgreater}}
\end{doi}

""" + body + r"""
\appendix
""" + appx + r"""
\section*{Author Contributions}
""" + credit_sentence() + r"""
\section*{Data and Code Availability}
""" + data_av + r"""

\begin{Acknowledgements}
""" + ack + r"""
\end{Acknowledgements}

\begin{thebibliography}{}{
\fontsize{9pt}{10pt}\selectfont\setlength{\itemsep}{0pt}\setlength{\parsep}{0pt}
""" + "\n\n".join(r"\bibitem[%s]{r%d} %s" % (lab, n, ent) for n, (lab, ent) in refs) + r"""
}\end{thebibliography}
\end{document}
"""


def check_refs():
    """Every J.UCS entry's title and year must occur in the corresponding v6 (EL) reference."""
    for n, (lab, ent) in JUCS_REFS.items():
        src = d.text(B[REF[n]])
        assert src.startswith("[%d]" % n), (n, src[:20])
        title = re.search(r"``(.+?)''", ent).group(1).replace("\\_", "_")
        norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
        assert norm(title) in norm(src), (n, title)
        year = re.search(r"(\d{4})[ab]?$", lab).group(1)
        assert year in src, (n, year)


if __name__ == "__main__":
    check_refs()
    for v, fn in (("el", el_tex), ("jucs", jucs_tex)):
        dst = OUT / v
        dst.mkdir(parents=True, exist_ok=True)
        for f in ("fig1_arch.tex", "fig2_flow.tex"):
            shutil.copy(OUT / "common" / f, dst / f)
        (dst / "fig1_architecture.png").unlink(missing_ok=True)     # the pre-v9 raster Fig. 1
        for f in RESULT_FIGS.values():
            f = f if v == "el" else f.replace(".pdf", "_jucs.pdf")
            shutil.copy(ROOT / "paper/figures" / f, dst / f)
        (dst / ("precis_%s.tex" % v)).write_text(fn())
        print("wrote", dst / ("precis_%s.tex" % v))
