"""Stages of the fresh-data study. Only `evaluate` ever reads test rows.

1. develop-d   per development seed: forecast (D) fits for every family and depth, scored on
               validation only.
2. select-d    choose circuit depths from mean validation log loss over development seeds.
3. develop-a   per development seed: realism (A) fits at the chosen depths for each lambda.
4. select-a    choose each family's lambda (0 means keep D) on validation selection score.
5. train       per final seed: D and A with frozen choices, plus hybrids; then `seal`.
6. evaluate    check the seal, then score the test period once.
"""

import hashlib
import json
import platform
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
from scipy.stats import wasserstein_distance

from .classical import SoftmaxModel
from .data import sha256
from .experiment import code_revision, write_json
from .final_evaluation import block_indices, numbers
from .final_study import fit_baselines, restore_baseline
from .finance_baselines import garch_variance
from .fresh_models import FAMILIES, FastBorn, Hybrid, make_model
from .fresh_study import (
    fit_lbfgs,
    fit_realism,
    forecast_loss,
    path_moments,
    split_dates,
    window_reference,
)
from .generation import generate
from .metrics import forecast_scores, hill_tail_index, moment_distance, moments

HYBRIDS = ("hybrid-quantum", "hybrid-softmax")


@dataclass
class FreshConfig:
    development_seeds: list[int] = field(default_factory=lambda: [900, 901])
    final_seeds: list[int] = field(default_factory=lambda: list(range(20)))
    depths: list[int] = field(default_factory=lambda: [1, 2, 3])
    lambdas: list[float] = field(default_factory=lambda: [0.01, 0.05, 0.2, 1.0])
    restarts: int = 5
    network_ridge: float = 0.001
    forecast_max_calls: int = 50000
    forecast_max_iterations: int = 2000
    realism_starts: int = 3
    realism_max_calls: int = 600
    realism_tolerance: float = 0.002
    train_days: int = 256
    train_paths: int = 4
    burn_in: int = 60
    selection_paths: int = 8
    selection_weight: float = 0.01
    evaluation_paths: int = 32
    evaluation_burn_in: int = 100
    bootstrap_replicates: int = 2000
    bootstrap_blocks: list[int] = field(default_factory=lambda: [7, 30])

    def realism(self):
        return {
            "train_days": self.train_days,
            "train_paths": self.train_paths,
            "burn_in": self.burn_in,
            "realism_starts": self.realism_starts,
            "realism_max_calls": self.realism_max_calls,
            "realism_tolerance": self.realism_tolerance,
        }


def ridge_for(family, config):
    return config.network_ridge if family.startswith("network") else 0.0


def hybrid_model(name, depth, base):
    expert = FastBorn(depth) if name == "hybrid-quantum" else SoftmaxModel()
    return Hybrid(base, expert)


def model_for(name, depth, base=None):
    return hybrid_model(name, depth, base) if name in HYBRIDS else make_model(name, depth)


def fit_forecast_restarts(name, depth, data, config, seed, base=None, base_train=None):
    model = model_for(name, depth, base)
    ridge = ridge_for(name, config)
    loss = forecast_loss(model, data, ridge, base_train)
    fits = []
    for restart in range(config.restarts):
        init_seed = 100000 + 100 * seed + 10 * depth + restart
        initial = None
        if name in HYBRIDS:
            initial = np.r_[
                0.0, np.random.default_rng(init_seed).normal(0, 0.3, model.n_params - 1)
            ]
        fit = fit_lbfgs(
            loss,
            model.n_params,
            init_seed,
            config.forecast_max_calls,
            config.forecast_max_iterations,
            initial,
        )
        fit.update({"restart": restart, "initialization_seed": init_seed})
        fits.append(fit)
    best = min(fits, key=lambda f: (f["objective"], f["restart"]))
    return model, best, fits


def selection_summary(model, parameters, data, config, seed):
    """Validation-only scores used for selection: forecast and same-length realism."""
    y = data.y[data.validation]
    probabilities = model.probabilities(data.x[data.validation], parameters)
    scores = forecast_scores(probabilities, data.labels[data.validation])
    scores.pop("extreme_calibration")
    _, scales = window_reference(data.y[data.train], len(y), count=12)
    m, _ = path_moments(model, parameters, data, len(y), config.selection_paths, 700000 + seed, 100)
    distance = moment_distance(m, moments(y), scales)
    return {
        "validation": scores,
        "validation_path_moments": m.tolist(),
        "validation_moment_distance": distance,
        "selection_score": scores["log_loss"] + config.selection_weight * distance,
    }


def baseline_bundle(data):
    bundle = fit_baselines(data)
    models = {r["id"]: restore_baseline(r) for r in bundle["models"]}
    return bundle, models


def develop_d(data, config, seed, output, progress=print, names=None, prefix="develop-d"):
    _, base_models = baseline_bundle(data)
    base = base_models["har-quantile"]
    base_train = base.probabilities(data.x[data.train])
    rows = []
    for name in names or FAMILIES + HYBRIDS:
        quantum = name.startswith("quantum") or name == "hybrid-quantum"
        for depth in config.depths if quantum else [0]:
            model, best, fits = fit_forecast_restarts(
                name, depth, data, config, seed, base, base_train if name in HYBRIDS else None
            )
            p = np.array(best["parameters"])
            row = {"name": name, "depth": depth, "seed": seed, "fit": best, "fits": fits}
            if name in HYBRIDS:
                probabilities = model.probabilities(data.x[data.validation], p)
                scores = forecast_scores(probabilities, data.labels[data.validation])
                scores.pop("extreme_calibration")
                row["validation"] = scores
            else:
                row.update(selection_summary(model, p, data, config, seed))
            rows.append(row)
            progress(
                f"dev-D seed {seed} {name} depth {depth}: train {best['objective']:.4f} "
                f"val {row['validation']['log_loss']:.4f} ok={best['eligible']}",
                flush=True,
            )
    write_json(Path(output) / f"{prefix}-seed{seed}.json", {"seed": seed, "rows": rows})


def select_d(config, output):
    rows = []
    for s in config.development_seeds:
        rows += json.loads((Path(output) / f"develop-d-seed{s}.json").read_text())["rows"]
        amended = Path(output) / f"develop-h-seed{s}.json"
        if amended.is_file():
            # Protocol amendment: hybrids re-developed with the bounded correction.
            rows = [r for r in rows if not (r["name"] in HYBRIDS and r["seed"] == s)]
            rows += json.loads(amended.read_text())["rows"]
    decisions = {}
    for name in FAMILIES + HYBRIDS:
        group = [r for r in rows if r["name"] == name]
        by_depth = {}
        for r in group:
            by_depth.setdefault(r["depth"], []).append(r["validation"]["log_loss"])
        means = {d: float(np.mean(v)) for d, v in by_depth.items()}
        depth = min(means, key=lambda d: (means[d], d))
        decisions[name] = {"depth": depth, "mean_validation_log_loss_by_depth": means}
    write_json(Path(output) / "select-d.json", decisions)
    return decisions


def develop_a(data, config, seed, output, progress=print):
    decisions = json.loads((Path(output) / "select-d.json").read_text())
    d_rows = json.loads((Path(output) / f"develop-d-seed{seed}.json").read_text())["rows"]
    reference, scales = window_reference(data.y[data.train], config.train_days)
    rows = []
    for name in FAMILIES:
        depth = decisions[name]["depth"]
        d = next(r for r in d_rows if r["name"] == name and r["depth"] == depth)
        model = make_model(name, depth)
        for weight in config.lambdas:
            best, fits = fit_realism(
                model,
                data,
                d["fit"]["parameters"],
                weight,
                reference,
                scales,
                config.realism(),
                seed,
                ridge_for(name, config),
            )
            row = {
                "name": name,
                "depth": depth,
                "lambda": weight,
                "seed": seed,
                "fit": best,
                "fits": fits,
            }
            row.update(selection_summary(model, np.array(best["parameters"]), data, config, seed))
            rows.append(row)
            progress(
                f"dev-A seed {seed} {name} lambda {weight}: val {row['validation']['log_loss']:.4f}"
                f" dist {row['validation_moment_distance']:.2f} score {row['selection_score']:.4f}",
                flush=True,
            )
    write_json(Path(output) / f"develop-a-seed{seed}.json", {"seed": seed, "rows": rows})


def select_a(config, output):
    out = Path(output)
    decisions = json.loads((out / "select-d.json").read_text())
    d_rows, a_rows = [], []
    for s in config.development_seeds:
        d_rows += json.loads((out / f"develop-d-seed{s}.json").read_text())["rows"]
        a_rows += json.loads((out / f"develop-a-seed{s}.json").read_text())["rows"]
    for name in FAMILIES:
        depth = decisions[name]["depth"]
        scores = {
            0.0: [r["selection_score"] for r in d_rows if r["name"] == name and r["depth"] == depth]
        }
        for r in a_rows:
            if r["name"] == name:
                scores.setdefault(r["lambda"], []).append(r["selection_score"])
        means = {float(k): float(np.mean(v)) for k, v in scores.items()}
        nonzero = {k: v for k, v in means.items() if k > 0}
        decisions[name]["mean_selection_score_by_lambda"] = means
        # Overall choice (0 = validation prefers plain D) and the best nonzero weight, which
        # is always trained so the A-versus-D test comparison exists either way.
        decisions[name]["lambda"] = min(means, key=lambda k: (means[k], k))
        decisions[name]["lambda_A"] = min(nonzero, key=lambda k: (nonzero[k], k))
    write_json(out / "select-a.json", decisions)
    return decisions


def train_seed(data, config, seed, output, progress=print):
    out = Path(output)
    decisions = json.loads((out / "select-a.json").read_text())
    _, base_models = baseline_bundle(data)
    base = base_models["har-quantile"]
    base_train = base.probabilities(data.x[data.train])
    reference, scales = window_reference(data.y[data.train], config.train_days)
    result = {"seed": seed, "models": {}}
    for name in FAMILIES + HYBRIDS:
        depth = decisions[name]["depth"]
        model, best, fits = fit_forecast_restarts(
            name, depth, data, config, seed, base, base_train if name in HYBRIDS else None
        )
        entry = {"depth": depth, "D": best, "D_fits": fits}
        if name in FAMILIES:
            entry["lambda_selected"] = decisions[name]["lambda"]
            entry["lambda_A"] = decisions[name]["lambda_A"]
            a_best, a_fits = fit_realism(
                model,
                data,
                best["parameters"],
                entry["lambda_A"],
                reference,
                scales,
                config.realism(),
                seed,
                ridge_for(name, config),
            )
            entry["A"], entry["A_fits"] = a_best, a_fits
        result["models"][name] = entry
        progress(f"train seed {seed} {name}: D ok={best['eligible']}", flush=True)
    write_json(out / f"train-seed{seed}.json", result)


def data_fingerprint(data):
    digest = hashlib.sha256()
    for values in (data.daily.returns, data.daily.rv):
        digest.update(np.asarray(values, dtype="<f8").tobytes())
    return digest.hexdigest()


def write_manifest(data, config, output, source):
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    write_json(
        out / "manifest.json",
        {
            "config": asdict(config),
            "splits": split_dates(data),
            "data_fingerprint": data_fingerprint(data),
            "source": source,
            "code": code_revision(),
            "python": platform.python_version(),
            "test_scores_computed": False,
        },
    )
    bundle, _ = baseline_bundle(data)
    write_json(out / "baselines.json", bundle)


def seal(config, output):
    out = Path(output)
    names = ["manifest.json", "baselines.json", "select-d.json", "select-a.json"]
    names += [f"develop-d-seed{s}.json" for s in config.development_seeds]
    names += [f"develop-a-seed{s}.json" for s in config.development_seeds]
    names += [
        f"develop-h-seed{s}.json"
        for s in config.development_seeds
        if (out / f"develop-h-seed{s}.json").is_file()
    ]
    names += [f"train-seed{s}.json" for s in config.final_seeds]
    missing = [n for n in names if not (out / n).is_file()]
    if missing:
        raise ValueError(f"Cannot seal, missing {missing}")
    record = {
        "artifacts": {n: sha256(out / n) for n in names},
        "code": code_revision(),
        "training_complete": True,
        "test_scores_computed": False,
    }
    write_json(out / "seal.json", record)
    return record


def check_seal(data, output):
    out = Path(output)
    record = json.loads((out / "seal.json").read_text())
    manifest = json.loads((out / "manifest.json").read_text())
    if manifest["data_fingerprint"] != data_fingerprint(data):
        raise ValueError("Data changed after sealing")
    if record["code"]["package_source_sha256"] != code_revision()["package_source_sha256"]:
        raise ValueError("Package source changed after sealing")
    for name, digest in record["artifacts"].items():
        if sha256(out / name) != digest:
            raise ValueError(f"Artifact changed after sealing: {name}")
    return manifest


CONTRASTS = (
    ("quantum-har-A", "quantum-har-D"),
    ("quantum-har-D", "quantum-short-D"),
    ("quantum-har-A", "quantum-short-A"),
    ("softmax-har-A", "softmax-har-D"),
    ("network-har-A", "network-har-D"),
    ("quantum-har-D", "softmax-har-D"),
    ("quantum-har-D", "network-har-D"),
    ("quantum-har-D", "har-quantile"),
    ("quantum-har-A", "softmax-har-A"),
    ("quantum-har-A", "network-har-A"),
    ("hybrid-quantum", "har-quantile"),
    ("hybrid-softmax", "har-quantile"),
    ("hybrid-quantum", "hybrid-softmax"),
)


def paired_intervals(losses, blocks, replicates, seed=600000):
    """Seed-averaged daily losses, paired circular block bootstrap over test dates."""
    means = {k: np.asarray(v).mean(axis=0) for k, v in losses.items()}
    rng = np.random.default_rng(seed)
    rows = []
    for block in blocks:
        indices = block_indices(len(next(iter(means.values()))), block, replicates, rng)
        for left, right in CONTRASTS:
            if left in means and right in means:
                delta = means[left] - means[right]
                boot = delta[indices].mean(axis=1)
                rows.append(
                    {
                        "left": left,
                        "right": right,
                        "block": block,
                        "mean_difference": float(delta.mean()),
                        "lower": float(np.quantile(boot, 0.025)),
                        "upper": float(np.quantile(boot, 0.975)),
                    }
                )
    return rows


def garch_test_paths(model, data, days, paths, seed, burn_in):
    """Shared categorical/empirical-bin observation law driven by the GARCH variance."""
    rng = np.random.default_rng(seed)
    horizon = days + burn_in
    level_u, within_u = rng.random((horizon, paths)), rng.random((horizon, paths))
    innovation = rng.normal(size=(horizon, paths))
    rows = data.target_rows[: data.train.stop + 1]
    filtered = garch_variance(
        data.daily.returns[rows] / model.return_scale, model.parameters, model.backcast
    )
    h = np.full(paths, filtered[-1])
    y, r = np.empty((paths, horizon)), np.empty((paths, horizon))
    omega, alpha, beta = model.parameters
    for t in range(horizon):
        p = model.probabilities_from_variance(h)
        k = np.minimum((level_u[t, :, None] >= p.cumsum(axis=1)).sum(axis=1), 3)
        for level, pool in enumerate(data.bins.pools):
            mask = k == level
            y[mask, t] = pool[
                np.minimum((within_u[t, mask] * len(pool)).astype(int), len(pool) - 1)
            ]
        r[:, t] = np.exp(y[:, t] / 2) * innovation[t]
        h = omega + alpha * (r[:, t] / model.return_scale) ** 2 + beta * h
    return y[:, burn_in:], r[:, burn_in:]


def path_record(log_rv, returns, test_y, test_scales, train_reference, train_scales, edges):
    vectors = np.array([moments(y) for y in log_rv])
    mean = vectors.mean(axis=0)
    levels = np.searchsorted(edges, log_rv, side="right")
    return {
        "mean_moments": mean.tolist(),
        "test_moment_distance": moment_distance(mean, moments(test_y), test_scales),
        "train_window_moment_distance": moment_distance(mean, train_reference, train_scales),
        "extreme_share": float(np.mean(levels == 3)),
        "wasserstein_log_rv": numbers([wasserstein_distance(y, test_y) for y in log_rv]),
        "hill_tail_index": numbers([hill_tail_index(r) for r in returns]),
    }


def evaluate(data, config, output, progress=print):
    out = Path(output)
    check_seal(data, out)
    destination = out / "evaluation"
    destination.mkdir(exist_ok=False)
    decisions = json.loads((out / "select-a.json").read_text())
    bundle = json.loads((out / "baselines.json").read_text())
    baselines = {r["id"]: restore_baseline(r) for r in bundle["models"]}
    test = data.test
    x, labels, test_y = data.x[test], data.labels[test], data.y[test]
    days = len(test_y)
    # Same-length training windows give the spread scales and the training-period target.
    train_reference, train_scales = window_reference(data.y[data.train], days, count=12)
    test_scales = train_scales
    garch = baselines["garch-calibrated"]
    variance = garch_variance(
        data.daily.returns[data.target_rows] / garch.return_scale, garch.parameters, garch.backcast
    )
    base = baselines["har-quantile"]
    records, path_rows, losses = [], [], {}
    for seed in config.final_seeds:
        trained = json.loads((out / f"train-seed{seed}.json").read_text())["models"]
        candidates = {k: (m, None, True) for k, m in baselines.items()}
        for name, entry in trained.items():
            model = model_for(name, entry["depth"], base)
            candidates[name if name in HYBRIDS else f"{name}-D"] = (
                model,
                np.array(entry["D"]["parameters"]),
                entry["D"]["eligible"],
            )
            if "A" in entry:
                candidates[f"{name}-A"] = (
                    model,
                    np.array(entry["A"]["parameters"]),
                    entry["A"]["eligible"],
                )
        for id_, (model, p, ok) in candidates.items():
            if id_ == "garch-calibrated":
                probabilities = model.probabilities_from_variance(variance[test])
            else:
                probabilities = model.probabilities(x, p)
            daily = -np.log(np.clip(probabilities[np.arange(len(labels)), labels], 1e-12, 1))
            losses.setdefault(id_, []).append(daily)
            records.append(
                {
                    "id": id_,
                    "seed": seed,
                    "fit_eligible": bool(ok),
                    "scores": forecast_scores(probabilities, labels),
                }
            )
            sim_seed = 500000 + seed
            if id_ == "garch-calibrated":
                y, r = garch_test_paths(
                    model, data, days, config.evaluation_paths, sim_seed, config.evaluation_burn_in
                )
            else:
                paths = generate(
                    model,
                    p,
                    data,
                    days,
                    config.evaluation_paths,
                    sim_seed,
                    config.evaluation_burn_in,
                )
                y, r = paths.log_rv, paths.returns
            row = path_record(
                y, r, test_y, test_scales, train_reference, train_scales, data.bins.edges
            )
            row.update({"id": id_, "seed": seed})
            path_rows.append(row)
        progress(f"evaluated seed {seed}", flush=True)
    summary = {}
    for id_ in losses:
        rs = [r for r in records if r["id"] == id_]
        ps = [r for r in path_rows if r["id"] == id_]
        summary[id_] = {
            "log_loss": numbers([r["scores"]["log_loss"] for r in rs]),
            "rps_normalized": numbers([r["scores"]["rps_normalized"] for r in rs]),
            "extreme_brier": numbers([r["scores"]["extreme_brier"] for r in rs]),
            "fits_eligible": int(sum(r["fit_eligible"] for r in rs)),
            "test_moment_distance": numbers([p["test_moment_distance"] for p in ps]),
            "train_window_moment_distance": numbers(
                [p["train_window_moment_distance"] for p in ps]
            ),
            "mean_moments": np.mean([p["mean_moments"] for p in ps], axis=0).tolist(),
            "extreme_share": numbers([p["extreme_share"] for p in ps]),
            "wasserstein_log_rv": numbers([p["wasserstein_log_rv"]["mean"] for p in ps]),
            "hill_tail_index": numbers([p["hill_tail_index"]["mean"] for p in ps]),
        }
    result = {
        "splits": split_dates(data),
        "test_moments": moments(test_y).tolist(),
        "train_window_reference": train_reference.tolist(),
        "test_level_counts": np.bincount(labels, minlength=4).tolist(),
        "decisions": decisions,
        "summary": summary,
        "intervals": paired_intervals(losses, config.bootstrap_blocks, config.bootstrap_replicates),
    }
    write_json(destination / "records.json", {"forecast": records, "paths": path_rows})
    write_json(destination / "results.json", result)
    np.savez_compressed(
        destination / "daily-losses.npz", **{k: np.asarray(v) for k, v in losses.items()}
    )
    return result
