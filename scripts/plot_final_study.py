#!/usr/bin/env python3
"""Export fixed-seed final forecasts, ablations, calibration, uncertainty and diagnostics."""

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from qcvol.data import load_author_data, prepare
from qcvol.final_study import read_json

LABELS = {
    "quantum-D": "Quantum D",
    "quantum-A": "Quantum A",
    "softmax-D": "Softmax D",
    "softmax-A": "Softmax A",
    "network-D": "Regularized NN D",
    "network-A": "Regularized NN A",
    "frequency": "Frequency",
    "short-ar": "Short AR",
    "har-residual": "HAR residual",
    "har-quantile": "HAR quantile",
    "short-quantile": "Short quantile",
    "garch-calibrated": "GARCH calibrated",
}


def color(id_):
    if id_.startswith("quantum"):
        return "#5b47a5"
    if id_.startswith("softmax"):
        return "#147b91"
    if id_.startswith("network"):
        return "#c56c2c"
    if id_.startswith("garch"):
        return "#ad4358"
    if id_.startswith("har"):
        return "#4f845a"
    return "#888888"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--author-data", type=Path, required=True)
    parser.add_argument("--evaluation", default="evaluation")
    args = parser.parse_args()
    root = args.run / args.evaluation
    summary = read_json(root / "summary.json")
    status = read_json(root / "status.json")
    assert status["status"] == "complete"
    rows = summary["models"]
    by_id = {r["id"]: r for r in rows}
    paths = read_json(root / "paths.json")
    records = read_json(root / "records.json")
    data = prepare(load_author_data(args.author_data))
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    rows = sorted(rows, key=lambda r: r["log_loss"]["mean"])
    labels = [LABELS[r["id"]] for r in rows]
    fig, axes = plt.subplots(1, 3, figsize=(16, 7), layout="constrained", sharey=True)
    for ax, key, title in zip(
        axes,
        ["log_loss", "rps_normalized", "extreme_brier"],
        ["Test NLL ↓", "Normalized RPS ↓", "Extreme-bin Brier ↓"],
        strict=True,
    ):
        means = [r[key]["mean"] for r in rows]
        sds = [r[key]["sd"] or 0 for r in rows]
        ax.barh(
            labels,
            means,
            xerr=sds,
            color=[color(r["id"]) for r in rows],
            error_kw={"capsize": 2, "lw": 1},
        )
        ax.set_title(title)
        ax.set_xlim(0, max(np.array(means) + np.array(sds)) * 1.2)
        for j, v in enumerate(means):
            ax.text(v + sds[j], j, f" {v:.4f}", va="center", fontsize=8)
    axes[0].invert_yaxis()
    fig.suptitle(
        f"Frozen {status['seeds']}-seed study — mean ± training-seed SD; information/capacity differ",
        fontsize=14,
    )
    fig.savefig(root / "final-scorecard.png", dpi=170)
    plt.close(fig)

    fig, axes = plt.subplots(2, 2, figsize=(14, 11), layout="constrained")
    ax = axes[0, 0]
    for j, family in enumerate(("quantum", "softmax", "network")):
        for seed in sorted({r["seed"] for r in records}):
            values = [
                next(
                    r["scores"]["log_loss"]
                    for r in records
                    if r["id"] == f"{family}-{stage}" and r["seed"] == seed
                )
                for stage in ("D", "A")
            ]
            ax.plot(
                [j - 0.13, j + 0.13],
                values,
                "o-",
                color=color(family),
                alpha=0.35,
                markersize=3,
                lw=0.8,
            )
    ax.set(
        xticks=[0, 1, 2],
        xticklabels=["Quantum D→A", "Softmax D→A", "NN D→A"],
        ylabel="Test NLL ↓",
        title="Paired loss change across training seeds",
    )
    ax = axes[0, 1]
    intervals = summary["bootstrap_nll"]
    contrasts = []
    for r in intervals:
        name = f"{LABELS[r['left']]} − {LABELS[r['right']]}"
        if name not in contrasts:
            contrasts.append(name)
    for j, name in enumerate(contrasts):
        for offset, block, shade in [(-0.12, 7, "#597fa4"), (0.12, 30, "#bb773d")]:
            r = next(
                r
                for r in intervals
                if f"{LABELS[r['left']]} − {LABELS[r['right']]}" == name and r["block"] == block
            )
            ax.errorbar(
                r["mean_difference"],
                j + offset,
                xerr=[[r["mean_difference"] - r["lower"]], [r["upper"] - r["mean_difference"]]],
                fmt="o",
                color=shade,
                markersize=4,
                capsize=2,
                label=f"{block}-day blocks" if j == 0 else None,
            )
    ax.axvline(0, color="#888888", lw=1)
    ax.set(
        yticks=np.arange(len(contrasts)),
        yticklabels=contrasts,
        xlabel="Paired NLL difference; negative favors left",
        title="Date-block bootstrap: descriptive 95% intervals",
    )
    ax.invert_yaxis()
    ax.legend(fontsize=8)
    ax = axes[1, 0]
    for r in rows:
        x = r["distance_of_mean"]["mean"]
        y = r["log_loss"]["mean"]
        ax.scatter(x, y, color=color(r["id"]), marker="*" if r["id"].endswith("-A") else "o", s=100)
        if r["id"] in ("quantum-A", "network-A", "har-quantile", "softmax-A", "garch-calibrated"):
            offset = (4, -14) if r["id"] == "softmax-A" else (4, 7)
            ax.annotate(
                LABELS[r["id"]], (x, y), xytext=offset, textcoords="offset points", fontsize=8
            )
    ax.set_xscale("log")
    ax.margins(x=0.3, y=0.15)
    ax.set(
        xlabel="Mean moment distance (log scale) ↓",
        ylabel="Test NLL ↓",
        title="Forecast / recursive realism trade-off",
    )
    ax = axes[1, 1]
    positions = np.arange(4)
    width = 0.21
    ax.bar(
        positions - 1.5 * width,
        summary["reference"]["test_moments"],
        width,
        color="#999999",
        label="Real test",
    )
    for j, id_ in enumerate(("quantum-A", "network-A", "har-quantile")):
        r = by_id[id_]
        keys = ["acf_1", "acf_7", "acf_30", "vol_of_vol"]
        ax.bar(
            positions + (j - 0.5) * width,
            [r[k]["mean"] for k in keys],
            width,
            yerr=[r[k]["sd"] or 0 for k in keys],
            color=color(id_),
            label=LABELS[id_],
            capsize=2,
        )
    ax.set(
        xticks=positions,
        xticklabels=["ACF 1", "ACF 7", "ACF 30", "SD Δlog RV"],
        title="Moment gaps remain visible",
    )
    ax.legend(fontsize=8)
    fig.suptitle(
        "Final ablations — training-seed variability and test-date uncertainty are separate",
        fontsize=14,
    )
    fig.savefig(root / "final-ablations.png", dpi=170)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(13, 7), layout="constrained")
    ax = axes[0]
    positions = np.arange(len(rows))
    ax.errorbar(
        [r["coverage_90"]["mean"] for r in rows],
        positions,
        xerr=[r["coverage_90"]["sd"] or 0 for r in rows],
        fmt="o",
        color="#666666",
        capsize=2,
        label="Common-bin law",
    )
    for j, r in enumerate(rows):
        if "native_quantile_scores" in r:
            ax.scatter(
                r["native_quantile_scores"]["coverage_90"]["mean"],
                j,
                marker="D",
                color=color(r["id"]),
                label="Native law"
                if j == next(i for i, v in enumerate(rows) if "native_quantile_scores" in v)
                else None,
            )
    ax.axvline(0.9, color="#b95757", ls="--")
    ax.set(
        yticks=positions,
        yticklabels=labels,
        xlabel="Observed coverage of nominal 90% interval",
        title="Coverage: mean ± seed SD",
    )
    ax.invert_yaxis()
    ax.legend(fontsize=8)
    ax = axes[1]
    ax.plot([0, 1], [0, 1], "--", color="#999999", lw=1)
    seed = min(r["seed"] for r in records)
    for id_ in ("quantum-A", "softmax-A", "network-A", "har-quantile"):
        r = next(r for r in records if r["id"] == id_ and r["seed"] == seed)
        bins = [b for b in r["scores"]["extreme_calibration"] if b["count"]]
        ax.scatter(
            [b["mean_probability"] for b in bins],
            [b["observed_frequency"] for b in bins],
            s=[15 + np.sqrt(b["count"]) * 5 for b in bins],
            color=color(id_),
            label=LABELS[id_],
        )
    ax.set(
        xlabel="Predicted extreme-bin probability",
        ylabel="Observed extreme frequency",
        title=f"Fixed seed {seed}: sparse-bin calibration",
    )
    ax.legend(fontsize=8)
    fig.suptitle("Calibration on one historical test period — no coverage guarantee", fontsize=14)
    fig.savefig(root / "final-calibration.png", dpi=170)
    plt.close(fig)

    fig, axes = plt.subplots(2, 2, figsize=(13, 9), layout="constrained")
    subset = [
        "quantum-D",
        "quantum-A",
        "softmax-A",
        "network-A",
        "har-quantile",
        "garch-calibrated",
    ]
    for ax, key, title in zip(
        axes.flat,
        [
            "mfdfa_log_rv_increments",
            "mfdfa_returns",
            "wasserstein_log_rv",
            "hill_return_tail_index",
        ],
        [
            "MFDFA h(2): log-RV changes, fixed path zero",
            "MFDFA h(2): returns, fixed path zero",
            "Wasserstein log RV (all paths) ↓",
            "Generated return Hill index (all paths)",
        ],
        strict=True,
    ):
        for j, id_ in enumerate(subset):
            group = [p for p in paths if p["id"] == id_]
            if key.startswith("mfdfa"):
                values = [
                    p["fixed_path_zero_diagnostics"][key]["h2"]
                    for p in group
                    if p["fixed_path_zero_diagnostics"][key]["available"]
                ]
                shuffled = (
                    "mfdfa_shuffled_increments"
                    if key.endswith("increments")
                    else "mfdfa_shuffled_returns"
                )
                controls = [
                    p["fixed_path_zero_diagnostics"][shuffled]["h2"]
                    for p in group
                    if p["fixed_path_zero_diagnostics"][shuffled]["available"]
                ]
                if values:
                    ax.errorbar(
                        j - 0.1,
                        np.mean(values),
                        yerr=np.std(values, ddof=1),
                        fmt="o",
                        color=color(id_),
                        capsize=2,
                    )
                if controls:
                    ax.errorbar(
                        j + 0.1,
                        np.mean(controls),
                        yerr=np.std(controls, ddof=1),
                        fmt="x",
                        color="#888888",
                        capsize=2,
                    )
            else:
                r = by_id[id_][key]
                ax.errorbar(j, r["mean"], yerr=r["sd"] or 0, fmt="o", color=color(id_), capsize=2)
        ax.set(xticks=range(len(subset)), xticklabels=[LABELS[i] for i in subset], title=title)
        ax.tick_params(axis="x", rotation=35, labelsize=8)
    fig.suptitle(
        "Finite-path diagnostics; MFDFA circles=original, crosses=shuffled; no test Hill estimate",
        fontsize=13,
    )
    fig.savefig(root / "final-path-diagnostics.png", dpi=170)
    plt.close(fig)

    fig, axes = plt.subplots(2, 1, figsize=(14, 8), layout="constrained")
    seed = min(r["seed"] for r in records)
    t = data.target_rows[data.test]
    axes[0].plot(t, data.y[data.test], color="#aaaaaa", lw=1, label="Observed log RV")
    centers = np.array([pool.mean() for pool in data.bins.pools])
    for id_ in ("quantum-A", "network-D", "har-quantile"):
        with np.load(root / f"{id_}-seed{seed}.npz") as saved:
            prediction = saved["probabilities"] @ centers
        axes[0].plot(t, prediction, label=LABELS[id_], color=color(id_), lw=1)
    axes[0].set(title=f"Fixed seed {seed}: teacher-forced bin-mean forecasts", ylabel="Log RV")
    axes[0].legend(fontsize=8)
    axes[1].plot(t, data.daily.rv[t], color="#aaaaaa", lw=1, label="Observed RV")
    with np.load(root / f"point-seed{seed}.npz") as saved:
        for id_, label in [
            ("paper", "Paper circuit"),
            ("persistence", "Persistence"),
            ("raw-har", "Raw-RV HAR"),
        ]:
            axes[1].plot(t, saved[id_], lw=1, label=label)
    axes[1].set(
        title="Separate raw-RV point panel: not categorical NLL",
        xlabel="Author observation row",
        ylabel="RV in author units",
    )
    axes[1].legend(fontsize=8)
    fig.savefig(root / "final-forecast-curves.png", dpi=170)
    plt.close(fig)

    effort = summary["effort"]
    fig, axes = plt.subplots(1, 2, figsize=(15, 7), layout="constrained", sharey=True)
    names = [r["id"] for r in effort]
    positions = np.arange(len(names))
    axes[0].barh(
        positions,
        [r.get("objective_calls", 0) for r in effort],
        color=[color(r["id"]) for r in effort],
    )
    axes[0].set(
        yticks=positions,
        yticklabels=names,
        xlabel="Recorded objective evaluations",
        title="All restarts, not only selected fits",
    )
    axes[1].barh(positions, [r["seconds"] for r in effort], color=[color(r["id"]) for r in effort])
    axes[1].set(
        xlabel="Summed fit wall seconds",
        title="One-thread library settings; not a hardware benchmark",
    )
    for j, row in enumerate(effort):
        note = f" {row['fits']} fits"
        if row.get("lp_solves"):
            note += f" / {row['lp_solves']} LP solves"
        axes[1].text(row["seconds"], j, note, va="center", fontsize=8)
    axes[0].invert_yaxis()
    axes[1].set_xlim(0, max(r["seconds"] for r in effort) * 1.3)
    fig.suptitle(
        "Training effort — neural calls include analytic gradients; LP work is separate",
        fontsize=13,
    )
    fig.savefig(root / "final-training-effort.png", dpi=170)
    plt.close(fig)

    with (root / "final-scorecard.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "model",
                "nll_mean",
                "nll_seed_sd",
                "rps_mean",
                "brier_mean",
                "coverage90",
                "realism_mean",
                "D_passes",
                "stage_passes",
            ]
        )
        for r in rows:
            writer.writerow(
                [
                    r["id"],
                    r["log_loss"]["mean"],
                    r["log_loss"]["sd"],
                    r["rps_normalized"]["mean"],
                    r["extreme_brier"]["mean"],
                    r["coverage_90"]["mean"],
                    r["distance_of_mean"]["mean"],
                    r["D_training_passes"],
                    r["stage_training_passes"],
                ]
            )
    print("Exported six figures and final-scorecard.csv to", root)


if __name__ == "__main__":
    main()
