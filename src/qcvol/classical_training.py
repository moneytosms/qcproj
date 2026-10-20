"""Analytic derivatives to investigate the previously capped short-network restarts."""

import time

import numpy as np
from scipy.optimize import minimize
from scipy.special import softmax

from .distribution_models import ShortNetwork, short_inputs
from .distribution_study import central_gradient
from .metrics import log_loss


def network_loss_gradient(parameters, x, labels, ridge=0.0):
    p = np.asarray(parameters)
    x = short_inputs(x)
    hidden = np.tanh(x @ p[:6].reshape(2, 3) + p[6:9])
    logits = hidden @ p[9:18].reshape(3, 3) + p[18:21] + x[:, :1] * p[21:24]
    probabilities = softmax(np.column_stack([logits, np.zeros(len(x))]), axis=1)
    delta = probabilities[:, :3].copy()
    for k in range(3):
        delta[:, k] -= labels == k
    observed = probabilities[np.arange(len(x)), labels]
    delta[observed < 1e-12] = 0  # derivative of the repository's explicitly clipped NLL
    delta /= len(x)
    dh = (delta @ p[9:18].reshape(3, 3).T) * (1 - hidden**2)
    gradient = np.r_[
        (x.T @ dh).ravel(),
        dh.sum(axis=0),
        (hidden.T @ delta).ravel(),
        delta.sum(axis=0),
        (x[:, :1] * delta).sum(axis=0),
    ]
    return log_loss(probabilities, labels) + ridge * float(p @ p), gradient + 2 * ridge * p


def continue_network(initial, data, max_calls=20000, max_iterations=10000, ridge=0.0):
    started = time.perf_counter()
    history = []
    best = [float("inf"), None]

    def objective(p):
        value, gradient = network_loss_gradient(
            p, data.x[data.train], data.labels[data.train], ridge
        )
        history.append(value)
        if value < best[0]:
            best[:] = [value, p.copy()]
        return value, gradient

    result = minimize(
        objective,
        np.array(initial),
        method="L-BFGS-B",
        jac=True,
        options={
            "maxfun": max_calls,
            "maxiter": max_iterations,
            "ftol": 1e-14,
            "gtol": 1e-7,
            "maxls": 50,
        },
    )
    parameters = best[1]
    model = ShortNetwork()
    loss = lambda p: (
        log_loss(model.probabilities(data.x[data.train], p), data.labels[data.train])
        + ridge * float(p @ p)
    )
    gradient = float(np.max(np.abs(central_gradient(loss, parameters))))
    return {
        "parameters": parameters.tolist(),
        "ridge": ridge,
        "initial_parameters": np.array(initial).tolist(),
        "objective": float(best[0]),
        "initial_objective": history[0],
        "objective_history": history,
        "success": bool(result.success),
        "message": str(result.message),
        "gradient_inf": gradient,
        "eligible": bool(result.success and gradient <= 1e-4),
        "objective_calls": len(history),
        "gradient_evaluations": len(history),
        "diagnostic_calls": 2 * len(parameters),
        "seconds": time.perf_counter() - started,
        "optimized_parameter_count": len(parameters),
        "method": "L-BFGS-B with analytic backpropagation",
    }


def sensitivity_rank(model, parameters, x):
    p = np.asarray(parameters)
    directions = np.eye(len(p)) * 1e-5
    jac = np.column_stack(
        [
            (
                (model.probabilities(x, p + d)[:, :3] - model.probabilities(x, p - d)[:, :3]) / 2e-5
            ).ravel()
            for d in directions
        ]
    )
    singular = np.linalg.svd(jac, compute_uv=False)
    threshold = max(1e-10, 1e-6 * singular[0])
    return {
        "singular_values": singular.tolist(),
        "relative_tolerance": 1e-6,
        "threshold": float(threshold),
        "local_rank": int(np.sum(singular > threshold)),
        "searched_coordinates": len(p),
        "diagnostic_probability_calls": 2 * len(p),
        "caution": "Local sensitivity rank depends on fit and tolerance; not structural dimension",
    }
