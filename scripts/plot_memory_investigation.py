#!/usr/bin/env python3
"""Plot saved training/validation diagnostics without reading the original dataset."""

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
        raise ValueError("Finish the investigation before plotting")
    summary = json.loads((root / "summary.json").read_text())
    records = json.loads((root / "records.json").read_text())
    output = root / "figures"
    output.mkdir(exist_ok=True)
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8), layout="constrained")
    for kind, label, color in [
        ("memory_b", "Full HAR", "#176287"),
        ("memory_short", "Short memory", "#a15721"),
    ]:
        for initialization, linestyle in [("legacy", "--"), ("rv_prior", "-")]:
            rows = sorted(
                [
                    r
                    for r in summary
                    if r["phase"] == "budget"
                    and r["layers"] == 3
                    and r["kind"] == kind
                    and r["initialization"] == initialization
                ],
                key=lambda r: r["budget"],
            )
            for ax, metric in zip(
                axes, ("train_selected_mse_rv", "validation_mse_rv"), strict=True
            ):
                ax.plot(
                    [r["budget"] for r in rows],
                    [r[metric] for r in rows],
                    marker="o",
                    color=color,
                    linestyle=linestyle,
                    label=f"{label}  {initialization}",
                )
                ax.set_xscale("log")
                ax.set_yscale("log")
                ax.set_xlabel("Objective evaluation ceiling per start")
                ax.set_ylabel("MSE in author RV units")
                ax.grid(alpha=0.2)
    axes[0].set_title("Training loss of the training-selected restart")
    axes[1].set_title("Validation loss of that same restart")
    axes[0].legend(fontsize=9)
    fig.suptitle("Three layers and three independent starts per setting")
    fig.savefig(output / "budget-and-initialization.png", dpi=180)
    plt.close(fig)
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), layout="constrained")
    for kind, label, color in [
        ("paper", "Paper", "#6d6d6d"),
        ("memory_b", "Full HAR", "#176287"),
        ("memory_short", "Short memory", "#a15721"),
    ]:
        choices = [r for r in summary if r["kind"] == kind]
        choice = min(choices, key=lambda r: r["validation_mse_rv"])
        record = next(r for r in records if r["id"] == choice["train_selected_id"])
        arrays = np.load(root / f"{record['id']}.npz")
        if kind == "paper":
            axes[0].plot(
                arrays["validation_target_rows"],
                arrays["validation_actual_rv"],
                color="black",
                alpha=0.7,
                label="Observed RV",
            )
        axes[0].plot(
            arrays["validation_target_rows"],
            arrays["validation_predicted_rv"],
            color=color,
            label=f"{label}  L{record['layers']}  {record['initialization']}  budget {record['budget']}"
            + ("  (not converged)" if not record["fit"]["success"] else ""),
        )
        axes[1].plot(np.minimum.accumulate(arrays["objective_history"]), color=color, label=label)
    axes[0].set_title(
        "Exploratory validation-selected settings after training-only restart selection"
    )
    axes[0].set_xlabel("Published observation row position")
    axes[0].set_ylabel("Standardized RV")
    axes[0].legend(fontsize=9)
    axes[1].set_title("Best training objective so far for those fits")
    axes[1].set_xlabel("Objective call including initial check")
    axes[1].set_ylabel("Normalized training RV MSE")
    axes[1].set_yscale("log")
    axes[1].legend()
    fig.savefig(output / "validation-curves.png", dpi=180)
    plt.close(fig)
    print(output)


if __name__ == "__main__":
    main()
