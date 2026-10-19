#!/usr/bin/env python3
"""Plot the prespecified penalty sweep and validation-selected follow-up forecasts."""

import argparse
import json
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    root = args.run
    manifest = json.loads((root / "manifest.json").read_text())
    if manifest["status"] != "complete":
        raise ValueError("Finish the sweep before plotting")
    summary = json.loads((root / "summary.json").read_text())
    records = json.loads((root / "records.json").read_text())
    decision = json.loads((root / "decision.json").read_text())
    output = root / "figures"
    output.mkdir(exist_ok=True)
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.7), layout="constrained")
    for kind, label, color in [
        ("nested_memory", "Weekly/monthly", "#176287"),
        ("nested_short", "Yesterday control", "#a15721"),
    ]:
        rows = sorted([s for s in summary if s["kind"] == kind], key=lambda s: s["regularization"])
        for ax, metric in zip(axes, ("train_mse_rv", "validation_mse_rv"), strict=True):
            ax.plot(
                [s["regularization"] for s in rows],
                [s[metric] for s in rows],
                "o-",
                label=label,
                color=color,
            )
            for s in rows:
                if not s["eligible"]:
                    ax.scatter(s["regularization"], s[metric], marker="x", s=130, color="red")
            ax.set_xscale("symlog", linthresh=1e-4)
            ax.set_xlabel("Penalty alpha on the two added weights")
            ax.set_ylabel("RV MSE")
            ax.grid(alpha=0.2)
    paper = next(s for s in summary if s["kind"] == "paper")
    har = next(r for r in records if r["kind"] == "har_rv")
    for ax, split in zip(axes, ("train", "validation"), strict=True):
        ax.axhline(paper[f"{split}_mse_rv"], color="gray", linestyle="--", label="Paper")
        ax.axhline(har[f"{split}_mse_rv"], color="#497745", linestyle=":", label="Classical HAR RV")
        ax.ticklabel_format(axis="y", style="sci", scilimits=(0, 0))
    axes[0].set_title("Training MSE of the training-selected restart")
    axes[1].set_title("Validation MSE of that same restart")
    axes[0].legend(fontsize=9)
    fig.savefig(output / "regularization-comparison.png", dpi=180)
    plt.close(fig)
    if decision["status"] == "inconclusive":
        print(output)
        return
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), layout="constrained")
    chosen = [
        (paper["winner"], "Paper", "gray"),
        (decision["selections"]["nested_memory"]["winner"], "Selected weekly/monthly", "#176287"),
        (decision["selections"]["nested_short"]["winner"], "Selected yesterday control", "#a15721"),
        ("har_rv", "Classical HAR RV", "#497745"),
    ]
    for index, (name, label, color) in enumerate(chosen):
        with np.load(root / f"{name}.npz") as arrays:
            if index == 0:
                axes[0].plot(
                    arrays["validation_rows"],
                    arrays["validation_actual_rv"],
                    color="black",
                    alpha=0.7,
                    label="Observed",
                )
            axes[0].plot(
                arrays["validation_rows"],
                arrays["validation_predicted_rv"],
                color=color,
                label=label,
            )
            if "objective_history" in arrays.files:
                axes[1].plot(
                    np.minimum.accumulate(arrays["objective_history"]), color=color, label=label
                )
    axes[0].set_title("Exploratory validation forecasts after training-only restart selection")
    axes[0].set_ylabel("Author-standardized RV")
    axes[0].set_xlabel("Observation row position")
    axes[0].legend(fontsize=9)
    axes[1].set_title("Penalized training objective including initial check")
    axes[1].set_xlabel("Objective call")
    axes[1].set_ylabel("Normalized RV MSE plus penalty")
    axes[1].set_yscale("log")
    axes[1].legend(fontsize=9)
    fig.savefig(output / "validation-forecasts.png", dpi=180)
    plt.close(fig)
    print(output)


if __name__ == "__main__":
    main()
