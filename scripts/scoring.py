"""Shared scoring rule: a prediction is correct if it matches the gold answer or ANY MRQA alternative.

Exact match = normalised string equality (precis.evaluation.metrics.compute_exact_match); containment = word-boundary
normalised containment. Aliases come from backend/data/nq_subset/nq_dev.jsonl (`answers`), keyed by doc_id = sample_id.
Used by unified_scoring.py and analyze_followup.py so every table uses one rule.
"""
import json, math, random, re, sys, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend/src"))
from precis.evaluation.metrics import compute_exact_match, normalize_answer  # noqa: E402

ALIASES = {}
for l in (ROOT / "backend/data/nq_subset/nq_dev.jsonl").open():
    r = json.loads(l)
    ALIASES[r["doc_id"]] = [a for a in dict.fromkeys([r["gold_answer"], *r.get("answers", [])]) if a]


def contains(text, ans):
    na, nt = normalize_answer(ans), normalize_answer(text)
    return bool(na and nt and re.search(r"(?:\b|^)" + re.escape(na) + r"(?:\b|$)", nt))


def em(sid, pred):
    return any(compute_exact_match(pred, a) for a in ALIASES[sid])


def cont(sid, pred):
    return any(contains(pred, a) for a in ALIASES[sid])


def mcn(b, c, alt="two"):
    n = b + c
    if n == 0: return 1.0
    if alt == "two":
        k = min(b, c)
        return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)
    return sum(math.comb(n, i) for i in range(c + 1)) / 2 ** n   # one-sided: b > c


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i]); m = len(ps); out = [0.0] * m; run = 0.0
    for r, i in enumerate(order):
        run = max(run, min(1.0, (m - r) * ps[i])); out[i] = run
    return out


def boot(groups, B=10000, seed=42):
    keys = list(groups); rnd = random.Random(seed); s = []
    for _ in range(B):
        t = n = 0
        for _ in keys:
            g = groups[keys[rnd.randrange(len(keys))]]; t += sum(g); n += len(g)
        s.append(t / n)
    s.sort()
    return [round(100 * s[int(.025 * B)], 2), round(100 * s[int(.975 * B)], 2)]


def paired(X, Y, f, cluster=None):
    """X,Y: dict id->record. returns x_only,y_only, net_pp, two-sided exact p, optional cluster bootstrap CI."""
    ids = sorted(X)
    b = sum(1 for i in ids if f(i, X[i]) and not f(i, Y[i])); c = sum(1 for i in ids if (not f(i, X[i])) and f(i, Y[i]))
    out = {"x_only": b, "y_only": c, "net_pp": round(100 * (b - c) / len(ids), 2), "p_two_sided": mcn(b, c)}
    if cluster:
        g = collections.defaultdict(list)
        for i in ids: g[cluster[i]].append(int(f(i, X[i])) - int(f(i, Y[i])))
        out["cluster_boot95_pp"] = boot(g)
    return out


