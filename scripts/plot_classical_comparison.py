#!/usr/bin/env python3
"""Export Step 4 forecast, quantile, simulation and training diagnostics."""

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    root = args.run
    read = lambda name: json.loads((root / name).read_text())
    rows = read("records.json")
    audit = read("audit.json")
    manifest = read("manifest.json")
    selected = [
        "quantum-prior-D",
        "quantum-prior-A",
        "softmax-prior-D",
        "softmax-prior-A",
        "har-residual",
        "har-quantile",
        "short-quantile",
        "garch-calibrated",
        "network-refined-D",
        "network-refined-A",
    ]
    rows = [r for r in rows if r["id"] in selected]
    labels = {
        "quantum-prior-D": "Quantum D (14 angles)",
        "quantum-prior-A": "Quantum D+A",
        "softmax-prior-D": "Softmax D (9 weights)",
        "softmax-prior-A": "Softmax D+A",
        "har-residual": "HAR residual (full history)",
        "har-quantile": "HAR quantile (60 coefficients)",
        "short-quantile": "Short quantile (45 coefficients)",
        "garch-calibrated": "GARCH + RV calibration",
        "network-refined-D": "Regularized NN D (24 weights)",
        "network-refined-A": "Regularized NN D+A",
    }

    def color(id_):
        if id_.startswith("quantum"):
            return "#5c48a6"
        if id_.startswith("softmax"):
            return "#147e94"
        if id_.startswith("network"):
            return "#c16a2d"
        if id_.startswith("garch"):
            return "#a84157"
        return "#55855b"

    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 3, figsize=(16, 6), layout="constrained", sharey=True)
    for ax, key, title in zip(
        axes,
        ["log_loss", "rps_normalized", "extreme_brier"],
        ["Validation NLL ↓", "Normalized RPS ↓", "Extreme-bin Brier ↓"],
        strict=True,
    ):
        values = [r["validation"][key] for r in rows]
        ax.barh([labels[r["id"]] for r in rows], values, color=[color(r["id"]) for r in rows])
        ax.set_title(title)
        ax.set_xlim(0, max(values) * 1.2)
        for j, v in enumerate(values):
            ax.text(v, j, f" {v:.4f}", va="center", fontsize=8)
    axes[0].invert_yaxis()
    fig.suptitle(
        "Step 4 validation forecasts — information and capacity differ; no test scores", fontsize=14
    )
    fig.savefig(root / "classical-scorecard.png", dpi=170)
    plt.close(fig)

    fig, axes = plt.subplots(2, 2, figsize=(13, 10), layout="constrained")
    ax = axes[0, 0]
    for row in rows:
        id_ = row["id"]
        distances = [r["summary"]["distance_of_mean"] for r in audit if r["id"] == id_]
        ax.scatter(
            np.mean(distances),
            row["validation"]["log_loss"],
            c=color(id_),
            marker="*" if "A" in id_ else "o",
            s=100,
        )
        # Label a compact subset; the table contains every candidate.
        if id_ in (
            "har-quantile",
            "garch-calibrated",
            "network-refined-A",
            "quantum-prior-A",
            "softmax-prior-A",
        ):
            text = {
                "har-quantile": "HAR QR",
                "garch-calibrated": "GARCH calibrated",
                "network-refined-A": "NN A",
                "quantum-prior-A": "Quantum A",
                "softmax-prior-A": "Softmax A",
            }[id_]
            ax.annotate(
                text,
                (np.mean(distances), row["validation"]["log_loss"]),
                xytext=(5, 6),
                textcoords="offset points",
                fontsize=8,
            )
    ax.set_xscale("log")
    ax.margins(x=0.35, y=0.15)
    ax.set(
        title="Fresh streams 50000/60000: forecast / realism",
        xlabel="Distance of mean moments (log scale) ↓",
        ylabel="Validation NLL ↓",
    )
    ax = axes[0, 1]
    for row in rows:
        ax.plot(
            np.array(
                [0.01, 0.025, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.975, 0.99]
            ),
            row["common_quantile_scores"]["pinball_by_quantile"],
            color=color(row["id"]),
            alpha=0.7,
            lw=1,
            label=labels[row["id"]],
        )
    ax.set(
        title="Shared empirical-bin quantile scores",
        xlabel="Quantile",
        ylabel="Validation pinball loss ↓",
    )
    ax.legend(fontsize=6, ncol=2)
    ax = axes[1, 0]
    positions = np.arange(4)
    width = 0.19
    ax.bar(
        positions - width * 1.5,
        manifest["validation_moments"],
        width,
        label="Real validation",
        color="#999999",
    )
    for index, id_ in enumerate(("quantum-prior-A", "har-quantile", "network-refined-A")):
        group = [r["summary"]["mean_moments"] for r in audit if r["id"] == id_]
        if group:
            ax.bar(
                positions + width * (index - 0.5),
                np.mean(group, axis=0),
                width,
                label=labels[id_],
                color=color(id_),
            )
    ax.set(
        title="Generated moments: aggregate distance is incomplete",
        xticks=positions,
        xticklabels=["ACF 1", "ACF 7", "ACF 30", "SD Δlog RV"],
    )
    ax.legend(fontsize=8)
    ax = axes[1, 1]
    selection = read("network-ridge-selection.json")
    winners = selection["winners"]
    for row in winners:
        ax.scatter(
            row["ridge"] if row["ridge"] else 1e-5,
            row["validation_nll"],
            color="#c16a2d",
            marker="*" if row["ridge"] == selection["ridge"] else "o",
            s=120,
        )
        ax.annotate(
            f"α={row['ridge']:g}",
            (row["ridge"] if row["ridge"] else 1e-5, row["validation_nll"]),
            xytext=(4, 5),
            textcoords="offset points",
            fontsize=8,
        )
    ax.set_xscale("log")
    ax.margins(x=0.3, y=0.2)
    ax.set(
        title="NN: training restart, then validation regularization",
        xlabel="Ridge penalty (zero placed at 1e−5)",
        ylabel="Validation NLL ↓",
    )
    fig.suptitle(
        "Step 4 development diagnostics — fresh simulations, reused validation data", fontsize=14
    )
    fig.savefig(root / "classical-diagnostics.png", dpi=170)
    plt.close(fig)
    print(root / "classical-scorecard.png")
    print(root / "classical-diagnostics.png")


if __name__ == "__main__":
    main()
