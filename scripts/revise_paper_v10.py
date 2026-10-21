"""Build Precis_paper_clean_plane_revised_v10.docx from v9: the current test count and, once archived, the release DOI.

  backend/venv/bin/python scripts/revise_paper_v10.py               # T1 only; the DOI placeholder stays
  backend/venv/bin/python scripts/revise_paper_v10.py 10.5281/zenodo.NNNNNNN   # T1 and D1
Changes:
  T1  Appendix B.2 gives the test count of the code to be tagged (the chat and ingest changes of 2026-10-21 added
      tests); TESTS and MODULES are the output of `pytest -q` in backend/.
  D1  (with a DOI argument) the Data and Code Availability statement names the tagged release paper-v1 and its archive
      DOI in place of "[DOI to be inserted]".
No result changes. v9 is left untouched.
"""
import re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from docx_tools import Doc, q

SRC = ROOT / "paper/research-paper/Precis_paper_clean_plane_revised_v9.docx"
DST = ROOT / "paper/research-paper/Precis_paper_clean_plane_revised_v10.docx"
TESTS, MODULES = 555, 17
TAG = "paper-v1"
DOI = sys.argv[1] if len(sys.argv) > 1 else None
assert DOI is None or re.fullmatch(r"10\.\d{4,9}/\S+", DOI), DOI
d = Doc(SRC)

# ------------------------------------------------------------------ T1: test count
d.replace(d.find("B.2 Negation-rendering defect"), "The test suite has 503 tests in 17 modules, all passing",
          "The test suite has %d tests in %d modules, all passing" % (TESTS, MODULES))

# ------------------------------------------------------------------ D1: archive DOI of the tagged release
if DOI:
    d.replace(d.find("The source code, experiment protocols"),
              "a tagged release that reproduces each table and its archive DOI will be given here at submission "
              "[DOI to be inserted]",
              "the tagged release %s, which reproduces each table, is archived at https://doi.org/%s" % (TAG, DOI))

full = "\n".join(d.text(p) for p in d.body.iter(q("p")))
assert "503 tests" not in full and ("[DOI to be inserted]" in full) == (DOI is None)
d.save(DST)
print("wrote", DST)
