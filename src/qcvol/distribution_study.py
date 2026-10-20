"""Sequential D then A development study. No test probabilities or scores are computed."""

import platform
import time
from dataclasses import asdict, dataclass, field
from importlib.metadata import version
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

from .classical import FrequencyModel, HARModel
from .distribution_models import ShortAR, distribution_model
from .experiment import code_revision, write_json
from .generation import generate
from .metrics import forecast_scores, log_loss, moment_distance, moment_scales, moments
from .training import optimize


@dataclass
class DistributionConfig:
    starts: list[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])
    depths: list[int] = field(default_factory=lambda: [1, 2, 3, 4])
    lambdas: list[float] = field(default_factory=lambda: [0, 0.01, 0.05, 0.2])
    forecast_max_calls: int = 50000
    forecast_max_iterations: int = 2000
    gradient_tolerance: float = 1e-4
    realism_starts: int = 3
    realism_max_calls: int = 600
    realism_tolerance: float = 0.002
    train_days: int = 128
    train_paths: int = 4
    selection_days: int = 256
    selection_paths: int = 8
    audit_days: int = 512
    audit_paths: int = 32
    burn_in: int = 60
    selection_weight: float = 0.01

    def __post_init__(self):
        for name in ("starts", "depths", "lambdas"):
            values = getattr(self, name)
            if not values or len(set(values)) != len(values):
                raise ValueError(f"{name} must be nonempty and distinct")
        if any(type(s) is not int or s < 0 for s in self.starts):
            raise ValueError("Starts must be nonnegative integers")
        if any(type(d) is not int or d not in range(1, 5) for d in self.depths):
            raise ValueError("Depths must be integers 1–4")
        if 0 not in self.lambdas or any(not np.isfinite(v) or v < 0 for v in self.lambdas):
            raise ValueError("Finite nonnegative lambdas must include zero")
        for name in (
            "forecast_max_calls",
            "forecast_max_iterations",
            "realism_starts",
            "realism_max_calls",
            "train_paths",
            "selection_paths",
            "audit_paths",
        ):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(f"{name} must be a positive integer")
        if self.realism_max_calls < max(24, 8 * max(self.depths) - 2) + 2:
            raise ValueError("Realism budget must cover each optimizer simplex")
        for name in ("train_days", "selection_days", "audit_days"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 64:
                raise ValueError("Moment horizons must be at least 64 days")
        if type(self.burn_in) is not int or self.burn_in < 0:
            raise ValueError("Burn-in must be a nonnegative integer")
        for name in ("gradient_tolerance", "realism_tolerance", "selection_weight"):
            if not np.isfinite(getattr(self, name)) or getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive and finite")


def central_gradient(objective, p):
    eye = np.eye(len(p)) * 1e-5
    return np.array([(objective(p + d) - objective(p - d)) / 2e-5 for d in eye])


def fit_forecast(model, data, seed, config):
    """Numerical-gradient L-BFGS-B with separately counted stationarity checks."""
    initial = np.random.default_rng(seed).normal(0, 0.3, model.n_params)
    history = []

    def loss(p):
        return log_loss(model.probabilities(data.x[data.train], p), data.labels[data.train])

    def tracked(p):
        value = loss(p)
        history.append(value)
        return value

    started = time.perf_counter()
    result = minimize(
        tracked,
        initial,
        method="L-BFGS-B",
        jac="3-point",
        options={
            "maxfun": config.forecast_max_calls,
            "maxiter": config.forecast_max_iterations,
            "gtol": 1e-6,
            "ftol": 1e-13,
            "maxls": 40,
        },
    )
    gradient = float(np.max(np.abs(central_gradient(loss, result.x))))
    return {
        "parameters": result.x.tolist(),
        "initial_parameters": initial.tolist(),
        "objective": float(result.fun),
        "initial_objective": history[0],
        "objective_history": history,
        "total_objective_calls": len(history),
        "diagnostic_calls": 2 * model.n_params,
        "seconds": time.perf_counter() - started,
        "success": bool(result.success),
        "message": str(result.message),
        "gradient_inf": gradient,
        "eligible": bool(result.success and gradient <= config.gradient_tolerance),
        "optimized_parameter_count": model.n_params,
        "method": "L-BFGS-B, numerical central differences",
    }


def path_summary(model, parameters, data, days, paths, seed, burn_in, reference, scales):
    generated = generate(model, parameters, data, days, paths, seed, burn_in)
    vectors = np.array([moments(y) for y in generated.log_rv])
    per_path = np.array([moment_distance(m, reference, scales) for m in vectors])
    return {
        "seed": seed,
        "mean_moments": vectors.mean(axis=0).tolist(),
        "distance_of_mean": moment_distance(vectors.mean(axis=0), reference, scales),
        "mean_path_distance": float(per_path.mean()),
        "path_distance_sd": float(per_path.std(ddof=1)) if paths > 1 else None,
        "finite_paths": int(np.isfinite(per_path).sum()),
        "paths": paths,
        "days": days,
    }, generated


def study_selection(records, config):
    """Restarts chosen on training; D depth then A lambda on validation only."""
    decisions = {}
    for family in ("quantum", "softmax", "network"):
        forecasts = [r for r in records if r["family"] == family and r["stage"] == "D"]
        winners = []
        for depth in sorted({r["depth"] for r in forecasts}):
            group = [r for r in forecasts if r["depth"] == depth]
            winners.append(min(group, key=lambda r: (r["fit"]["objective"], r["start"])))
        forecast = min(winners, key=lambda r: (r["validation"]["log_loss"], r["depth"]))
        candidates = [forecast]
        for weight in config.lambdas:
            if weight == 0:
                continue
            group = [
                r
                for r in records
                if r["family"] == family and r["stage"] == "A" and r["lambda"] == weight
            ]
            if group:
                candidates.append(min(group, key=lambda r: (r["fit"]["objective"], r["start"])))
        selected = min(candidates, key=lambda r: (r["selection_score"], r["lambda"]))
        decisions[family] = {
            "forecast_id": forecast["id"],
            "selected_id": selected["id"],
            "depth": forecast["depth"],
            "lambda": selected["lambda"],
            "depth_winners": [r["id"] for r in winners],
            "lambda_winners": [r["id"] for r in candidates],
            "forecast_training_adequate": all(r["fit"]["eligible"] for r in winners),
        }
    return decisions


def run_distribution_study(data, config, output, source=None, progress=print):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    scales, reference = moment_scales(data.y[data.train]), moments(data.y[data.validation])
    train_reference = moments(data.y[data.train])
    manifest = {
        "status": "running",
        "config": asdict(config),
        "data": data.metadata(),
        "source": source,
        "code": code_revision(),
        "python": platform.python_version(),
        "numpy": version("numpy"),
        "scipy": version("scipy"),
        "feature_policy": "previous-day log RV and return only; HAR reference separate",
        "moment_scales": scales.tolist(),
        "train_moments": train_reference.tolist(),
        "validation_moments": reference.tolist(),
        "test_scored": False,
    }
    write_json(output / "manifest.json", manifest)
    records = []

    def save_record(model, row, p):
        probs = model.probabilities(data.x[data.validation], p)
        row["validation"] = forecast_scores(probs, data.labels[data.validation])
        summary, paths = path_summary(
            model,
            p,
            data,
            config.selection_days,
            config.selection_paths,
            20000,
            config.burn_in,
            reference,
            scales,
        )
        row["selection_paths"] = summary
        row["selection_score"] = row["validation"]["log_loss"] + (
            config.selection_weight * summary["distance_of_mean"]
        )
        np.savez_compressed(
            output / f"{row['id']}.npz",
            parameters=np.array([]) if p is None else p,
            train_probabilities=model.probabilities(data.x[data.train], p),
            validation_probabilities=probs,
            selection_log_rv=paths.log_rv,
            selection_returns=paths.returns,
            selection_levels=paths.levels,
        )
        records.append(row)
        write_json(output / "records.json", records)
        progress(f"{row['id']}: validation NLL={row['validation']['log_loss']:.6f}", flush=True)

    for family in ("quantum", "softmax", "network"):
        for depth in config.depths if family == "quantum" else [0]:
            model = distribution_model(family, depth)
            for start in config.starts:
                fit = fit_forecast(model, data, start, config)
                save_record(
                    model,
                    {
                        "id": f"{family}-d{depth}-D-s{start}",
                        "family": family,
                        "depth": depth,
                        "stage": "D",
                        "lambda": 0,
                        "start": start,
                        "fit": fit,
                    },
                    np.array(fit["parameters"]),
                )
    decisions = study_selection(records, config)
    write_json(output / "forecast-selection.json", decisions)
    # Freeze depth before A: lambda tuning cannot change D's circuit depth.
    for family, decision in decisions.items():
        base = next(r for r in records if r["id"] == decision["forecast_id"])
        depth, initial = base["depth"], np.array(base["fit"]["parameters"])
        model = distribution_model(family, depth)
        for weight in config.lambdas:
            if weight == 0:
                continue

            def objective(p, model=model, weight=weight):
                nll = log_loss(model.probabilities(data.x[data.train], p), data.labels[data.train])
                summary, _ = path_summary(
                    model,
                    p,
                    data,
                    config.train_days,
                    config.train_paths,
                    10000,
                    config.burn_in,
                    train_reference,
                    scales,
                )
                return nll + weight * summary["distance_of_mean"]

            for start in range(config.realism_starts):
                p0 = initial.copy()
                if start:
                    p0 += np.random.default_rng(start).normal(0, 0.03, len(initial))
                fit = optimize(objective, p0, config.realism_max_calls, config.realism_tolerance)
                record = fit.record()
                record.update(
                    {
                        "initial_parameters": p0.tolist(),
                        "diagnostic_calls": 0,
                        "method": "COBYLA, fixed-stream discrete simulation",
                        "warm_start_id": base["id"],
                    }
                )
                save_record(
                    model,
                    {
                        "id": f"{family}-d{depth}-A-l{weight}-s{start}",
                        "family": family,
                        "depth": depth,
                        "stage": "A",
                        "lambda": weight,
                        "start": start,
                        "fit": record,
                    },
                    fit.parameters,
                )
    decisions = study_selection(records, config)
    controls = {
        "frequency": FrequencyModel.fit(data.labels[data.train]),
        "short-ar": ShortAR.fit(data.x[data.train], data.y[data.train], data.bins.edges),
        "har-reference": HARModel.fit(data.x[data.train], data.y[data.train], data.bins.edges),
    }
    for family, model in controls.items():
        save_record(
            model,
            {
                "id": family,
                "family": family,
                "stage": "control",
                "lambda": 0,
                "depth": 0,
                "start": 0,
                "information": "HAR" if family == "har-reference" else "short",
            },
            None,
        )
    ids = set(controls)
    for decision in decisions.values():
        ids.update(decision["lambda_winners"])
    audit = []
    for row in records:
        if row["id"] not in ids:
            continue
        model = controls.get(row["family"])
        if model is None:
            model = distribution_model(row["family"], row["depth"])
        p = np.array(row["fit"]["parameters"]) if "fit" in row else None
        for seed in (30000, 40000):
            summary, paths = path_summary(
                model,
                p,
                data,
                config.audit_days,
                config.audit_paths,
                seed,
                config.burn_in,
                reference,
                scales,
            )
            audit.append({"id": row["id"], **summary})
            np.savez_compressed(
                output / f"audit-{row['id']}-{seed}.npz",
                log_rv=paths.log_rv,
                returns=paths.returns,
                levels=paths.levels,
            )
    write_json(output / "audit.json", audit)
    write_json(output / "decision.json", decisions)
    manifest.update(
        {
            "status": "complete",
            "record_count": len(records),
            "objective_calls": sum(
                r["fit"]["total_objective_calls"] for r in records if "fit" in r
            ),
            "diagnostic_calls": sum(r["fit"]["diagnostic_calls"] for r in records if "fit" in r),
            "fit_seconds": sum(r["fit"]["seconds"] for r in records if "fit" in r),
        }
    )
    write_json(output / "manifest.json", manifest)
    return decisions
