"""Quantum v2 and its same-input classical comparators (doc/v2-protocol.md).

Kept in a separate package so the sealed fresh study (which hashes src/qcvol) stays valid.
"""

from dataclasses import dataclass

import numpy as np

WEEKEND, MONDAY = (5, 6), 0


def weekdays(data):
    """Weekday of each target date, Monday = 0."""
    dates = np.asarray(data.daily.index, dtype="datetime64[D]")[data.target_rows]
    return (dates.astype(np.int64) + 3) % 7


def features(data, calendar=True):
    """Squashed HAR inputs 2*tanh(x/2), plus centered weekend and Monday flags of the target."""
    x = 2 * np.tanh(np.asarray(data.x, float) / 2)
    if not calendar:
        return x
    wd = weekdays(data)
    flags = np.column_stack([np.isin(wd, WEEKEND), wd == MONDAY]).astype(float)
    return np.column_stack([x, flags - flags[data.train].mean(axis=0)])


@dataclass(frozen=True)
class Spec:
    kind: str  # "quantum", "softmax" or "network"
    inputs: int
    layers: int = 3
    hidden: int = 2

    @property
    def n_params(self):
        k = self.inputs
        if self.kind == "quantum":
            return self.layers * 2 * 2 * (k + 1)
        if self.kind == "softmax":
            return 4 * (k + 1)
        return k * self.hidden + self.hidden + 4 * self.hidden + 4


def _ry(a):
    c, s = np.cos(a / 2), np.sin(a / 2)
    return np.array([[c, -s], [s, c]], complex)


def _rz(a):
    return np.diag([np.exp(-0.5j * a), np.exp(0.5j * a)])


CNOT = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]], complex)


def reference_probabilities(spec, x, parameters):
    """Plain 4x4 statevector simulation, one day at a time (slow; used to test the fast path).

    Basis order |q0 q1>, level = 2*q0 + q1.
    """
    if spec.kind != "quantum":
        raise ValueError("Reference only for the circuit")
    x = np.atleast_2d(x)
    w = np.asarray(parameters).reshape(spec.layers, 2, 2, spec.inputs + 1)
    out = []
    for row in x:
        xb = np.r_[row, 1.0]
        psi = np.zeros(4, complex)
        psi[0] = 1
        for layer in w:
            u = [_rz(layer[q, 1] @ xb) @ _ry(layer[q, 0] @ xb) for q in range(2)]
            psi = CNOT @ np.kron(u[0], u[1]) @ psi
        out.append(np.abs(psi) ** 2)
    return np.array(out)


def build(spec):
    """Return jitted probabilities(p, x) and value_and_grad of mean log loss (p, x, labels)."""
    import jax
    import jax.numpy as jnp

    jax.config.update("jax_enable_x64", True)
    k = spec.inputs

    def ry(a):
        c, s = jnp.cos(a / 2), jnp.sin(a / 2)
        return jnp.stack([jnp.stack([c, -s], -1), jnp.stack([s, c], -1)], -2).astype(jnp.complex128)

    def rz(a):
        e = jnp.exp(-0.5j * a)
        zero = jnp.zeros_like(e)
        return jnp.stack([jnp.stack([e, zero], -1), jnp.stack([zero, jnp.conj(e)], -1)], -2)

    def quantum(p, x):
        n = x.shape[0]
        xb = jnp.column_stack([x, jnp.ones(n)])
        w = p.reshape(spec.layers, 2, 2, k + 1)
        # state[i, a, b] = amplitude of |q0=a, q1=b>
        st = jnp.zeros((n, 2, 2), jnp.complex128).at[:, 0, 0].set(1)
        for layer in range(spec.layers):
            u = [rz(xb @ w[layer, q, 1]) @ ry(xb @ w[layer, q, 0]) for q in range(2)]
            st = u[0] @ st @ jnp.swapaxes(u[1], 1, 2)
            st = st.at[:, 1, :].set(st[:, 1, ::-1])  # CNOT, control q0
        pr = (jnp.abs(st) ** 2).reshape(n, 4)
        return pr / pr.sum(axis=1, keepdims=True)

    def softmax(p, x):
        xb = jnp.column_stack([x, jnp.ones(x.shape[0])])
        return jax.nn.softmax(xb @ p.reshape(k + 1, 4), axis=1)

    def network(p, x):
        h = spec.hidden
        a = k * h
        hidden = jnp.tanh(x @ p[:a].reshape(k, h) + p[a : a + h])
        logits = hidden @ p[a + h : a + 5 * h].reshape(h, 4) + p[a + 5 * h : a + 5 * h + 4]
        return jax.nn.softmax(logits, axis=1)

    probs = {"quantum": quantum, "softmax": softmax, "network": network}[spec.kind]

    def nll(p, x, labels):
        pr = jnp.clip(probs(p, x), 1e-12, 1)
        return -jnp.mean(jnp.log(pr[jnp.arange(x.shape[0]), labels]))

    return jax.jit(probs), jax.jit(jax.value_and_grad(nll))


def fit(spec, x, labels, seed, restarts=5, ridge=0.0):
    """L-BFGS-B with exact gradients; best restart by training objective."""
    from scipy.optimize import minimize

    _, value_and_grad = build(spec)
    fits = []
    for restart in range(restarts):
        init_seed = 100000 + 100 * seed + 10 * spec.layers + restart
        initial = np.random.default_rng(init_seed).normal(0, 0.3, spec.n_params)

        def objective(p):
            value, grad = value_and_grad(p, x, labels)
            return float(value) + ridge * p @ p, np.asarray(grad, float) + 2 * ridge * p

        result = minimize(
            objective,
            initial,
            jac=True,
            method="L-BFGS-B",
            options={"maxiter": 20000, "maxfun": 40000, "gtol": 1e-7},
        )
        gradient = float(np.max(np.abs(objective(result.x)[1])))
        fits.append(
            {
                "restart": restart,
                "initialization_seed": init_seed,
                "parameters": result.x.tolist(),
                "objective": float(result.fun),
                "train_log_loss": float(value_and_grad(result.x, x, labels)[0]),
                "success": bool(result.success),
                "gradient_inf": gradient,
                "eligible": bool(result.success and gradient <= 1e-4),
            }
        )
    best = min(fits, key=lambda f: (f["objective"], f["restart"]))
    return best, fits


MODELS = {
    "quantum-v2": (Spec("quantum", 6, layers=3), True, 1e-3),
    "quantum-v2-nocal": (Spec("quantum", 4, layers=3), False, 1e-3),
    "softmax-v2": (Spec("softmax", 6), True, 0.0),
    "network-v2": (Spec("network", 6, hidden=2), True, 0.0),
}
