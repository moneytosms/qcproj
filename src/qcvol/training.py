"""COBYLA training with explicit budgets and common simulation random numbers."""

import time
from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

from .data import PreparedData
from .generation import generate
from .metrics import log_loss, moment_distance, moment_scales, moments
from .quantum import MemoryCircuit, paper_probability


@dataclass
class Fit:
    parameters: np.ndarray
    objective: float
    initial_objective: float
    evaluations: int
    success: bool
    message: str
    seconds: float

    def record(self):
        return {
            **self.__dict__,
            "parameters": self.parameters.tolist(),
            "initial_check_evaluations": 1,
            "total_objective_calls": self.evaluations + 1,
        }


def optimize(objective, initial, max_evaluations):
    if max_evaluations < len(initial) + 2:
        raise ValueError("COBYLA budget must be at least parameter count + 2")
    started = time.perf_counter()
    initial_loss = float(objective(initial))
    result = minimize(
        objective,
        initial,
        method="COBYLA",
        options={"maxiter": max_evaluations, "rhobeg": 0.3, "tol": 1e-5},
    )
    parameters, loss = result.x, float(result.fun)
    if not np.isfinite(loss):
        raise ValueError("Training objective became nonfinite")
    if initial_loss < loss:
        parameters, loss = initial.copy(), initial_loss
    return Fit(
        parameters,
        loss,
        initial_loss,
        int(result.nfev),
        bool(result.success),
        str(result.message),
        time.perf_counter() - started,
    )


def fit_distribution(
    model,
    data: PreparedData,
    seed=0,
    max_evaluations=150,
    realism_weight=0.0,
    initial=None,
    path_days=128,
    paths=2,
    burn_in=30,
):
    if realism_weight < 0:
        raise ValueError("Realism weight must be nonnegative")
    x, labels = data.x[data.train], data.labels[data.train]
    reference, scales = moments(data.y[data.train]), moment_scales(data.y[data.train])
    if not np.all(np.isfinite(reference)):
        raise ValueError("Undefined real training moments")
    if initial is None:
        initial = np.random.default_rng(seed).normal(0, 0.3, model.n_params)

    def objective(parameters):
        forecast = log_loss(model.probabilities(x, parameters), labels)
        if realism_weight == 0:
            return forecast
        generated = generate(
            model,
            parameters,
            data,
            days=path_days,
            paths=paths,
            seed=10_000 + seed,
            burn_in=burn_in,
        )
        path_moments = np.mean([moments(y) for y in generated.log_rv], axis=0)
        distance = moment_distance(path_moments, reference, scales)
        return forecast + realism_weight * (distance if np.isfinite(distance) else 1e8)

    return optimize(objective, np.asarray(initial), max_evaluations)


@dataclass
class PointScaling:
    return_scale: float
    rv_scale: float

    @classmethod
    def fit(cls, data):
        if data.daily.units == "author-standardized":
            return cls(1.0, 1.0)
        end = data.target_rows[data.train.stop - 1] + 1
        return cls(
            max(1.2 * np.max(np.abs(data.daily.returns[:end])), 1e-12),
            max(1.2 * np.max(data.daily.rv[:end]), 1e-12),
        )


def point_prediction(kind, parameters, data, rows, scaling):
    if kind == "paper":
        r = np.clip(data.daily.returns[rows - 1] / scaling.return_scale, -1, 1)
        v = np.clip(data.daily.rv[rows - 1] / scaling.rv_scale, 0, 1)
        return paper_probability(r, v, parameters) * scaling.rv_scale
    return (
        MemoryCircuit(len(parameters) // 6).predict(data.x[rows - 30], parameters)
        * scaling.rv_scale
    )


def fit_point(kind, data, seed=0, layers=3, max_evaluations=150):
    scaling = PointScaling.fit(data)
    rows = data.target_rows[data.train]
    y = data.daily.rv[rows] / scaling.rv_scale
    n_params = 3 if kind == "paper" else MemoryCircuit(layers).n_params

    def objective(parameters):
        prediction = point_prediction(kind, parameters, data, rows, scaling) / scaling.rv_scale
        return float(np.mean((prediction - y) ** 2))

    fit = optimize(objective, np.random.default_rng(seed).normal(0, 0.3, n_params), max_evaluations)
    return fit, scaling


def generate_point(kind, parameters, data, scaling, days=256, paths=4, seed=2000, burn_in=60):
    """Point baselines: Gaussian innovations; clip only paper encoding, count events."""
    rng = np.random.default_rng(seed)
    end = data.target_rows[data.train.stop - 1] + 1
    y = np.tile(np.log(data.daily.rv[end - 30 : end]), (paths, 1))
    r = np.tile(data.daily.returns[end - 30 : end], (paths, 1))
    clipped = 0
    for _ in range(days + burn_in):
        if kind == "paper":
            return_input, rv_input = (
                r[:, -1] / scaling.return_scale,
                np.exp(y[:, -1]) / scaling.rv_scale,
            )
            clipped += int(
                (np.abs(return_input) > 1).sum() + ((rv_input < 0) | (rv_input > 1)).sum()
            )
            v = paper_probability(np.clip(return_input, -1, 1), np.clip(rv_input, 0, 1), parameters)
        else:
            x = np.column_stack(
                [y[:, -1], y[:, -7:].mean(axis=1), y[:, -30:].mean(axis=1), r[:, -1]]
            )
            v = MemoryCircuit(len(parameters) // 6).predict(data.scaler.transform(x), parameters)
        new_y = np.log(np.maximum(v * scaling.rv_scale, 1e-12))
        new_r = np.exp(new_y / 2) * rng.normal(size=paths)
        y, r = np.column_stack([y, new_y]), np.column_stack([r, new_r])
    return y[:, 30 + burn_in :], r[:, 30 + burn_in :], clipped
