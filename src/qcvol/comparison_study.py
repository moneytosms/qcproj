"""Step 4 classical forecasts, capped-network continuation and explicit effort ledger."""

import json
import os
import time
from dataclasses import asdict, dataclass, field
from importlib.metadata import version
from pathlib import Path

import numpy as np

from .classical import FrequencyModel, HARModel
from .classical_training import continue_network, sensitivity_rank
from .data import sha256
from .distribution_models import ShortAR, ShortNetwork, distribution_model
from .distribution_study import path_summary, study_selection
from .experiment import code_revision, write_json
from .finance_baselines import (
    CalibratedGARCH,
    QuantileHAR,
    empirical_bin_quantiles,
    quantile_scores,
)
from .generation import Paths
from .metrics import forecast_scores, log_loss, moment_distance, moment_scales, moments
from .training import optimize


@dataclass
class ComparisonConfig:
    ridge_penalties: list[float] = field(default_factory=lambda: [0.0001, 0.001, 0.01, 0.1])
    network_max_calls: int = 20000
    network_max_iterations: int = 10000
    garch_max_iterations: int = 5000
    audit_days: int = 512
    audit_paths: int = 32
    burn_in: int = 60

    def __post_init__(self):
        if (
            not self.ridge_penalties
            or len(set(self.ridge_penalties)) != len(self.ridge_penalties)
            or any(not np.isfinite(a) or a <= 0 for a in self.ridge_penalties)
        ):
            raise ValueError("Need distinct positive finite ridge penalties")
        for name, value in asdict(self).items():
            if name == "ridge_penalties":
                continue
            if type(value) is not int or value < (0 if name == "burn_in" else 1):
                raise ValueError(f"{name} must be a valid integer")
        if self.audit_days < 64:
            raise ValueError("Need at least 64 audit days")


def load_prior(root, data):
    root = Path(root)
    manifest = json.loads((root / "manifest.json").read_text())
    if manifest["status"] != "complete" or manifest["data"] != data.metadata():
        raise ValueError("Need complete matching prior data and split")
    current = code_revision()["package_source_sha256"]
    if any(
        current.get(name) != digest
        for name, digest in manifest["code"]["package_source_sha256"].items()
    ):
        raise ValueError("Prior implementation changed: verify at its original source checkpoint")
    records = json.loads((root / "records.json").read_text())
    decisions = json.loads((root / "decision.json").read_text())
    from .distribution_study import DistributionConfig

    if study_selection(records, DistributionConfig(**manifest["config"])) != decisions:
        raise ValueError("Prior selections do not match records")
    return manifest, records, decisions


def garch_paths(model, data, config, seed, native=False):
    days, paths, burn = config.audit_days, config.audit_paths, config.burn_in
    rng = np.random.default_rng(seed)
    horizon = days + burn
    level_u = rng.random((horizon, paths))
    within_u = rng.random((horizon, paths))
    innovation = rng.normal(size=(horizon, paths))
    filtered = model.filter(data)
    h = np.full(paths, filtered[data.train.stop])  # first validation variance, past returns only
    y = np.empty((paths, horizon))
    r = np.empty_like(y)
    levels = np.empty((paths, horizon), int)
    omega, alpha, beta = model.parameters
    for t in range(horizon):
        if native:
            residual = model.residuals[
                np.minimum(
                    (within_u[t] * len(model.residuals)).astype(int), len(model.residuals) - 1
                )
            ]
            y[:, t] = model.mean_log_rv(h) + residual
            r[:, t] = model.return_scale * np.sqrt(h) * innovation[t]
            levels[:, t] = data.bins.label(y[:, t])
        else:
            p = model.probabilities_from_variance(h)
            k = np.minimum((level_u[t, :, None] >= p.cumsum(axis=1)).sum(axis=1), 3)
            levels[:, t] = k
            for level, pool in enumerate(data.bins.pools):
                mask = k == level
                indices = np.minimum((within_u[t, mask] * len(pool)).astype(int), len(pool) - 1)
                y[mask, t] = pool[indices]
            r[:, t] = np.exp(y[:, t] / 2) * innovation[t]
        h = omega + alpha * (r[:, t] / model.return_scale) ** 2 + beta * h
        if not np.all(np.isfinite(h)) or np.any(h <= 0):
            raise ValueError("GARCH simulation became invalid")
    return Paths(y[:, burn:], r[:, burn:], levels[:, burn:])


def summarize_paths(paths, reference, scales, seed):
    vectors = np.array([moments(y) for y in paths.log_rv])
    distances = np.array([moment_distance(v, reference, scales) for v in vectors])
    return {
        "seed": seed,
        "mean_moments": vectors.mean(axis=0).tolist(),
        "distance_of_mean": moment_distance(vectors.mean(axis=0), reference, scales),
        "mean_path_distance": float(distances.mean()),
        "path_distance_sd": float(distances.std(ddof=1)) if len(distances) > 1 else None,
        "finite_paths": int(np.isfinite(distances).sum()),
        "paths": len(distances),
        "days": paths.log_rv.shape[1],
    }


def run_comparison(data, prior, output, config, source, progress=print):
    prior = Path(prior)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    old_manifest, old_records, old_decision = load_prior(prior, data)
    scales = moment_scales(data.y[data.train])
    reference = moments(data.y[data.validation])
    manifest = {
        "status": "running",
        "config": asdict(config),
        "data": data.metadata(),
        "source": source,
        "code": code_revision(),
        "versions": {name: version(name) for name in ("numpy", "scipy", "arch")},
        "thread_environment": {
            name: os.environ.get(name)
            for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")
        },
        "prior_manifest_sha256": sha256(prior / "manifest.json"),
        "prior_records_sha256": sha256(prior / "records.json"),
        "prior_directory": str(prior.resolve()),
        "prior_import_sha256": {},
        "test_scored": False,
        "moment_scales": scales.tolist(),
        "validation_moments": reference.tolist(),
    }
    write_json(output / "manifest.json", manifest)
    records = []
    models = {}
    audit = []
    continuations = []

    def save(row, model=None, p=None, probabilities=None, native_quantiles=None):
        if probabilities is None:
            probabilities = model.probabilities(data.x[data.validation], p)
        common = empirical_bin_quantiles(probabilities, data.bins.pools)
        row["validation"] = forecast_scores(probabilities, data.labels[data.validation])
        row["common_quantile_scores"] = quantile_scores(common, data.y[data.validation])
        if native_quantiles is not None:
            row["native_quantile_scores"] = quantile_scores(
                native_quantiles, data.y[data.validation]
            )
        np.savez_compressed(
            output / f"{row['id']}.npz",
            parameters=np.array([]) if p is None else p,
            validation_probabilities=probabilities,
            common_quantiles=common,
            native_quantiles=np.array([]) if native_quantiles is None else native_quantiles,
        )
        records.append(row)
        models[row["id"]] = (model, p)
        write_json(output / "records.json", records)
        progress(f"{row['id']}: NLL={row['validation']['log_loss']:.6f}", flush=True)

    # Import predictions by recomputing saved parameters, not copying reported scores.
    for family, selection in old_decision.items():
        for stage, key in (("D", "forecast_id"), ("A", "selected_id")):
            old = next(r for r in old_records if r["id"] == selection[key])
            model = distribution_model(family, old["depth"])
            p = np.array(old["fit"]["parameters"])
            path = prior / f"{old['id']}.npz"
            with np.load(path) as saved:
                np.testing.assert_allclose(
                    saved["validation_probabilities"],
                    model.probabilities(data.x[data.validation], p),
                    atol=1e-13,
                )
            manifest["prior_import_sha256"][path.name] = sha256(path)
            save(
                {
                    "id": f"{family}-prior-{stage}",
                    "family": family,
                    "origin": "prior",
                    "prior_id": old["id"],
                    "stored_coordinates": 8 * old["depth"]
                    if family == "quantum"
                    else model.n_params,
                    "removed_coordinates": 2 if family == "quantum" else 0,
                    "searched_coordinates": model.n_params,
                    "sensitivity": sensitivity_rank(model, p, data.x[data.train]),
                },
                model,
                p,
            )
    for family, factory in {
        "frequency": lambda: FrequencyModel.fit(data.labels[data.train]),
        "short-ar": lambda: ShortAR.fit(data.x[data.train], data.y[data.train], data.bins.edges),
        "har-residual": lambda: HARModel.fit(
            data.x[data.train], data.y[data.train], data.bins.edges
        ),
    }.items():
        started = time.perf_counter()
        model = factory()
        seconds = time.perf_counter() - started
        save(
            {
                "id": family,
                "family": family,
                "origin": "new-closed-form",
                "searched_coordinates": model.n_params,
                "fit_seconds": seconds,
                "linear_solves": int(family != "frequency"),
                "empirical_residual_count": len(model.residuals)
                if hasattr(model, "residuals")
                else 0,
            },
            model,
        )
    for short in (False, True):
        model, fit = QuantileHAR.fit(
            data.x[data.train], data.y[data.train], data.bins.edges, short=short
        )
        id_ = "short-quantile" if short else "har-quantile"
        raw = model.raw_quantiles(data.x[data.validation])
        save(
            {
                "id": id_,
                "family": id_,
                "origin": "new",
                "fit": fit,
                "coefficients": model.coefficients.tolist(),
                "quantiles": model.quantiles.tolist(),
                "tail_floor": model.tail_floor,
                "raw_crossing_rows": int(np.sum(np.any(np.diff(raw, axis=1) < 0, axis=1))),
                "searched_coordinates": model.n_params,
            },
            model,
            native_quantiles=model.predict_quantiles(data.x[data.validation]),
        )
    garch, garch_fit = CalibratedGARCH.fit(data, config.garch_max_iterations)
    h = garch.filter(data)[data.validation]
    save(
        {
            "id": "garch-calibrated",
            "family": "garch",
            "origin": "new",
            "fit": garch_fit,
            "garch_parameters": garch.parameters.tolist(),
            "return_scale": garch.return_scale,
            "backcast": garch.backcast,
            "calibration": garch.calibration.tolist(),
            "residuals": garch.residuals.tolist(),
            "searched_coordinates": 5,
        },
        probabilities=garch.probabilities_from_variance(h),
        native_quantiles=garch.predict_quantiles(h),
    )
    np.savez_compressed(output / "garch-state.npz", variance=garch.filter(data))
    # Every old start gets the same extra allowance; include inherited costs below.
    for old in [r for r in old_records if r["family"] == "network" and r["stage"] == "D"]:
        fit = continue_network(
            old["fit"]["parameters"], data, config.network_max_calls, config.network_max_iterations
        )
        fit.update({"start": old["start"], "prior_id": old["id"]})
        continuations.append(fit)
        write_json(output / "network-continuations.json", continuations)
        progress(
            f"network continuation {old['start']}: success={fit['eligible']}, train={fit['objective']:.6f}",
            flush=True,
        )
    winner = min(continuations, key=lambda f: (f["objective"], f["start"]))
    model = ShortNetwork()
    base = np.array(winner["parameters"])
    save(
        {
            "id": "network-continued-D",
            "family": "network",
            "origin": "continued",
            "fit": winner,
            "searched_coordinates": 24,
            "sensitivity": sensitivity_rank(model, base, data.x[data.train]),
        },
        model,
        base,
    )
    ridge_fits = []
    ridge_winners = [
        {
            "fit": winner,
            "ridge": 0.0,
            "start": winner["start"],
            "validation_nll": log_loss(
                model.probabilities(data.x[data.validation], base), data.labels[data.validation]
            ),
        }
    ]
    for ridge in config.ridge_penalties:
        group = []
        for start in old_manifest["config"]["starts"]:
            initial = np.random.default_rng(start).normal(0, 0.3, model.n_params)
            fit = continue_network(
                initial, data, config.network_max_calls, config.network_max_iterations, ridge
            )
            fit.update({"start": start})
            row = {"ridge": ridge, "start": start, "fit": fit}
            group.append(row)
            ridge_fits.append(row)
            write_json(output / "network-ridge-fits.json", ridge_fits)
        best = min(group, key=lambda r: (r["fit"]["objective"], r["start"]))
        best = dict(best)
        best["validation_nll"] = log_loss(
            model.probabilities(data.x[data.validation], np.array(best["fit"]["parameters"])),
            data.labels[data.validation],
        )
        ridge_winners.append(best)
    ridge_selection = min(ridge_winners, key=lambda r: (r["validation_nll"], r["ridge"]))
    winner = ridge_selection["fit"]
    ridge = ridge_selection["ridge"]
    base = np.array(winner["parameters"])
    write_json(
        output / "network-ridge-selection.json",
        {"ridge": ridge, "start": winner["start"], "winners": ridge_winners},
    )
    save(
        {
            "id": "network-refined-D",
            "family": "network",
            "origin": "ridge-selected",
            "fit": winner,
            "ridge": ridge,
            "searched_coordinates": 24,
            "sensitivity": sensitivity_rank(model, base, data.x[data.train]),
        },
        model,
        base,
    )
    # Refresh A; old network A was trained from a different D fit.
    candidates = []
    prior_config = old_manifest["config"]

    def validation_candidate(id_, p, weight, start, fit):
        summary, _ = path_summary(
            model,
            p,
            data,
            prior_config["selection_days"],
            prior_config["selection_paths"],
            20000,
            prior_config["burn_in"],
            reference,
            scales,
        )
        nll = log_loss(
            model.probabilities(data.x[data.validation], p), data.labels[data.validation]
        )
        return {
            "id": id_,
            "lambda": weight,
            "start": start,
            "parameters": p.tolist(),
            "fit": fit,
            "validation_nll": nll,
            "selection_paths": summary,
            "selection_score": nll + prior_config["selection_weight"] * summary["distance_of_mean"],
        }

    candidates.append(validation_candidate("network-refined-D", base, 0, winner["start"], winner))
    for weight in prior_config["lambdas"]:
        if weight == 0:
            continue
        for start in range(prior_config["realism_starts"]):
            initial = base.copy()
            if start:
                initial += np.random.default_rng(start).normal(0, 0.03, len(base))

            def objective(p, weight=weight):
                nll = log_loss(model.probabilities(data.x[data.train], p), data.labels[data.train])
                summary, _ = path_summary(
                    model,
                    p,
                    data,
                    prior_config["train_days"],
                    prior_config["train_paths"],
                    10000,
                    prior_config["burn_in"],
                    moments(data.y[data.train]),
                    scales,
                )
                return nll + ridge * float(p @ p) + weight * summary["distance_of_mean"]

            fit = optimize(
                objective,
                initial,
                prior_config["realism_max_calls"],
                prior_config["realism_tolerance"],
            )
            fit_record = fit.record()
            fit_record["initial_parameters"] = initial.tolist()
            candidates.append(
                validation_candidate(
                    f"network-refined-A-l{weight}-s{start}",
                    fit.parameters,
                    weight,
                    start,
                    fit_record,
                )
            )
            write_json(output / "network-candidates.json", candidates)
    winners = [candidates[0]]
    for weight in prior_config["lambdas"]:
        if weight:
            winners.append(
                min(
                    [r for r in candidates if r["lambda"] == weight],
                    key=lambda r: (r["fit"]["objective"], r["start"]),
                )
            )
    selected = min(winners, key=lambda r: (r["selection_score"], r["lambda"]))
    if selected["id"] != "network-refined-D":
        p = np.array(selected["parameters"])
        save(
            {
                "id": "network-refined-A",
                "family": "network",
                "origin": "continued",
                "fit": selected["fit"],
                "candidate_id": selected["id"],
                "lambda": selected["lambda"],
                "searched_coordinates": 24,
                "sensitivity": sensitivity_rank(model, p, data.x[data.train]),
            },
            model,
            p,
        )
    decision = {
        "network_forecast_start": winner["start"],
        "network_ridge": ridge,
        "network_forecast_eligible": winner["eligible"],
        "selected_network_candidate": selected["id"],
        "selected_lambda": selected["lambda"],
        "lambda_winners": [c["id"] for c in winners],
    }
    write_json(output / "decision.json", decision)
    write_json(output / "network-candidates.json", candidates)
    for row in records:
        id_ = row["id"]
        model, p = models[id_]
        for seed in (50000, 60000):
            if id_ == "garch-calibrated":
                paths = garch_paths(garch, data, config, seed)
                summary = summarize_paths(paths, reference, scales, seed)
            else:
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
            audit.append({"id": id_, "law": "common-bin", "summary": summary})
            np.savez_compressed(
                output / f"audit-{id_}-{seed}.npz",
                log_rv=paths.log_rv,
                returns=paths.returns,
                levels=paths.levels,
            )
    for seed in (50000, 60000):
        paths = garch_paths(garch, data, config, seed, native=True)
        audit.append(
            {
                "id": "garch-native-reference",
                "law": "native-garch",
                "summary": summarize_paths(paths, reference, scales, seed),
            }
        )
        np.savez_compressed(
            output / f"audit-garch-native-reference-{seed}.npz",
            log_rv=paths.log_rv,
            returns=paths.returns,
            levels=paths.levels,
        )
    write_json(output / "audit.json", audit)
    manifest.update(
        {
            "status": "complete",
            "record_count": len(records),
            "prior_training_objective_calls": old_manifest["objective_calls"],
            "prior_training_diagnostic_calls": old_manifest["diagnostic_calls"],
            "prior_fit_seconds": old_manifest["fit_seconds"],
            "new_ridge_objective_calls": sum(r["fit"]["objective_calls"] for r in ridge_fits),
            "new_ridge_gradient_evaluations": sum(
                r["fit"]["gradient_evaluations"] for r in ridge_fits
            ),
            "new_ridge_diagnostic_calls": sum(r["fit"]["diagnostic_calls"] for r in ridge_fits),
            "new_ridge_fit_seconds": sum(r["fit"]["seconds"] for r in ridge_fits),
            "new_network_objective_calls": sum(f["objective_calls"] for f in continuations),
            "new_network_gradient_evaluations": sum(
                f["gradient_evaluations"] for f in continuations
            ),
            "new_network_diagnostic_calls": sum(f["diagnostic_calls"] for f in continuations),
            "new_network_fit_seconds": sum(f["seconds"] for f in continuations),
            "new_realism_objective_calls": sum(
                c["fit"]["total_objective_calls"] for c in candidates if c["lambda"]
            ),
            "new_realism_fit_seconds": sum(c["fit"]["seconds"] for c in candidates if c["lambda"]),
        }
    )
    write_json(output / "manifest.json", manifest)
    return decision
