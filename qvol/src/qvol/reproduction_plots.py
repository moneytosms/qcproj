"""Measured comparison figures; paper panel/figure numbers are identified in titles."""

import csv
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .multifractal import analyze_batch
from .reproduction import write_json

COLORS = {"empirical": "#222222", "author": "#8b6552", "rebuild_seed0": "#236ca3"}
LABELS = {
    "empirical": "Empirical Bitcoin",
    "author": "Author's published series",
    "rebuild_seed0": "Rebuild, generation seed 0",
}
FEATURES = {
    "returns": "Return",
    "irv": "Log-RV increment",
    "iar": "Log-|return| increment",
}


def export(result):
    out = result["output"] / "figures"
    out.mkdir(exist_ok=False)
    plt.rcParams.update(
        {"axes.spines.right": False, "axes.spines.top": False, "font.size": 10}
    )
    records = result["analysis"]
    selected = [
        name for name in ("empirical", "author", "rebuild_seed0") if name in records
    ]
    sources = {name: (v, r) for name, v, r, _ in result["sources"]}
    artifacts = []

    def save(fig, name):
        fig.savefig(out / name, dpi=170)
        plt.close(fig)
        artifacts.append(name)

    arrays = np.load(result["output"] / "fit-arrays.npz")
    fig, axes = plt.subplots(2, 1, figsize=(12, 7), layout="constrained")
    for row in result["fit"]["restarts"]:
        axes[0].semilogy(
            np.arange(1, len(row["objective_history"]) + 1),
            np.minimum.accumulate(row["objective_history"]),
            alpha=0.65,
        )
    axes[0].set(
        xlabel="Objective evaluations",
        ylabel="Best MSE so far",
        title="Figure 3 comparison: ten full-sample COBYLA starts",
    )
    axes[1].plot(
        arrays["observation_ids"],
        arrays["actual"],
        color="black",
        lw=0.8,
        label="Observed RV",
    )
    axes[1].plot(
        arrays["observation_ids"],
        arrays["predicted"],
        color="#ba3434",
        lw=0.8,
        label="One-step P0",
    )
    axes[1].set(
        xlabel="Published observation ID",
        ylabel="Author-standardized RV",
        title="Figure 4 comparison: observed input and fitted one-step output",
    )
    axes[1].legend()
    save(fig, "fit-and-convergence.png")

    fig, axes = plt.subplots(2, 1, figsize=(12, 6), layout="constrained")
    for name in selected:
        v, r = sources[name]
        limit = min(25000, len(v))
        axes[0].plot(
            np.arange(limit),
            r[:limit],
            color=COLORS[name],
            lw=0.35,
            alpha=0.8,
            label=LABELS[name],
        )
        axes[1].plot(
            np.arange(limit), v[:limit], color=COLORS[name], lw=0.35, alpha=0.8
        )
    axes[0].set(
        title="Figures 5–6 comparison: first 25,000 generated observations",
        ylabel="Standardized return",
    )
    axes[0].legend(fontsize=9)
    axes[1].set(
        xlabel="Series observation (empirical record ends at 913)",
        ylabel="Standardized RV",
    )
    save(fig, "generated-series.png")

    fig, ax = plt.subplots(figsize=(8, 5), layout="constrained")
    v, r = sources["empirical"]
    grid = np.unique(np.geomspace(5, 182, 35).astype(int))
    qs = np.linspace(-5, 5, 101)
    diagnostic = analyze_batch(r, q=qs, scales=grid)
    for j in range(0, len(qs), 5):
        ax.loglog(
            grid,
            np.exp(diagnostic["log_f"][0, :, j]),
            lw=0.8,
            color=plt.cm.viridis(j / (len(qs) - 1)),
        )
    ax.axvline(
        result["scales"][0], color="gray", linestyle="--", label="Fit begins at s=20"
    )
    ax.set(
        xlabel="Scale s",
        ylabel="Fq(s)",
        title="Figure 7 comparison: empirical return fluctuations",
    )
    ax.legend()
    save(fig, "scaling-functions.png")

    fig, axes = plt.subplots(3, 2, figsize=(13, 10), layout="constrained", sharex=True)
    for row, feature in enumerate(FEATURES):
        for col, name in enumerate(["author", "rebuild_seed0"]):
            if name not in records:
                continue
            roll = records[name]["series"][feature]["rolling"]
            ax = axes[row, col]
            ax.plot(
                roll["starts"],
                roll["h2"],
                lw=0.8,
                label="Original windows",
                color=COLORS[name],
            )
            ax.plot(
                roll["starts"],
                roll["shuffled_mean"],
                lw=0.8,
                label="20 shuffles/window",
                color="#737373",
            )
            ax.axhline(0.5, ls=":", color="gray", lw=0.7)
            ax.set(
                title=f"{LABELS[name]}: {FEATURES[feature]}",
                ylabel="h(2)",
                xlabel="Window start",
            )
            ax.legend(fontsize=8)
    fig.suptitle(
        "Figures 8, 18–20 comparison: all overlapping 913-day windows, step 365\n"
        "Overlapping windows are descriptive, not independent replicates"
    )
    save(fig, "rolling-h2.png")

    fig, axes = plt.subplots(3, 3, figsize=(13, 11), layout="constrained")
    for row, feature in enumerate(FEATURES):
        for name in selected:
            spec = records[name]["series"][feature]["spectrum"]
            q = spec["q"]
            for axis, y in [(axes[row, 0], spec["h"]), (axes[row, 2], spec["tau"])]:
                axis.plot(q, y[0], lw=1, label=LABELS[name], color=COLORS[name])
                axis.plot(
                    q, np.mean(y[1:], axis=0), ls="--", lw=0.8, color=COLORS[name]
                )
            axes[row, 1].plot(
                spec["alpha"][0],
                spec["f_alpha"][0],
                lw=1,
                color=COLORS[name],
                label=LABELS[name],
            )
            axes[row, 1].plot(
                np.mean(spec["alpha"][1:], axis=0),
                np.mean(spec["f_alpha"][1:], axis=0),
                ls="--",
                lw=0.8,
                color=COLORS[name],
            )
        for col, (x, y) in enumerate(
            [("q", "h(q)"), ("alpha", "f(alpha)"), ("q", "tau(q)")]
        ):
            axes[row, col].set(xlabel=x, ylabel=y, title=FEATURES[feature])
    axes[0, 0].legend(fontsize=8)
    fig.suptitle(
        "Figures 9–11, 15–17, 21–26: preselected first-window spectra\n"
        "Solid: original; dashed: mean of 20 shuffled controls; q step .02"
    )
    save(fig, "multifractal-spectra.png")

    controls = result["gaussian_controls"]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), layout="constrained")
    for ax, key, xlabel, ylabel in [
        (axes[0], "h", "q", "h(q)"),
        (axes[2], "tau", "q", "tau(q)"),
    ]:
        values = controls[key]
        mu, sd = values.mean(axis=0), values.std(axis=0, ddof=1)
        ax.plot(controls["q"], mu, color="#236ca3")
        ax.fill_between(controls["q"], mu - sd, mu + sd, alpha=0.2)
        ax.set(xlabel=xlabel, ylabel=ylabel)
    axes[1].plot(
        controls["alpha"].mean(axis=0),
        controls["f_alpha"].mean(axis=0),
        color="#236ca3",
    )
    axes[1].set(xlabel="alpha", ylabel="f(alpha)")
    fig.suptitle(
        f"Figures 12–14 comparison: {len(controls['h'])} Gaussian controls, N={result['config']['window']}\n"
        "Bands show one sample standard deviation across controls"
    )
    save(fig, "gaussian-finite-size.png")

    fig, ax = plt.subplots(figsize=(9, 4), layout="constrained")
    from .metrics import acf

    for name in selected:
        v, _ = sources[name]
        ax.plot(
            np.arange(1, 61),
            [acf(np.log(v), lag) for lag in range(1, 61)],
            label=LABELS[name],
            color=COLORS[name],
        )
    ax.set(
        xlabel="Lag (days)",
        ylabel="Correlation of log RV",
        title="Additional audit: volatility memory",
    )
    ax.axhline(0, color="gray", lw=0.7)
    ax.legend()
    save(fig, "memory-comparison.png")

    with (result["output"] / "scorecard.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "source",
                "feature",
                "window_count",
                "mean_h2",
                "shuffled_mean_h2",
                "std_across_overlapping_windows",
                "pearson_kurtosis",
            ]
        )
        for name, record in records.items():
            for feature, values in record["series"].items():
                writer.writerow(
                    [
                        name,
                        feature,
                        len(values["rolling"]["starts"]),
                        values["h2_mean"],
                        values["shuffled_h2_mean"],
                        values["h2_std_across_overlapping_windows"],
                        record["statistics"]["pearson_kurtosis"][feature],
                    ]
                )
    manifest = json.loads((result["output"] / "manifest.json").read_text())
    manifest["figures"] = artifacts
    manifest["status"] = "complete"
    write_json(result["output"] / "manifest.json", manifest)
    print(f"Saved {len(artifacts)} figures and scorecard.csv", flush=True)
