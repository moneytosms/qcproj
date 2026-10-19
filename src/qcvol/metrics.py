"""Explicit metric conventions; undefined estimates are NaN internally, null in JSON."""

import numpy as np
from scipy.optimize import brentq
from scipy.special import logsumexp, xlogy
from scipy.stats import chi2, norm, wasserstein_distance

MOMENT_NAMES = ("acf_1", "acf_7", "acf_30", "vol_of_vol")


def validate_probabilities(probabilities, labels=None):
    p = np.asarray(probabilities, dtype=float)
    if p.ndim != 2 or p.shape[1] != 4 or not np.all(np.isfinite(p)):
        raise ValueError("Need a finite (days,4) probability matrix")
    if np.any(p < 0) or not np.allclose(p.sum(axis=1), 1, atol=1e-10):
        raise ValueError("Probabilities must be nonnegative and sum to one")
    if labels is not None:
        y = np.asarray(labels)
        if y.shape != (len(p),) or not np.all(np.isin(y, np.arange(4))):
            raise ValueError("One label in 0..3 is required per probability row")
    return p


def log_loss(probabilities, labels):
    p = validate_probabilities(probabilities, labels)
    return float(-np.log(np.clip(p[np.arange(len(p)), labels], 1e-12, 1)).mean())


def ranked_probability_score(probabilities, labels):
    """Mean over three ordered cut points (range 0..1); some sources use their sum."""
    p = validate_probabilities(probabilities, labels)
    observed = np.asarray(labels)[:, None] <= np.arange(3)
    return float(np.mean((p.cumsum(axis=1)[:, :3] - observed) ** 2))


def calibration(probabilities, labels, bins=10):
    p = validate_probabilities(probabilities, labels)[:, 3]
    group = np.minimum((p * bins).astype(int), bins - 1)
    return [
        {
            "lower": j / bins,
            "upper": (j + 1) / bins,
            "count": int((group == j).sum()),
            "mean_probability": float(p[group == j].mean()) if np.any(group == j) else None,
            "observed_frequency": float((np.asarray(labels)[group == j] == 3).mean())
            if np.any(group == j)
            else None,
        }
        for j in range(bins)
    ]


def forecast_scores(probabilities, labels):
    return {
        "log_loss": log_loss(probabilities, labels),
        "rps_normalized": ranked_probability_score(probabilities, labels),
        "extreme_brier": float(np.mean((np.asarray(probabilities)[:, 3] - (labels == 3)) ** 2)),
        "extreme_calibration": calibration(probabilities, labels),
    }


def acf(values, lag):
    y = np.asarray(values, dtype=float)
    if len(y) <= lag or np.std(y[:-lag]) < 1e-12 or np.std(y[lag:]) < 1e-12:
        return np.nan
    return float(np.corrcoef(y[:-lag], y[lag:])[0, 1])


def moments(log_rv):
    y = np.asarray(log_rv)
    return np.array([acf(y, lag) for lag in (1, 7, 30)] + [float(np.std(np.diff(y)))])


def moment_scales(train_y):
    """Descriptive scale from overlapping training windows, not confidence intervals."""
    y = np.asarray(train_y)
    width = min(128, max(40, len(y) // 3))
    starts = np.unique(np.linspace(0, len(y) - width, 12).astype(int))
    blocks = np.array([moments(y[s : s + width]) for s in starts])
    if not np.all(np.isfinite(blocks)):
        raise ValueError("Training moments undefined (constant or insufficient data)")
    return np.maximum(np.std(blocks, axis=0), 0.02)


def moment_distance(generated_moments, reference_moments, scales):
    m = np.asarray(generated_moments)
    if not np.all(np.isfinite(m)):
        return float("inf")
    return float(np.sum(((m - np.asarray(reference_moments)) / scales) ** 2))


def hill_tail_index(returns):
    """Hill alpha of |return|, sqrt(n) largest values; small samples are not estimated."""
    tail = np.sort(np.abs(returns))
    k = max(20, int(np.sqrt(len(tail))))
    if len(tail) < 200 or len(tail) <= k or tail[-k - 1] <= 0:
        return np.nan
    denominator = np.mean(np.log(tail[-k:] / tail[-k - 1]))
    return float(1 / denominator) if denominator > 0 else np.nan


def mfdfa(values, order=3):
    """Two-ended, cubic-detrended MFDFA; diagnostic defaults, not paper replication.

    11 q values [-5,5], ~12 log scales [20,N/4], excluding scales with zero variance.
    Save all arrays so the fit can be inspected rather than trusting a single exponent.
    """
    x = np.asarray(values, float)
    if len(x) < 160 or not np.all(np.isfinite(x)) or np.std(x) < 1e-12:
        return {"available": False, "reason": "Need >=160 finite nonconstant observations"}
    scales = np.unique(np.geomspace(20, len(x) // 4, 12).astype(int))
    if len(scales) < 6:
        return {"available": False, "reason": "Insufficient distinct scaling windows"}
    profile = np.cumsum(x - x.mean())
    q = np.arange(-5.0, 6.0)
    fluctuation = []
    for scale in scales:
        segments = []
        for origin in (0, len(x) % scale):
            for start in range(origin, len(x) - scale + 1, scale):
                segment = profile[start : start + scale]
                grid = np.linspace(-1, 1, scale)
                fit = np.polynomial.polynomial.polyfit(grid, segment, order)
                residual = segment - np.polynomial.polynomial.polyval(grid, fit)
                segments.append(np.mean(residual**2))
        variances = np.asarray(segments)
        if np.any(variances <= 1e-30):
            return {"available": False, "reason": "Degenerate detrended variance"}
        logs = np.log(variances)
        fluctuation.append(
            [
                float(0.5 * logs.mean())
                if power == 0
                else float((logsumexp(power / 2 * logs) - np.log(len(logs))) / power)
                for power in q
            ]
        )
    log_f = np.asarray(fluctuation)
    h = np.polyfit(np.log(scales), log_f, 1)[0]
    fitted = np.outer(np.log(scales), h) + np.polyfit(np.log(scales), log_f, 1)[1]
    total = ((log_f - log_f.mean(axis=0)) ** 2).sum(axis=0)
    r2 = 1 - ((log_f - fitted) ** 2).sum(axis=0) / np.maximum(total, 1e-30)
    tau = q * h - 1
    alpha = np.gradient(tau, q)
    return {
        "available": True,
        "order": order,
        "q": q.tolist(),
        "scales": scales.tolist(),
        "h": h.tolist(),
        "fit_r2": r2.tolist(),
        "tau": tau.tolist(),
        "alpha": alpha.tolist(),
        "f_alpha": (q * alpha - tau).tolist(),
        "h2": float(h[np.where(q == 2)[0][0]]),
        "spectrum_width": float(np.ptp(alpha)),
        "caution": "Finite-sample diagnostic; no scaling-range validation or uncertainty",
    }


def path_diagnostics(log_rv, returns, reference_y, scales, seed=2000):
    y = np.asarray(log_rv)
    rng = np.random.default_rng(seed)
    increments = np.diff(y)
    return {
        "moments": dict(zip(MOMENT_NAMES, moments(y).tolist())),
        "moment_distance": moment_distance(moments(y), moments(reference_y), scales),
        "wasserstein_log_rv": float(wasserstein_distance(y, reference_y)),
        "hill_return_tail_index": hill_tail_index(returns),
        "mfdfa_log_rv_increments": mfdfa(increments),
        "mfdfa_shuffled_increments": mfdfa(rng.permutation(increments)),
        "mfdfa_returns": mfdfa(returns),
        "mfdfa_shuffled_returns": mfdfa(rng.permutation(returns)),
    }


def kupiec_test(violations, alpha=0.05):
    """Unconditional coverage of return VaR; not volatility-bin exceedance frequency."""
    v = np.asarray(violations, dtype=bool)
    n, hits = len(v), int(v.sum())
    if n == 0 or not 0 < alpha < 1:
        raise ValueError("Need observations and alpha in (0,1)")
    rate = hits / n
    null = xlogy(hits, alpha) + xlogy(n - hits, 1 - alpha)
    alternative = xlogy(hits, rate) + xlogy(n - hits, 1 - rate)
    lr = float(max(0, 2 * (alternative - null)))
    return {
        "n": n,
        "violations": hits,
        "alpha": alpha,
        "lr": lr,
        "p_value": float(chi2.sf(lr, 1)),
        "caution": "Asymptotic coverage test; low power in short series",
    }


def return_quantiles(probabilities, pools, alpha=0.05):
    """Exact Gaussian/empirical-RV mixture CDF inversion under the assumed return law."""
    p = validate_probabilities(probabilities)
    if not 0 < alpha < 0.5:
        raise ValueError("Lower-tail alpha must be in (0,.5)")
    sigmas = [np.exp(pool / 2) for pool in pools]
    bound = 12 * max(s.max() for s in sigmas)
    return np.array(
        [
            brentq(
                lambda z, row=row: (
                    sum(weight * norm.cdf(z / s).mean() for weight, s in zip(row, sigmas)) - alpha
                ),
                -bound,
                0,
            )
            for row in p
        ]
    )
