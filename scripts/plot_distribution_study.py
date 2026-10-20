#!/usr/bin/env python3
"""Plot the sequential D/A development results and fresh-stream diagnostics."""

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from qcvol.data import load_author_data, prepare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--author-data", type=Path, default=Path("data/raw/author"))
    args = parser.parse_args()
    root = args.run
    read = lambda name: json.loads((root / name).read_text())
    rows = read("records.json")
    decision = read("decision.json")
    audit = read("audit.json")
    manifest = read("manifest.json")
    by_id = {r["id"]: r for r in rows}
    data = prepare(load_author_data(args.author_data))
    colors = {"quantum": "#5a49a7", "softmax": "#147d92", "network": "#c56a2d"}
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(2, 2, figsize=(13, 9), layout="constrained")
    ax = axes[0, 0]
    winners = [by_id[i] for i in decision["quantum"]["depth_winners"]]
    ax.plot(
        [r["depth"] for r in winners],
        [r["fit"]["objective"] for r in winners],
        "o-",
        label="Training NLL",
        color=colors["quantum"],
    )
    ax.plot(
        [r["depth"] for r in winners],
        [r["validation"]["log_loss"] for r in winners],
        "s--",
        label="Validation NLL",
        color="#d48d18",
    )
    ax.set(
        title="D: depth after training-only restart selection",
        xlabel="Quantum layers",
        ylabel="NLL (lower is better)",
        xticks=[1, 2, 3, 4],
    )
    ax.legend()
    ax = axes[0, 1]
    for family, d in decision.items():
        for j, id_ in enumerate(d["lambda_winners"]):
            row = by_id[id_]
            runs = [v for v in audit if v["id"] == id_]
            x = np.mean([v["distance_of_mean"] for v in runs])
            y = row["validation"]["log_loss"]
            selected = id_ == d["selected_id"]
            ax.scatter(
                x,
                y,
                color=colors[family],
                marker="*" if selected else "o",
                s=160 if selected else 35,
                label=family if j == 0 else None,
            )
            if selected or row["lambda"] == 0:
                ax.annotate(
                    f"λ={row['lambda']:g}",
                    (x, y),
                    xytext=(5, 6),
                    textcoords="offset points",
                    fontsize=8,
                )
    ax.margins(x=0.12, y=0.08)
    ax.set(
        title="Fresh streams: trade-off (stars = selected)",
        xlabel="Distance of mean moments (two-stream mean)",
        ylabel="Validation NLL",
    )
    ax.legend()
    ax = axes[1, 0]
    reference = manifest["validation_moments"]
    positions = np.arange(4)
    ax.bar(positions - 0.25, reference, width=0.25, color="#999999", label="Real validation")
    for k, kind in enumerate(("forecast_id", "selected_id")):
        id_ = decision["quantum"][kind]
        vectors = np.array([v["mean_moments"] for v in audit if v["id"] == id_])
        ax.bar(
            positions + k * 0.25,
            vectors.mean(axis=0),
            width=0.25,
            label="Quantum D" if k == 0 else "Quantum D+A",
            color="#9a8cc6" if k == 0 else colors["quantum"],
        )
    ax.set(
        title="Quantum histories: measured moments",
        xticks=positions,
        xticklabels=["ACF 1", "ACF 7", "ACF 30", "SD Δlog RV"],
        ylabel="Moment value",
    )
    ax.legend()
    ax = axes[1, 1]
    t = np.arange(len(data.y[data.validation]))
    ax.plot(t, data.y[data.validation], lw=1, color="#aaaaaa", label="Observed log RV")
    centers = np.array([pool.mean() for pool in data.bins.pools])
    for family in ("quantum", "softmax"):
        id_ = decision[family]["forecast_id"]
        with np.load(root / f"{id_}.npz") as saved:
            expectation = saved["validation_probabilities"] @ centers
        ax.plot(t, expectation, lw=1.1, label=f"{family} D bin-mean forecast", color=colors[family])
    ax.set(
        title="Teacher-forced probability forecasts, shown as bin means",
        xlabel="Validation target index",
        ylabel="Log RV",
    )
    ax.legend(fontsize=8)
    fig.suptitle("Step 3 development study — validation reused; test unscored", fontsize=15)
    fig.savefig(root / "distribution-study.png", dpi=170)
    plt.close(fig)

    ids = ["frequency", "short-ar", "har-reference"]
    ids += [decision[f]["forecast_id"] for f in colors]
    ids += [
        decision[f]["selected_id"]
        for f in colors
        if decision[f]["selected_id"] != decision[f]["forecast_id"]
    ]
    labels = [
        i.replace("-d", " / depth ").replace("-D-s", " / D start ").replace("-A-l", " / A λ ")
        for i in ids
    ]
    fig, axes = plt.subplots(1, 3, figsize=(16, 6), layout="constrained", sharey=True)
    for ax, key, title in zip(
        axes,
        ["log_loss", "rps_normalized", "extreme_brier"],
        ["Validation NLL", "Normalized RPS", "Extreme-bin Brier"],
        strict=True,
    ):
        values = [by_id[i]["validation"][key] for i in ids]
        ax.barh(labels, values, color=[colors.get(by_id[i]["family"], "#888888") for i in ids])
        ax.set_title(title + " ↓")
        for y, v in enumerate(values):
            ax.text(v, y, f" {v:.4f}", va="center", fontsize=8)
        ax.set_xlim(0, max(values) * 1.22)
    axes[0].invert_yaxis()
    fig.suptitle(
        "Probability scorecard — HAR has additional weekly/monthly information", fontsize=14
    )
    fig.savefig(root / "distribution-scorecard.png", dpi=170)
    plt.close(fig)
    print(root / "distribution-study.png")
    print(root / "distribution-scorecard.png")


if __name__ == "__main__":
    main()
