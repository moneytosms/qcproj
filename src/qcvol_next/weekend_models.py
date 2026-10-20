"""Weekend-aware, four-level forecasters for the ETH upgrade experiment."""

from dataclasses import dataclass

import numpy as np
from scipy.special import softmax


def _ry(angle):
    c, s = np.cos(angle / 2), np.sin(angle / 2)
    m = np.empty(angle.shape + (2, 2), complex)
    m[..., 0, 0], m[..., 0, 1], m[..., 1, 0], m[..., 1, 1] = c, -s, s, c
    return m


def _rz(angle):
    m = np.zeros(angle.shape + (2, 2), complex)
    m[..., 0, 0], m[..., 1, 1] = np.exp(-0.5j * angle), np.exp(0.5j * angle)
    return m


def _single(a, b, c, d):
    return _rz(d) @ _ry(c) @ _rz(b) @ _ry(a)


@dataclass(frozen=True)
class WeekendBorn:
    """Two-qubit HAR circuit with learned weekend rotations on both qubits per layer."""

    layers: int = 2
    weekend_axis: str = "z"
    alternate_entangler: bool = False

    def __post_init__(self):
        if type(self.layers) is not int or self.layers not in (1, 2, 3, 4):
            raise ValueError("Choose 1-4 layers")
        if self.weekend_axis not in ("y", "z"):
            raise ValueError("Weekend rotation axis must be y or z")

    @property
    def n_params(self):
        return 10 * self.layers

    def probabilities(self, x, parameters):
        x = np.atleast_2d(np.asarray(x, float))
        if x.shape[1] != 5 or not np.all(np.isfinite(x)):
            raise ValueError("Need four HAR inputs and a weekend feature per row")
        w = np.asarray(parameters, float).reshape(self.layers, 10)
        state = np.zeros((len(x), 2, 2), complex)
        state[:, 0, 0] = 1
        for index, layer in enumerate(w):
            ones = np.ones(len(x))
            weekend_rotation = _ry if self.weekend_axis == "y" else _rz
            u0 = weekend_rotation(layer[8] * x[:, 4]) @ _single(
                layer[0] * x[:, 0], layer[1] * x[:, 1], layer[4] * ones, layer[5] * ones
            )
            u1 = weekend_rotation(layer[9] * x[:, 4]) @ _single(
                layer[2] * x[:, 2], layer[3] * x[:, 3], layer[6] * ones, layer[7] * ones
            )
            state = u0 @ state @ np.swapaxes(u1, 1, 2)
            if self.alternate_entangler and index % 2:
                state[:, :, 1] = state[:, ::-1, 1].copy()
            else:
                state[:, 1, :] = state[:, 1, ::-1].copy()
        p = (np.abs(state) ** 2).reshape(len(x), 4)
        return p / p.sum(axis=1, keepdims=True)


@dataclass(frozen=True)
class WeekendSoftmax:
    n_params: int = 24

    def probabilities(self, x, parameters):
        x = np.atleast_2d(np.asarray(x, float))
        design = np.column_stack([x, np.ones(len(x))])
        return softmax(design @ np.asarray(parameters).reshape(6, 4), axis=1)


@dataclass(frozen=True)
class WeekendNetwork:
    """27-parameter 5→2 tanh classifier with direct feature skips."""

    n_params: int = 27

    def probabilities(self, x, parameters):
        x, p = np.atleast_2d(np.asarray(x, float)), np.asarray(parameters, float)
        hidden = np.tanh(x @ p[:10].reshape(5, 2) + p[10:12])
        logits = hidden @ p[12:18].reshape(2, 3) + p[18:21]
        logits[:, 0] += x @ p[21:26]
        logits[:, 1] += x[:, 0] * p[26]
        return softmax(np.column_stack([logits, np.zeros(len(x))]), axis=1)


@dataclass
class WeekendQuantumReadout:
    """Use quantum outcome probabilities as features for a trainable HAR correction."""

    base: object
    layers: int = 1

    @property
    def n_params(self):
        return 10 * self.layers + 15

    def pooled(self, base_probabilities, x, parameters):
        parameters = np.asarray(parameters, float)
        quantum_parameters = parameters[: 10 * self.layers]
        readout = parameters[10 * self.layers :]
        quantum = WeekendBorn(self.layers, weekend_axis="y").probabilities(x, quantum_parameters)
        logits = np.column_stack(
            [quantum @ readout[:12].reshape(4, 3) + readout[12:15], np.zeros(len(x))]
        )
        return softmax(np.log(np.clip(base_probabilities, 1e-12, 1)) + logits, axis=1)

    def probabilities(self, x, parameters):
        return self.pooled(self.base.probabilities(x), x, parameters)


@dataclass
class WeekendHAR:
    coefficients: np.ndarray
    residuals: np.ndarray
    edges: np.ndarray

    @classmethod
    def fit(cls, x, y, edges):
        x = np.atleast_2d(np.asarray(x, float))
        design = np.column_stack([x[:, :3], x[:, 4], np.ones(len(x))])
        coefficients = np.linalg.lstsq(design, y, rcond=None)[0]
        residuals = np.sort(y - design @ coefficients)
        return cls(coefficients, residuals, np.asarray(edges).copy())

    def predict(self, x):
        x = np.atleast_2d(np.asarray(x, float))
        return np.column_stack([x[:, :3], x[:, 4], np.ones(len(x))]) @ self.coefficients

    def probabilities(self, x, parameters=None):
        thresholds = self.edges[None, :] - self.predict(x)[:, None]
        cdf = (np.searchsorted(self.residuals, thresholds, side="right") + 0.5) / (
            len(self.residuals) + 1
        )
        return np.diff(np.column_stack([np.zeros(len(cdf)), cdf, np.ones(len(cdf))]), axis=1)
