#!/usr/bin/env python3
"""Measured v4-v6 development study; 2023 selection, reused 2024 development audit."""

import argparse
import csv
import json
import platform
import time
from pathlib import Path

import numpy as np
import scipy
from scipy.optimize import minimize
from scipy.special import logsumexp, softmax

from qcvol.data import DailyData, Standardizer, load_daily_csv, sha256
from qcvol.fresh_study import prepare_dates
from qcvol_next.weekend_models import WeekendBorn, WeekendHAR
from qcvol_v2.models import features


def prepare_development(daily):
    dates = np.asarray(daily.index, dtype="datetime64[D]")
    keep = dates < np.datetime64("2025-01-01")
    trimmed = DailyData(dates[keep], daily.returns[keep], daily.rv[keep], daily.units)
    return prepare_dates(trimmed, "2022-12-31", "2023-12-31")


def normalized(p):
    p = np.asarray(p, float)
    if p.ndim != 2 or p.shape[1] != 4 or not np.all(np.isfinite(p)) or np.any(p < 0):
        raise ValueError("Need finite nonnegative four-class probabilities")
    if np.any(p.sum(axis=1) <= 0):
        raise ValueError("Probability row has zero mass")
    p = np.clip(p, 1e-12, 1)
    return p / p.sum(axis=1, keepdims=True)


def head_objective(parameters, design, labels, offset, ridge):
    weights = parameters.reshape(design.shape[1], 3)
    logits = np.column_stack([design @ weights, np.zeros(len(design))]) + offset
    value = np.mean(logsumexp(logits, axis=1) - logits[np.arange(len(labels)), labels])
    residual = softmax(logits, axis=1)
    residual[np.arange(len(labels)), labels] -= 1
    gradient = design.T @ residual[:, :3] / len(labels) + 2 * ridge * weights
    return float(value + ridge * np.sum(weights**2)), gradient.ravel()


def fit_head(design, labels, offset, train, ridge, maxiter=1000):
    started = time.perf_counter()
    result = minimize(
        head_objective,
        np.zeros(design.shape[1] * 3),
        args=(design[train], labels[train], offset[train], ridge),
        jac=True,
        method="L-BFGS-B",
        options={"maxiter": maxiter, "gtol": 1e-7, "ftol": 1e-12},
    )
    gradient = head_objective(result.x, design[train], labels[train], offset[train], ridge)[1]
    logits = (
        np.column_stack([design @ result.x.reshape(design.shape[1], 3), np.zeros(len(design))])
        + offset
    )
    probabilities = normalized(softmax(logits, axis=1))
    record = {
        "parameters": result.x.tolist(),
        "n_trainable_parameters": len(result.x),
        "ridge": ridge,
        "success": bool(result.success),
        "message": str(result.message),
        "gradient_inf": float(np.max(np.abs(gradient))),
        "eligible": bool(result.success and np.max(np.abs(gradient)) <= 1e-4),
        "objective": float(result.fun),
        "iterations": int(result.nit),
        "objective_calls": int(result.nfev),
        "diagnostic_calls": 1,
        "seconds": time.perf_counter() - started,
    }
    return probabilities, record


def feature_maps(x, train, seed):
    """Same inputs, seeds and output width; fixed parameter counts differ by map."""
    maps, records = {}, {}
    for kind in ("quantum", "tanh", "sine"):
        blocks, frozen = [], []
        started = time.perf_counter()
        for map_seed in (seed, seed + 1, seed + 2):
            rng = np.random.default_rng(map_seed)
            if kind == "quantum":
                parameters = rng.normal(0, 1, 20)
                block = WeekendBorn(2, weekend_axis="y").probabilities(x, parameters)
            else:
                parameters = rng.normal(0, 1, (6, 4))
                projection = np.column_stack([x, np.ones(len(x))]) @ parameters
                block = np.tanh(projection) if kind == "tanh" else np.sin(projection)
            blocks.append(block)
            frozen.append({"seed": map_seed, "parameters": parameters.tolist()})
        raw = np.column_stack(blocks)
        scaler = Standardizer.fit(raw[train])
        maps[kind] = scaler.transform(raw)
        records[kind] = {
            "maps": frozen,
            "width": raw.shape[1],
            "mean": scaler.mean.tolist(),
            "scale": scaler.scale.tolist(),
            "seconds": time.perf_counter() - started,
            "n_frozen_parameters": sum(np.asarray(r["parameters"]).size for r in frozen),
        }
    return maps, records


def losses(p, labels, rv, bin_means):
    p = normalized(p)
    prediction = p @ bin_means
    ratio = rv / prediction
    return {
        "nll": -np.log(p[np.arange(len(labels)), labels]),
        "brier": np.sum((p - np.eye(4)[labels]) ** 2, axis=1),
        "qlike": ratio - np.log(ratio) - 1,
    }


def select_candidate(names, records):
    eligible = [name for name in names if records[name]["eligible"]]
    return min(eligible or ["har"], key=lambda n: (records[n]["calibration_nll"], n))


def run_study(daily, seed=42, ridges=(1e-3, 1e-2), maxiter=1000):
    started = time.perf_counter()
    data = prepare_development(daily)
    x = features(data)[:, :5]
    maps, map_records = feature_maps(x, data.train, seed)
    har = WeekendHAR.fit(x[data.train], data.y[data.train], data.bins.edges)
    base = normalized(har.probabilities(x))
    probabilities = {"har": base}
    records = {
        "har": {
            "eligible": True,
            "n_trainable_parameters": len(har.coefficients),
            "parameters": har.coefficients.tolist(),
            "residuals": har.residuals.tolist(),
            "success": True,
            "calibration_nll": float(
                -np.log(
                    base[data.validation][
                        np.arange(len(data.labels[data.validation])), data.labels[data.validation]
                    ]
                ).mean()
            ),
        }
    }
    families = {}
    for kind in ("linear", "quantum", "tanh", "sine"):
        values = x if kind == "linear" else np.column_stack([x, maps[kind]])
        design = np.column_stack([values, np.ones(len(x))])
        for residual in (False, True):
            family = kind + ("-residual" if residual else "")
            families[family] = ["har"] if residual else []
            offset = np.log(base) if residual else np.zeros_like(base)
            for ridge in ridges:
                name = f"{family}-ridge-{ridge:g}"
                p, record = fit_head(design, data.labels, offset, data.train, ridge, maxiter)
                record["calibration_nll"] = float(
                    -np.log(
                        p[data.validation][
                            np.arange(len(data.labels[data.validation])),
                            data.labels[data.validation],
                        ]
                    ).mean()
                )
                probabilities[name], records[name] = p, record
                families[family].append(name)
    selected = {family: select_candidate(names, records) for family, names in families.items()}
    classical = ["har"] + [name for family, name in selected.items() if "quantum" not in family]
    control = select_candidate(classical, records)
    selected.update({"v4": selected["quantum"], "v5": selected["quantum-residual"]})
    blend_records = []
    for quantum_weight in (0.0, 0.25, 0.5, 0.75, 1.0):
        for v4_weight in (0.0, 0.5, 1.0):
            p = (
                quantum_weight
                * (
                    v4_weight * probabilities[selected["v4"]]
                    + (1 - v4_weight) * probabilities[selected["v5"]]
                )
                + (1 - quantum_weight) * probabilities[control]
            )
            score = -np.log(
                p[data.validation][
                    np.arange(len(data.labels[data.validation])), data.labels[data.validation]
                ]
            ).mean()
            blend_records.append(
                {
                    "quantum_weight": quantum_weight,
                    "v4_weight": v4_weight,
                    "calibration_nll": float(score),
                }
            )
    blend = min(
        blend_records, key=lambda b: (b["calibration_nll"], b["quantum_weight"], b["v4_weight"])
    )
    for name in ("v4", "v5"):
        probabilities[name] = probabilities[selected[name]]
    probabilities["classical-selected"] = probabilities[control]
    probabilities["v6"] = normalized(
        blend["quantum_weight"]
        * (
            blend["v4_weight"] * probabilities["v4"]
            + (1 - blend["v4_weight"]) * probabilities["v5"]
        )
        + (1 - blend["quantum_weight"]) * probabilities[control]
    )
    bin_means = np.array([np.exp(pool).mean() for pool in data.bins.pools])
    dates = data.daily.index[data.target_rows]
    metrics = {}
    for name, p in probabilities.items():
        metrics[name] = {}
        for split, selection in (("calibration", data.validation), ("audit", data.test)):
            scores = losses(
                p[selection], data.labels[selection], np.exp(data.y[selection]), bin_means
            )
            metrics[name][split] = {metric: float(value.mean()) for metric, value in scores.items()}
    summary = {
        "status": "development_only; 2024 previously reused; no confirmatory inference",
        "seed": seed,
        "software_versions": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "config": {"ridges": list(ridges), "maxiter": maxiter, "layers": 2, "map_count": 3},
        "splits": {
            name: [str(dates[s][0]), str(dates[s][-1]), len(dates[s])]
            for name, s in (
                ("train", data.train),
                ("calibration", data.validation),
                ("audit", data.test),
            )
        },
        "preprocessing": data.metadata(),
        "rv_bin_means": bin_means.tolist(),
        "feature_maps": map_records,
        "fits": records,
        "head_fit_count": len(records) - 1,
        "total_fit_count_including_har": len(records),
        "eligible_head_fit_count": sum(r["eligible"] for n, r in records.items() if n != "har"),
        "selections": selected,
        "classical_control": control,
        "v6": {"selected": blend, "candidates": blend_records, "classical": control},
        "metrics": metrics,
        "seconds": time.perf_counter() - started,
    }
    return summary, probabilities, data


def write_results(output, summary, probabilities, data, source):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    summary["source"] = source
    (output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    bin_means = np.asarray(summary["rv_bin_means"])
    with (output / "predictions.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "model",
                "split",
                "date",
                "label",
                "rv",
                "p0",
                "p1",
                "p2",
                "p3",
                "nll",
                "brier",
                "qlike",
            ]
        )
        for name, p in probabilities.items():
            for split, selection in (("calibration", data.validation), ("audit", data.test)):
                rv = np.exp(data.y[selection])
                scores = losses(p[selection], data.labels[selection], rv, bin_means)
                dates = data.daily.index[data.target_rows[selection]]
                for i, date in enumerate(dates):
                    writer.writerow(
                        [
                            name,
                            split,
                            str(date),
                            int(data.labels[selection][i]),
                            rv[i],
                            *p[selection][i],
                            scores["nll"][i],
                            scores["brier"][i],
                            scores["qlike"][i],
                        ]
                    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; refusing overwrite")
    summary, probabilities, data = run_study(load_daily_csv(args.data), args.seed)
    root = Path(__file__).resolve().parents[1]
    sources = [
        Path(__file__).resolve(),
        root / "pyproject.toml",
        root / "uv.lock",
        root / "doc/frontier-protocol.md",
    ]
    for package in ("qcvol", "qcvol_v2", "qcvol_next"):
        sources.extend((root / "src" / package).glob("*.py"))
    source = {
        "data_path": str(args.data),
        "data_sha256": sha256(args.data),
        "code_hashes": {str(path.relative_to(root)): sha256(path) for path in sources},
    }
    write_results(args.output, summary, probabilities, data, source)
    print(
        json.dumps(
            {
                name: summary["metrics"][name]
                for name in ("har", "classical-selected", "v4", "v5", "v6")
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
