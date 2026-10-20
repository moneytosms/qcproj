"""Exact statevector simulators. Basis order is |q0 q1>: 00,01,10,11."""

from dataclasses import dataclass

import numpy as np

CNOT = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]], complex)


def ry(angle):
    c, s = np.cos(angle / 2), np.sin(angle / 2)
    return np.array([[c, -s], [s, c]], complex)


def rz(angle):
    return np.diag([np.exp(-0.5j * angle), np.exp(0.5j * angle)])


def u3(theta, phi, lam):
    c, s = np.cos(theta / 2), np.sin(theta / 2)
    return np.array(
        [[c, -np.exp(1j * lam) * s], [np.exp(1j * phi) * s, np.exp(1j * (phi + lam)) * c]]
    )


def _rotate(state, angle, axis, qubit, qubits):
    """Vectorized independent rotations of a batch of states without constructing kron."""
    angle = np.broadcast_to(angle, (len(state),))
    stride = 2 ** (qubits - 1 - qubit)
    low = np.array([i for i in range(2**qubits) if not i & stride])
    high = low + stride
    a, b = state[:, low].copy(), state[:, high].copy()
    if axis == "y":
        c, s = np.cos(angle / 2)[:, None], np.sin(angle / 2)[:, None]
        state[:, low], state[:, high] = c * a - s * b, s * a + c * b
    else:
        state[:, low] = np.exp(-0.5j * angle)[:, None] * a
        state[:, high] = np.exp(0.5j * angle)[:, None] * b


def encoded_state(returns, variance):
    """Paper encoding, variance denotes sigma^2 (so sigma^4 = variance**2)."""
    r, v = np.broadcast_arrays(np.asarray(returns, float), np.asarray(variance, float))
    if not np.all(np.isfinite(r)) or not np.all(np.isfinite(v)):
        raise ValueError("Encoding inputs must be finite")
    if np.any(np.abs(r) > 1 + 1e-12) or np.any((v < -1e-12) | (v > 1 + 1e-12)):
        raise ValueError("Paper encoding requires return in [-1,1], variance in [0,1]")
    r, v = np.clip(r, -1, 1).ravel(), np.clip(v, 0, 1).ravel()
    state = np.zeros((len(r), 2), complex)
    state[:, 0] = 1
    for angle, axis in [
        (np.arcsin(r), "y"),
        (np.arccos(r * r), "z"),
        (np.arcsin(2 * v - 1), "y"),
        (np.arccos(v * v), "z"),
    ]:
        _rotate(state, angle, axis, 0, 1)
    return state


def bloch_vector(state):
    a, b = state[:, 0], state[:, 1]
    return np.column_stack(
        [2 * (a.conj() * b).real, 2 * (a.conj() * b).imag, np.abs(a) ** 2 - np.abs(b) ** 2]
    )


def paper_probability(returns, variance, parameters):
    """Parameter order explicitly (theta, phi, lambda), matching standard U3."""
    psi = encoded_state(returns, variance)
    return np.abs((psi @ u3(*parameters).T)[:, 0]) ** 2


def paper_twin(returns, variance, parameters):
    theta, _, lam = parameters
    n = np.array([-np.sin(theta) * np.cos(lam), np.sin(theta) * np.sin(lam), np.cos(theta)])
    return 0.5 + 0.5 * bloch_vector(encoded_state(returns, variance)) @ n


@dataclass(frozen=True)
class BornCircuit:
    layers: int = 3

    def __post_init__(self):
        if self.layers not in (1, 2, 3, 4):
            raise ValueError("Choose 1–4 circuit layers")

    @property
    def n_params(self):
        return 8 * self.layers

    def probabilities(self, x, parameters):
        x = np.atleast_2d(np.asarray(x, float))
        if x.shape[1] != 4 or not np.all(np.isfinite(x)):
            raise ValueError("Circuit needs four finite HAR inputs per row")
        w = np.asarray(parameters).reshape(self.layers, 8)
        state = np.zeros((len(x), 4), complex)
        state[:, 0] = 1
        for layer in w:
            for qubit, j in [(0, 0), (1, 2)]:
                _rotate(state, layer[j] * x[:, j], "y", qubit, 2)
                _rotate(state, layer[j + 1] * x[:, j + 1], "z", qubit, 2)
                _rotate(state, layer[4 + 2 * qubit], "y", qubit, 2)
                _rotate(state, layer[5 + 2 * qubit], "z", qubit, 2)
            state = state[:, [0, 1, 3, 2]]
        probs = np.abs(state) ** 2
        return probs / probs.sum(axis=1, keepdims=True)


@dataclass(frozen=True)
class MemoryCircuit:
    """Explicit B-only design: four data rotations then RY/RZ each layer, point P0."""

    layers: int = 3
    short_memory: bool = False

    def __post_init__(self):
        if type(self.layers) is not int or self.layers not in (1, 2, 3, 4):
            raise ValueError("Choose 1–4 memory circuit layers")

    @property
    def n_params(self):
        return 6 * self.layers

    def predict(self, x, parameters):
        x = np.atleast_2d(np.asarray(x, float))
        if x.shape[1] != 4 or not np.all(np.isfinite(x)):
            raise ValueError("Memory circuit needs four finite HAR inputs per row")
        if self.short_memory:
            # Repeat standardized yesterday log RV in the same gate slots. This
            # preserves the ansatz and nominal budget without 7/30-day information.
            x = x[:, [0, 0, 0, 3]]
        state = np.zeros((len(x), 2), complex)
        state[:, 0] = 1
        for w in np.asarray(parameters).reshape(self.layers, 6):
            for j in range(4):
                _rotate(state, w[j] * x[:, j], "y" if j % 2 == 0 else "z", 0, 1)
            _rotate(state, w[4], "y", 0, 1)
            _rotate(state, w[5], "z", 0, 1)
        return np.abs(state[:, 0]) ** 2


def verify_paper(seed=17, samples=256):
    rng = np.random.default_rng(seed)
    r, v, p = rng.uniform(-1, 1, samples), rng.uniform(0, 1, samples), rng.normal(size=3)
    base = paper_probability(r, v, p)
    changed = p.copy()
    changed[1] += 2.345
    return {
        "samples": samples,
        "phi_max_error": float(np.max(np.abs(base - paper_probability(r, v, changed)))),
        "twin_max_error": float(np.max(np.abs(base - paper_twin(r, v, p)))),
    }
