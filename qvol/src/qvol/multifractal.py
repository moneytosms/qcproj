"""Auditable MFDFA using the paper's cubic, two-ended detrending convention.

The scale grid/upper cutoff are not published. They are explicit configuration here.
Rolling h(2) uses the full requested rolling grid and independent shuffled controls;
full q spectra are calculated for preselected representative windows.
"""

from functools import lru_cache

import numpy as np
from scipy.special import logsumexp


@lru_cache(maxsize=256)
def _trend_basis(scale, order):
    grid = np.linspace(-1.0, 1.0, scale)
    design = np.vander(grid, N=order + 1, increasing=True)
    return np.linalg.qr(design, mode="reduced")[0]


def scale_grid(length, minimum=20, maximum=None, count=24):
    maximum = length // 5 if maximum is None else maximum
    if minimum < 5 or maximum < minimum or maximum > length // 2 or count < 6:
        raise ValueError("Need >=6 scales with 5 <= minimum <= maximum <= length/2")
    scales = np.unique(np.geomspace(minimum, maximum, count).astype(int))
    if len(scales) < 6:
        raise ValueError("Too few distinct scales for fitting")
    return scales


def analyze_batch(values, q=(2.0,), scales=None, order=3):
    """Return h(q), regression SE and log fluctuation functions for independent rows.

    SE is an OLS scale-fit diagnostic, not an uncertainty interval for the process H.
    No artificial variance floor is used: degenerate input is rejected.
    """
    x = np.atleast_2d(np.asarray(values, float))
    q = np.asarray(q, float)
    if x.ndim != 2 or not np.all(np.isfinite(x)) or np.any(np.std(x, axis=1) < 1e-14):
        raise ValueError("MFDFA needs finite nonconstant series")
    if q.ndim != 1 or len(q) == 0 or not np.all(np.isfinite(q)):
        raise ValueError("q must be a finite one-dimensional array")
    n = x.shape[1]
    scales = scale_grid(n) if scales is None else np.asarray(scales)
    if scales.ndim != 1 or len(scales) < 3 or np.any(scales != scales.astype(int)):
        raise ValueError("Need at least three integer scales")
    if np.any(np.diff(scales) <= 0) or scales[0] <= order + 1 or scales[-1] > n // 2:
        raise ValueError("Scales must increase and permit detrending and two segments")
    scales = scales.astype(int)
    profile = np.cumsum(x - x.mean(axis=1, keepdims=True), axis=1)
    log_f = np.empty((len(x), len(scales), len(q)))
    nonzero = np.abs(q) > 1e-12
    for j, scale in enumerate(scales):
        count = n // scale
        segments = np.concatenate(
            [
                profile[:, : count * scale].reshape(len(x), count, scale),
                profile[:, n - count * scale :].reshape(len(x), count, scale),
            ],
            axis=1,
        )
        basis = _trend_basis(int(scale), order)
        residual = segments - (segments @ basis) @ basis.T
        variance = np.mean(residual**2, axis=2)
        if np.any(variance <= 1e-28):
            raise ValueError("Degenerate detrended segment variance")
        log_variance = np.log(variance)
        log_f[:, j, ~nonzero] = 0.5 * log_variance.mean(axis=1, keepdims=True)
        log_f[:, j, nonzero] = (
            logsumexp(log_variance[:, :, None] * q[nonzero] / 2, axis=1)
            - np.log(2 * count)
        ) / q[nonzero]
    log_s = np.log(scales)
    centered_s = log_s - log_s.mean()
    h = np.einsum("s,bsq->bq", centered_s, log_f) / np.sum(centered_s**2)
    intercept = log_f.mean(axis=1) - h * log_s.mean()
    fitted = intercept[:, None, :] + h[:, None, :] * log_s[None, :, None]
    sse = np.sum((log_f - fitted) ** 2, axis=1)
    stderr = np.sqrt(sse / (len(scales) - 2) / np.sum(centered_s**2))
    sst = np.sum((log_f - log_f.mean(axis=1, keepdims=True)) ** 2, axis=1)
    r_squared = 1 - sse / np.maximum(sst, 1e-30)
    return {
        "q": q,
        "scales": scales,
        "h": h,
        "stderr": stderr,
        "r_squared": r_squared,
        "log_f": log_f,
    }


def spectrum(values, q=None, scales=None):
    q = np.linspace(-5.0, 5.0, 501) if q is None else np.asarray(q)
    if len(q) < 3 or np.any(np.diff(q) <= 0):
        raise ValueError("Spectrum needs at least three increasing q values")
    result = analyze_batch(values, q=q, scales=scales)
    tau = q * result["h"] - 1
    alpha = np.gradient(tau, q, axis=1)
    return {
        **result,
        "tau": tau,
        "alpha": alpha,
        "f_alpha": q * alpha - tau,
        "alpha_width": np.ptp(alpha, axis=1),
        "h_width": result["h"][:, 0] - result["h"][:, -1],
    }


def rolling_starts(length, window=913, step=365):
    if window < 32 or step < 1 or length < window:
        raise ValueError("Need a positive step and enough data for one complete window")
    return np.arange(0, length - window + 1, step)


def rolling_h2(values, window=913, step=365, shuffles=20, seed=0, scales=None):
    x = np.asarray(values, float)
    starts = rolling_starts(len(x), window, step)
    if shuffles < 1:
        raise ValueError("Need at least one shuffled control")
    rng = np.random.default_rng(seed)
    h, se, r2, shuffled = [], [], [], []
    for start in starts:
        segment = x[start : start + window]
        rows = np.vstack(
            [segment, *[rng.permutation(segment) for _ in range(shuffles)]]
        )
        result = analyze_batch(rows, scales=scales)
        h.append(result["h"][0, 0])
        se.append(result["stderr"][0, 0])
        r2.append(result["r_squared"][0, 0])
        shuffled.append(result["h"][1:, 0])
    return {
        "starts": starts,
        "h2": np.asarray(h),
        "fit_stderr": np.asarray(se),
        "fit_r_squared": np.asarray(r2),
        "shuffled_h2": np.asarray(shuffled),
        "shuffled_mean": np.mean(shuffled, axis=1),
        "shuffled_std": np.std(shuffled, axis=1, ddof=1) if shuffles > 1 else None,
    }
