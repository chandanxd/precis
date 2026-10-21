"""Baseline-adequacy and binding-budget experiments (protocol: experiments/baseline_budget/PROTOCOL.md).

  PYTHONPATH=backend/src backend/venv/bin/python scripts/run_baseline_budget.py single   # E1, E2, E4
  PYTHONPATH=backend/src backend/venv/bin/python scripts/run_baseline_budget.py multi    # E3
Resumable; writes experiments/baseline_budget/{single,multi}_records.jsonl.
"""
import hashlib, html, inspect, json, math, random, re, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend/src")); sys.path.insert(0, str(ROOT / "scripts"))
import lxml.html
from precis.api.security import sanitize_document
from precis.evaluation.naive_rag import naive_rag_retrieve
from precis.graph.store import FactStore
from precis.pipeline import orchestrator, structural
from precis.pipeline.inference import generate_answer
from precis.pipeline.orchestrator import assemble_query_context, ingest_document
from precis.pipeline.sdh import embed_texts
from eval_table_selection_v2 import check_containment, check_exact_match

D = ROOT / "experiments/baseline_budget"
MANI = ROOT / "experiments/fresh_table_cohort/manifest.jsonl"
NQ = ROOT / "backend/data/nq_subset/nq_dev.jsonl"
BASE, MODEL = "http://127.0.0.1:11434", "qwen2.5-coder:7b"
est = lambda t: structural.estimate_text_tokens(t) if t else 0

# ---------------------------------------------------------------- G variants (E4)
_SRC = inspect.getsource(structural.assemble_structural_query_context)


def make_variant(rel=0.25, kw=0.15, elig=0.40, cap=3):
    s = _SRC
    for old, new in (
        ("if sim >= 0.25 or (has_kw_match and sim >= 0.15):", f"if sim >= {rel} or (has_kw_match and sim >= {kw}):"),
        ("elif sim >= 0.40:", f"elif sim >= {elig}:"),
        ("selected_struct = ranked_struct[:3]", f"selected_struct = ranked_struct[:{cap}]"),
    ):
        assert s.count(old) == 1, old
        s = s.replace(old, new)
    ns = dict(structural.__dict__); exec(s, ns)
    return ns["assemble_structural_query_context"]


G_FN = orchestrator.assemble_structural_query_context
VARIANTS = {"rel0.20": dict(rel=0.20), "rel0.30": dict(rel=0.30), "kw0.10": dict(kw=0.10), "kw0.20": dict(kw=0.20),
            "elig0.30": dict(elig=0.30), "elig0.50": dict(elig=0.50), "cap2": dict(cap=2), "cap4": dict(cap=4)}
VAR_FNS = {k: make_variant(**v) for k, v in VARIANTS.items()}


def g_context(fn, q, store, ceiling):
    orchestrator.assemble_structural_query_context = fn
    try:
        r = assemble_query_context(query=q, store=store, token_ceiling=ceiling, enable_list_extraction=True, raw_document=None)
    finally:
        orchestrator.assemble_structural_query_context = G_FN
    return r.context


# ---------------------------------------------------------------- independent HTML -> Markdown blocks
BLOCK = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "dl", "dd", "dt", "blockquote", "section", "article", "center"}
SKIP = {"script", "style"}


def ws(t):
    return re.sub(r"\s+", " ", html.unescape(t or "")).strip()


def table_md(el):
    rows = []
    for tr in el.iter("tr"):
        cells = [ws(c.text_content()).replace("|", "/") for c in tr if isinstance(c.tag, str) and c.tag.lower() in ("td", "th")]
        if any(cells): rows.append(cells)
    if not rows: return ""
    n = max(len(r) for r in rows); rows = [r + [""] * (n - len(r)) for r in rows]
    out = ["| " + " | ".join(rows[0]) + " |", "| " + " | ".join(["---"] * n) + " |"]
    out += ["| " + " | ".join(r) + " |" for r in rows[1:]]
    return "\n".join(out)


def list_md(el, depth=0):
    lines = []
    for li in el:
        if not isinstance(li.tag, str) or li.tag.lower() != "li": continue
        own = ws(" ".join([li.text or ""] + [c.text_content() + (c.tail or "") for c in li
                                              if isinstance(c.tag, str) and c.tag.lower() not in ("ul", "ol")]))
        if own: lines.append("  " * depth + "- " + own)
        for c in li:
            if isinstance(c.tag, str) and c.tag.lower() in ("ul", "ol"): lines += list_md(c, depth + 1)
    return lines


def html_blocks(raw):
    """Document-order list of (kind, text) with kind in prose/table/list."""
    root = lxml.html.fromstring("<div>" + raw + "</div>")
    blocks, buf = [], []

    def flush():
        t = ws(" ".join(buf)); buf.clear()
        if t: blocks.append(("prose", t))

    def walk(el):
        if not isinstance(el.tag, str): return
        tag = el.tag.lower()
        if tag in SKIP: return
        if tag == "table":
            flush(); t = table_md(el)
            if t: blocks.append(("table", t))
            return
        if tag in ("ul", "ol"):
            flush(); ls = list_md(el)
            if ls: blocks.append(("list", "\n".join(ls)))
            return
        if tag in BLOCK: flush()
        buf.append(el.text or "")
        for c in el:
            walk(c); buf.append(c.tail or "")
        if tag in BLOCK: flush()

    walk(root); flush()
    return blocks


def trim(text, ceiling):
    words = text.split()
    if est(text) <= ceiling: return text
    return " ".join(words[: int(ceiling / 1.3)])


def split_table(t, limit=300):
    lines = t.split("\n"); head, body = lines[:2], lines[2:]
    pieces, cur = [], []
    for ln in body:
        if cur and est("\n".join(head + cur + [ln])) > limit:
            pieces.append("\n".join(head + cur)); cur = []
        cur.append(ln)
    if cur or not pieces: pieces.append("\n".join(head + cur))
    return pieces


def aware_chunks(blocks, prose_words=128):
    chunks, cur = [], []

    def flush():
        if cur: chunks.append(" ".join(cur)); cur.clear()

    for kind, t in blocks:
        if kind == "prose":
            cur.append(t)
            if len(" ".join(cur).split()) >= prose_words: flush()
        else:
            flush()
            if kind == "table" and est(t) > 400: chunks += split_table(t)
            elif kind == "list" and est(t) > 400:
                ls, c = t.split("\n"), []
                for ln in ls:
                    if c and est("\n".join(c + [ln])) > 300: chunks.append("\n".join(c)); c = []
                    c.append(ln)
                if c: chunks.append("\n".join(c))
            else: chunks.append(t)
    flush()
    return chunks


TOK = re.compile(r"\w+")


def bm25_scores(query, chunks, k1=1.5, b=0.75):
    docs = [TOK.findall(c.lower()) for c in chunks]; N = len(docs)
    avg = sum(map(len, docs)) / max(1, N)
    df = {}
    for d in docs:
        for w in set(d): df[w] = df.get(w, 0) + 1
    out = []
    for d in docs:
        s = 0.0
        for w in set(TOK.findall(query.lower())):
            f = d.count(w)
            if not f: continue
            idf = math.log(1 + (N - df[w] + 0.5) / (df[w] + 0.5))
            s += idf * f * (k1 + 1) / (f + k1 * (1 - b + b * len(d) / max(1e-9, avg)))
        out.append(s)
    return out


def rank(scores):
    return sorted(range(len(scores)), key=lambda i: (-scores[i], i))


def select(chunks, order, ceiling, k=5):
    sel, used = [], 0
    for i in order:
        c = chunks[i]; cost = est(c) + 2
        if len(sel) >= k: break
        if used + cost > ceiling:
            if not sel: sel.append(trim(c, ceiling)); used = ceiling
            continue
        sel.append(c); used += cost
    return "\n\n".join(sel)


def retrieval_arms(blocks, q, ceilings):
    chunks = aware_chunks(blocks)
    if not chunks: return {c: {"TC": "", "H": ""} for c in ceilings}
    emb = embed_texts(chunks + [q]); qv = emb[-1]
    dense = [sum(a * b for a, b in zip(v, qv)) for v in emb[:-1]]
    bm = bm25_scores(q, chunks)
    rd, rb = rank(dense), rank(bm)
    fused = [0.0] * len(chunks)
    for r in (rd, rb):
        for pos, i in enumerate(r): fused[i] += 1.0 / (60 + pos + 1)
    rh = rank(fused)
    return {c: {"TC": select(chunks, rd, c), "H": select(chunks, rh, c)} for c in ceilings}


def md_doc(blocks):
    return "\n\n".join(t for _, t in blocks)


def gen(q, ctx, gold, answers):
    if not ctx.strip():
        return {"pred": "", "em": False, "cont": False, "status": "empty_context", "prompt_tokens": None, "context": ctx, "est_tokens": 0}
    res = generate_answer(query=q, context=ctx, model=MODEL, temperature=0.0, top_p=0.9, max_tokens=512,
                          prompt_style="concise", base_url=BASE)
    p = (res.answer or "").strip()
    return {"pred": p, "em": check_exact_match(p, gold, answers) if p else False,
            "cont": check_containment(p, gold, answers) if p else False,
            "status": "ok" if p else "empty_answer", "prompt_tokens": res.prompt_tokens,
            "context": ctx, "est_tokens": est(ctx)}


def load():
    rows = [json.loads(l) for l in MANI.open()][1:]
    docs = {}
    for l in NQ.open():
        r = json.loads(l); docs[r["doc_id"]] = r
    return rows, docs


def run_single():
    out = D / "single_records.jsonl"
    rows, docs = load()
    done = {json.loads(l)["sample_id"] for l in out.open()} if out.exists() else set()
    with out.open("a") as fo:
        for i, m in enumerate(rows, 1):
            sid = m["sample_id"]
            if sid in done: continue
            t0 = time.time()
            raw, q, gold, answers = docs[sid]["document"], m["question"], m["gold_answer"], m["answers"]
            clean = sanitize_document(raw)
            blocks = html_blocks(raw)
            full = md_doc(blocks)
            store = FactStore(in_memory=True, collection_name=f"bb_{i}_{sid[:10]}")
            ingest_document(text=clean, source_doc=sid, store=store, enable_list_extraction=True, raw_document=raw)
            row = {"sample_id": sid, "e1": {}, "e2": {}, "e4": {}}
            # E1 + E2 contexts
            ceil_all = [256, 512, 1024, 2048]
            ra = retrieval_arms(blocks, q, ceil_all)
            ch, _ = naive_rag_retrieve(document=clean, query=q, top_k=5, chunk_size=512, overlap=128)
            ncl = "\n\n".join(ch) if ch else ""
            for c in ceil_all:
                ctxs = {"G": g_context(G_FN, q, store, c), "N": trim(ncl, c), "H": ra[c]["H"], "W": trim(full, c)}
                if c == 2048: ctxs["TC"] = ra[c]["TC"]
                tgt = row["e1"] if c == 2048 else row["e2"].setdefault(str(c), {})
                for a, ctx in ctxs.items():
                    if c == 2048 and a == "N": continue   # N_clean/N_raw already in the fresh cohort
                    tgt[a] = gen(q, ctx, gold, answers)
            row["e2"].pop("2048", None)
            # E4 variants at 2048
            g2048 = row["e1"]["G"]
            for name, fn in VAR_FNS.items():
                ctx = g_context(fn, q, store, 2048)
                if ctx == g2048["context"]:
                    r = {k: g2048[k] for k in ("pred", "em", "cont", "status", "prompt_tokens", "est_tokens")}; r["same_as_G"] = True
                else:
                    r = gen(q, ctx, gold, answers); r["same_as_G"] = False
                    r.pop("context")
                row["e4"][name] = r
            fo.write(json.dumps(row) + "\n"); fo.flush()
            print(i, sid[:8], "G", row["e1"]["G"]["em"], "H", row["e1"]["H"]["em"], "W", row["e1"]["W"]["em"],
                  "TC", row["e1"]["TC"]["em"], round(time.time() - t0), "s", flush=True)


def run_multi():
    out = D / "multi_records.jsonl"
    rows, docs = load()
    pool = [r for r in docs.values() if 100 <= len(r["document"].split()) <= 800]
    done = {json.loads(l)["sample_id"] for l in out.open()} if out.exists() else set()
    rnd = random.Random(42)
    with out.open("a") as fo:
        for i, m in enumerate(rows, 1):
            sid = m["sample_id"]
            # draw distractors for every case (keeps the random stream identical when resuming)
            dis = []
            while len(dis) < 4:
                r = rnd.choice(pool)
                if r["doc_id"] == sid or r["question"] == m["question"] or r["doc_id"] in {d["doc_id"] for d in dis}: continue
                try: sanitize_document(r["document"])
                except ValueError: continue
                dis.append(r)
            order = [docs[sid]] + dis; rnd.shuffle(order)
            if sid in done: continue
            t0 = time.time(); q, gold, answers = m["question"], m["gold_answer"], m["answers"]
            store = FactStore(in_memory=True, collection_name=f"bm_{i}_{sid[:10]}")
            blocks, cleans = [], []
            for d in order:
                ingest_document(text=sanitize_document(d["document"]), source_doc=d["doc_id"], store=store,
                                enable_list_extraction=True, raw_document=d["document"])
                blocks += html_blocks(d["document"]); cleans.append(sanitize_document(d["document"]))
            full = md_doc(blocks)
            ceil = [1024, 2048]
            ra = retrieval_arms(blocks, q, ceil)
            ch, _ = naive_rag_retrieve(document="\n\n".join(cleans), query=q, top_k=5, chunk_size=512, overlap=128)
            ncl = "\n\n".join(ch) if ch else ""
            row = {"sample_id": sid, "target_pos": [d["doc_id"] for d in order].index(sid), "corpus_est_tokens": est(full), "e3": {}}
            for c in ceil:
                ctxs = {"G": g_context(G_FN, q, store, c), "N": trim(ncl, c), "H": ra[c]["H"], "W": trim(full, c)}
                row["e3"][str(c)] = {a: gen(q, ctx, gold, answers) for a, ctx in ctxs.items()}
            fo.write(json.dumps(row) + "\n"); fo.flush()
            print(i, sid[:8], {a: v["em"] for a, v in row["e3"]["1024"].items()}, round(time.time() - t0), "s", flush=True)


if __name__ == "__main__":
    {"single": run_single, "multi": run_multi}[sys.argv[1]]()
