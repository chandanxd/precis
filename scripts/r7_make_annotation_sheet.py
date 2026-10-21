"""R7: build the annotation sheet for extractor quality (negation polarity, modality).

  PYTHONPATH=backend/src backend/venv/bin/python scripts/r7_make_annotation_sheet.py
Outputs experiments/extractor_eval/{facts_to_annotate.csv, sentences_to_annotate.csv, sample_meta.json}.
Part A (facts): is the stored polarity and the stored modality right for the source sentence?
Part B (sentences): independent of the extractor, is the sentence negated, and what is its modality? Used for recall.
"""
import csv, json, random, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend/src"))
from precis.api.security import sanitize_document
from precis.pipeline.svoa import extract_facts, get_nlp

OUT = ROOT / "experiments/extractor_eval"; OUT.mkdir(exist_ok=True)
rnd = random.Random(42)
docs = [json.loads(l) for l in (ROOT / "backend/data/nq_subset/nq_dev.jsonl").open()]
rnd.shuffle(docs)
CUE = re.compile(r"\b(not|n't|no|never|neither|nor|none|nothing|nobody|without|cannot|unable|fail(?:s|ed)? to)\b", re.I)
HEDGE = re.compile(r"\b(might|may|could|would|if|unless|said|says|claimed|claims|reported|according to|believed|alleged|suggest(?:s|ed)?|perhaps|possibly)\b", re.I)

facts, sents = [], []
nlp = get_nlp()
for d in docs[:700]:
    try: text = sanitize_document(d["document"])
    except ValueError: continue
    try: fs = extract_facts(text, source_doc=d["doc_id"])
    except Exception: continue
    for f in fs: facts.append((d["doc_id"], f))
    for s in nlp(text[:6000]).sents:
        st = s.text.strip()
        if 5 <= len(st.split()) <= 60: sents.append((d["doc_id"], st))

neg = [x for x in facts if x[1].negated]
mod = [x for x in facts if (not x[1].negated) and x[1].modality != "asserted"]
asr = [x for x in facts if (not x[1].negated) and x[1].modality == "asserted"]
for g in (neg, mod, asr): rnd.shuffle(g)
sel = neg[:130] + mod[:120] + asr[:150]
rnd.shuffle(sel)
with open(OUT / "facts_to_annotate.csv", "w", newline="") as fo:
    w = csv.writer(fo)
    w.writerow(["item", "doc_id", "source_sentence", "subject", "verb", "object", "stored_negated", "stored_modality", "stored_attribution",
                "A_polarity_correct(Y/N)", "A_modality_correct(Y/N)", "A_true_modality(asserted/attributed/conditional/hypothetical)",
                "B_polarity_correct(Y/N)", "B_modality_correct(Y/N)", "B_true_modality(asserted/attributed/conditional/hypothetical)", "notes"])
    for i, (did, f) in enumerate(sel, 1):
        w.writerow([i, did, f.raw_sentence, f.subject, f.verb, f.object, int(f.negated), f.modality, f.attributed_to or "", "", "", "", "", "", "", ""])

cue = [x for x in sents if CUE.search(x[1])]; hed = [x for x in sents if HEDGE.search(x[1]) and not CUE.search(x[1])]
oth = [x for x in sents if not CUE.search(x[1]) and not HEDGE.search(x[1])]
for g in (cue, hed, oth): rnd.shuffle(g)
ssel = cue[:100] + hed[:60] + oth[:40]; rnd.shuffle(ssel)
with open(OUT / "sentences_to_annotate.csv", "w", newline="") as fo:
    w = csv.writer(fo)
    w.writerow(["item", "doc_id", "sentence", "A_main_claim_negated(Y/N)", "A_modality(asserted/attributed/conditional/hypothetical)",
                "B_main_claim_negated(Y/N)", "B_modality(asserted/attributed/conditional/hypothetical)", "notes"])
    for i, (did, s) in enumerate(ssel, 1): w.writerow([i, did, s, "", "", "", "", ""])

ext = {}
for i, (did, st) in enumerate(ssel, 1):
    try: fs = extract_facts(st, source_doc=did)
    except Exception: fs = []
    ext[i] = [{"negated": bool(f.negated), "modality": f.modality} for f in fs]
json.dump(ext, open(OUT / "sentences_extractor_output.json", "w"))   # do not show to annotators

json.dump({"docs_scanned": 700, "facts_total": len(facts), "negated": len(neg), "non_asserted": len(mod), "asserted": len(asr),
           "facts_sampled": len(sel), "sentences_total": len(sents), "sentences_sampled": len(ssel),
           "sampling": "seed 42; facts: 130 negated + 120 non-asserted + 150 asserted (shuffled); sentences: 100 with a negation cue, 60 with a hedge/attribution/condition cue, 40 without",
           "strata_available": {"cue": len(cue), "hedge": len(hed), "other": len(oth)}}, open(OUT / "sample_meta.json", "w"), indent=1)
print(len(facts), len(neg), len(mod), len(asr), len(sel), len(ssel))
