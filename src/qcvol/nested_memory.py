"""A two-weight extension containing the literal paper readout, plus an RV HAR control."""

from dataclasses import dataclass

import numpy as np

from .data import Standardizer
from .quantum import _rotate, encoded_state, u3
from .training import PointScaling, optimize


@dataclass(frozen=True)
class NestedMemoryCircuit:
    """P0 of U3(theta,0,lambda) RZ(b*x_month) RY(a*x_week) E(r,v)|0>.

    Parameters are (theta, lambda, a, b). Zero added weights recover the paper's
    probabilities exactly. The short control replaces both horizons with yesterday.
    """

    short_memory: bool = False

    @property
    def n_params(self):
        return 4

    def predict_encoded(self, encoded, x, parameters):
        state = np.asarray(encoded, complex).copy()
        x, p = np.atleast_2d(np.asarray(x, float)), np.asarray(parameters, float)
        if state.shape != (len(x), 2) or x.shape[1] != 4 or p.shape != (4,):
            raise ValueError(
                "Need aligned (N,2) encoded states, (N,4) features and four parameters"
            )
        if not all(np.all(np.isfinite(v)) for v in (state, x, p)):
            raise ValueError("Nested circuit inputs must be finite")
        week, month = (0, 0) if self.short_memory else (1, 2)
        _rotate(state, p[2] * x[:, week], "y", 0, 1)
        _rotate(state, p[3] * x[:, month], "z", 0, 1)
        return np.abs((state @ u3(p[0], 0, p[1]).T)[:, 0]) ** 2

    def predict(self, returns, variance, x, parameters):
        return self.predict_encoded(encoded_state(returns, variance), x, parameters)


def nested_inputs(data, rows, scaling):
    """Apply the paper's existing domain handling; no transform is fitted here."""
    rows = np.asarray(rows)
    positions = np.searchsorted(data.target_rows, rows)
    if np.any(positions >= len(data.target_rows)) or not np.array_equal(
        data.target_rows[positions], rows
    ):
        raise ValueError("Rows must be prepared target rows")
    r = data.daily.returns[rows - 1] / scaling.return_scale
    v = data.daily.rv[rows - 1] / scaling.rv_scale
    clips = int((np.abs(r) > 1).sum() + ((v < 0) | (v > 1)).sum())
    return encoded_state(np.clip(r, -1, 1), np.clip(v, 0, 1)), data.x[positions], clips


def warm_initial(baseline_parameters, seed, jitter=0.05):
    baseline = np.asarray(baseline_parameters)
    if baseline.shape != (3,) or not np.all(np.isfinite(baseline)):
        raise ValueError("Need the three stored paper angles")
    if type(seed) is not int or seed < 0 or not np.isfinite(jitter) or jitter < 0:
        raise ValueError("Need a nonnegative seed and finite nonnegative jitter")
    weights = np.zeros(2) if seed == 0 else np.random.default_rng(seed).normal(0, jitter, 2)
    return np.r_[baseline[[0, 2]], weights]


def fit_nested(
    data,
    baseline_parameters,
    regularization,
    seed=0,
    short_memory=False,
    max_evaluations=10000,
    jitter=0.05,
):
    if not np.isfinite(regularization) or regularization < 0:
        raise ValueError("Regularization must be finite and nonnegative")
    scaling = PointScaling.fit(data)
    rows = data.target_rows[data.train]
    encoded, x, _ = nested_inputs(data, rows, scaling)
    target = data.daily.rv[rows] / scaling.rv_scale
    model = NestedMemoryCircuit(short_memory)
    initial = warm_initial(baseline_parameters, seed, jitter)

    def objective(parameters):
        residual = model.predict_encoded(encoded, x, parameters) - target
        return float(np.mean(residual**2) + regularization * np.sum(parameters[2:] ** 2))

    fit = optimize(objective, initial, max_evaluations)
    # Independent finite-difference stationarity check in addition to optimizer status.
    step = 1e-5
    gradient = np.empty(4)
    for i in range(4):
        direction = np.eye(4)[i] * step
        gradient[i] = (
            objective(fit.parameters + direction) - objective(fit.parameters - direction)
        ) / (2 * step)
    return fit, scaling, gradient


def har_features(rv, rows):
    rv, rows = np.asarray(rv), np.asarray(rows)
    if rows.ndim != 1 or np.any(rows < 30) or np.any(rows >= len(rv)):
        raise ValueError("HAR targets require thirty completed days")
    return np.array([[rv[t - 1], rv[t - 7 : t].mean(), rv[t - 30 : t].mean()] for t in rows])


@dataclass
class HARPointModel:
    """OLS HAR in RV units with 1/7/30 crypto horizons; nonnegative point readout."""

    coefficients: np.ndarray
    scaler: Standardizer
    rv_scale: float
    rank: int

    @classmethod
    def fit(cls, data):
        rows = data.target_rows[data.train]
        x = har_features(data.daily.rv, rows)
        scaler = Standardizer.fit(x)
        design = np.column_stack([np.ones(len(rows)), scaler.transform(x)])
        rv_scale = PointScaling.fit(data).rv_scale
        coefficients, _, rank, _ = np.linalg.lstsq(
            design, data.daily.rv[rows] / rv_scale, rcond=None
        )
        return cls(coefficients, scaler, rv_scale, int(rank))

    def predict(self, rv, rows):
        x = self.scaler.transform(har_features(rv, rows))
        return (
            np.maximum(np.column_stack([np.ones(len(x)), x]) @ self.coefficients, 0) * self.rv_scale
        )

    def record(self):
        return {
            "coefficients": self.coefficients.tolist(),
            "feature_mean": self.scaler.mean.tolist(),
            "feature_scale": self.scaler.scale.tolist(),
            "rv_scale": self.rv_scale,
            "rank": self.rank,
            "parameters": 4,
            "method": "OLS on raw RV horizons, nonnegative forecast",
            "optimizer_calls": 0,
            "linear_solves": 1,
        }
