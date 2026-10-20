"""Quantum v3 candidates: same 2-qubit data-reuploading circuit as v2, with a
restart ensemble and an optional Pauli-expectation readout.

The Born-rule readout of a 2-qubit state is a fixed linear map of its 15 non-trivial
Pauli expectations. The "pauli" readout learns that map (plus a softmax) instead.
"""

from dataclasses import dataclass

import numpy as np

I2 = np.eye(2, dtype=complex)
PX = np.array([[0, 1], [1, 0]], complex)
PY = np.array([[0, -1j], [1j, 0]], complex)
PZ = np.array([[1, 0], [0, -1]], complex)
PAULI_2Q = np.stack(
    [np.kron(a, b) for a in (I2, PX, PY, PZ) for b in (I2, PX, PY, PZ)][1:]
)  # drop identity: 15 operators


@dataclass(frozen=True)
class Spec:
    readout: str  # "born" or "pauli"
    inputs: int
    layers: int = 3

    @property
    def n_circuit(self):
        return self.layers * 2 * 2 * (self.inputs + 1)

    @property
    def n_params(self):
        extra = 15 * 4 + 4 if self.readout == "pauli" else 0
        return self.n_circuit + extra


def build(spec):
    """Jitted probabilities(p, x) and value_and_grad of mean log loss (p, x, labels)."""
    import jax
    import jax.numpy as jnp

    jax.config.update("jax_enable_x64", True)
    k = spec.inputs
    pauli = jnp.asarray(PAULI_2Q)

    def ry(a):
        c, s = jnp.cos(a / 2), jnp.sin(a / 2)
        return jnp.stack([jnp.stack([c, -s], -1), jnp.stack([s, c], -1)], -2).astype(jnp.complex128)

    def rz(a):
        e = jnp.exp(-0.5j * a)
        zero = jnp.zeros_like(e)
        return jnp.stack([jnp.stack([e, zero], -1), jnp.stack([zero, jnp.conj(e)], -1)], -2)

    def state(p, x):
        n = x.shape[0]
        xb = jnp.column_stack([x, jnp.ones(n)])
        w = p[: spec.n_circuit].reshape(spec.layers, 2, 2, k + 1)
        st = jnp.zeros((n, 2, 2), jnp.complex128).at[:, 0, 0].set(1)
        for layer in range(spec.layers):
            u = [rz(xb @ w[layer, q, 1]) @ ry(xb @ w[layer, q, 0]) for q in range(2)]
            st = u[0] @ st @ jnp.swapaxes(u[1], 1, 2)
            st = st.at[:, 1, :].set(st[:, 1, ::-1])  # CNOT, control q0
        return st.reshape(n, 4)

    def probs(p, x):
        psi = state(p, x)
        if spec.readout == "born":
            pr = jnp.abs(psi) ** 2
            return pr / pr.sum(axis=1, keepdims=True)
        e = jnp.real(jnp.einsum("ni,pij,nj->np", jnp.conj(psi), pauli, psi))
        r = p[spec.n_circuit :]
        logits = e @ r[:60].reshape(15, 4) + r[60:]
        return jax.nn.softmax(logits, axis=1)

    def nll(p, x, labels):
        pr = jnp.clip(probs(p, x), 1e-12, 1)
        return -jnp.mean(jnp.log(pr[jnp.arange(x.shape[0]), labels]))

    return jax.jit(probs), jax.jit(jax.value_and_grad(nll))


def fit_restarts(spec, x, labels, seed, restarts=5, ridge=0.0, tag=0):
    """L-BFGS-B with exact gradients from N(0, 0.3^2) starts; returns all restart fits."""
    from scipy.optimize import minimize

    _, value_and_grad = build(spec)
    fits = []
    for restart in range(restarts):
        init_seed = 200000 + 100 * seed + 10 * tag + restart
        initial = np.random.default_rng(init_seed).normal(0, 0.3, spec.n_params)

        def objective(p):
            value, grad = value_and_grad(p, x, labels)
            return float(value) + ridge * p @ p, np.asarray(grad, float) + 2 * ridge * p

        res = minimize(
            objective,
            initial,
            jac=True,
            method="L-BFGS-B",
            options={"maxiter": 20000, "maxfun": 40000, "gtol": 1e-7},
        )
        fits.append({"restart": restart, "parameters": res.x, "objective": float(res.fun)})
    return fits


def ensemble_probs(spec, fits, x, top=None):
    """Average the probabilities of the best `top` restarts (by training objective)."""
    probs_fn, _ = build(spec)
    ranked = sorted(fits, key=lambda f: f["objective"])[:top]
    return np.mean([np.asarray(probs_fn(f["parameters"], x)) for f in ranked], axis=0)
