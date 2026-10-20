"""Training-only quantile HAR and explicitly calibrated return-GARCH references."""

import time
from dataclasses import dataclass

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csc_matrix, eye, hstack

QUANTILES = np.array(
    [0.01, 0.025, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.975, 0.99]
)


def quantile_design(x, short=False):
    x = np.atleast_2d(x)
    inputs = x[:, [0, 3]] if short else x[:, :3]
    return np.column_stack([inputs, np.ones(len(x))])


def quantile_scores(predictions, y, quantiles=QUANTILES):
    predictions, y, quantiles = np.asarray(predictions), np.asarray(y), np.asarray(quantiles)
    if predictions.shape != (len(y), len(quantiles)) or not np.all(np.isfinite(predictions)):
        raise ValueError("Need finite predictions for every row and quantile")
    residual = y[:, None] - predictions
    pinball = np.maximum(quantiles * residual, (quantiles - 1) * residual).mean(axis=0)
    lo, hi = (predictions[:, np.flatnonzero(np.isclose(quantiles, q))[0]] for q in (0.05, 0.95))
    width = hi - lo
    interval_score = width + 20 * np.maximum(lo - y, 0) + 20 * np.maximum(y - hi, 0)
    return {
        "mean_pinball": float(pinball.mean()),
        "pinball_by_quantile": pinball.tolist(),
        "coverage_90": float(np.mean((lo <= y) & (y <= hi))),
        "mean_width_90": float(width.mean()),
        "interval_score_90": float(interval_score.mean()),
    }


def empirical_bin_quantiles(probabilities, pools, quantiles=QUANTILES):
    """Left-continuous inverse of the common categorical/empirical-bin law."""
    values = np.concatenate(pools)
    order = np.argsort(values)
    weights = np.concatenate(
        [
            probabilities[:, k : k + 1] / len(pool) * np.ones((1, len(pool)))
            for k, pool in enumerate(pools)
        ],
        axis=1,
    )[:, order]
    cumulative = weights.cumsum(axis=1)
    result = []
    for row in cumulative:
        indices = np.minimum(np.searchsorted(row, quantiles, side="left"), len(values) - 1)
        result.append(values[order][indices])
    return np.array(result)


@dataclass
class QuantileHAR:
    coefficients: np.ndarray
    quantiles: np.ndarray
    short: bool
    tail_floor: float
    frequencies: np.ndarray
    edges: np.ndarray

    @property
    def n_params(self):
        return self.coefficients.size

    @classmethod
    def fit(cls, x, y, edges, short=False, quantiles=QUANTILES):
        started = time.perf_counter()
        design = quantile_design(x, short)
        n, p = design.shape
        aeq = hstack(
            [csc_matrix(design), eye(n, format="csc"), -eye(n, format="csc")], format="csc"
        )
        coefficients, records = [], []
        for tau in quantiles:
            cost = np.r_[np.zeros(p), np.full(n, tau), np.full(n, 1 - tau)]
            result = linprog(
                cost,
                A_eq=aeq,
                b_eq=y,
                bounds=[(None, None)] * p + [(0, None)] * (2 * n),
                method="highs",
                options={"dual_feasibility_tolerance": 1e-8, "primal_feasibility_tolerance": 1e-8},
            )
            if not result.success:
                raise RuntimeError(f"Quantile LP failed at {tau}: {result.message}")
            beta, u, v = result.x[:p], result.x[p : p + n], result.x[p + n :]
            dual = result.eqlin.marginals
            primal_error = np.max(np.abs(design @ beta + u - v - y))
            dual_error = max(
                np.max(np.abs(design.T @ dual)), np.max(dual - tau), np.max(-dual - (1 - tau)), 0
            )
            complementarity = max(
                np.max(np.abs(u * (tau - dual))), np.max(np.abs(v * (1 - tau + dual)))
            )
            gap = abs(cost @ result.x - y @ dual) / n
            coefficients.append(beta)
            records.append(
                {
                    "quantile": float(tau),
                    "success": bool(result.success),
                    "iterations": int(result.nit),
                    "objective": float(result.fun / n),
                    "primal_error": float(primal_error),
                    "dual_error": float(dual_error),
                    "complementarity": float(complementarity),
                    "duality_gap_per_row": float(gap),
                    "dual": dual.tolist(),
                }
            )
        model = cls(
            np.array(coefficients).T,
            np.array(quantiles),
            short,
            max(0.02 * np.std(y), 1e-6),
            np.bincount(np.searchsorted(edges, y, side="right"), minlength=4) / n,
            edges.copy(),
        )
        return model, {
            "quantile_fits": records,
            "seconds": time.perf_counter() - started,
            "optimized_parameter_count": model.n_params,
            "solver": "HiGHS linear program",
            "eligible": all(
                max(
                    r["primal_error"],
                    r["dual_error"],
                    r["complementarity"],
                    r["duality_gap_per_row"],
                )
                <= 1e-6
                for r in records
            ),
        }

    def raw_quantiles(self, x):
        return quantile_design(x, self.short) @ self.coefficients

    def predict_quantiles(self, x):
        # Rearrangement is prespecified, not a validation-fitted crossing repair.
        return np.sort(self.raw_quantiles(x), axis=1)

    def probabilities(self, x, parameters=None):
        predictions = self.predict_quantiles(x)
        rows = []
        for q in predictions:
            left_scale = max(
                (q[1] - q[0]) / np.log(self.quantiles[1] / self.quantiles[0]), self.tail_floor
            )
            right_scale = max(
                (q[-1] - q[-2]) / np.log((1 - self.quantiles[-2]) / (1 - self.quantiles[-1])),
                self.tail_floor,
            )
            # Coalesce ties; selecting the rightmost probability yields a valid CDF.
            keep = np.r_[q[1:] != q[:-1], True]
            cdf = np.interp(self.edges, q[keep], self.quantiles[keep])
            left = self.edges < q[0]
            right = self.edges > q[-1]
            cdf[left] = self.quantiles[0] * np.exp((self.edges[left] - q[0]) / left_scale)
            cdf[right] = 1 - (1 - self.quantiles[-1]) * np.exp(
                -(self.edges[right] - q[-1]) / right_scale
            )
            probability = np.diff(np.r_[0, cdf, 1])
            rows.append((1 - 1e-6) * probability + 1e-6 * self.frequencies)
        return np.array(rows)


def garch_variance(returns, parameters, backcast):
    """Same initial condition as arch GARCH(1,1); no future returns enter h[t]."""
    omega, alpha, beta = parameters
    h = np.empty(len(returns))
    h[0] = omega + (alpha + beta) * backcast
    for t in range(1, len(h)):
        h[t] = omega + alpha * returns[t - 1] ** 2 + beta * h[t - 1]
    return h


@dataclass
class CalibratedGARCH:
    parameters: np.ndarray
    return_scale: float
    backcast: float
    calibration: np.ndarray
    residuals: np.ndarray
    edges: np.ndarray
    n_params: int = 5  # three return-GARCH + two RV observation-calibration coefficients

    def mean_log_rv(self, variance):
        return self.calibration[0] + self.calibration[1] * np.log(variance * self.return_scale**2)

    def probabilities_from_variance(self, variance):
        thresholds = self.edges[None, :] - self.mean_log_rv(np.atleast_1d(variance))[:, None]
        cdf = (np.searchsorted(self.residuals, thresholds, side="right") + 0.5) / (
            len(self.residuals) + 1
        )
        return np.diff(np.column_stack([np.zeros(len(cdf)), cdf, np.ones(len(cdf))]), axis=1)

    def predict_quantiles(self, variance, quantiles=QUANTILES):
        return (
            self.mean_log_rv(np.atleast_1d(variance))[:, None]
            + np.quantile(self.residuals, quantiles)[None, :]
        )

    def filter(self, data):
        # Filter only through the validation block, never compute a test forecast.
        rows = data.target_rows[: data.validation.stop]
        return garch_variance(
            data.daily.returns[rows] / self.return_scale, self.parameters, self.backcast
        )

    @classmethod
    def fit(cls, data, max_iterations=5000):
        from arch import arch_model

        started = time.perf_counter()
        rows = data.target_rows[data.train]
        r = data.daily.returns[rows]
        scale = float(np.sqrt(np.mean(r * r)))
        scaled = r / scale
        backcast = float(np.mean((data.daily.returns[: rows[0]] / scale) ** 2))
        model = arch_model(scaled, mean="Zero", vol="GARCH", p=1, q=1, dist="normal", rescale=False)
        fits = []
        # Valid stationary starts; selection uses only return likelihood, not RV validation.
        for alpha, beta in ((0.05, 0.9), (0.15, 0.7), (0.3, 0.4), (0.05, 0.5), (0.2, 0.79)):
            initial = np.array([1 - alpha - beta, alpha, beta])
            fit = model.fit(
                disp="off",
                update_freq=0,
                starting_values=initial,
                backcast=backcast,
                options={"maxiter": max_iterations, "ftol": 1e-10},
                show_warning=False,
            )
            params = fit.params.to_numpy()
            h = garch_variance(scaled, params, backcast)
            relative_error = float(
                np.max(np.abs(h - fit.conditional_volatility**2) / np.maximum(h, 1e-12))
            )
            result = fit.optimization_result
            fits.append(
                {
                    "parameters": params.tolist(),
                    "initial_parameters": initial.tolist(),
                    "objective": float(-fit.loglikelihood),
                    "success": bool(fit.convergence_flag == 0),
                    "message": str(result.message),
                    "objective_calls": int(result.nfev),
                    "gradient_evaluations": int(result.njev),
                    "recursion_relative_error": relative_error,
                    "kkt": garch_kkt(scaled, params, backcast),
                }
            )
        winner = min(fits, key=lambda f: f["objective"])
        parameters = np.array(winner["parameters"])
        h = garch_variance(scaled, parameters, backcast)
        design = np.column_stack([np.ones(len(h)), np.log(h * scale**2)])
        calibration = np.linalg.lstsq(design, data.y[data.train], rcond=None)[0]
        residuals = np.sort(data.y[data.train] - design @ calibration)
        calibrated = cls(
            parameters, scale, backcast, calibration, residuals, data.bins.edges.copy()
        )
        return calibrated, {
            "fits": fits,
            "selected_start": fits.index(winner),
            "seconds": time.perf_counter() - started,
            "objective_calls": sum(f["objective_calls"] for f in fits),
            "eligible": bool(
                winner["success"]
                and winner["recursion_relative_error"] < 1e-8
                and winner["kkt"]["feasible"]
                and winner["kkt"]["stationarity_inf"] <= 1e-4
            ),
            "optimized_parameter_count": 5,
            "return_likelihood_rows": len(r),
        }


def garch_likelihood_gradient(returns, parameters, backcast):
    """Analytic derivative of mean Gaussian negative likelihood, fixed backcast."""
    beta = parameters[2]
    h = garch_variance(returns, parameters, backcast)
    derivatives = np.empty((len(h), 3))
    derivatives[0] = [1, backcast, backcast]
    for t in range(1, len(h)):
        derivatives[t] = [1, returns[t - 1] ** 2, h[t - 1]] + beta * derivatives[t - 1]
    factor = 0.5 * (1 / h - returns**2 / h**2)
    return float(0.5 * np.mean(np.log(2 * np.pi * h) + returns**2 / h)), np.mean(
        factor[:, None] * derivatives, axis=0
    )


def garch_kkt(returns, parameters, backcast):
    from scipy.optimize import nnls

    value, gradient = garch_likelihood_gradient(returns, parameters, backcast)
    omega, alpha, beta = parameters
    margins = np.array([omega, alpha, beta, 1 - alpha - beta])
    directions = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1], [0, -1, -1]])
    active = margins <= 1e-6
    if active.any():
        multipliers, _ = nnls(directions[active].T, gradient)
        residual = gradient - directions[active].T @ multipliers
    else:
        multipliers = np.array([])
        residual = gradient
    return {
        "mean_negative_loglikelihood": value,
        "gradient": gradient.tolist(),
        "constraint_margins": margins.tolist(),
        "active_constraints": np.flatnonzero(active).tolist(),
        "multipliers": multipliers.tolist(),
        "stationarity_inf": float(np.max(np.abs(residual))),
        "feasible": bool(np.min(margins) >= -1e-8),
    }
