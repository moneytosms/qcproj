"""Previous-day distribution controls; the input policy also applies during rollout."""

from dataclasses import dataclass

import numpy as np
from scipy.special import softmax

from .quantum import BornCircuit


def short_inputs(x):
    """Read only standardized previous log RV and previous return from HAR rows."""
    x = np.atleast_2d(np.asarray(x, float))
    if x.shape[1] != 4 or not np.all(np.isfinite(x[:, [0, 3]])):
        raise ValueError("Need finite previous-day log RV and return")
    return x[:, [0, 3]]


@dataclass(frozen=True)
class ShortBorn:
    layers: int

    def __post_init__(self):
        BornCircuit(self.layers)

    @property
    def n_params(self):
        return 8 * self.layers - 2

    def expand(self, parameters):
        p = np.zeros(8 * self.layers)
        active = np.ones(len(p), dtype=bool)
        active[[-3, -1]] = False
        p[active] = parameters
        return p

    def probabilities(self, x, parameters):
        x = short_inputs(x)
        w = self.expand(parameters).reshape(self.layers, 8)
        state = np.zeros((len(x), 4), complex)
        state[:, 0] = 1
        # Fuse each RY/RZ/RY/RZ block algebraically to reduce Python rollout overhead.
        for layer in w:
            for qubit in (0, 1):
                j = 2 * qubit
                a = layer[j] * x[:, 0] / 2
                b = layer[j + 1] * x[:, qubit] / 2
                c, d = layer[4 + j] / 2, layer[5 + j] / 2
                ca, sa, cb, sb = np.cos(a), np.sin(a), np.exp(-1j * b), np.exp(1j * b)
                cc, sc = np.cos(c), np.sin(c)
                low = np.array([0, 1] if qubit == 0 else [0, 2])
                high = low + (2 if qubit == 0 else 1)
                u00 = (cc * cb * ca - sc * sb * sa) * np.exp(-1j * d)
                u01 = (-cc * cb * sa - sc * sb * ca) * np.exp(-1j * d)
                u10 = (sc * cb * ca + cc * sb * sa) * np.exp(1j * d)
                u11 = (-sc * cb * sa + cc * sb * ca) * np.exp(1j * d)
                lo, hi = state[:, low].copy(), state[:, high].copy()
                state[:, low] = u00[:, None] * lo + u01[:, None] * hi
                state[:, high] = u10[:, None] * lo + u11[:, None] * hi
            state = state[:, [0, 1, 3, 2]]
        probabilities = np.abs(state) ** 2
        return probabilities / probabilities.sum(axis=1, keepdims=True)


@dataclass(frozen=True)
class ShortSoftmax:
    n_params: int = 9

    def probabilities(self, x, parameters):
        x = short_inputs(x)
        design = np.column_stack([x, np.ones(len(x))])
        logits = design @ np.asarray(parameters).reshape(3, 3)
        return softmax(np.column_stack([logits, np.zeros(len(x))]), axis=1)


@dataclass(frozen=True)
class ShortNetwork:
    """24 stored coordinates: 2→3 tanh→3 reference logits, plus three RV skips."""

    n_params: int = 24

    def probabilities(self, x, parameters):
        x, p = short_inputs(x), np.asarray(parameters)
        hidden = np.tanh(x @ p[:6].reshape(2, 3) + p[6:9])
        logits = hidden @ p[9:18].reshape(3, 3) + p[18:21]
        logits += x[:, :1] * p[21:24]
        return softmax(np.column_stack([logits, np.zeros(len(x))]), axis=1)


@dataclass
class ShortAR:
    coefficients: np.ndarray
    residuals: np.ndarray
    edges: np.ndarray
    n_params: int = 3

    @classmethod
    def fit(cls, x, y, edges):
        design = np.column_stack([short_inputs(x), np.ones(len(x))])
        beta = np.linalg.lstsq(design, y, rcond=None)[0]
        return cls(beta, np.sort(y - design @ beta), edges.copy())

    def probabilities(self, x, parameters=None):
        design = np.column_stack([short_inputs(x), np.ones(len(np.atleast_2d(x)))])
        thresholds = self.edges[None, :] - (design @ self.coefficients)[:, None]
        cdf = (np.searchsorted(self.residuals, thresholds, side="right") + 0.5) / (
            len(self.residuals) + 1
        )
        return np.diff(np.column_stack([np.zeros(len(cdf)), cdf, np.ones(len(cdf))]), axis=1)


def distribution_model(family, depth):
    return {"quantum": lambda: ShortBorn(depth), "softmax": ShortSoftmax, "network": ShortNetwork}[
        family
    ]()
