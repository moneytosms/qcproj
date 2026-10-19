"""Prespecified warm-started memory comparison on training and validation only."""

import platform
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import numpy as np

from .experiment import code_revision, write_json
from .nested_memory import (
    HARPointModel,
    NestedMemoryCircuit,
    fit_nested,
    nested_inputs,
    warm_initial,
)
from .quantum import paper_probability
from .training import PointScaling, fit_point, point_prediction


@dataclass
class NestedStudyConfig:
    seeds: list[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])
    regularization: list[float] = field(default_factory=lambda: [0, 0.0001, 0.001, 0.01, 0.1, 1])
    max_evaluations: int = 10000
    jitter: float = 0.05
    gradient_tolerance: float = 1e-5
    optimizer_tolerance: float = 1e-7
    minimum_relative_gain: float = 0.01

    def __post_init__(self):
        if (
            not self.seeds
            or 0 not in self.seeds
            or len(set(self.seeds)) != len(self.seeds)
            or any(type(s) is not int or s < 0 for s in self.seeds)
        ):
            raise ValueError(
                "Need distinct nonnegative integer seeds including exact warm start zero"
            )
        if (
            not self.regularization
            or 0 not in self.regularization
            or len(set(self.regularization)) != len(self.regularization)
            or any(not np.isfinite(a) or a < 0 for a in self.regularization)
        ):
            raise ValueError("Need distinct finite nonnegative penalties including zero")
        if type(self.max_evaluations) is not int or self.max_evaluations < 6:
            raise ValueError("Budget must allow the four-parameter optimizer simplex")
        if not np.isfinite(self.jitter) or self.jitter < 0:
            raise ValueError("Warm-start jitter must be finite and nonnegative")
        if not np.isfinite(self.gradient_tolerance) or self.gradient_tolerance <= 0:
            raise ValueError("Stationarity tolerance must be positive")
        if not np.isfinite(self.optimizer_tolerance) or self.optimizer_tolerance <= 0:
            raise ValueError("Optimizer trust-region tolerance must be positive")
        if not np.isfinite(self.minimum_relative_gain) or not 0 <= self.minimum_relative_gain < 1:
            raise ValueError("Minimum validation gain must lie in [0,1)")


def mse(actual, predicted):
    return float(np.mean((np.asarray(actual) - predicted) ** 2))


def summarize(records):
    groups = {}
    for r in records:
        if r["kind"] in ("paper", "nested_memory", "nested_short"):
            groups.setdefault((r["kind"], r["regularization"]), []).append(r)
    summary = []
    for (kind, alpha), group in groups.items():
        winner = min(group, key=lambda r: (r["fit"]["objective"], r["seed"]))
        summary.append(
            {
                "kind": kind,
                "regularization": alpha,
                "winner": winner["id"],
                "starts": len(group),
                "converged_starts": sum(r["eligible"] for r in group),
                "eligible": winner["eligible"],
                "train_objective": winner["fit"]["objective"],
                "train_mse_rv": winner["train_mse_rv"],
                "validation_mse_rv": winner["validation_mse_rv"],
                "optimizer_objective_calls": sum(r["fit"]["total_objective_calls"] for r in group),
                "stationarity_objective_calls": sum(
                    r["stationarity_objective_calls"] for r in group
                ),
                "fit_seconds": sum(r["fit"]["seconds"] for r in group),
            }
        )
    return summary


def decide(summary, config):
    """Keep the paper as an explicit zero-weight fallback in both candidate families."""
    baseline = next(s for s in summary if s["kind"] == "paper")
    if not baseline["eligible"]:
        return {
            "status": "inconclusive",
            "reason": "Training-selected paper fit is not stationary/converged",
        }
    if any(not s["eligible"] for s in summary):
        return {
            "status": "inconclusive",
            "reason": "Resolve nonconverged or nonstationary training-selected settings before deciding B",
            "ineligible_settings": [s["winner"] for s in summary if not s["eligible"]],
        }
    selections = {}
    for kind in ("nested_memory", "nested_short"):
        eligible = [baseline] + [s for s in summary if s["kind"] == kind and s["eligible"]]
        selections[kind] = min(
            eligible,
            key=lambda s: (
                s["validation_mse_rv"],
                s["kind"] != "paper",
                -(s["regularization"] or 0),
            ),
        )
    full, short = selections["nested_memory"], selections["nested_short"]
    reference = min(baseline["validation_mse_rv"], short["validation_mse_rv"])
    gain = (reference - full["validation_mse_rv"]) / reference if reference > 0 else 0.0
    retain = (
        full["kind"] == "nested_memory"
        and gain >= config.minimum_relative_gain
        and full["validation_mse_rv"] < reference
    )
    return {
        "status": "retain_long_memory_for_next_stage"
        if retain
        else "retain_short_memory_for_next_stage",
        "selections": selections,
        "relative_gain_over_best_short_or_paper": gain,
        "minimum_relative_gain": config.minimum_relative_gain,
        "feature_policy_for_D": "HAR" if retain else "previous_day_only",
        "next_step": "D probability forecasting, then A realism training; keep classical controls and the original baseline",
        "scope": "Exploratory validation decision, not a test result or statistical proof of memory benefit",
        "excluded_unconverged_or_nonstationary_settings": [
            s["winner"] for s in summary if not s["eligible"]
        ],
    }


def run_followup(data, config, output, source=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    scaling = PointScaling.fit(data)
    train_rows = data.target_rows[data.train]
    target = data.daily.rv[train_rows] / scaling.rv_scale
    if np.any((target < 0) | (target > 1)):
        raise ValueError("Training RV targets are outside the bounded circuit readout")
    manifest = {
        "created_utc": datetime.now(UTC).isoformat(),
        "config": asdict(config),
        "data": data.metadata(),
        "source": source,
        "code": code_revision(),
        "scaling": asdict(scaling),
        "status": "running",
        "versions": {
            "python": platform.python_version(),
            **{n: version(n) for n in ("qcvol", "numpy", "scipy")},
        },
        "protocol": "Select restarts by penalized training objective; eligible only on optimizer success and central-gradient check. Select regularization by validation MSE. Paper zero-weight fallback included. No test scores.",
        "convergence": {
            "method": "COBYLA",
            "rhobeg": 0.3,
            "paper_tolerance": 1e-5,
            "nested_tolerance": config.optimizer_tolerance,
            "gradient_step": 1e-5,
            "diagnostic_calls_counted_separately": True,
        },
        "capacity": "Paper 2 optimized/3 stored angles. Nested full and short: 4 optimized angles. HAR: 4 OLS coefficients, one linear solve. Families have different information maps and forward costs.",
        "limitations": [
            "Upstream author rescaling may use full-sample information",
            "Validation reused during model development; exploratory only",
            "Different objectives: HAR OLS in RV, circuits MSE plus stated weight penalty",
            "No hardware, 20-seed study or recursive-realism claim",
        ],
    }
    write_json(output / "manifest.json", manifest)
    records = []

    def save(row, predictions):
        arrays = {}
        if "fit" in row:
            arrays["parameters"] = np.array(row["fit"]["parameters"])
            arrays["objective_history"] = np.array(row["fit"]["objective_history"])
        for split, predicted in predictions.items():
            rows = data.target_rows[getattr(data, split)]
            actual = data.daily.rv[rows]
            row[f"{split}_mse_rv"] = mse(actual, predicted)
            arrays.update(
                {
                    f"{split}_rows": rows,
                    f"{split}_actual_rv": actual,
                    f"{split}_predicted_rv": predicted,
                }
            )
        records.append(row)
        np.savez_compressed(output / f"{row['id']}.npz", **arrays)
        write_json(output / "records.json", records)
        print(
            f"{row['id']} train={row['train_mse_rv']:.8f} validation={row['validation_mse_rv']:.8f} eligible={row.get('eligible', True)}",
            flush=True,
        )

    for seed in config.seeds:
        fit, _ = fit_point(
            "paper",
            data,
            seed=seed,
            initialization="uniform",
            reduce_inactive=True,
            max_evaluations=config.max_evaluations,
        )

        def objective(angles):
            return mse(
                target,
                paper_probability(
                    np.clip(data.daily.returns[train_rows - 1] / scaling.return_scale, -1, 1),
                    np.clip(data.daily.rv[train_rows - 1] / scaling.rv_scale, 0, 1),
                    np.array([angles[0], 0, angles[1]]),
                ),
            )

        angles = fit.parameters[[0, 2]]
        gradient = [
            (objective(angles + np.eye(2)[j] * 1e-5) - objective(angles - np.eye(2)[j] * 1e-5))
            / 2e-5
            for j in range(2)
        ]
        norm = float(np.max(np.abs(gradient)))
        row = {
            "id": f"paper-seed{seed}",
            "kind": "paper",
            "regularization": None,
            "seed": seed,
            "fit": fit.record(),
            "gradient_inf": norm,
            "stationarity_objective_calls": 4,
            "eligible": bool(fit.success and norm <= config.gradient_tolerance),
        }
        save(
            row,
            {
                split: point_prediction(
                    "paper", fit.parameters, data, data.target_rows[getattr(data, split)], scaling
                )
                for split in ("train", "validation")
            },
        )
    baseline = min(records, key=lambda r: (r["fit"]["objective"], r["seed"]))
    if not baseline["eligible"]:
        raise ValueError("Training-selected baseline did not pass convergence checks")
    baseline_parameters = np.array(baseline["fit"]["parameters"])
    zero_errors = {}
    for split in ("train", "validation"):
        rows = data.target_rows[getattr(data, split)]
        encoded, x, clips = nested_inputs(data, rows, scaling)
        zero = (
            NestedMemoryCircuit().predict_encoded(encoded, x, warm_initial(baseline_parameters, 0))
            * scaling.rv_scale
        )
        expected = point_prediction("paper", baseline_parameters, data, rows, scaling)
        zero_errors[split] = {
            "max_error": float(np.max(np.abs(zero - expected))),
            "input_clips": clips,
        }
    if max(r["max_error"] for r in zero_errors.values()) > 1e-12:
        raise ValueError("Zero-weight nesting check failed")
    manifest["baseline_fit_id"] = baseline["id"]
    manifest["zero_weight_identity"] = zero_errors
    write_json(output / "manifest.json", manifest)
    for kind in ("nested_memory", "nested_short"):
        for alpha in config.regularization:
            for seed in config.seeds:
                fit, _, gradient = fit_nested(
                    data,
                    baseline_parameters,
                    alpha,
                    seed=seed,
                    short_memory=kind == "nested_short",
                    max_evaluations=config.max_evaluations,
                    jitter=config.jitter,
                    optimizer_tolerance=config.optimizer_tolerance,
                )
                norm = float(np.max(np.abs(gradient)))
                row = {
                    "id": f"{kind}-a{alpha:g}-seed{seed}",
                    "kind": kind,
                    "regularization": alpha,
                    "seed": seed,
                    "fit": fit.record(),
                    "gradient_inf": norm,
                    "stationarity_objective_calls": 8,
                    "eligible": bool(fit.success and norm <= config.gradient_tolerance),
                    "baseline_fit_id": baseline["id"],
                    "initial_parameters": warm_initial(
                        baseline_parameters, seed, config.jitter
                    ).tolist(),
                }
                predictions = {}
                for split in ("train", "validation"):
                    encoded, x, _ = nested_inputs(
                        data, data.target_rows[getattr(data, split)], scaling
                    )
                    predictions[split] = (
                        NestedMemoryCircuit(kind == "nested_short").predict_encoded(
                            encoded, x, fit.parameters
                        )
                        * scaling.rv_scale
                    )
                save(row, predictions)
    started = time.perf_counter()
    har = HARPointModel.fit(data)
    har_seconds = time.perf_counter() - started
    save(
        {"id": "har_rv", "kind": "har_rv", "model": har.record(), "fit_seconds": har_seconds},
        {
            split: har.predict(data.daily.rv, data.target_rows[getattr(data, split)])
            for split in ("train", "validation")
        },
    )
    mean = float(np.mean(data.daily.rv[train_rows]))
    for kind in ("training_mean", "persistence"):
        save(
            {"id": kind, "kind": kind},
            {
                split: (
                    np.full(len(data.target_rows[getattr(data, split)]), mean)
                    if kind == "training_mean"
                    else data.daily.rv[data.target_rows[getattr(data, split)] - 1]
                )
                for split in ("train", "validation")
            },
        )
    summary = summarize(records)
    decision = decide(summary, config)
    fits = [r for r in records if "fit" in r]
    manifest.update(
        {
            "status": "complete",
            "fit_count": len(fits),
            "record_count": len(records),
            "optimizer_objective_calls": sum(r["fit"]["total_objective_calls"] for r in fits),
            "stationarity_objective_calls": sum(r["stationarity_objective_calls"] for r in fits),
            "fit_seconds": sum(r["fit"]["seconds"] for r in fits),
            "har_fit_seconds": har_seconds,
        }
    )
    write_json(output / "summary.json", summary)
    write_json(output / "decision.json", decision)
    write_json(output / "manifest.json", manifest)
    return decision
