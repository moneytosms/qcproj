#!/usr/bin/env python3
"""Export validation ablations and, when available, sealed benchmark comparisons."""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from qcvol.calendar_study import read

COLORS = {
    "linear": "#718096",
    "quantum": "#6a50a3",
    "quantum-shared": "#a35d98",
    "tanh": "#bf6d30",
    "sine": "#188298",
}
LABELS = {
    "linear": "Calendar linear",
    "quantum": "Quantum readout",
    "quantum-shared": "Quantum + direct day",
    "tanh": "Tanh control",
    "sine": "Sine control",
}


def development(out):
    records, selected = read(out / "development.json"), read(out / "selection.json")
    fig, axes = plt.subplots(2, 2, figsize=(13, 9), constrained_layout=True)
    linear = list(records["linear"].values())
    halves = sorted({r["half_life"] for r in linear})
    ax = axes[0, 0]
    for cal, color in [(False, "#9a9a9a"), (True, "#307754")]:
        scores = [
            min(
                r["validation"]["pooled"]["log_loss"]
                for r in linear
                if r["calendar"] == cal and r["half_life"] == half
            )
            for half in halves
        ]
        ax.plot(
            np.arange(len(halves)),
            scores,
            "o-",
            color=color,
            label="With weekday" if cal else "Without weekday",
        )
    ax.set(
        xticks=np.arange(len(halves)),
        xticklabels=[str(h) if h else "Uniform" for h in halves],
        xlabel="Training half-life in days; best ridge per setting",
        ylabel="Validation NLL ↓",
        title="Calendar / recency ablation",
    )
    ax.legend()
    ax = axes[0, 1]
    selected_rows = {}
    for i, (kind, choice) in enumerate(selected["choices"].items()):
        group = [
            r
            for r in records["nonlinear"].values()
            if r["kind"] == kind
            and r["depth"] == choice["depth"]
            and r["feature_ridge"] == choice["feature_ridge"]
        ]
        selected_rows[kind] = group
        values = [r["validation"]["pooled"]["log_loss"] for r in group]
        ax.errorbar(
            np.mean(values),
            i,
            xerr=np.std(values, ddof=1) if len(values) > 1 else 0,
            fmt="o",
            color=COLORS[kind],
            capsize=3,
        )
    ax.axvline(
        selected["policy"]["validation"]["pooled"]["log_loss"],
        color=COLORS["linear"],
        ls="--",
        label="Selected linear",
    )
    ax.set(
        yticks=range(len(selected_rows)),
        yticklabels=[LABELS[k] for k in selected_rows],
        xlabel="Validation NLL ↓; mean ± development-seed SD",
        title="Selected nonlinear settings",
    )
    ax.legend()
    ax = axes[1, 0]
    for kind in ("quantum", "quantum-shared"):
        for penalty, style in [(0.001, "-"), (0.01, "--")]:
            depths = sorted(
                {r["depth"] for r in records["nonlinear"].values() if r["kind"] == kind}
            )
            means = [
                np.mean(
                    [
                        r["validation"]["pooled"]["log_loss"]
                        for r in records["nonlinear"].values()
                        if r["kind"] == kind
                        and r["depth"] == depth
                        and r["feature_ridge"] == penalty
                    ]
                )
                for depth in depths
            ]
            ax.plot(
                depths,
                means,
                "o" + style,
                color=COLORS[kind],
                label=f"{LABELS[kind]}, ridge {penalty}",
            )
    ax.set(
        xlabel="Circuit layers",
        ylabel="Validation NLL ↓",
        title="Direct-day routing at matched depth / penalty",
        xticks=depths,
    )
    ax.legend(fontsize=8)
    ax = axes[1, 1]
    years = sorted(selected["policy"]["validation"]["years"])
    for kind, group in {"linear": [selected["policy"]], **selected_rows}.items():
        vals = [
            np.mean([r["validation"]["years"][year]["log_loss"] for r in group]) for year in years
        ]
        ax.plot(years, vals, "o-", color=COLORS[kind], label=LABELS[kind])
    ax.set(ylabel="Validation NLL ↓", title="Year-to-year stability; same selected settings")
    ax.legend(fontsize=8)
    fig.suptitle(
        "Development only: classical controls receive the same calendar and recency policy"
    )
    fig.savefig(out / "validation-ablations.png", dpi=170)
    plt.close(fig)


def benchmark(out):
    destination = out / "evaluation"
    result = read(destination / "summary.json")
    rows = sorted(result["summary"].items(), key=lambda item: item[1]["log_loss"]["mean"])
    fig, axes = plt.subplots(1, 3, figsize=(16, 6), constrained_layout=True)
    for ax, key, title in zip(
        axes,
        ("log_loss", "test_moment_distance", "coverage_90"),
        ("Benchmark NLL ↓", "Moment distance ↓", "Nominal 90% interval coverage"),
    ):
        for i, (name, row) in enumerate(rows):
            value = row[key]
            ax.barh(
                i,
                value["mean"],
                xerr=value["sd"] or 0,
                color=COLORS.get(name, "#50805e"),
                alpha=0.9,
            )
        ax.set(
            yticks=np.arange(len(rows)),
            yticklabels=[LABELS.get(k, k) for k, _ in rows],
            title=title,
        )
        ax.invert_yaxis()
        if key == "coverage_90":
            ax.axvline(0.9, ls="--", color="#a54444")
    fig.suptitle("Exposed 2025–2026 benchmark; mean ± seed SD; one historical market")
    fig.savefig(destination / "benchmark-scorecard.png", dpi=170)
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), constrained_layout=True)
    ax = axes[0]
    ax.plot(range(7), result["test_weekday_means"], "ko-", label="Observed benchmark")
    for kind, color in COLORS.items():
        ax.plot(
            range(7),
            result["summary"][kind]["weekday_means"],
            "o-",
            color=color,
            label=LABELS[kind],
        )
    ax.set(
        xticks=range(7),
        xticklabels=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        ylabel="Mean log RV",
        title="Weekday structure in unconditional simulations",
    )
    ax.legend(fontsize=8)
    ax = axes[1]
    intervals = [
        r
        for r in result["bootstrap"]
        if r["block"] == 30 and r["right"] in ("linear", "tanh", "sine", "legacy-softmax-har")
    ]
    for i, r in enumerate(intervals):
        ax.errorbar(
            r["mean"],
            i,
            xerr=[[r["mean"] - r["lower"]], [r["upper"] - r["mean"]]],
            fmt="o",
            color=COLORS.get(r["left"], "#777"),
            capsize=3,
        )
    ax.axvline(0, color="#777", lw=1)
    ax.set(
        yticks=range(len(intervals)),
        yticklabels=[
            f"{LABELS.get(r['left'], r['left'])} − {LABELS.get(r['right'], r['right'])}"
            for r in intervals
        ],
        xlabel="Paired NLL difference; negative favors left",
        title="30-day date-block bootstrap, descriptive 95%",
    )
    fig.savefig(destination / "calendar-and-uncertainty.png", dpi=170)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    development(args.output)
    if (args.output / "evaluation/summary.json").exists():
        benchmark(args.output)
    print(f"Exported comparison figures to {args.output}")


if __name__ == "__main__":
    main()
