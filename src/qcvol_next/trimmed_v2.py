"""Quantum v2 without its inactive final-layer RZ weights (84 -> 70 parameters at depth 3).

In the last layer each qubit's RZ is followed only by a CNOT (a basis permutation) and a
Z-basis measurement, so its 7 weights per qubit cannot change the Born probabilities.
This model optimizes only the active weights and runs them through the unchanged v2
circuit with the inactive ones fixed at zero. The sealed `qcvol_v2` package is not edited.
"""

from dataclasses import dataclass

import numpy as np

from qcvol_v2 import models as v2


@dataclass(frozen=True)
class TrimmedSpec:
    inputs: int
    layers: int = 3

    @property
    def full(self):
        return v2.Spec("quantum", self.inputs, layers=self.layers)

    @property
    def active(self):
        """Mask over the v2 parameter vector; layout is (layer, qubit, RY/RZ, weight)."""
        mask = np.ones((self.layers, 2, 2, self.inputs + 1), bool)
        mask[-1, :, 1, :] = False
        return mask.ravel()

    @property
    def n_params(self):
        return int(self.active.sum())


def expand(spec, parameters):
    """Full v2 parameter vector with the inactive final-layer RZ weights set to zero."""
    full = np.zeros(spec.full.n_params)
    full[spec.active] = parameters
    return full


def build(spec):
    """Probabilities(p, x) and value_and_grad of mean log loss (p, x, labels), as in v2."""
    probabilities, value_and_grad = v2.build(spec.full)

    def probs(p, x):
        return probabilities(expand(spec, p), x)

    def loss(p, x, labels):
        value, grad = value_and_grad(expand(spec, p), x, labels)
        return value, np.asarray(grad)[spec.active]

    return probs, loss


def fit(spec, x, labels, seed, restarts=5, ridge=0.0):
    """Same L-BFGS-B procedure and restart seeding as `v2.fit`, over active weights only."""
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
