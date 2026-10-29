#!/usr/bin/env python3
"""Replay sprint losses and describe paired date uncertainty on exposed development data."""

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from qcvol.data import sha256
from qcvol.final_evaluation import block_indices

MODELS = ("classical-selected", "v4", "v5", "v6")
METRICS = ("nll", "brier", "qlike")


def read_run(path):
    path = Path(path)
    summary = json.loads((path / "summary.json").read_text())
    root = Path(__file__).resolve().parents[1]
    source = summary["source"]
    for filename, digest in source["code_hashes"].items():
        if sha256(root / filename) != digest:
            raise ValueError(f"Source changed since fitting: {filename}")
    if sha256(root / source["data_path"]) != source["data_sha256"]:
        raise ValueError("Data changed since fitting")
    with (path / "predictions.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    losses, reference = {}, None
    means = np.asarray(summary["rv_bin_means"])
    for model in MODELS:
        selected = [r for r in rows if r["model"] == model and r["split"] == "audit"]
        dates = [r["date"] for r in selected]
        labels = np.array([int(r["label"]) for r in selected])
        rv = np.array([float(r["rv"]) for r in selected])
        p = np.array([[float(r[f"p{k}"]) for k in range(4)] for r in selected])
        if (
            not selected
            or any(not date.startswith("2024-") for date in dates)
            or len(set(dates)) != len(dates)
            or dates != sorted(dates)
            or np.any((labels < 0) | (labels > 3))
            or not np.all(np.isfinite(rv))
            or np.any(rv <= 0)
            or not np.all(np.isfinite(p))
            or np.any(p <= 0)
            or not np.allclose(p.sum(axis=1), 1, atol=1e-10, rtol=0)
        ):
            raise ValueError(f"Invalid audit forecasts: {path}/{model}")
        identity = (dates, labels.tolist(), rv.tolist())
        if reference is not None and identity != reference:
            raise ValueError("Models must share dates and targets")
        reference = identity
        ratio = rv / (p @ means)
        replay = {
            "nll": -np.log(p[np.arange(len(labels)), labels]),
            "brier": np.sum((p - np.eye(4)[labels]) ** 2, axis=1),
            "qlike": ratio - np.log(ratio) - 1,
        }
        for metric, values in replay.items():
            np.testing.assert_allclose(values, [float(r[metric]) for r in selected], atol=1e-10)
            np.testing.assert_allclose(
                values.mean(), summary["metrics"][model]["audit"][metric], atol=1e-10
            )
        losses[model] = replay
    return summary, losses, reference


def paired_intervals(delta, seed=20261022, replicates=4000):
    """Unadjusted descriptive intervals, not confirmatory significance tests."""
    delta = np.asarray(delta, float)
    if delta.ndim != 1 or len(delta) < 30 or not np.all(np.isfinite(delta)):
        raise ValueError("Need at least 30 finite paired daily differences")
    rng = np.random.default_rng(seed)
    result = []
    for block in (7, 30):
        samples = delta[block_indices(len(delta), block, replicates, rng)].mean(axis=1)
        result.append(
            {
                "block": block,
                "mean_difference": float(delta.mean()),
                "lower": float(np.quantile(samples, 0.025)),
                "upper": float(np.quantile(samples, 0.975)),
            }
        )
    return result


def summarize(paths):
    groups = {}
    for path in paths:
        summary, losses, identity = read_run(path)
        key = summary["source"]["data_path"]
        groups.setdefault(key, []).append((path, summary, losses, identity))
    report = {
        "status": "exposed development data; unadjusted descriptive intervals; not confirmation",
        "interval_method": "95% paired circular date bootstrap on seed-averaged daily NLL",
        "replicates": 4000,
        "bootstrap_seed": 20261022,
        "assets": {},
    }
    for asset, runs in groups.items():
        seeds = [r[1]["seed"] for r in runs]
        if len(set(seeds)) != len(seeds) or any(r[3] != runs[0][3] for r in runs):
            raise ValueError("Need distinct seeds and aligned targets within each asset")
        if len({r[1]["source"]["data_sha256"] for r in runs}) != 1:
            raise ValueError("Data fingerprints differ across seeds")
        for _, summary, *_ in runs[1:]:
            if (
                any(
                    summary[key] != runs[0][1][key]
                    for key in ("config", "software_versions", "splits", "rv_bin_means")
                )
                or summary["source"]["code_hashes"] != runs[0][1]["source"]["code_hashes"]
            ):
                raise ValueError("Configuration or source differs across seeds")
        averaged = {
            model: {
                metric: np.mean([r[2][model][metric] for r in runs], axis=0) for metric in METRICS
            }
            for model in MODELS
        }
        control = averaged["classical-selected"]["nll"]
        report["assets"][asset] = {
            "seeds": seeds,
            "days": len(control),
            "scores": {
                model: {metric: float(v.mean()) for metric, v in values.items()}
                for model, values in averaged.items()
            },
            "nll_relative_gain_percent": {
                model: float(
                    100 * (control.mean() - averaged[model]["nll"].mean()) / control.mean()
                )
                for model in MODELS[1:]
            },
            "paired_nll_intervals": {
                model: paired_intervals(averaged[model]["nll"] - control) for model in MODELS[1:]
            },
            "eligible_heads": [r[1]["eligible_head_fit_count"] for r in runs],
            "total_heads": [r[1]["head_fit_count"] for r in runs],
            "run_seconds": [r[1]["seconds"] for r in runs],
            "mixtures": [r[1]["v6"]["selected"] for r in runs],
            "effective_quantum_weights": [
                r[1]["v6"]["selected"]["quantum_weight"]
                * (
                    r[1]["v6"]["selected"]["v4_weight"]
                    * r[1]["selections"]["v4"].startswith("quantum")
                    + (1 - r[1]["v6"]["selected"]["v4_weight"])
                    * r[1]["selections"]["v5"].startswith("quantum")
                )
                for r in runs
            ],
            "sources": {
                str(path): {
                    filename: sha256(Path(path) / filename)
                    for filename in ("summary.json", "predictions.csv")
                }
                for path, *_ in runs
            },
        }
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = summarize(args.runs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    for asset, row in report["assets"].items():
        print(asset, json.dumps(row["nll_relative_gain_percent"]))


if __name__ == "__main__":
    main()
