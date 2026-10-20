"""Vectorized paper circuit, optimizer diagnostics, and explicit generation safeguards."""

import hashlib
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

from . import paper_model
from .gates import bloch

UPSTREAM_REVISION = "2fec7ee621006bcbe1b7860d05b9589a7276a8f6"
EXPECTED_HASHES = {
    "data-rstand": "012921f0e86b426fa6e1af4ae9f30f015218ab6d2d7c52c35cab6bdf2363d69c",
    "data-ystand": "0d76b3da662642453c898a8e5417a2a6d0ec7b519bd0d638f9fc82b1eec6a09e",
    "data-predicted-return": "0309b4d23b46444043d3892c708066caf78d946a4766e10d94e74d4dc511f335",
    "data-predicted-volatility": "8e3daff6ce0118f3a1e883b5e18edc76ac1560aeea443a224bb5d10f74097f84",
}


def load_verified(directory):
    root = Path(directory)
    loaded, provenance = {}, {}
    for name, expected in EXPECTED_HASHES.items():
        path = root / name
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != expected:
            raise ValueError(f"{name}: content differs from pinned upstream revision")
        rows = np.loadtxt(path)
        expected_rows = 50_000 if "predicted" in name else 913
        if rows.shape != (expected_rows, 2) or not np.all(np.isfinite(rows)):
            raise ValueError(f"{name}: invalid shape or nonfinite values")
        if not np.array_equal(rows[:, 0], np.arange(1, len(rows) + 1)):
            raise ValueError(f"{name}: unexpected observation indexes")
        loaded[name] = rows[:, 1]
        provenance[name] = {
            "sha256": digest,
            "rows": len(rows),
            "revision": UPSTREAM_REVISION,
        }
    for name in ("data-ystand", "data-predicted-volatility"):
        if np.any((loaded[name] <= 0) | (loaded[name] > 1)):
            raise ValueError("Variance outside positive paper encoding domain")
    if np.any(np.abs(loaded["data-rstand"]) > 1):
        raise ValueError("Observed return outside paper encoding domain")
    return loaded, provenance


def encoded_bloch(returns, variance):
    r, v = np.broadcast_arrays(np.asarray(returns, float), np.asarray(variance, float))
    if not np.all(np.isfinite(r)) or not np.all(np.isfinite(v)):
        raise ValueError("Inputs must be finite")
    if np.any(np.abs(r) > 1) or np.any((v < 0) | (v > 1)):
        raise ValueError("Inputs outside arcsin/arccos domains")
    a, z = np.arcsin(r) / 2, np.arccos(r * r) / 2
    c, w = np.arcsin(2 * v - 1) / 2, np.arccos(v * v) / 2
    u, t = np.cos(a) * np.exp(-1j * z), np.sin(a) * np.exp(1j * z)
    first = (np.cos(c) * u - np.sin(c) * t) * np.exp(-1j * w)
    second = (np.sin(c) * u + np.cos(c) * t) * np.exp(1j * w)
    cross = first.conj() * second
    return np.stack(
        [2 * cross.real, 2 * cross.imag, np.abs(first) ** 2 - np.abs(second) ** 2],
        axis=-1,
    )


def direction(parameters):
    theta, _, lam = parameters
    return np.array(
        [-np.sin(theta) * np.cos(lam), np.sin(theta) * np.sin(lam), np.cos(theta)]
    )


def predict(parameters, returns, variance):
    return 0.5 + 0.5 * encoded_bloch(returns, variance) @ direction(parameters)


def fit(ret, rv, restarts=10, seed=0, max_evaluations=2000, tolerance=1e-8):
    ret, rv = np.asarray(ret), np.asarray(rv)
    if ret.ndim != 1 or ret.shape != rv.shape or len(rv) < 3 or restarts < 1:
        raise ValueError("Need aligned time series and at least one restart")
    features = encoded_bloch(ret[:-1], rv[:-1])
    targets = rv[1:]
    rng = np.random.default_rng(seed)
    records = []
    for restart in range(restarts):
        initial = rng.uniform(-np.pi, np.pi, 3)
        losses = []

        def objective(parameters, losses=losses):
            loss = float(
                np.mean((0.5 + 0.5 * features @ direction(parameters) - targets) ** 2)
            )
            losses.append(loss)
            return loss

        result = minimize(
            objective,
            initial,
            method="COBYLA",
            options={"maxiter": max_evaluations, "tol": tolerance},
        )
        records.append(
            {
                "restart": restart,
                "initial": initial,
                "parameters": result.x,
                "mse": float(result.fun),
                "success": bool(result.success),
                "message": str(result.message),
                "nfev": int(result.nfev),
                "objective_history": losses,
            }
        )
    best = min(records, key=lambda row: row["mse"])
    return {
        "parameters": best["parameters"],
        "mse": best["mse"],
        "best_restart": best["restart"],
        "restarts": records,
        "training_pairs": len(targets),
        "seed": seed,
        "tolerance": tolerance,
    }


def audit_circuit(parameters, ret, rv):
    exact = paper_model.predict(parameters, ret, rv)
    fast = predict(parameters, ret, rv)
    phi = np.array(parameters, copy=True)
    phi[1] += 2.73
    b = np.array(
        [bloch(paper_model.encode(r, v)) for r, v in zip(ret, rv, strict=True)]
    )
    return {
        "samples": len(rv),
        "vectorized_max_error": float(np.max(np.abs(exact - fast))),
        "phi_max_error": float(
            np.max(np.abs(exact - paper_model.predict(phi, ret, rv)))
        ),
        "twin_max_error": float(
            np.max(np.abs(exact - (0.5 + 0.5 * b @ direction(parameters))))
        ),
        "direction_norm": float(np.linalg.norm(direction(parameters))),
    }


def generate(parameters, n_steps, r0, v0, seed=0, policy="clip", epsilon=1e-12):
    """Eq. 34 innovations stay unmodified; only out-of-domain encoding inputs clip.

    'strict' fails on domain escape. Clipping is an explicit implementation assumption
    because an unbounded Gaussian can leave the circuit's [-1,1] return domain.
    """
    if policy not in ("clip", "strict") or n_steps < 1 or not 0 < epsilon < 0.5:
        raise ValueError("Invalid generation settings")
    rng = np.random.default_rng(seed)
    innovations = rng.standard_normal(n_steps)
    r, v = float(r0), float(v0)
    out_v, out_r = np.empty(n_steps), np.empty(n_steps)
    counts = {"return_encoding_clips": 0, "variance_clips": 0}
    n = direction(parameters)
    for t in range(n_steps):
        escaped = abs(r) > 1
        if escaped and policy == "strict":
            raise ValueError(
                f"Gaussian return left encoding domain at generation step {t}"
            )
        counts["return_encoding_clips"] += int(escaped)
        raw_v = float(0.5 + 0.5 * encoded_bloch(np.clip(r, -1, 1), v) @ n)
        counts["variance_clips"] += int(raw_v < epsilon or raw_v > 1 - epsilon)
        v = float(np.clip(raw_v, epsilon, 1 - epsilon))
        r = float(np.sqrt(v) * innovations[t])
        out_v[t], out_r[t] = v, r
    return out_v, out_r, counts
