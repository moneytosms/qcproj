"""Fresh-data study: memory inputs (B) with realism training (A), and HAR+quantum hybrids.

Design choices, fixed before any test score is computed:

* Data: Bitstamp BTC/USD daily RV from 5-minute returns, 2016-12-01 to 2026-10-19.
  Targets: train 2016-12-31..2022-12-31, validation 2023..2024, test 2025-01-01..2026-10-19.
  The paper's data is Bitstamp 2020-08-30..2023-02-28, so the test period lies entirely
  after it and after everything examined by the earlier studies.
* Realism target: moments of the real series are measured over windows of the SAME
  length as the simulated paths they are compared with. The earlier study compared
  128-day simulated paths with full-sample moments, which biases the 30-day ACF target.
* Every choice (circuit depth, realism weight) is made on validation data only.
"""

import time

import numpy as np
from scipy.optimize import minimize

from .data import DailyData, PreparedData, Standardizer, VolatilityBins, history_features
from .distribution_study import central_gradient
from .generation import generate
from .metrics import log_loss, moment_distance, moments
from .training import optimize

SPLIT_DATES = {"train_end": "2022-12-31", "validation_end": "2024-12-31"}


def prepare_dates(daily: DailyData, train_end=None, validation_end=None) -> PreparedData:
    """Chronological split by target date; scaler and volatility bins use training only."""
    train_end = np.datetime64(train_end or SPLIT_DATES["train_end"])
    validation_end = np.datetime64(validation_end or SPLIT_DATES["validation_end"])
    log_rv = np.log(daily.rv)
    rows = np.arange(30, len(log_rv))
    raw_x = np.array(
        [history_features(log_rv[t - 30 : t], daily.returns[t - 30 : t]) for t in rows]
    )
    y = log_rv[rows]
    dates = np.asarray(daily.index, dtype="datetime64[D]")[rows]
    a = int(np.searchsorted(dates, train_end, side="right"))
    b = int(np.searchsorted(dates, validation_end, side="right"))
    if min(a, b - a, len(y) - b) < 64:
        raise ValueError("Each split needs at least 64 targets")
    train, validation, test = slice(0, a), slice(a, b), slice(b, len(y))
    scaler, bins = Standardizer.fit(raw_x[train]), VolatilityBins.fit(y[train])
    return PreparedData(
        daily,
        rows,
        raw_x,
        scaler.transform(raw_x),
        y,
        bins.label(y),
        train,
        validation,
        test,
        scaler,
        bins,
    )


def split_dates(data: PreparedData):
    dates = np.asarray(data.daily.index, dtype="datetime64[D]")[data.target_rows]
    return {
        k: [str(dates[s][0]), str(dates[s][-1]), len(dates[s])]
        for k, s in (("train", data.train), ("validation", data.validation), ("test", data.test))
    }


def window_reference(y, width, count=24):
    """Mean and spread of the four moments over training windows of a fixed width."""
    y = np.asarray(y)
    if width > len(y):
        raise ValueError("Window longer than the series")
    starts = np.unique(np.linspace(0, len(y) - width, count).astype(int))
    blocks = np.array([moments(y[s : s + width]) for s in starts])
    if not np.all(np.isfinite(blocks)):
        raise ValueError("Undefined window moments")
    return blocks.mean(axis=0), np.maximum(blocks.std(axis=0), 0.02)


def path_moments(model, parameters, data, days, paths, seed, burn_in):
    generated = generate(model, parameters, data, days, paths, seed, burn_in)
    return np.mean([moments(y) for y in generated.log_rv], axis=0), generated


def fit_lbfgs(loss, n_params, seed, max_calls, max_iterations, initial=None, tolerance=1e-4):
    """Numerical-gradient L-BFGS-B, then an independent central-difference stationarity check."""
    if initial is None:
        initial = np.random.default_rng(seed).normal(0, 0.3, n_params)
    initial = np.asarray(initial, float)
    calls = [0]

    def counted(p):
        calls[0] += 1
        return loss(p)

    started = time.perf_counter()
    result = minimize(
        counted,
        initial,
        method="L-BFGS-B",
        jac="3-point",
        options={
            "maxfun": max_calls,
            "maxiter": max_iterations,
            "gtol": 1e-6,
            "ftol": 1e-13,
            "maxls": 40,
        },
    )
    gradient = float(np.max(np.abs(central_gradient(loss, result.x))))
    return {
        "parameters": result.x.tolist(),
        "initial_parameters": initial.tolist(),
        "objective": float(result.fun),
        "objective_calls": calls[0],
        "diagnostic_calls": 2 * n_params,
        "seconds": time.perf_counter() - started,
        "success": bool(result.success),
        "message": str(result.message),
        "gradient_inf": gradient,
        "eligible": bool(result.success and gradient <= tolerance),
    }


def forecast_loss(model, data, ridge=0.0, base_probabilities=None):
    """Training negative log likelihood (+ ridge). Hybrids reuse fixed base probabilities."""
    x, labels = data.x[data.train], data.labels[data.train]

    def loss(p):
        if base_probabilities is None:
            probabilities = model.probabilities(x, p)
        else:
            probabilities = model.pooled(base_probabilities, x, p)
        return log_loss(probabilities, labels) + ridge * float(np.dot(p, p))

    return loss


def realism_objective(model, data, weight, reference, scales, cfg, seed, ridge=0.0):
    nll = forecast_loss(model, data, ridge)

    def objective(p):
        m, _ = path_moments(
            model, p, data, cfg["train_days"], cfg["train_paths"], 400000 + seed, cfg["burn_in"]
        )
        distance = moment_distance(m, reference, scales)
        return nll(p) + weight * (distance if np.isfinite(distance) else 1e8)

    return objective


def fit_realism(model, data, start, weight, reference, scales, cfg, seed, ridge=0.0):
    """COBYLA from the forecast-trained solution, common random numbers per seed."""
    objective = realism_objective(model, data, weight, reference, scales, cfg, seed, ridge)
    fits = []
    for restart in range(cfg["realism_starts"]):
        initial = np.asarray(start, float).copy()
        if restart:
            jitter = 300000 + 100 * seed + restart
            initial += np.random.default_rng(jitter).normal(0, 0.03, len(initial))
        fit = optimize(objective, initial, cfg["realism_max_calls"], cfg["realism_tolerance"])
        row = fit.record()
        row.pop("objective_history", None)
        row.update({"restart": restart, "eligible": bool(fit.success)})
        fits.append(row)
    best = min(fits, key=lambda f: (f["objective"], f["restart"]))
    return best, fits
