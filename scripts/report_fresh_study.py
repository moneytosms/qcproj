#!/usr/bin/env python3
"""Turn the sealed fresh-study evaluation into markdown tables and figures."""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ORDER = [
    "har-quantile",
    "har-residual",
    "hybrid-quantum",
    "hybrid-softmax",
    "short-quantile",
    "short-ar",
    "softmax-har-D",
    "softmax-har-A",
    "network-har-D",
    "network-har-A",
    "quantum-har-D",
    "quantum-har-A",
    "softmax-short-D",
    "softmax-short-A",
    "network-short-D",
    "network-short-A",
    "quantum-short-D",
    "quantum-short-A",
    "garch-calibrated",
    "frequency",
]
INK, MUTED, GRID = "#1f2937", "#6b7280", "#e5e7eb"
QUANTUM, CLASSICAL, BASE = "#2563eb", "#0d9488", "#9ca3af"


def colour(name):
    if "quantum" in name:
        return QUANTUM
    if any(k in name for k in ("softmax", "network")):
        return CLASSICAL
    return BASE


def fmt(stat, digits=4):
    if stat["mean"] is None:
        return "n/a"
    sd = stat["sd"] or 0.0
    return (
        f"{stat['mean']:.{digits}f} ± {sd:.{digits}f}" if sd > 0 else f"{stat['mean']:.{digits}f}"
    )


def tables(result):
    s = result["summary"]
    names = [n for n in ORDER if n in s]
    out = [
        "| Model | Test log loss ↓ | RPS ↓ | Extreme Brier ↓ | Test realism distance ↓ | Fits passing |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for n in sorted(names, key=lambda k: s[k]["log_loss"]["mean"]):
        r = s[n]
        out.append(
            f"| {n} | {fmt(r['log_loss'])} | {fmt(r['rps_normalized'])} | "
            f"{fmt(r['extreme_brier'])} | {fmt(r['test_moment_distance'], 2)} | "
            f"{r['fits_eligible']}/{r['log_loss']['count']} |"
        )
    moments = [
        "| Model | ACF 1 | ACF 7 | ACF 30 | Vol-of-vol | Extreme share |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    tm = result["test_moments"]
    counts = result["test_level_counts"]
    moments.append(
        f"| Real test period | {tm[0]:.3f} | {tm[1]:.3f} | {tm[2]:.3f} | {tm[3]:.3f} | "
        f"{counts[3] / sum(counts):.3f} |"
    )
    tr = result["train_window_reference"]
    moments.append(
        f"| Real training windows (same length) | {tr[0]:.3f} | {tr[1]:.3f} | "
        f"{tr[2]:.3f} | {tr[3]:.3f} | 0.050 |"
    )
    for n in names:
        m = s[n]["mean_moments"]
        moments.append(
            f"| {n} | {m[0]:.3f} | {m[1]:.3f} | {m[2]:.3f} | {m[3]:.3f} | "
            f"{s[n]['extreme_share']['mean']:.3f} |"
        )
    intervals = [
        "| Left − right | Mean log-loss difference | 7-day 95% interval | 30-day 95% interval |",
        "| --- | ---: | --- | --- |",
    ]
    pairs = {}
    for row in result["intervals"]:
        pairs.setdefault((row["left"], row["right"]), {})[row["block"]] = row
    for (left, right), by in pairs.items():
        b7, b30 = by.get(7), by.get(30)
        intervals.append(
            f"| {left} − {right} | {b7['mean_difference']:+.4f} | "
            f"[{b7['lower']:+.4f}, {b7['upper']:+.4f}] | [{b30['lower']:+.4f}, {b30['upper']:+.4f}] |"
        )
    return "\n".join(out), "\n".join(moments), "\n".join(intervals)


def figures(result, out):
    s = result["summary"]
    names = sorted(
        [n for n in ORDER if n in s and n != "frequency"], key=lambda k: s[k]["log_loss"]["mean"]
    )
    fig, ax = plt.subplots(figsize=(8, 0.32 * len(names) + 1.2))
    means = [s[n]["log_loss"]["mean"] for n in names]
    sds = [s[n]["log_loss"]["sd"] or 0 for n in names]
    ax.barh(range(len(names)), means, xerr=sds, color=[colour(n) for n in names], height=0.65)
    ax.set_yticks(range(len(names)), names, fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlim(min(means) * 0.9, max(m + e for m, e in zip(means, sds)) * 1.02)
    ax.set_xlabel("test log loss (lower is better), mean ± SD over 20 seeds")
    ax.set_title(
        "Test-period forecast scores, Jan 2025 to Oct 2026",
        loc="left",
        fontsize=11,
        fontweight="bold",
    )
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(out / "fig_test_log_loss.png", dpi=180)
    plt.close(fig)

    focus = [
        n
        for n in (
            "quantum-short-D",
            "quantum-short-A",
            "quantum-har-D",
            "quantum-har-A",
            "softmax-har-A",
            "network-har-A",
            "har-quantile",
        )
        if n in s
    ]
    lags = ["lag 1", "lag 7", "lag 30"]
    fig, ax = plt.subplots(figsize=(8, 3.4))
    width = 0.8 / (len(focus) + 1)
    xs = np.arange(3)
    ax.bar(
        xs - 0.4 + width / 2, result["test_moments"][:3], width, color=INK, label="real test period"
    )
    for i, n in enumerate(focus, start=1):
        c = (
            QUANTUM
            if "quantum" in n
            else ("#5eead4" if "network" in n else (CLASSICAL if "softmax" in n else BASE))
        )
        alpha = 1.0 if n.endswith("-A") else 0.45
        ax.bar(
            xs - 0.4 + width / 2 + i * width,
            s[n]["mean_moments"][:3],
            width,
            color=c,
            alpha=alpha,
            label=n,
        )
    ax.set_xticks(xs, lags)
    ax.set_ylabel("autocorrelation of log RV")
    ax.axhline(0, color=GRID)
    ax.legend(fontsize=7.5, frameon=False, ncol=2)
    ax.set_title(
        "Memory in simulated paths vs the real test period",
        loc="left",
        fontsize=11,
        fontweight="bold",
    )
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(out / "fig_memory.png", dpi=180)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", type=Path, default=Path("results/fresh-study"))
    parser.add_argument("--output", type=Path, default=Path("doc/fresh-study-results"))
    args = parser.parse_args()
    result = json.loads((args.study / "evaluation" / "results.json").read_text())
    args.output.mkdir(parents=True, exist_ok=True)
    scores, moments, intervals = tables(result)
    (args.output / "tables.md").write_text(
        "## Forecast scores\n\n"
        + scores
        + "\n\n## Simulated-path moments\n\n"
        + moments
        + "\n\n## Paired date-bootstrap intervals\n\n"
        + intervals
        + "\n"
    )
    figures(result, args.output)
    keep = {
        k: result[k]
        for k in (
            "splits",
            "test_moments",
            "train_window_reference",
            "test_level_counts",
            "decisions",
            "summary",
            "intervals",
        )
    }
    (args.output / "results.json").write_text(json.dumps(keep, indent=2) + "\n")
    print(scores)


if __name__ == "__main__":
    main()
