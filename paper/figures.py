"""Vector figures for the paper, drawn from paper/results.json only."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

here = Path(__file__).parent
d = json.loads((here / "results.json").read_text())
plt.rcParams.update(
    {
        "font.family": "serif",
        "font.size": 9,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "svg.fonttype": "none",
    }
)
COL = {"quantum": "#4c3fb0", "classical": "#2f7d6b", "paper": "#8a8a8a"}


def bars(rows, name, xlabel="Test log loss (lower is better)", w=5.4):
    fig, ax = plt.subplots(figsize=(w, 0.36 * len(rows) + 0.7))
    ys = range(len(rows))[::-1]
    ax.barh(list(ys), [r["value"] for r in rows], color=[COL[r["kind"]] for r in rows], height=0.62)
    for y, r in zip(ys, rows):
        ax.text(r["value"] + 0.01, y, f"{r['value']:.4g}", va="center", fontsize=8)
    ax.set_yticks(list(ys), [r["label"] for r in rows])
    ax.set_xlabel(xlabel)
    ax.set_xlim(0, max(r["value"] for r in rows) * 1.12)
    fig.tight_layout()
    fig.savefig(here / "fig" / name)


bars(d["fresh_btc"], "fresh.svg")
bars(d["paper_data"], "paperdata.svg")

fig, ax = plt.subplots(figsize=(5.4, 1.9))
for i, c in enumerate(d["contrasts"]):
    y = len(d["contrasts"]) - 1 - i
    ax.errorbar(
        c["mean"],
        y,
        xerr=[[c["mean"] - c["lower"]], [c["upper"] - c["mean"]]],
        fmt="o",
        color=COL["quantum"],
        capsize=3,
    )
ax.axvline(0, color="k", lw=0.8)
ax.set_yticks(range(len(d["contrasts"]))[::-1], [c["label"] for c in d["contrasts"]])
ax.set_xlabel("Paired log-loss difference, 95% block bootstrap interval")
fig.tight_layout()
fig.savefig(here / "fig" / "contrasts.svg")

fig, ax = plt.subplots(figsize=(5.4, 2.4))
cs = sorted(d["coins"], key=lambda c: c["gain"])
ax.bar(
    [c["coin"] for c in cs],
    [c["gain"] for c in cs],
    color=[COL["quantum"] if c["gain"] > 0 else COL["classical"] for c in cs],
)
ax.axhline(d["threshold_percent"], color="#b3261e", lw=1, ls="--")
ax.text(0, d["threshold_percent"] + 0.25, "5% pre-registered target", color="#b3261e", fontsize=8)
ax.axhline(0, color="k", lw=0.8)
ax.set_ylabel("Quantum gain over best\nclassical (%)")
fig.tight_layout()
fig.savefig(here / "fig" / "coins.svg")
