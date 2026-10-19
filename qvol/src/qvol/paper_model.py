"""Takaishi's single-qubit volatility model (Fractal Fract. 2026, 10(7):442), rebuilt in NumPy.

Circuit: RY(arcsin r) RZ(arccos r^2) RY(arcsin(2 s - 1)) RZ(arccos s^2) U(theta, phi, lam),
where r is yesterday's return and s is yesterday's volatility. The forecast is P0, the
probability of measuring |0>, computed exactly (no sampling), as in the paper.
"""
import numpy as np
from scipy.optimize import minimize

from .gates import ry, rz, u3, bloch


def encode(r, s):
    """One-qubit state after the four data-encoding gates."""
    psi = np.array([1, 0], complex)
    for g in (ry(np.arcsin(r)), rz(np.arccos(r * r)), ry(np.arcsin(2 * s - 1)), rz(np.arccos(s * s))):
        psi = g @ psi
    return psi


def p0(r, s, theta, phi, lam):
    return abs((u3(theta, phi, lam) @ encode(r, s))[0]) ** 2


def p0_closed_form(r, s, theta, lam):
    """Exact closed form: P0 = 1/2 + 1/2 n(theta, lam) . b(r, s). Note: phi does not appear."""
    n = np.array([-np.sin(theta) * np.cos(lam), np.sin(theta) * np.sin(lam), np.cos(theta)])
    return 0.5 + 0.5 * n @ bloch(encode(r, s))


def predict(params, ret, vol):
    theta, phi, lam = params
    return np.array([p0(r, s, theta, phi, lam) for r, s in zip(ret, vol)])


def fit(ret, vol, restarts=10, seed=0, maxiter=2000):
    """Fit (theta, phi, lam) by minimizing mean squared error of the next-day forecast, with COBYLA."""
    x_r, x_s, target = ret[:-1], vol[:-1], vol[1:]
    rng = np.random.default_rng(seed)

    def loss(p):
        return np.mean((predict(p, x_r, x_s) - target) ** 2)

    best = None
    for _ in range(restarts):
        res = minimize(loss, rng.uniform(-np.pi, np.pi, 3), method="COBYLA", options={"maxiter": maxiter})
        if best is None or res.fun < best.fun:
            best = res
    return best.x, best.fun


def generate(params, n_steps, r0, s0, ret_scale=1.0, seed=0, eps=1e-6):
    """Run the trained circuit recursively to make a synthetic history.

    v[t+1] = P0(r[t], v[t]);  r[t+1] = ret_scale * sqrt(v[t+1]) * N(0, 1).
    The paper states the generic rule r = sigma * epsilon; ret_scale lets us test other scalings.
    Values are kept inside the encoding domains (|r| < 1, 0 < v < 1).
    """
    theta, phi, lam = params
    rng = np.random.default_rng(seed)
    r, s = r0, s0
    out_v, out_r = np.empty(n_steps), np.empty(n_steps)
    for t in range(n_steps):
        s = min(max(p0(r, s, theta, phi, lam), eps), 1 - eps)
        r = float(np.clip(ret_scale * np.sqrt(s) * rng.standard_normal(), -0.999, 0.999))
        out_v[t], out_r[t] = s, r
    return out_v, out_r
