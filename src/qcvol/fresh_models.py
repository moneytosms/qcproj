"""Models for the fresh-data memory+realism study.

FastBorn is the same circuit as quantum.BornCircuit (identical probabilities, tested),
written with batched 2x2 matrices so small-batch path simulation is fast.
Hybrid adds a learned log-probability correction to a fixed base forecaster; with
weight 0 it reproduces the base model exactly.
"""

from dataclasses import dataclass

import numpy as np
from scipy.special import softmax

from .classical import SoftmaxModel, TinyNetwork
from .distribution_models import ShortNetwork, ShortSoftmax, short_inputs
from .quantum import BornCircuit


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
    """RZ(d) RY(c) RZ(b) RY(a), applied in that time order: RY(a) first."""
    return _rz(d) @ _ry(c) @ _rz(b) @ _ry(a)


@dataclass(frozen=True)
class FastBorn:
    """Two-qubit data re-uploading circuit; inputs (day, week, month, return) or short."""

    layers: int = 2
    short: bool = False

    def __post_init__(self):
        if type(self.layers) is not int or self.layers not in (1, 2, 3, 4):
            raise ValueError("Choose 1-4 layers")

    @property
    def n_params(self):
        return 8 * self.layers

    def inputs(self, x):
        x = np.atleast_2d(np.asarray(x, float))
        if x.shape[1] != 4 or not np.all(np.isfinite(x)):
            raise ValueError("Need four finite standardized HAR inputs per row")
        if self.short:
            # Same gate slots, previous-day log RV repeated: no weekly/monthly information.
            return x[:, [0, 0, 0, 3]]
        return x

    def probabilities(self, x, parameters):
        x = self.inputs(x)
        n = len(x)
        if n > 64:
            # Large batches: the original vectorized simulator is faster; same circuit.
            return BornCircuit(self.layers).probabilities(x, parameters)
        w = np.asarray(parameters, float).reshape(self.layers, 8)
        state = np.zeros((n, 2, 2), complex)
        state[:, 0, 0] = 1
        for layer in w:
            ones = np.ones(n)
            u0 = _single(layer[0] * x[:, 0], layer[1] * x[:, 1], layer[4] * ones, layer[5] * ones)
            u1 = _single(layer[2] * x[:, 2], layer[3] * x[:, 3], layer[6] * ones, layer[7] * ones)
            state = u0 @ state @ np.swapaxes(u1, 1, 2)
            state[:, 1, :] = state[:, 1, ::-1].copy()  # CNOT, control q0, target q1
        probabilities = (np.abs(state) ** 2).reshape(n, 4)
        return probabilities / probabilities.sum(axis=1, keepdims=True)


@dataclass
class Hybrid:
    """p(x) proportional to base(x) * expert(x)**gamma; parameter 0 is gamma.

    gamma = 0 gives the base forecaster exactly, so training can only add what the
    expert contributes on top of it. The base model is fixed (fitted beforehand).
    """

    base: object
    expert: object

    @property
    def n_params(self):
        return 1 + self.expert.n_params

    def pooled(self, base_probabilities, x, parameters):
        p = np.asarray(parameters, float)
        q = np.clip(self.expert.probabilities(x, p[1:]), 1e-12, 1)
        logits = np.log(np.clip(base_probabilities, 1e-12, 1)) + p[0] * np.log(q)
        return softmax(logits, axis=1)

    def probabilities(self, x, parameters):
        return self.pooled(self.base.probabilities(x), x, parameters)


FAMILIES = (
    "quantum-har",
    "softmax-har",
    "network-har",
    "quantum-short",
    "softmax-short",
    "network-short",
)


def make_model(name, layers=2):
    """Learned models. '-har' sees yesterday, week and month; '-short' sees yesterday only."""
    factories = {
        "quantum-har": lambda: FastBorn(layers),
        "quantum-short": lambda: FastBorn(layers, short=True),
        "softmax-har": SoftmaxModel,
        "softmax-short": ShortSoftmax,
        "network-har": TinyNetwork,
        "network-short": ShortNetwork,
    }
    return factories[name]()


__all__ = ["FAMILIES", "FastBorn", "Hybrid", "make_model", "short_inputs"]
