"""Build Precis_paper_clean_plane_revised_v9.docx from v8: legible diagrams and the two results figures.

  backend/venv/bin/python scripts/plot_figures_results.py      # paper/figures/figure_{3,4}_*.png from the v8 tables
  backend/venv/bin/python scripts/revise_paper_v9.py
Changes:
  F1  Figure 1 (architecture) redrawn in TikZ to match Sections IV and V (two stores, coref and SDH, the stage numbers),
      replacing the v5 raster whose labels printed at 3-5 pt; F2 Figure 2 (query flow) re-laid at 8 pt. Both sources are
      paper/venues/common/fig{1_arch,2_flow}.tex, shared with the venue builds; Word gets 600-dpi renders at print size.
  F3  Figure 3 (ceiling sweeps, the values of Table 6) after Table 6, cited in Section 6.4.
  F4  Figure 4 (G − arm exact-match differences with 99% intervals on the fresh and long-document cohorts, Tables 5
      and 7, with the non-inferiority margin) after the long-document results, cited there.
  G1-G6 venue-guideline fixes: the abstract no longer uses the undefined "LLM"; keywords in alphabetical order;
      the AI-use statement names the figure work; each author's role, e-mail and ORCID iD; G5 ethics statement; G6 tables cited in order;
      G7 CRediT Visualization role (Chandan D).
No number changes; the figures are plotted from the v8 tables. v8 is left untouched.
"""
import copy, re, shutil, struct, subprocess, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from docx_tools import Doc, NS, q

SRC = ROOT / "paper/research-paper/Precis_paper_clean_plane_revised_v8.docx"
DST = ROOT / "paper/research-paper/Precis_paper_clean_plane_revised_v9.docx"
FIG = ROOT / "paper/figures"
d = Doc(SRC)
P = d.orig                      # handles by v8 body index
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
PIC = "http://schemas.openxmlformats.org/drawingml/2006/picture"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
WIDTH_EMU = 504 * 12700        # the figures are plotted 504 pt (7.0 in) wide, the EL text width

assert d.text(P[40]).startswith("Figure 1:") and P[39].find(".//w:drawing", NS) is not None
assert d.text(P[79]).startswith("Table 6:") and d.text(P[84]).startswith("Table 7:")
assert d.text(P[85]).startswith("When the ceiling bound on long pages, G was the worst arm")
assert "[Content_Types].xml" in d.parts and b'Extension="png"' in d.parts["[Content_Types].xml"]


def png_size(path):
    b = path.read_bytes()
    assert b[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", b[16:24])


def add_figure(after, n, png, caption):
    """Clone Figure 1's picture and caption paragraphs after `after`, embedding png as a new image part."""
    rels = d.parts["word/_rels/document.xml.rels"].decode()
    rid = "rId%d" % (max(int(x) for x in re.findall(r'Id="rId(\d+)"', rels)) + 1)
    media = "media/image%d.png" % (max(int(x) for x in re.findall(r"word/media/image(\d+)\.png", " ".join(d.parts))) + 1)
    d.parts["word/" + media] = png.read_bytes()
    d.parts["word/_rels/document.xml.rels"] = rels.replace(
        "</Relationships>", '<Relationship Id="%s" Type="%s/image" Target="%s"/></Relationships>' % (rid, R, media)).encode()

    w, h = png_size(png)
    cy = round(WIDTH_EMU * h / w)
    pic = copy.deepcopy(P[39])
    for ext in pic.iter("{%s}extent" % WP, "{%s}ext" % A):
        ext.set("cx", str(WIDTH_EMU)); ext.set("cy", str(cy))
    doc_pr = pic.find(".//{%s}docPr" % WP)
    doc_pr.set("id", str(max(int(e.get("id")) for e in d.root.iter("{%s}docPr" % WP)) + 1))
    doc_pr.set("name", "Picture %d" % n)
    pic.find(".//{%s}cNvPr" % PIC).set("name", png.name)
    pic.find(".//{%s}blip" % A).set("{%s}embed" % R, rid)
    after.addnext(pic)
    cap = copy.deepcopy(P[40])
    d.set_runs(cap, [("Figure %d: " % n, {"bold": True}), (caption, {"bold": False})])
    pic.addnext(cap)
    return cap


# ------------------------------------------------------------------ F1, F2: diagrams from the shared TikZ sources
COMMON = ROOT / "paper/venues/common"
STANDALONE = r"""\documentclass[10pt,border=2pt]{standalone}
\usepackage[T1]{fontenc}
\usepackage{mathptmx}
\usepackage{tikz}
\usetikzlibrary{positioning,arrows.meta,shapes.geometric,fit,calc}
\begin{document}
\input{%s}
\end{document}
"""


def render_tikz(name):
    """Compile common/<name>.tex standalone (same fonts as the venue builds) to common/<name>.{pdf,png}, 600 dpi."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        shutil.copy(COMMON / (name + ".tex"), tmp)
        (tmp / "f.tex").write_text(STANDALONE % (name + ".tex"))
        subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "f.tex"], cwd=tmp, check=True,
                       stdout=subprocess.DEVNULL)
        subprocess.run(["pdftoppm", "-r", "600", "-png", "-singlefile", "f.pdf", "f"], cwd=tmp, check=True)
        shutil.copy(tmp / "f.pdf", COMMON / (name + ".pdf"))
        shutil.copy(tmp / "f.png", COMMON / (name + ".png"))
    return COMMON / (name + ".png")


def replace_picture(pic, png):
    """Swap the image behind an existing picture paragraph and set it to the render's print size (600 dpi)."""
    rid = pic.find(".//{%s}blip" % A).get("{%s}embed" % R)
    rels = d.parts["word/_rels/document.xml.rels"].decode()
    target = re.search(r'Id="%s"[^>]*Target="([^"]+)"' % rid, rels).group(1)
    d.parts["word/" + target] = png.read_bytes()
    w, h = png_size(png)
    cx, cy = round(w / 600 * 914400), round(h / 600 * 914400)
    for ext in pic.iter("{%s}extent" % WP, "{%s}ext" % A):
        ext.set("cx", str(cx)); ext.set("cy", str(cy))
    pic.find(".//{%s}cNvPr" % PIC).set("name", png.name)


assert d.text(P[47]).startswith("Figure 2:") and P[46].find(".//w:drawing", NS) is not None
replace_picture(P[39], render_tikz("fig1_arch"))
replace_picture(P[46], render_tikz("fig2_flow"))


# ------------------------------------------------------------------ F3: ceiling sweeps (Section 6.4)
d.replace(P[77], "Table 6 gives exact match and, in brackets, the number of the 200 contexts that contain an answer string.",
          "Table 6 gives exact match and, in brackets, the number of the 200 contexts that contain an answer string; "
          "Fig. 3 plots the exact-match values.")
add_figure(P[79], 3, FIG / "figure_3_ceiling_sweep.png",
           "Exploratory ceiling sweeps of Table 6 (N = 200, qwen2.5-coder:7b, concise prompt): exact match against the "
           "ceiling for G, budgeted tag-stripped chunks (N), hybrid table-aware retrieval (H) and truncated whole-document "
           "Markdown (W), on (a) single documents and (b) five-document corpora.")

# ------------------------------------------------------------------ F4: G − arm on the two protocol-first cohorts
d.replace(P[85], "(7 correct against 9 to 14).",
          "(7 correct against 9 to 14). Fig. 4 sets these differences beside those of the fresh cohort (Table 5): there "
          "every interval except that against D includes zero, here every interval lies below zero.")
add_figure(P[85], 4, FIG / "figure_4_forest.png",
           "Exact-match difference of G from each arm (percentage points, positive when G is ahead) with its 99% "
           "question-level bootstrap interval, on (a) the fresh table- and list-bearing cohort (Table 5) and (b) the "
           "long-document cohort at the 2,048 ceiling (Table 7). The dashed line marks the 5-point non-inferiority "
           "margin and the shaded band the 3 to 7 points over which the fresh-cohort margin was varied.")

# ------------------------------------------------------------------ G1-G3: venue-guideline fixes in the shared text
# G1 the abstract defines its symbols (EL); G2 keywords in alphabetical order (EL "Index Terms"); G3 the AI-use statement
# names the figure work done with Claude Code (J.UCS: tool, version and purpose).
d.replace(d.find("Abstract: "), "but an LLM judge, checked", "but a language-model judge, checked")
kw = d.find("Keywords: ")
terms = d.text(kw)[len("Keywords: "):].rstrip(".").split(", ")
assert len(terms) == 6
d.replace(kw, ", ".join(terms) + ".", ", ".join(sorted(terms, key=str.lower)) + ".")
d.replace(d.find("During the preparation of this manuscript"), "and scripts/revise_paper_v8.py), and revised",
          "and scripts/revise_paper_v8.py), drew Figs. 1 to 4 (scripts/plot_figures_results.py and the TikZ sources in "
          "paper/venues/common), and revised")

# G4 each author's role, e-mail and ORCID iD (EL lists every author's role and e-mail; J.UCS every author's ORCID iD)
d.set_text(d.find("Corresponding author: Chandan D"),
           "All authors are final-year undergraduate students. Chandan D (corresponding author): chandanxdev@gmail.com, "
           "ORCID 0009-0004-0814-4356; M P Jeevan Gowda: mpjeevangowda@gmail.com, ORCID 0009-0008-6843-7133; Bhimsen: "
           "harishbhimsen12396@gmail.com, ORCID 0009-0008-0387-931X; Chandu S: kingskingchandu143@gmail.com, ORCID "
           "0009-0007-3799-4167.")

# G5 ethics statement (J.UCS: authors must state whether ethics approval was obtained); wording confirmed by the authors
d.replace(d.find("The authors thank Dr Kaipaa Sandhya"), "Funding: no specific funding was received for this work.",
          "Funding: no specific funding was received for this work. No ethics approval was required; no human participants "
          "other than the authors were involved.")

# G6 tables are cited in numerical order (IEEE): the fresh-cohort paragraph pointed to Table 6 before Table 5 appears
d.replace(d.find("Fresh cohort. "), "In the exploratory sweeps (Table 6)", "In the exploratory sweeps (Section 6.4)")

# G7 CRediT table: Chandan D drew Figs. 1 to 4 (Visualization), placed before the writing roles
tbl = d.find("VIII. AUTHOR").getnext()
assert tbl.tag == q("tbl")
rows = {d.text(tr.find("w:tc", NS)).strip(): tr for tr in tbl.findall("w:tr", NS)}
assert "Visualization" not in rows and "Writing – original draft" in rows
viz = copy.deepcopy(rows["Data curation"])
for tc, text in zip(viz.findall("w:tc", NS), ("Visualization", "Chandan D")):
    d.set_text(tc.find("w:p", NS), text)
rows["Writing – original draft"].addprevious(viz)

# ------------------------------------------------------------------ consistency checks on the result
body = [el for el in d.body if el.tag in (q("p"), q("tbl"))]
figs = [i for i, el in enumerate(body) if el.tag == q("p") and el.find(".//w:drawing", NS) is not None]
assert [d.text(body[i + 1])[:9] for i in figs] == ["Figure 1:", "Figure 2:", "Figure 3:", "Figure 4:"], figs
full = "\n".join(d.text(p) for p in d.body.iter(q("p")))
assert all(full.count("Fig. %d" % n) >= 1 for n in (1, 2, 3, 4))
d.save(DST)
print("wrote", DST)
