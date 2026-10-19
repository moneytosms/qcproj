"""Validation-only model selection, then one held-out evaluation per named model/seed."""

import json
import platform
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import numpy as np

from .classical import FrequencyModel, HARModel, SoftmaxModel, TinyNetwork
from .data import PreparedData, sha256
from .generation import generate
from .metrics import (
    forecast_scores,
    kupiec_test,
    log_loss,
    moment_distance,
    moment_scales,
    moments,
    path_diagnostics,
    return_quantiles,
)
from .quantum import BornCircuit, verify_paper
from .training import fit_distribution, fit_point, generate_point, point_prediction


@dataclass
class ExperimentConfig:
    seeds: list[int] = field(default_factory=lambda: [0])
    layers: list[int] = field(default_factory=lambda: [3])
    lambdas: list[float] = field(default_factory=lambda: [0.0, 0.05])
    max_evaluations: int = 80
    train_path_days: int = 128
    train_paths: int = 2
    evaluation_days: int = 256
    evaluation_paths: int = 4
    burn_in: int = 30
    validation_realism_weight: float = 0.01

    def __post_init__(self):
        if (
            not self.seeds
            or len(set(self.seeds)) != len(self.seeds)
            or any(type(s) is not int or not 0 <= s < 10_000 for s in self.seeds)
        ):
            raise ValueError("Need distinct integer seeds in 0..9999")
        if not self.layers or any(type(i) is not int or i not in (1, 2, 3, 4) for i in self.layers):
            raise ValueError("Choose layers in 1..4")
        if (
            not self.lambdas
            or 0 not in self.lambdas
            or any(not np.isfinite(w) or w < 0 for w in self.lambdas)
        ):
            raise ValueError("Lambda sweep must include zero and nonnegative finite values")
        if len(set(self.layers)) != len(self.layers) or len(set(self.lambdas)) != len(self.lambdas):
            raise ValueError("Duplicate sweep candidates")
        if type(self.max_evaluations) is not int or self.max_evaluations < max(
            26, 8 * max(self.layers) + 2
        ):
            raise ValueError("Evaluation budget must allow all parameters + 2 (at least 26)")
        if min(self.train_path_days, self.evaluation_days) < 32:
            raise ValueError("Simulation paths need >=32 days")
        if min(self.train_paths, self.evaluation_paths) < 1 or self.burn_in < 0:
            raise ValueError("Positive path counts and nonnegative burn-in required")
        if not np.isfinite(self.validation_realism_weight) or self.validation_realism_weight < 0:
            raise ValueError("Validation realism weight must be finite and nonnegative")

    @classmethod
    def load(cls, path):
        return cls(**json.loads(Path(path).read_text()))


def clean_json(value):
    """Emit standards-compliant JSON: undefined metrics become null, never bare NaN."""
    if isinstance(value, dict):
        return {str(k): clean_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean_json(v) for v in value]
    if isinstance(value, np.ndarray):
        return clean_json(value.tolist())
    if isinstance(value, np.generic):
        return clean_json(value.item())
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def write_json(path, value):
    Path(path).write_text(json.dumps(clean_json(value), indent=2, allow_nan=False) + "\n")


def code_revision():
    source_hashes = {p.name: sha256(p) for p in Path(__file__).parent.glob("*.py")}
    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        status = subprocess.check_output(["git", "status", "--porcelain"], text=True).splitlines()
        return {
            "head": revision,
            "dirty": bool(status),
            "status": status,
            "package_source_sha256": source_hashes,
        }
    except (OSError, subprocess.CalledProcessError):
        return {"head": None, "dirty": None, "package_source_sha256": source_hashes}


def _validation(model, fit, data, config, seed, scales):
    nll = log_loss(
        model.probabilities(data.x[data.validation], fit.parameters), data.labels[data.validation]
    )
    paths = generate(
        model,
        fit.parameters,
        data,
        days=config.train_path_days,
        paths=config.train_paths,
        seed=20_000 + seed,
        burn_in=config.burn_in,
    )
    generated_moments = np.mean([moments(y) for y in paths.log_rv], axis=0)
    distance = moment_distance(generated_moments, moments(data.y[data.validation]), scales)
    if not np.isfinite(distance):
        distance = 1e8
    return {
        "log_loss": nll,
        "moment_distance": distance,
        "selection_score": nll + config.validation_realism_weight * distance,
    }


def _diagnostics(y_paths, r_paths, data, config, seed, scales):
    raw = [
        path_diagnostics(y, r, data.y[data.test], scales, seed=40_000 + seed + i)
        for i, (y, r) in enumerate(zip(y_paths, r_paths))
    ]
    # Mean of per-path distances; this differs deliberately from distance of mean
    # moments used during optimization and validation. Both definitions are recorded.
    names = ("moment_distance", "wasserstein_log_rv", "hill_return_tail_index")
    averages, valid_counts = {}, {}
    for name in names:
        values = [v[name] for v in raw if np.isfinite(v[name])]
        valid_counts[name] = len(values)
        # Do not improve the reported mean by silently dropping undefined paths.
        averages[name] = float(np.mean(values)) if len(values) == len(raw) else None
    return {
        "path_count": config.evaluation_paths,
        "path_days": config.evaluation_days,
        "mean_per_path": averages,
        "valid_path_counts": valid_counts,
        "paths": raw,
    }


def run_experiment(data: PreparedData, config: ExperimentConfig, output, source=None):
    output = Path(output)
    # Refuse reuse: preserve previous results, especially after a partial failed run.
    output.mkdir(parents=True, exist_ok=False)
    scales = moment_scales(data.y[data.train])
    manifest = {
        "created_utc": datetime.now(UTC).isoformat(),
        "config": asdict(config),
        "data": data.metadata(),
        "source": source,
        "code": code_revision(),
        "versions": {
            "python": platform.python_version(),
            **{name: version(name) for name in ("qcvol", "numpy", "scipy")},
        },
        "simulation_seeds": "train=10000+seed; validation=20000+seed; test=30000+seed",
        "moment_scales": scales.tolist(),
        "paper_algebra": verify_paper(),
        "parameter_notes": {
            "paper": "3 nominal; phi inactive; 2 effective",
            "memory_b": "18 nominal; terminal RZ inactive; capacity differs from paper",
            "quantum": "8*layers nominal; last two RZ angles inactive; at most 8*layers-2 effective",
            "softmax": "20 nominal; 15 identifiable due to shared-logit shift invariance",
            "tiny_nn": "24 nominal; reference logits; specified skip architecture",
            "har_residual": "4 OLS coefficients plus nonparametric training residual pool",
        },
        "status": "running",
        "scope": "Research scaffold; not a completed replication",
        "metric_conventions": {
            "rps": "mean across 3 cutpoints",
            "training_distance": "sum of squared standardized differences of mean moments",
            "test_distance": "mean of per-path squared standardized moment distances",
        },
        "limitations": [
            "Author-standardized data may use full-sample upstream scaling",
            "No physical-unit risk claims from author-standardized inputs",
            "Finite samples and low optimizer budgets can dominate differences",
            "MFDFA defaults are diagnostic, not paper-matched rolling-window analysis",
            "Point models and categorical models have separate forecast panels",
            "GARCH, 8 levels, hardware, transfer and final paper comparison remain pending",
        ],
    }
    write_json(output / "manifest.json", manifest)
    records, candidates = [], []
    raw_test = data.target_rows[data.test]

    def evaluate(name, model, parameters, seed, details):
        print(f"  evaluating {name}", flush=True)
        probabilities = model.probabilities(data.x[data.test], parameters)
        paths = generate(
            model,
            parameters,
            data,
            days=config.evaluation_days,
            paths=config.evaluation_paths,
            seed=30_000 + seed,
            burn_in=config.burn_in,
        )
        forecast = forecast_scores(probabilities, data.labels[data.test])
        if data.daily.units == "author-standardized":
            risk = {
                "available": False,
                "reason": "Upstream return and RV scales differ; raw units unknown",
            }
        else:
            quantile = return_quantiles(probabilities, data.bins.pools)
            risk = {
                "available": True,
                "units": data.daily.units,
                "assumption": "zero-mean Gaussian return conditional on empirical RV",
                "kupiec": kupiec_test(data.daily.returns[raw_test] < quantile),
            }
        record = {
            "name": name,
            "seed": seed,
            "panel": "distribution",
            "parameters": model.n_params,
            "forecast": forecast,
            "risk": risk,
            "selection": details,
            "realism": _diagnostics(paths.log_rv, paths.returns, data, config, seed, scales),
        }
        records.append(record)
        np.savez_compressed(
            output / f"{name}-seed{seed}.npz",
            probabilities=probabilities,
            labels=data.labels[data.test],
            target_rows=raw_test,
            log_rv_paths=paths.log_rv,
            return_paths=paths.returns,
            sampled_levels=paths.levels,
            parameters=np.array([]) if parameters is None else parameters,
        )
        write_json(output / "records.json", records)

    for seed in config.seeds:
        print(f"Seed {seed}", flush=True)
        # Point forecasts are directly comparable to one another in RV units.
        for kind in ("paper", "memory_b"):
            fit, scaling = fit_point(
                kind, data, seed=seed, layers=3, max_evaluations=config.max_evaluations
            )
            prediction = point_prediction(kind, fit.parameters, data, raw_test, scaling)
            y, r, clipped = generate_point(
                kind,
                fit.parameters,
                data,
                scaling,
                days=config.evaluation_days,
                paths=config.evaluation_paths,
                seed=30_000 + seed,
                burn_in=config.burn_in,
            )
            previous_r = data.daily.returns[raw_test - 1] / scaling.return_scale
            previous_v = data.daily.rv[raw_test - 1] / scaling.rv_scale
            input_clipped = int((np.abs(previous_r) > 1).sum() + (previous_v > 1).sum())
            record = {
                "name": kind,
                "seed": seed,
                "panel": "point",
                "parameters": len(fit.parameters),
                "forecast": {"mse_rv": float(np.mean((prediction - data.daily.rv[raw_test]) ** 2))},
                "fit": fit.record(),
                "scaling": asdict(scaling),
                "paper_encoding_clips_in_generation": clipped,
                "paper_encoding_clips_in_test": input_clipped if kind == "paper" else 0,
                "realism": _diagnostics(y, r, data, config, seed, scales),
            }
            records.append(record)
            np.savez_compressed(
                output / f"{kind}-seed{seed}.npz",
                prediction=prediction,
                actual=data.daily.rv[raw_test],
                parameters=fit.parameters,
                log_rv_paths=y,
                return_paths=r,
                target_rows=raw_test,
            )
            print(f"  fitted {kind}, MSE={record['forecast']['mse_rv']:.5f}", flush=True)

        evaluate("frequency", FrequencyModel.fit(data.labels[data.train]), None, seed, {})
        har = HARModel.fit(data.x[data.train], data.y[data.train], data.bins.edges)
        evaluate(
            "har_residual",
            har,
            None,
            seed,
            {
                "coefficients": har.coefficients.tolist(),
                "residuals": har.residuals.tolist(),
                "edges": har.edges.tolist(),
            },
        )
        families = [
            ("quantum", [BornCircuit(depth) for depth in config.layers]),
            ("softmax", [SoftmaxModel()]),
            ("tiny_nn", [TinyNetwork()]),
        ]
        for family, models in families:
            choices = []
            for model in models:
                print(f"  training {family}, parameters={model.n_params}", flush=True)
                forecast_fit = fit_distribution(
                    model, data, seed=seed, max_evaluations=config.max_evaluations
                )
                for weight in config.lambdas:
                    fit = (
                        forecast_fit
                        if weight == 0
                        else fit_distribution(
                            model,
                            data,
                            seed=seed,
                            max_evaluations=config.max_evaluations,
                            realism_weight=weight,
                            initial=forecast_fit.parameters,
                            path_days=config.train_path_days,
                            paths=config.train_paths,
                            burn_in=config.burn_in,
                        )
                    )
                    scores = _validation(model, fit, data, config, seed, scales)
                    record = {
                        "family": family,
                        "seed": seed,
                        "lambda": weight,
                        "layers": getattr(model, "layers", None),
                        "n_params": model.n_params,
                        "fit": fit.record(),
                        "validation": scores,
                        "forecast_fit_evaluations": forecast_fit.evaluations,
                    }
                    candidates.append(record)
                    choices.append((model, fit, record))
                    write_json(output / "candidates.json", candidates)
            forecast_choice = min(
                (c for c in choices if c[2]["lambda"] == 0),
                key=lambda c: c[2]["validation"]["log_loss"],
            )
            selected_choice = min(choices, key=lambda c: c[2]["validation"]["selection_score"])
            for suffix, choice in [("forecast", forecast_choice), ("selected", selected_choice)]:
                model, fit, details = choice
                evaluate(f"{family}_{suffix}", model, fit.parameters, seed, details)
    summary = summarize(records)
    write_json(output / "summary.json", summary)
    manifest["status"] = "complete"
    write_json(output / "manifest.json", manifest)
    write_json(output / "records.json", records)
    return summary


def summarize(records):
    result = []
    for name in sorted({r["name"] for r in records}):
        entries = [r for r in records if r["name"] == name]
        metrics = {}
        for key in ("mse_rv", "log_loss", "rps_normalized", "extreme_brier"):
            values = [r["forecast"][key] for r in entries if key in r["forecast"]]
            if values:
                metrics[key] = {
                    "mean": float(np.mean(values)),
                    "std": float(np.std(values, ddof=1)) if len(values) > 1 else None,
                }
        for key in ("moment_distance", "wasserstein_log_rv"):
            values = [r["realism"]["mean_per_path"][key] for r in entries]
            finite = [v for v in values if v is not None and np.isfinite(v)]
            metrics[key] = {
                "mean": float(np.mean(finite)) if finite else None,
                "std": float(np.std(finite, ddof=1)) if len(finite) > 1 else None,
            }
        result.append(
            {"name": name, "panel": entries[0]["panel"], "seeds": len(entries), "metrics": metrics}
        )
    return result
