"""Matplotlib chart builders — one consistent executive design system.

Every slide's visual is rendered here to a PNG and embedded into the deck by
``deck.py``. Colors, fonts and spacing are shared so the 13 slides read as one
system. Each method returns the path to a written PNG.
"""

from __future__ import annotations

import os
import tempfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

from . import i18n

# --------------------------------------------------------------------------- #
# Design tokens
# --------------------------------------------------------------------------- #
INK = "#1B2A4A"        # titles / dark navy
ACCENT = "#2F6DB4"     # primary blue
WITHIN = "#6FA8DC"     # within-limit (light blue)
MGMT = "#1B2A4A"       # management approval (dark navy)
POS = "#2E8B6F"        # positive delta (green)
NEG = "#C0504D"        # negative delta (red)
MUTED = "#9AA5B1"      # grid / secondary
LIGHT = "#D7E3F0"      # light fill
CAT = ["#1F3B6D", "#3E7CB1", "#4CA1A3", "#7DAA6A", "#C8A15A", "#B0656B", "#7A6C9B"]

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.edgecolor": MUTED,
    "axes.labelcolor": INK,
    "text.color": INK,
    "xtick.color": INK,
    "ytick.color": INK,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 200,
})

FIGSIZE = (9.0, 4.6)


def fmt_try(x: float) -> str:
    ax = abs(x)
    if ax >= 1e9:
        return f"₺{x/1e9:.1f}B"
    if ax >= 1e6:
        return f"₺{x/1e6:.1f}M"
    if ax >= 1e3:
        return f"₺{x/1e3:.0f}k"
    return f"₺{x:.0f}"


class Charts:
    """Builds and saves all slide charts for one report, in one language."""

    def __init__(self, lang: str = "en", outdir: str | None = None):
        self.lang = lang
        self.outdir = outdir or tempfile.mkdtemp(prefix="procreport_")

    # -- infra ----------------------------------------------------------- #
    def _save(self, fig, name: str) -> str:
        path = os.path.join(self.outdir, f"{name}.png")
        fig.savefig(path, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        return path

    def _tv(self, v):
        return i18n.tv(v, self.lang)

    def _try_axis(self, ax, axis="x"):
        f = FuncFormatter(lambda v, _: fmt_try(v))
        (ax.xaxis if axis == "x" else ax.yaxis).set_major_formatter(f)

    # -- 1. horizontal bar ---------------------------------------------- #
    def hbar(self, series, name, color=ACCENT, value_labels=True):
        s = series.sort_values()
        labels = [self._tv(i) for i in s.index]
        fig, ax = plt.subplots(figsize=FIGSIZE)
        bars = ax.barh(labels, s.values, color=color, height=0.62)
        self._try_axis(ax, "x")
        ax.grid(axis="x", color=LIGHT, linewidth=0.8)
        ax.set_axisbelow(True)
        if value_labels:
            for b, v in zip(bars, s.values):
                ax.text(b.get_width(), b.get_y() + b.get_height() / 2,
                        "  " + fmt_try(v), va="center", ha="left",
                        fontsize=10, color=INK)
            ax.margins(x=0.14)
        fig.tight_layout()
        return self._save(fig, name)

    # -- 2. stacked horizontal bar (buyer: within vs mgmt) --------------- #
    def stacked_buyer(self, df, name):
        d = df.iloc[::-1]  # largest on top
        labels = list(d.index)
        within = d["Limit İçi"].values
        mgmt = d["Yönetim Onayı"].values
        fig, ax = plt.subplots(figsize=FIGSIZE)
        ax.barh(labels, within, color=WITHIN, height=0.64,
                label=i18n.t("within_limit", self.lang))
        ax.barh(labels, mgmt, left=within, color=MGMT, height=0.64,
                label=i18n.t("mgmt_approval", self.lang))
        self._try_axis(ax, "x")
        ax.grid(axis="x", color=LIGHT, linewidth=0.8)
        ax.set_axisbelow(True)
        ax.legend(loc="lower right", frameon=False, fontsize=10)
        fig.tight_layout()
        return self._save(fig, name)

    # -- 3. donut -------------------------------------------------------- #
    def donut(self, series, name, center=None, colors=None):
        vals = series.values
        labels = [self._tv(i) for i in series.index]
        colors = colors or CAT[:len(vals)]
        fig, ax = plt.subplots(figsize=(5.2, 4.6))
        wedges, _ = ax.pie(vals, colors=colors, startangle=90,
                           wedgeprops=dict(width=0.42, edgecolor="white"))
        total = vals.sum()
        ax.legend(wedges, [f"{l}  ·  {v/total:.0%}" for l, v in zip(labels, vals)],
                  loc="center left", bbox_to_anchor=(1.0, 0.5),
                  frameon=False, fontsize=10)
        if center:
            ax.text(0, 0, center, ha="center", va="center",
                    fontsize=13, fontweight="bold", color=INK)
        ax.set(aspect="equal")
        fig.tight_layout()
        return self._save(fig, name)

    # -- 4. Pareto ------------------------------------------------------- #
    def pareto(self, series, name, top=12):
        s = series.head(top)
        labels = [self._tv(i) for i in s.index]
        cum = s.cumsum() / series.sum() * 100
        fig, ax = plt.subplots(figsize=FIGSIZE)
        ax.bar(range(len(s)), s.values, color=ACCENT, width=0.7)
        self._try_axis(ax, "y")
        ax.set_xticks(range(len(s)))
        ax.set_xticklabels(labels, rotation=40, ha="right", fontsize=8.5)
        ax.grid(axis="y", color=LIGHT, linewidth=0.8)
        ax.set_axisbelow(True)
        ax2 = ax.twinx()
        ax2.plot(range(len(s)), cum.values, color=NEG, marker="o",
                 markersize=4, linewidth=1.8)
        ax2.axhline(80, color=MUTED, linestyle="--", linewidth=1)
        ax2.set_ylim(0, 105)
        ax2.set_ylabel(i18n.t("cumulative", self.lang))
        ax2.spines["top"].set_visible(False)
        fig.tight_layout()
        return self._save(fig, name)

    # -- 5. YTD trend line ---------------------------------------------- #
    def trend(self, series, marker, name):
        fig, ax = plt.subplots(figsize=FIGSIZE)
        ax.plot(series.index, series.values, color=ACCENT, linewidth=2)
        ax.fill_between(series.index, series.values, color=ACCENT, alpha=0.10)
        if marker in set(series.index):
            ax.scatter([marker], [series.loc[marker]], color=NEG, zorder=5, s=45)
            ax.axvline(marker, color=NEG, linestyle="--", linewidth=1, alpha=0.7)
        self._try_axis(ax, "y")
        ax.grid(axis="y", color=LIGHT, linewidth=0.8)
        ax.set_axisbelow(True)
        fig.autofmt_xdate(rotation=35)
        fig.tight_layout()
        return self._save(fig, name)

    # -- 6. savings waterfall ------------------------------------------- #
    def waterfall(self, wf, name):
        gross, saved, net = wf["gross"], wf["saved"], wf["net"]
        labels = ["List Price\nSpend" if self.lang == "en" else "Liste Fiyatı\nHarcaması",
                  "Savings" if self.lang == "en" else "Tasarruf",
                  "Net\nActual" if self.lang == "en" else "Net\nGerçekleşen"]
        fig, ax = plt.subplots(figsize=FIGSIZE)
        ax.bar(0, gross, color=MUTED, width=0.6)
        ax.bar(1, saved, bottom=net, color=POS, width=0.6)
        ax.bar(2, net, color=ACCENT, width=0.6)
        for x, top, v in [(0, gross, gross), (1, gross, saved), (2, net, net)]:
            ax.text(x, top, "\n" + fmt_try(v), ha="center", va="bottom",
                    fontsize=10, color=INK)
        ax.set_xticks([0, 1, 2])
        ax.set_xticklabels(labels, fontsize=9.5)
        self._try_axis(ax, "y")
        ax.grid(axis="y", color=LIGHT, linewidth=0.8)
        ax.set_axisbelow(True)
        ax.margins(y=0.18)
        fig.tight_layout()
        return self._save(fig, name)

    # -- 7. budget vs actual (grouped horizontal) ----------------------- #
    def budget_actual(self, df, name):
        d = df.iloc[::-1]
        labels = [self._tv(i) for i in d.index]
        y = range(len(d))
        fig, ax = plt.subplots(figsize=FIGSIZE)
        h = 0.36
        ax.barh([i + h/2 for i in y], d["Bütçe"].values, height=h,
                color=LIGHT, label=i18n.t("budget", self.lang))
        colors = [NEG if a > b else POS
                  for a, b in zip(d["Gerçekleşen"].values, d["Bütçe"].values)]
        ax.barh([i - h/2 for i in y], d["Gerçekleşen"].values, height=h,
                color=colors, label=i18n.t("actual", self.lang))
        ax.set_yticks(list(y))
        ax.set_yticklabels(labels)
        self._try_axis(ax, "x")
        ax.grid(axis="x", color=LIGHT, linewidth=0.8)
        ax.set_axisbelow(True)
        ax.legend(loc="lower right", frameon=False, fontsize=10)
        fig.tight_layout()
        return self._save(fig, name)

    # -- 8. risk panel: mini-pareto + two gauges ------------------------ #
    def risk_panel(self, model, name):
        risk = model["risk"]
        sup = model["supplier_pareto"].head(8)
        fig = plt.figure(figsize=FIGSIZE)
        gs = fig.add_gridspec(2, 2, width_ratios=[1.7, 1], height_ratios=[1, 1])
        axb = fig.add_subplot(gs[:, 0])
        s = sup.sort_values()
        axb.barh([self._tv(i) for i in s.index], s.values, color=ACCENT, height=0.6)
        self._try_axis(axb, "x")
        axb.grid(axis="x", color=LIGHT, linewidth=0.8)
        axb.set_axisbelow(True)
        axb.set_title("Top suppliers" if self.lang == "en" else "En büyük tedarikçiler",
                      fontsize=10, color=INK, loc="left")
        self._gauge(fig.add_subplot(gs[0, 1]), risk["top5_share"],
                    "Top-5 share" if self.lang == "en" else "İlk-5 payı", NEG)
        self._gauge(fig.add_subplot(gs[1, 1]), risk["fx_share"],
                    "FX exposure" if self.lang == "en" else "Döviz payı", ACCENT)
        fig.tight_layout()
        return self._save(fig, name)

    def _gauge(self, ax, frac, label, color):
        ax.pie([frac, 1 - frac], colors=[color, LIGHT], startangle=90,
               counterclock=False, wedgeprops=dict(width=0.35, edgecolor="white"))
        ax.text(0, 0, f"{frac:.0%}", ha="center", va="center",
                fontsize=13, fontweight="bold", color=INK)
        ax.set_title(label, fontsize=9.5, color=INK)
        ax.set(aspect="equal")
