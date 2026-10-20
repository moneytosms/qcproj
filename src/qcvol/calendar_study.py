"""Training and validation for the predeclared calendar/readout improvement study."""

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

from .calendar_models import CalendarReadout, calendar_inputs, recency_weights
from .data import sha256
from .distribution_study import central_gradient
from .experiment import code_revision, write_json
from .fresh_study import split_dates
from .generation import Paths
from .metrics import forecast_scores


@dataclass
class CalendarConfig:
    kind: str = "final"
    development_seeds: list[int] = field(default_factory=lambda: [910, 911])
    final_seeds: list[int] = field(default_factory=lambda: list(range(20)))
    calendars: list[bool] = field(default_factory=lambda: [False, True])
    half_lives: list[int] = field(default_factory=lambda: [0, 730, 365])
    base_ridges: list[float] = field(default_factory=lambda: [0, 0.0001, 0.001])
    depths: list[int] = field(default_factory=lambda: [2, 3])
    feature_ridges: list[float] = field(default_factory=lambda: [0.001, 0.01])
    restarts: int = 3
    max_calls: int = 10000
    max_iterations: int = 5000
    gradient_tolerance: float = 1e-4

    def __post_init__(self):
        if self.kind not in ("final", "integration"):
            raise ValueError("Choose final or integration kind")
        for name in ("development_seeds", "final_seeds", "half_lives", "depths"):
            values = getattr(self, name)
            if not values or len(set(values)) != len(values):
                raise ValueError(f"{name} must be nonempty and distinct")
            if any(type(v) is not int or v < 0 for v in values):
                raise ValueError(f"{name} must contain nonnegative integers")
        if self.kind == "final" and len(self.final_seeds) < 20:
            raise ValueError("Final study requires at least 20 seeds")
        if set(self.development_seeds) & set(self.final_seeds):
            raise ValueError("Development and final seeds must differ")
        if any(d not in (1, 2, 3, 4) for d in self.depths):
            raise ValueError("Choose depths 1..4")
        if not self.calendars or any(type(c) is not bool for c in self.calendars):
            raise ValueError("Calendar policies must be booleans")
        for name in ("base_ridges", "feature_ridges"):
            values = getattr(self, name)
            if not values or any(not np.isfinite(v) or v < 0 for v in values):
                raise ValueError("Finite nonnegative penalties required")
        for name in ("restarts", "max_calls", "max_iterations"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError("Positive integer budgets required")
        if not np.isfinite(self.gradient_tolerance) or self.gradient_tolerance <= 0:
            raise ValueError("Positive finite gradient tolerance required")


def read(path):
    return json.loads(Path(path).read_text())


def fingerprint(data):
    h = hashlib.sha256()
    h.update(np.asarray(data.daily.index, dtype="datetime64[D]").astype("<i8").tobytes())
    for v in (data.daily.returns, data.daily.rv):
        h.update(np.asarray(v, dtype="<f8").tobytes())
    h.update(json.dumps(split_dates(data), sort_keys=True).encode())
    return h.hexdigest()


def initialize(data, config, output):
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    write_json(
        out / "manifest.json",
        {
            "config": asdict(config),
            "data_fingerprint": fingerprint(data),
            "splits": split_dates(data),
            "code": code_revision(),
            "test_status": "exposed benchmark from PR 8; not scored by this run yet",
        },
    )


def check_context(data, output):
    manifest = read(Path(output) / "manifest.json")
    if manifest["data_fingerprint"] != fingerprint(data):
        raise ValueError("Study data or dates changed")
    if manifest["code"]["package_source_sha256"] != code_revision()["package_source_sha256"]:
        raise ValueError("Study package source changed")
    return CalendarConfig(**manifest["config"])


def arrays(data, model, half_life):
    dates = data.daily.index[data.target_rows]
    x = calendar_inputs(data.x, dates, model.calendar)
    weights = recency_weights(dates[data.train], half_life)
    return x, weights, dates


def fit_model(model, data, config, half_life, base_ridge, feature_ridge, seed, initial):
    x, weights, _ = arrays(data, model, half_life)
    train_x, labels = x[data.train], data.labels[data.train]
    objective = lambda p: model.loss_gradient(
        train_x, labels, p, weights, base_ridge, feature_ridge
    )
    started = time.perf_counter()
    result = minimize(
        objective,
        initial,
        jac=True,
        method="L-BFGS-B",
        options={
            "maxfun": config.max_calls,
            "maxiter": config.max_iterations,
            "gtol": 1e-7,
            "ftol": 1e-13,
            "maxls": 40,
        },
    )
    gradient = central_gradient(lambda p: objective(p)[0], result.x)
    return {
        "parameters": result.x.tolist(),
        "initial_parameters": np.asarray(initial).tolist(),
        "seed": seed,
        "objective": float(result.fun),
        "objective_calls": int(result.nfev),
        "diagnostic_calls": 2 * model.n_params,
        "iterations": int(result.nit),
        "seconds": time.perf_counter() - started,
        "success": bool(result.success),
        "message": str(result.message),
        "gradient_inf": float(np.max(np.abs(gradient))),
        "eligible": bool(result.success and np.max(np.abs(gradient)) <= config.gradient_tolerance),
    }


def validation(model, data, parameters):
    x, _, dates = arrays(data, model, 0)
    p = model.probabilities(x[data.validation], parameters)
    labels = data.labels[data.validation]
    years = dates[data.validation].astype("datetime64[Y]").astype(str)
    return {
        "pooled": forecast_scores(p, labels),
        "years": {y: forecast_scores(p[years == y], labels[years == y]) for y in np.unique(years)},
    }


def fit_restarts(kind, depth, data, config, policy, feature_ridge, seed):
    model = CalendarReadout(
        kind, depth if kind.startswith("quantum") else depth + 1, policy["calendar"]
    )
    fits = []
    for restart in range(config.restarts):
        init_seed = 800000 + 100 * seed + restart
        rng = np.random.default_rng(init_seed)
        initial = np.r_[
            policy["fit"]["parameters"],
            rng.normal(0, 0.5, model.feature_count),
            rng.normal(0, 0.03, model.hidden_count * 3),
        ]
        fit = fit_model(
            model,
            data,
            config,
            policy["half_life"],
            policy["ridge"],
            feature_ridge,
            init_seed,
            initial,
        )
        fit["restart"] = restart
        fits.append(fit)
    best = min(fits, key=lambda r: (r["objective"], r["restart"]))
    return {
        "kind": kind,
        "depth": depth,
        "feature_ridge": feature_ridge,
        "seed": seed,
        "model": asdict(model),
        "fit": best,
        "fits": fits,
    }


def develop(data, output, progress=print):
    out = Path(output)
    config = check_context(data, out)
    if (out / "seal.json").exists():
        raise ValueError("Training is sealed")
    destination = out / "development.json"
    records = read(destination) if destination.exists() else {"linear": {}, "nonlinear": {}}
    for cal in config.calendars:
        model = CalendarReadout(calendar=cal)
        for half in config.half_lives:
            for ridge in config.base_ridges:
                key = f"calendar{int(cal)}-half{half}-ridge{ridge}"
                if key in records["linear"]:
                    continue
                fit = fit_model(model, data, config, half, ridge, 0, 0, np.zeros(model.n_params))
                row = {
                    "calendar": cal,
                    "half_life": half,
                    "ridge": ridge,
                    "fit": fit,
                    "validation": validation(model, data, fit["parameters"]),
                }
                records["linear"][key] = row
                write_json(destination, records)
                progress(
                    f"linear {key}: val {row['validation']['pooled']['log_loss']:.6f} "
                    f"ok={fit['eligible']}",
                    flush=True,
                )
    chosen_key = min(
        records["linear"],
        key=lambda k: (records["linear"][k]["validation"]["pooled"]["log_loss"], k),
    )
    policy = records["linear"][chosen_key]
    for kind in ("quantum", "quantum-shared", "tanh", "sine"):
        for depth in config.depths:
            for ridge in config.feature_ridges:
                for seed in config.development_seeds:
                    key = f"{kind}-depth{depth}-ridge{ridge}-seed{seed}"
                    if key in records["nonlinear"]:
                        continue
                    row = fit_restarts(kind, depth, data, config, policy, ridge, seed)
                    model = CalendarReadout(**row["model"])
                    row["validation"] = validation(model, data, row["fit"]["parameters"])
                    records["nonlinear"][key] = row
                    write_json(destination, records)
                    progress(
                        f"{key}: val {row['validation']['pooled']['log_loss']:.6f} "
                        f"ok={row['fit']['eligible']}",
                        flush=True,
                    )
    choices = {}
    for kind in ("quantum", "quantum-shared", "tanh", "sine"):
        candidates = []
        for depth in config.depths:
            for ridge in config.feature_ridges:
                group = [
                    r
                    for r in records["nonlinear"].values()
                    if r["kind"] == kind and r["depth"] == depth and r["feature_ridge"] == ridge
                ]
                candidates.append(
                    {
                        "depth": depth,
                        "feature_ridge": ridge,
                        "validation_nll": float(
                            np.mean([r["validation"]["pooled"]["log_loss"] for r in group])
                        ),
                    }
                )
        choices[kind] = min(
            candidates, key=lambda r: (r["validation_nll"], r["depth"], r["feature_ridge"])
        )
    selection = {
        "linear_key": chosen_key,
        "policy": policy,
        "choices": choices,
        "development_sha256": sha256(destination),
    }
    write_json(out / "selection.json", selection)
    return selection


def train(data, output, progress=print):
    out = Path(output)
    config = check_context(data, out)
    if (out / "seal.json").exists():
        raise ValueError("Training is sealed")
    selection = read(out / "selection.json")
    if sha256(out / "development.json") != selection["development_sha256"]:
        raise ValueError("Development records changed")
    for seed in config.final_seeds:
        dest = out / f"train-seed{seed}.json"
        if dest.exists():
            continue
        records = {}
        for kind, choice in selection["choices"].items():
            records[kind] = fit_restarts(
                kind,
                choice["depth"],
                data,
                config,
                selection["policy"],
                choice["feature_ridge"],
                seed,
            )
        write_json(
            dest,
            {"seed": seed, "selection_sha256": sha256(out / "selection.json"), "models": records},
        )
        progress(
            f"trained seed {seed}: " + str({k: r["fit"]["eligible"] for k, r in records.items()}),
            flush=True,
        )


def seal(data, output):
    out = Path(output)
    config = check_context(data, out)
    if (out / "seal.json").exists():
        raise ValueError("Training already sealed")
    names = ["manifest.json", "development.json", "selection.json"]
    for seed in config.final_seeds:
        name = f"train-seed{seed}.json"
        if read(out / name)["selection_sha256"] != sha256(out / "selection.json"):
            raise ValueError("Final fits use different selections")
        names.append(name)
    write_json(
        out / "seal.json",
        {
            "artifacts": {n: sha256(out / n) for n in names},
            "training_complete": True,
            "test_scored": False,
        },
    )


def check_seal(data, output):
    config = check_context(data, output)
    out = Path(output)
    record = read(out / "seal.json")
    for name, digest in record["artifacts"].items():
        if sha256(out / name) != digest:
            raise ValueError(f"Training artifact changed: {name}")
    return config


def generate_calendar(model, parameters, data, days, paths, seed, burn_in=100):
    """Advance forecast dates with recursive histories, starting after training ends."""
    if days < 32 or paths < 1 or burn_in < 0:
        raise ValueError("Need days >=32, paths >=1, burn-in >=0")
    rng = np.random.default_rng(seed)
    horizon = days + burn_in
    u, within, z = (
        rng.random((horizon, paths)),
        rng.random((horizon, paths)),
        rng.normal(size=(horizon, paths)),
    )
    first = data.target_rows[data.train.stop - 1] + 1
    start_date = np.datetime64(data.daily.index[first - 1], "D") + np.timedelta64(1, "D")
    y, r = np.empty((paths, 30 + horizon)), np.empty((paths, 30 + horizon))
    y[:, :30] = np.log(data.daily.rv[first - 30 : first])
    r[:, :30] = data.daily.returns[first - 30 : first]
    levels = np.empty((paths, horizon), int)
    for step in range(horizon):
        t = 30 + step
        raw = np.column_stack(
            [y[:, t - 1], y[:, t - 7 : t].mean(axis=1), y[:, t - 30 : t].mean(axis=1), r[:, t - 1]]
        )
        dates = np.full(paths, start_date + np.timedelta64(step, "D"))
        x = calendar_inputs(data.scaler.transform(raw), dates, model.calendar)
        probs = model.probabilities(x, parameters)
        k = np.minimum((u[step, :, None] >= probs.cumsum(axis=1)).sum(axis=1), 3)
        levels[:, step] = k
        for level, pool in enumerate(data.bins.pools):
            mask = k == level
            y[mask, t] = pool[
                np.minimum((within[step, mask] * len(pool)).astype(int), len(pool) - 1)
            ]
        r[:, t] = np.exp(y[:, t] / 2) * z[step]
    return Paths(y[:, 30 + burn_in :], r[:, 30 + burn_in :], levels[:, burn_in:])
