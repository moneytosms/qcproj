#!/usr/bin/env python3
"""Export scorecards, validation trade-off and held-out calibration from a saved run."""

import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    manifest = json.loads((args.run / "manifest.json").read_text())
    if manifest["status"] != "complete":
        raise ValueError("Only plot a completed run")
    records = json.loads((args.run / "records.json").read_text())
    candidates = json.loads((args.run / "candidates.json").read_text())
    summary = json.loads((args.run / "summary.json").read_text())
    out = args.run / "figures"
    out.mkdir(exist_ok=True)
    plt.rcParams.update(
        {"figure.dpi": 150, "axes.spines.top": False, "axes.spines.right": False, "font.size": 10}
    )
    stamp = f"{manifest['data']['units']} | {len(manifest['config']['seeds'])} seed(s)"
    for panel, metric in [("point", "mse_rv"), ("distribution", "log_loss")]:
        rows = [r for r in summary if r["panel"] == panel]
        fig, axes = plt.subplots(1, 2, figsize=(13, 5), layout="constrained")
        names = [r["name"] for r in rows]
        for ax, name, title in [
            (axes[0], metric, "Held-out forecast"),
            (axes[1], "moment_distance", "Held-out generated realism"),
        ]:
            values = [r["metrics"][name]["mean"] for r in rows]
            plot_values = [np.nan if v is None else v for v in values]
            ax.bar(np.arange(len(rows)), plot_values, color="#306c91")
            for index, row in enumerate(rows):
                spread = row["metrics"][name]["std"]
                if spread is not None and values[index] is not None:
                    ax.errorbar(
                        index, values[index], yerr=spread, fmt="none", ecolor="black", capsize=3
                    )
            ax.set_xticks(np.arange(len(rows)), names, rotation=45, ha="right")
            ax.set_title(title)
            ax.set_ylabel(f"{name} (lower is better)")
        fig.suptitle(
            f"{panel.capitalize()} scorecard · {stamp}\n"
            "Software smoke runs do not establish scientific performance"
        )
        fig.savefig(out / f"{panel}-scorecard.png")
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 6), layout="constrained")
    for family in ("quantum", "softmax", "tiny_nn"):
        rows = [r for r in candidates if r["family"] == family]
        ax.scatter(
            [r["validation"]["log_loss"] for r in rows],
            [r["validation"]["moment_distance"] for r in rows],
            label=family,
            s=50,
        )
        for row in rows:
            label = f"λ={row['lambda']}"
            if row["layers"] is not None:
                label += f", L={row['layers']}"
            ax.annotate(
                label,
                (row["validation"]["log_loss"], row["validation"]["moment_distance"]),
                xytext=(-4, 6),
                ha="right",
                textcoords="offset points",
                fontsize=8,
            )
    ax.set(
        xlabel="Validation log loss (lower is better)",
        ylabel="Validation moment distance (lower is better)",
        title=f"Candidate trade-off · validation only\n{stamp}",
    )
    ax.legend()
    fig.savefig(out / "validation-tradeoff.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 6), layout="constrained")
    for name in ("quantum_selected", "softmax_selected", "tiny_nn_selected"):
        rows = [r for r in records if r["name"] == name]
        means, frequencies, counts = [], [], []
        for index in range(10):
            cells = [r["forecast"]["extreme_calibration"][index] for r in rows]
            count = sum(c["count"] for c in cells)
            if count:
                means.append(sum(c["count"] * (c["mean_probability"] or 0) for c in cells) / count)
                frequencies.append(
                    sum(c["count"] * (c["observed_frequency"] or 0) for c in cells) / count
                )
                counts.append(count)
        ax.scatter(means, frequencies, s=np.minimum(100, 12 + np.sqrt(counts) * 5), label=name)
    ax.plot([0, 1], [0, 1], "--", color="gray", linewidth=1)
    ax.set(
        xlabel="Mean predicted extreme-bin probability",
        ylabel="Observed extreme-bin frequency",
        xlim=(-0.02, 1.02),
        ylim=(-0.02, 1.02),
        title=f"Held-out calibration · {stamp}\nMarker size reflects count; repeated days across seeds",
    )
    ax.legend()
    fig.savefig(out / "extreme-calibration.png")
    plt.close(fig)

    with (out / "scorecard.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["model", "panel", "seeds", "metric", "mean", "std_across_seeds"])
        for row in summary:
            for metric, values in row["metrics"].items():
                writer.writerow(
                    [row["name"], row["panel"], row["seeds"], metric, values["mean"], values["std"]]
                )
    print(f"Saved figures and scorecard to {out}")


if __name__ == "__main__":
    main()
