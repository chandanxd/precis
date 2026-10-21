"""Minimal lxml helpers to edit the Précis manuscript DOCX in place (paragraph text, cloned paragraphs/tables, moves).

Body paragraphs of the manuscript are plain runs (Times New Roman 10 pt), headings are bold runs, captions are a bold
label run followed by a regular run. Equations are OMML paragraphs and are never touched here.
"""
import copy, re, zipfile
from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
q = lambda t: "{%s}%s" % (W, t)


class Doc:
    def __init__(self, path):
        self.path = path
        z = zipfile.ZipFile(path)
        self.parts = {n: z.read(n) for n in z.namelist()}
        self.root = etree.fromstring(self.parts["word/document.xml"])
        self.body = self.root.find("w:body", NS)
        self.orig = list(self.body)           # stable handles by original index

    # ---------------------------------------------------------------- reading
    def text(self, el):
        return "".join(t.text or "" for t in el.iter(q("t")))

    def find(self, startswith, after=None):
        """First body element whose text starts with the given string (optionally after a given element)."""
        seen = after is None
        for el in self.body:
            if not seen:
                seen = el is after
                continue
            if el.tag == q("p") and self.text(el).startswith(startswith):
                return el
        raise KeyError(startswith)

    # ---------------------------------------------------------------- run builders
    def _run(self, tmpl_run, text, bold=None, italic=None, sup=False, sub=False):
        r = copy.deepcopy(tmpl_run)
        for t in r.findall("w:t", NS): r.remove(t)
        rpr = r.find("w:rPr", NS)
        if bold is not None:
            for b in rpr.findall("w:b", NS): rpr.remove(b)
            b = etree.SubElement(rpr, q("b"))
            if not bold: b.set(q("val"), "0")
        if italic is not None:
            for b in rpr.findall("w:i", NS): rpr.remove(b)
            b = etree.SubElement(rpr, q("i"))
            if not italic: b.set(q("val"), "0")
        if sup or sub:
            va = etree.SubElement(rpr, q("vertAlign")); va.set(q("val"), "superscript" if sup else "subscript")
        t = etree.SubElement(r, q("t")); t.text = text; t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        self._order_rpr(rpr)
        return r

    @staticmethod
    def _order_rpr(rpr):
        order = ["rFonts", "b", "i", "color", "sz", "vertAlign"]
        kids = sorted(list(rpr), key=lambda e: order.index(e.tag.split("}")[1]) if e.tag.split("}")[1] in order else 99)
        for k in list(rpr): rpr.remove(k)
        for k in kids: rpr.append(k)

    def set_runs(self, p, parts):
        """Replace all runs of paragraph p by parts = [(text, {bold:.., italic:..}), ...] using the first run's formatting."""
        runs = p.findall("w:r", NS)
        tmpl = copy.deepcopy(runs[0])
        for r in runs: p.remove(r)
        for text, fmt in parts:
            p.append(self._run(tmpl, text, **fmt))
        return p

    def set_text(self, p, text, lead=None):
        parts = ([(lead, {"bold": True})] if lead else []) + [(text, {"bold": False} if lead else {})]
        return self.set_runs(p, parts)

    def replace(self, p, old, new, count=1):
        """Cross-run find/replace inside one paragraph; raises if old is absent."""
        runs = p.findall("w:r", NS)
        ts = [r.find("w:t", NS) for r in runs]
        full = "".join((t.text or "") if t is not None else "" for t in ts)
        i = full.find(old)
        if i < 0: raise KeyError("%r not in %r" % (old, full[:80]))
        pos = 0; done = False
        for r, t in zip(runs, ts):
            if t is None: continue
            L = len(t.text or "")
            s, e = max(i, pos), min(i + len(old), pos + L)
            if s < e or (not done and L == 0):
                a = t.text
                if not done and s < e:
                    t.text = a[: s - pos] + new + a[e - pos:]; done = True
                elif s < e:
                    t.text = a[: s - pos] + a[e - pos:]
            pos += L
        return p

    # ---------------------------------------------------------------- structure
    def clone_after(self, ref, tmpl, parts):
        p = copy.deepcopy(tmpl)
        self.set_runs(p, parts)
        ref.addnext(p)
        return p

    def delete(self, el):
        el.getparent().remove(el)

    def move_after(self, ref, els):
        cur = ref
        for e in els:
            cur.addnext(e); cur = e
        return cur

    def make_table(self, tmpl_tbl, header, rows, widths, first_col_left=True, font_sz=None):
        """Clone a manuscript table and rebuild header/body with len(widths) columns (widths in twips)."""
        t = copy.deepcopy(tmpl_tbl)
        trs = t.findall("w:tr", NS)
        hdr_tr, body_tr = copy.deepcopy(trs[0]), copy.deepcopy(trs[1])
        for tr in trs: t.remove(tr)
        grid = t.find("w:tblGrid", NS)
        for g in list(grid): grid.remove(g)
        for w_ in widths:
            g = etree.SubElement(grid, q("gridCol")); g.set(q("w"), str(w_))
        t.find("w:tblPr/w:tblW", NS).set(q("w"), str(sum(widths)))

        def build(tmpl_tr, cells, left_first):
            tr = copy.deepcopy(tmpl_tr)
            tcs = tr.findall("w:tc", NS)
            base = copy.deepcopy(tcs[min(1, len(tcs) - 1)])
            for tc in tcs: tr.remove(tc)
            for k, (txt, w_) in enumerate(zip(cells, widths)):
                tc = copy.deepcopy(base)
                tc.find("w:tcPr/w:tcW", NS).set(q("w"), str(w_))
                p = tc.find("w:p", NS)
                self.set_runs(p, [(str(txt), {})])
                if font_sz:
                    for sz in p.iter(q("sz")): sz.set(q("val"), str(font_sz))
                jc = p.find("w:pPr/w:jc", NS)
                if jc is not None and left_first and k == 0: jc.set(q("val"), "left")
                tr.append(tc)
            return tr

        t.append(build(hdr_tr, header, False))
        for i, row in enumerate(rows):
            t.append(build(body_tr, row, first_col_left))
        return t

    def save(self, path):
        self.parts["word/document.xml"] = etree.tostring(self.root, xml_declaration=True, encoding="UTF-8", standalone=True)
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            for n, b in self.parts.items(): z.writestr(n, b)
