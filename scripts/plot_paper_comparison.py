#!/usr/bin/env python3
"""Figure for doc/paper-comparison.md: paper model versus our quantum models on test."""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

r = json.loads(Path(sys.argv[1]).read_text())
names = ["paper", "quantum-short-D", "quantum-har-D", "quantum-har-A"]
labels = [
    "Paper's model\n(1 qubit, yesterday)",
    "Ours, no memory\n(2 qubits, yesterday)",
    "Ours\n(2 qubits, +week, +month)",
    "Ours + realism\ntraining",
]
cols = ["#9ca3af", "#93c5fd", "#2563eb", "#1e40af"]
panels = [
    ("log_loss", "Range forecast (log loss)"),
    ("qlike", "Point forecast (QLIKE)"),
    ("realism", "Realism of fake history\n(distance to real)"),
]
fig, axs = plt.subplots(1, 3, figsize=(10.5, 3.6))
for ax, (key, title) in zip(axs, panels):
    if key == "realism":
        vals = [r["realism"][n]["mean"] for n in names]
        err = [r["realism"][n]["sd"] or 0 for n in names]
    else:
        vals = [r["summary"][n][key]["mean"] for n in names]
        err = [r["summary"][n][key]["sd"] or 0 for n in names]
    ax.bar(range(4), vals, yerr=err, color=cols, width=0.7, capsize=2)
    for i, (v, e) in enumerate(zip(vals, err)):
        ax.text(
            i,
            v + e + max(vals) * 0.03,
            f"{v:.2f}" if v < 10 else f"{v:.0f}",
            ha="center",
            fontsize=8.5,
        )
    ax.set_xticks(range(4), [""] * 4)
    ax.set_title(title, fontsize=10, loc="left")
    ax.set_ylim(0, max(v + e for v, e in zip(vals, err)) * 1.2)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=8.5)
handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in cols]
fig.legend(handles, labels, loc="lower center", ncol=4, frameon=False, fontsize=8.5)
fig.suptitle(
    "Our quantum model beats the paper's model on every measure (lower is better)",
    x=0.01,
    ha="left",
    fontsize=11.5,
    fontweight="bold",
)
fig.tight_layout(rect=(0, 0.13, 1, 0.95))
fig.savefig(sys.argv[2], dpi=180)
