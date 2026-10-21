"""Plot the two results figures of the Précis paper from the tables of the shared Word text (v8).

  backend/venv/bin/python scripts/plot_figures_results.py
Figure 3  ceiling sweeps (Table 6): exact match against the ceiling for G, N, H and W.
Figure 4  G − arm exact-match differences with 99% bootstrap intervals on the two protocol-first cohorts (Tables 5, 7),
          with the 5-point non-inferiority margin and the 3-7-point sensitivity band.
Values are parsed from the manuscript tables, not retyped, so a figure cannot drift from its table. Writes PDF (venue
LaTeX) and 300-dpi PNG (Word) to paper/figures/.
"""
import re, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from docx_tools import Doc, NS, q

SRC = ROOT / "paper/research-paper/Precis_paper_clean_plane_revised_v8.docx"
OUT = ROOT / "paper/figures"
d = Doc(SRC)


def table(first_cell):
    """Rows (lists of cell text) of the manuscript table whose top-left cell is first_cell."""
    for t in d.body.iter(q("tbl")):
        rows = [[d.text(tc).strip() for tc in tr.findall("w:tc", NS)] for tr in t.findall("w:tr", NS)]
        if rows[0][0] == first_cell:
            return rows
    raise KeyError(first_cell)


num = lambda s: float(s.replace("−", "-").replace(",", ""))


def diff(cell):
    """'+1.0 [-4.5, 7.0]' -> (1.0, -4.5, 7.0)"""
    m = re.fullmatch(r"([+\-−]?[\d.]+) \[([+\-−]?[\d.]+), ([+\-−]?[\d.]+)\]", cell)
    return tuple(num(x) for x in m.groups())


T5, T6, T7 = table("Arm"), table("Setting, ceiling (est. tokens)"), table("Arm (long documents)")
arm = lambda label: label.split(" (")[0]
FRESH = [(arm(r[0]), *diff(r[5])) for r in T5[1:] if r[5] != "reference"]
LONG = [(arm(r[0]), *diff(r[4])) for r in T7[1:] if r[4] != "reference"]
SWEEP = {}                                    # setting -> {arm: [(ceiling, EM)]}
for r in T6[1:]:
    setting, ceil = r[0].rsplit(", ", 1)
    for a, cell in zip(("G", "N", "H", "W"), r[1:5]):
        SWEEP.setdefault(setting, {}).setdefault(a, []).append((num(ceil), num(cell.split(" (")[0])))

# spot checks against the printed tables
assert [x[0] for x in FRESH] == ["N_raw", "N_clean", "W", "TC", "H", "D", "F2"]
assert ("H", -1.0, -6.0, 4.0) in FRESH and ("D", 8.5, 3.0, 14.5) in FRESH
assert [x[0] for x in LONG] == ["N", "N_raw", "W", "TC", "H"] and ("TC", -19.5, -28.5, -10.5) in LONG
assert SWEEP["Single document"]["G"] == [(256, 67), (512, 91), (1024, 96)]
assert SWEEP["Five-document corpus"]["H"] == [(1024, 91), (2048, 92)]

# ------------------------------------------------------------------ style: Times, thin marks, recessive axes
INK, INK2, GRID = "#0b0b0b", "#52514e", "#d9d8d4"
plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman", "TeX Gyre Termes", "Nimbus Roman"],
    "mathtext.fontset": "stix", "font.size": 8.5, "axes.titlesize": 8.5, "axes.labelsize": 8.5,
    "xtick.labelsize": 8, "ytick.labelsize": 8, "axes.edgecolor": INK2, "axes.labelcolor": INK,
    "xtick.color": INK2, "ytick.color": INK2, "axes.linewidth": 0.6, "xtick.major.width": 0.6,
    "ytick.major.width": 0.6, "axes.spines.top": False, "axes.spines.right": False,
    "pdf.fonttype": 42, "savefig.dpi": 300,
})
# validated categorical slots 1-4 (dataviz reference palette, light); markers and dashes carry identity in grey print
SERIES = {"G": ("#2a78d6", "o", "-"), "N": ("#eb6834", "s", "--"), "H": ("#1baf7a", "^", "-."), "W": ("#eda100", "D", ":")}
LABEL = {"G": "G (guarded priority)", "N": "N (budgeted chunks)", "H": "H (hybrid, table-aware)", "W": "W (whole doc, truncated)"}


def save(fig, name):
    # no tight bbox: the page is exactly figsize, so LaTeX places it at 100% and the text prints at its set size
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"{name}.{ext}", facecolor="white")
    plt.close(fig)


# Each size is the final print width, so text prints at 8-8.5 pt (EL asks for 8-12 pt figure labels): 504 pt (7.0 in),
# the EL two-column text width, also used in Word; 347.12 pt, the J.UCS text width. Table numbers stay out of the images
# (they differ per venue); panels carry (a)/(b) labels as EL requires for two-part figures.
SIZES = {"": (504 / 72, 2.7, 2.6), "_jucs": (347.12 / 72, 2.4, 2.2)}   # width, Figure 3 height, Figure 4 height (in)
LAYOUT = {"layout": "constrained"}


# ------------------------------------------------------------------ Figure 3: ceiling sweeps
def ceiling_sweep(width, height, suffix):
    narrow = width < 6
    fig, axes = plt.subplots(1, 2, figsize=(width, height), width_ratios=[3, 2], **LAYOUT)
    panels = [("(a) Single document", "Single document", [256, 512, 1024]),
              ("(b) Five-document corpus", "Five-document corpus", [1024, 2048])]
    for ax, (title, setting, ticks) in zip(axes, panels):
        for a, pts in SWEEP[setting].items():
            c, mk, ls = SERIES[a]
            xs, ys = zip(*pts)
            ax.plot(xs, ys, color=c, marker=mk, ls=ls, lw=1.4, ms=4.5, mec="white", mew=0.6, label=LABEL[a], zorder=3)
        ax.set_xscale("log", base=2)
        ax.set_xticks(ticks, [f"{t:,}" for t in ticks])
        ax.minorticks_off()
        ax.set_xlim(ticks[0] / 1.25, ticks[-1] * 1.25)
        ax.set_ylim(60, 102)
        ax.grid(axis="y", color=GRID, lw=0.5)
        ax.set_axisbelow(True)
        ax.set_title(title, color=INK, loc="left")
        ax.set_xlabel("Ceiling (estimated tokens)")
    axes[0].set_ylabel("Exact matches (of 200)")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="outside upper center", ncol=2 if narrow else 4, frameon=False, handlelength=2.6,
               columnspacing=1.4, fontsize=8)
    save(fig, "figure_3_ceiling_sweep" + suffix)


# ------------------------------------------------------------------ Figure 4: forest plot of G − arm
def forest(width, height, suffix):
    fig, axes = plt.subplots(1, 2, figsize=(width, height), sharex=True, **LAYOUT)
    panels = [("(a) Fresh table/list cohort", FRESH), ("(b) Long-document cohort", LONG)]
    for ax, (title, rows) in zip(axes, panels):
        ax.axvspan(-7, -3, color="#eeedea", lw=0, zorder=0)
        ax.axvline(-5, color=INK2, lw=0.8, ls="--", zorder=1)
        ax.axvline(0, color=INK, lw=0.8, zorder=1)
        for y, (a, est, lo, hi) in enumerate(reversed(rows)):
            ax.plot([lo, hi], [y, y], color=INK, lw=1.2, solid_capstyle="round", zorder=2)
            ax.plot(est, y, "o", color="#2a78d6", ms=5, mec="white", mew=0.8, zorder=3)
        ax.set_yticks(range(len(rows)), [r[0] for r in reversed(rows)])
        ax.set_ylim(-0.7, len(rows) - 0.3)
        ax.tick_params(axis="y", length=0)
        ax.spines["left"].set_visible(False)
        ax.grid(axis="x", color=GRID, lw=0.5)
        ax.set_axisbelow(True)
        ax.set_title(title, color=INK, loc="left")
    fig.supxlabel("Exact-match difference, G − arm (percentage points)", fontsize=8.5, color=INK)
    axes[0].set_xlim(-31, 17)
    axes[0].set_xticks([-30, -20, -10, 0, 10])
    axes[0].text(-6.0, len(FRESH) - 0.45, "−5 margin", ha="right", va="center", fontsize=8, color=INK2)
    save(fig, "figure_4_forest" + suffix)


for suffix, (width, h3, h4) in SIZES.items():
    ceiling_sweep(width, h3, suffix)
    forest(width, h4, suffix)
print("wrote", *sorted(p.name for p in OUT.glob("figure_[34]_[cf]*")))
