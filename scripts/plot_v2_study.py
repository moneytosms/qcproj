#!/usr/bin/env python3
"""Figure for doc/v2-study.md: test log loss, old versus v2, quantum versus classical."""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

r = json.loads(Path(sys.argv[1]).read_text())["summary"]
paper = json.loads(Path(sys.argv[2]).read_text())["summary"]["paper"]["log_loss"]["mean"]
fig, ax = plt.subplots(figsize=(7.5, 3.8))
bars = [
    ("Paper's model\n(1 qubit)", paper, 0, "#d1d5db"),
    (
        "Our quantum\nv1",
        r["quantum-har-D"]["log_loss"]["mean"],
        r["quantum-har-D"]["log_loss"]["sd"],
        "#93c5fd",
    ),
    (
        "Our quantum\nv2",
        r["quantum-v2"]["log_loss"]["mean"],
        r["quantum-v2"]["log_loss"]["sd"],
        "#1d4ed8",
    ),
    ("Softmax\nv1 inputs", r["softmax-har-D"]["log_loss"]["mean"], 0, "#d6d3d1"),
    ("Softmax\nv2 inputs", r["softmax-v2"]["log_loss"]["mean"], 0, "#78716c"),
]
for i, (label, value, sd, color) in enumerate(bars):
    ax.bar(i, value, yerr=sd, color=color, width=0.68, capsize=2)
    ax.text(i, value + 0.02, f"{value:.3f}", ha="center", fontsize=9)
ax.set_xticks(range(len(bars)), [b[0] for b in bars], fontsize=8.5)
ax.set_ylabel("Test log loss (lower is better)", fontsize=9)
ax.set_ylim(0, 1.32)
ax.spines[["top", "right"]].set_visible(False)
ax.set_title(
    "Quantum v2: 0.041 better than v1, still behind classical (post-hoc test)",
    loc="left",
    fontsize=10.5,
    fontweight="bold",
)
fig.tight_layout()
fig.savefig(sys.argv[3], dpi=180)
