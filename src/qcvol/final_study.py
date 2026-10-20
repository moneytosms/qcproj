"""Sealed training for the frozen, short-input twenty-seed comparison."""

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass, field
from importlib.metadata import version
from pathlib import Path

import numpy as np

from .classical import FrequencyModel, HARModel
from .classical_training import continue_network
from .data import sha256
from .distribution_models import ShortAR, distribution_model
from .distribution_study import DistributionConfig, central_gradient, fit_forecast
from .experiment import code_revision, write_json
from .finance_baselines import CalibratedGARCH, QuantileHAR
from .generation import generate
from .metrics import log_loss, moment_distance, moment_scales, moments
from .nested_memory import HARPointModel
from .training import PointScaling, fit_point, optimize, point_prediction


@dataclass
class FinalConfig:
    kind: str = "final"
    seeds: list[int] = field(default_factory=lambda: list(range(20)))
    restarts: int = 5
    quantum_layers: int = 2
    network_ridge: float = 0.001
    realism_weights: dict[str, float] = field(
        default_factory=lambda: {"quantum": 0.05, "softmax": 0.2, "network": 0.05}
    )
    forecast_max_calls: int = 50000
    forecast_max_iterations: int = 2000
    network_max_calls: int = 20000
    network_max_iterations: int = 10000
    paper_max_calls: int = 10000
    realism_starts: int = 3
    realism_max_calls: int = 600
    realism_tolerance: float = 0.002
    train_days: int = 128
    train_paths: int = 4
    train_burn_in: int = 60
    evaluation_days: int = 1024
    evaluation_paths: int = 32
    evaluation_burn_in: int = 100
    bootstrap_replicates: int = 2000
    bootstrap_blocks: list[int] = field(default_factory=lambda: [7, 30])

    def __post_init__(self):
        if self.kind not in ("final", "integration"):
            raise ValueError("Kind must be final or integration")
        if (
            not self.seeds
            or len(set(self.seeds)) != len(self.seeds)
            or any(type(s) is not int or not 0 <= s < 1000 for s in self.seeds)
        ):
            raise ValueError("Need distinct integer run seeds in 0..999")
        if self.kind == "final" and len(self.seeds) < 20:
            raise ValueError("Final study needs at least 20 seeds")
        if self.quantum_layers not in (1, 2, 3, 4) or type(self.quantum_layers) is not int:
            raise ValueError("Need 1–4 layers")
        if not np.isfinite(self.network_ridge) or self.network_ridge <= 0:
            raise ValueError("Need finite positive network ridge")
        if set(self.realism_weights) != {"quantum", "softmax", "network"} or any(
            not np.isfinite(w) or w <= 0 for w in self.realism_weights.values()
        ):
            raise ValueError("Need positive fixed weights for the three learned families")
        for name in (
            "restarts",
            "forecast_max_calls",
            "forecast_max_iterations",
            "network_max_calls",
            "network_max_iterations",
            "paper_max_calls",
            "realism_starts",
            "realism_max_calls",
            "train_days",
            "train_paths",
            "evaluation_days",
            "evaluation_paths",
            "bootstrap_replicates",
        ):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(f"{name} must be a positive integer")
        if (
            self.realism_max_calls < max(24, 8 * self.quantum_layers - 2) + 2
            or min(self.train_days, self.evaluation_days) < 64
        ):
            raise ValueError("Insufficient simplex budget or simulation horizon")
        if (
            self.paper_max_calls < 4
            or not np.isfinite(self.realism_tolerance)
            or self.realism_tolerance <= 0
        ):
            raise ValueError("Invalid optimizer allowance/tolerance")
        for name in ("train_burn_in", "evaluation_burn_in"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 0:
                raise ValueError("Burn-in must be a nonnegative integer")
        if (
            not self.bootstrap_blocks
            or len(set(self.bootstrap_blocks)) != len(self.bootstrap_blocks)
            or any(type(k) is not int or k < 1 for k in self.bootstrap_blocks)
        ):
            raise ValueError("Need distinct positive bootstrap blocks")


def read_json(path):
    return json.loads(Path(path).read_text())


def data_fingerprint(data):
    digest = hashlib.sha256()
    for values in (data.daily.returns, data.daily.rv):
        digest.update(np.asarray(values, dtype="<f8").tobytes())
    digest.update(json.dumps([str(v) for v in data.daily.index]).encode())
    return digest.hexdigest()


def restore_baseline(row):
    values = {k: np.array(v) if isinstance(v, list) else v for k, v in row["state"].items()}
    classes = {
        "frequency": FrequencyModel,
        "short-ar": ShortAR,
        "har-residual": HARModel,
        "har-quantile": QuantileHAR,
        "short-quantile": QuantileHAR,
        "garch-calibrated": CalibratedGARCH,
    }
    return classes[row["id"]](**values)


def fit_baselines(data):
    rows = []
    for id_, factory in {
        "frequency": lambda: FrequencyModel.fit(data.labels[data.train]),
        "short-ar": lambda: ShortAR.fit(data.x[data.train], data.y[data.train], data.bins.edges),
        "har-residual": lambda: HARModel.fit(
            data.x[data.train], data.y[data.train], data.bins.edges
        ),
    }.items():
        started = time.perf_counter()
        model = factory()
        rows.append(
            {
                "id": id_,
                "state": asdict(model),
                "fit": {
                    "seconds": time.perf_counter() - started,
                    "eligible": True,
                    "linear_solves": int(id_ != "frequency"),
                    "objective_calls": 0,
                },
            }
        )
    for short in (False, True):
        model, fit = QuantileHAR.fit(
            data.x[data.train], data.y[data.train], data.bins.edges, short=short
        )
        rows.append(
            {
                "id": "short-quantile" if short else "har-quantile",
                "state": asdict(model),
                "fit": fit,
            }
        )
    model, fit = CalibratedGARCH.fit(data)
    rows.append({"id": "garch-calibrated", "state": asdict(model), "fit": fit})
    point = HARPointModel.fit(data).record()
    return {
        "models": rows,
        "point_har": point,
        "point_mean": float(data.daily.rv[data.target_rows[data.train]].mean()),
    }


def training_seed(data, config, seed, progress=print):
    result = {"seed": seed, "families": {}, "paper": {}}
    train_y = data.y[data.train]
    reference = moments(train_y)
    scales = moment_scales(train_y)
    forecast_config = DistributionConfig(
        forecast_max_calls=config.forecast_max_calls,
        forecast_max_iterations=config.forecast_max_iterations,
    )
    for family in ("quantum", "softmax", "network"):
        model = distribution_model(family, config.quantum_layers if family == "quantum" else 0)
        fits = []
        for restart in range(config.restarts):
            init_seed = 100000 + 100 * seed + restart
            if family == "network":
                initial = np.random.default_rng(init_seed).normal(0, 0.3, model.n_params)
                fit = continue_network(
                    initial,
                    data,
                    config.network_max_calls,
                    config.network_max_iterations,
                    config.network_ridge,
                )
                fit["total_objective_calls"] = fit["objective_calls"]
            else:
                fit = fit_forecast(model, data, init_seed, forecast_config)
            fit.update({"restart": restart, "initialization_seed": init_seed})
            fits.append(fit)
        d = min(fits, key=lambda f: (f["objective"], f["restart"]))
        base = np.array(d["parameters"])
        ridge = config.network_ridge if family == "network" else 0
        weight = config.realism_weights[family]
        a_fits = []

        def objective(p, model=model, ridge=ridge, weight=weight):
            nll = log_loss(model.probabilities(data.x[data.train], p), data.labels[data.train])
            paths = generate(
                model,
                p,
                data,
                config.train_days,
                config.train_paths,
                400000 + seed,
                config.train_burn_in,
            )
            vector = np.mean([moments(y) for y in paths.log_rv], axis=0)
            return nll + ridge * float(p @ p) + weight * moment_distance(vector, reference, scales)

        for restart in range(config.realism_starts):
            initial = base.copy()
            jitter_seed = 300000 + 100 * seed + restart
            if restart:
                initial += np.random.default_rng(jitter_seed).normal(0, 0.03, len(base))
            fit = optimize(
                objective, initial, config.realism_max_calls, config.realism_tolerance
            ).record()
            fit.update(
                {
                    "restart": restart,
                    "initial_parameters": initial.tolist(),
                    "jitter_seed": jitter_seed,
                    "diagnostic_calls": 0,
                    "eligible": bool(fit["success"]),
                }
            )
            a_fits.append(fit)
        a = min(a_fits, key=lambda f: (f["objective"], f["restart"]))
        result["families"][family] = {
            "D_fits": fits,
            "D_restart": d["restart"],
            "D_parameters": d["parameters"],
            "D_eligible": d["eligible"],
            "A_fits": a_fits,
            "A_restart": a["restart"],
            "A_parameters": a["parameters"],
            "A_eligible": a["eligible"],
            "ridge": ridge,
            "lambda": weight,
        }
        progress(
            f"seed {seed} {family}: D pass={d['eligible']}, A radius success={a['eligible']}",
            flush=True,
        )
    fits = []
    rows = data.target_rows[data.train]
    for restart in range(config.restarts):
        init_seed = 200000 + 100 * seed + restart
        fit, scaling = fit_point(
            "paper",
            data,
            seed=init_seed,
            max_evaluations=config.paper_max_calls,
            initialization="uniform",
            reduce_inactive=True,
        )
        parameters = fit.parameters.copy()

        def objective(active, parameters=parameters, scaling=scaling):
            p = parameters.copy()
            p[[0, 2]] = active
            pred = point_prediction("paper", p, data, rows, scaling) / scaling.rv_scale
            target = data.daily.rv[rows] / scaling.rv_scale
            return float(np.mean((pred - target) ** 2))

        gradient = float(np.max(np.abs(central_gradient(objective, parameters[[0, 2]]))))
        record = fit.record()
        record.update(
            {
                "restart": restart,
                "initialization_seed": init_seed,
                "diagnostic_calls": 4,
                "gradient_inf": gradient,
                "eligible": bool(fit.success and gradient <= 1e-5),
            }
        )
        fits.append(record)
    best = min(fits, key=lambda f: (f["objective"], f["restart"]))
    result["paper"] = {
        "fits": fits,
        "restart": best["restart"],
        "parameters": best["parameters"],
        "eligible": best["eligible"],
        "scaling": asdict(PointScaling.fit(data)),
    }
    return result


def seal_training(output):
    output = Path(output)
    manifest = read_json(output / "manifest.json")
    config = FinalConfig(**manifest["config"])
    names = ["manifest.json", "baselines.json"] + [f"training-seed{s}.json" for s in config.seeds]
    if not all((output / name).is_file() for name in names):
        raise ValueError("Incomplete training")
    seal = {
        "artifacts": {name: sha256(output / name) for name in names},
        "code": manifest["code"],
        "config": manifest["config"],
        "training_complete": True,
        "test_scores_computed": False,
    }
    write_json(output / "training-seal.json", seal)
    return seal


def check_seal(output, data):
    output = Path(output)
    seal = read_json(output / "training-seal.json")
    manifest = read_json(output / "manifest.json")
    if (
        not seal["training_complete"]
        or manifest["config"] != seal["config"]
        or manifest["data"] != data.metadata()
        or manifest["data_fingerprint"] != data_fingerprint(data)
    ):
        raise ValueError("Sealed training/data mismatch")
    if seal["code"]["package_source_sha256"] != code_revision()["package_source_sha256"]:
        raise ValueError("Package source changed after training")
    for name, digest in seal["artifacts"].items():
        if Path(name).name != name or sha256(output / name) != digest:
            raise ValueError(f"Training artifact changed: {name}")
    return manifest, FinalConfig(**manifest["config"])


def train_final(data, config, output, source=None, progress=print):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "kind": config.kind,
        "data_fingerprint": data_fingerprint(data),
        "config": asdict(config),
        "data": data.metadata(),
        "source": source,
        "code": code_revision(),
        "versions": {n: version(n) for n in ("numpy", "scipy", "arch")},
        "thread_environment": {
            n: os.environ.get(n) for n in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS")
        },
        "test_scores_computed": False,
        "historical_test_smoke_was_inspected": True,
        "moment_scales": moment_scales(data.y[data.train]).tolist(),
    }
    write_json(output / "manifest.json", manifest)
    write_json(output / "baselines.json", fit_baselines(data))
    for seed in config.seeds:
        row = training_seed(data, config, seed, progress)
        write_json(output / f"training-seed{seed}.json", row)
    seal = seal_training(output)
    progress(f"Training sealed for {len(config.seeds)} seeds; no test scores computed", flush=True)
    return seal
