"""Validation-only test of BTC weekly volatility as an exogenous market feature."""

import argparse
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
from scipy.special import softmax

from qcvol.data import load_daily_csv
from qcvol.fresh_runner import FreshConfig
from qcvol.fresh_study import fit_lbfgs
from qcvol.metrics import log_loss
from qcvol_next.eth_upgrade import calibrated_probabilities, fit_temperature, weekend_data
from qcvol_next.weekend_models import _ry, _rz, _single


def market_data(daily, btc):
    data, weekend_scaling = weekend_data(daily)
    dates = np.asarray(daily.index, dtype="datetime64[D]")[data.target_rows]
    btc_dates = np.asarray(btc.index, dtype="datetime64[D]")
    btc_log_rv = np.log(btc.rv)
    positions = np.searchsorted(btc_dates, dates)
    if np.any(positions >= len(btc_dates)) or not np.array_equal(btc_dates[positions], dates):
        raise ValueError("BTC feature dates do not cover every target date")
    if np.any(positions < 7):
        raise ValueError("BTC feature needs seven past days")
    raw = np.array([btc_log_rv[i - 7 : i].mean() for i in positions])
    mean, scale = raw[data.train].mean(), raw[data.train].std()
    scaled = (raw - mean) / (scale if scale > 1e-12 else 1)
    return replace(data, x=np.column_stack([data.x, scaled])), {
        "weekend": weekend_scaling,
        "btc_week_mean": {"mean": float(mean), "scale": float(scale)},
    }


class MarketBorn:
    """Weekend RY circuit with a conditional BTC-volatility RZ on each qubit."""

    def __init__(self, layers):
        self.layers = layers
        self.n_params = 12 * layers

    def probabilities(self, x, parameters):
        x = np.atleast_2d(np.asarray(x, float))
        if x.shape[1] != 6 or not np.all(np.isfinite(x)):
            raise ValueError("Need six inputs: four HAR, weekend, and BTC volatility")
        weights = np.asarray(parameters, float).reshape(self.layers, 12)
        state = np.zeros((len(x), 2, 2), complex)
        state[:, 0, 0] = 1
        ones = np.ones(len(x))
        for layer in weights:
            u0 = (
                _rz(layer[10] * x[:, 5])
                @ _ry(layer[8] * x[:, 4])
                @ _single(
                    layer[0] * x[:, 0],
                    layer[1] * x[:, 1],
                    layer[4] * ones,
                    layer[5] * ones,
                )
            )
            u1 = (
                _rz(layer[11] * x[:, 5])
                @ _ry(layer[9] * x[:, 4])
                @ _single(
                    layer[2] * x[:, 2],
                    layer[3] * x[:, 3],
                    layer[6] * ones,
                    layer[7] * ones,
                )
            )
            state = u0 @ state @ np.swapaxes(u1, 1, 2)
            state[:, 1, :] = state[:, 1, ::-1].copy()
        probabilities = np.abs(state).reshape(len(x), 4) ** 2
        return probabilities / probabilities.sum(axis=1, keepdims=True)


class MarketHAR:
    def __init__(self, coefficients, residuals, edges):
        self.coefficients = coefficients
        self.residuals = residuals
        self.edges = edges

    @staticmethod
    def design(x):
        return np.column_stack([x, np.ones(len(x))])

    @classmethod
    def fit(cls, x, y, edges):
        design = cls.design(x)
        coefficients = np.linalg.lstsq(design, y, rcond=None)[0]
        residuals = np.sort(y - design @ coefficients)
        return cls(coefficients, residuals, np.asarray(edges).copy())

    def probabilities(self, x, parameters=None):
        prediction = self.design(np.atleast_2d(np.asarray(x, float))) @ self.coefficients
        thresholds = self.edges[None, :] - prediction[:, None]
        cdf = (np.searchsorted(self.residuals, thresholds, side="right") + 0.5) / (
            len(self.residuals) + 1
        )
        return np.diff(np.column_stack([np.zeros(len(cdf)), cdf, np.ones(len(cdf))]), axis=1)


class MarketSoftmax:
    n_params = 28

    def probabilities(self, x, parameters):
        design = np.column_stack([x, np.ones(len(x))])
        return softmax(design @ np.asarray(parameters).reshape(7, 4), axis=1)


class MarketNetwork:
    """35-parameter 6→2 tanh classifier with direct feature-to-logit skips."""

    n_params = 35

    def probabilities(self, x, parameters):
        x, p = np.atleast_2d(np.asarray(x, float)), np.asarray(parameters, float)
        hidden = np.tanh(x @ p[:12].reshape(6, 2) + p[12:14])
        logits = hidden @ p[14:20].reshape(2, 3) + p[20:23]
        logits += x @ p[23:35].reshape(6, 2)
        return softmax(np.column_stack([logits, np.zeros(len(x))]), axis=1)


def score_asset(asset, config, output):
    data_path = Path(f"data/{asset}usdt_daily.csv")
    data, scaling = market_data(load_daily_csv(data_path), load_daily_csv("data/btcusdt_daily.csv"))
    base = MarketHAR.fit(data.x[data.train], data.y[data.train], data.bins.edges)
    base_train = base.probabilities(data.x[data.train])
    x_train, y_train = data.x[data.train], data.labels[data.train]
    x_val, y_val = data.x[data.validation], data.labels[data.validation]
    records = []

    def fit_model(name, model, depth, seed, ridge=0.0, hybrid=False):
        def objective(parameters):
            probabilities = (
                softmax(
                    np.log(np.clip(base_train, 1e-12, 1))
                    + parameters[0] * (model.probabilities(x_train, parameters[1:]) - 0.25),
                    axis=1,
                )
                if hybrid
                else model.probabilities(x_train, parameters)
            )
            return log_loss(probabilities, y_train) + ridge * float(np.dot(parameters, parameters))

        fits = []
        for restart in range(config.restarts):
            init_seed = 710000 + 100 * seed + 10 * depth + restart
            initial = None
            if hybrid:
                rng = np.random.default_rng(init_seed)
                initial = np.r_[0.0, rng.normal(0, 0.3, model.n_params)]
            fit = fit_lbfgs(
                objective,
                (1 + model.n_params) if hybrid else model.n_params,
                init_seed,
                config.forecast_max_calls,
                config.forecast_max_iterations,
                initial,
            )
            fit["restart"] = restart
            fits.append(fit)
        best = min(fits, key=lambda row: (row["objective"], row["restart"]))
        parameters = np.asarray(best["parameters"])
        val_p = (
            softmax(
                np.log(np.clip(base.probabilities(x_val), 1e-12, 1))
                + parameters[0] * (model.probabilities(x_val, parameters[1:]) - 0.25),
                axis=1,
            )
            if hybrid
            else model.probabilities(x_val, parameters)
        )
        temperature = fit_temperature(val_p, y_val)
        calibrated = calibrated_probabilities(val_p, temperature)
        return {
            "name": name,
            "depth": depth,
            "seed": seed,
            "eligible": bool(best["eligible"]),
            "fit": best,
            "fits": fits,
            "temperature": temperature,
            "validation_raw_log_loss": log_loss(val_p, y_val),
            "validation_calibrated_log_loss": log_loss(calibrated, y_val),
            "validation_probabilities": calibrated.tolist(),
        }

    for seed in config.development_seeds:
        base_p = base.probabilities(x_val)
        base_temperature = fit_temperature(base_p, y_val)
        records.append(
            {
                "name": "market-har",
                "depth": 0,
                "seed": seed,
                "eligible": True,
                "temperature": base_temperature,
                "validation_raw_log_loss": log_loss(base_p, y_val),
                "validation_calibrated_log_loss": log_loss(
                    calibrated_probabilities(base_p, base_temperature), y_val
                ),
                "validation_probabilities": calibrated_probabilities(
                    base_p, base_temperature
                ).tolist(),
            }
        )
        for name, model, depth, ridge, hybrid in (
            ("market-quantum", MarketBorn(1), 1, 0.0, True),
            ("market-quantum", MarketBorn(2), 2, 0.0, True),
            ("market-quantum", MarketBorn(3), 3, 0.0, True),
            ("market-softmax", MarketSoftmax(), 0, 0.0, False),
            ("market-network", MarketNetwork(), 0, config.network_ridge, False),
        ):
            row = fit_model(name, model, depth, seed, ridge, hybrid)
            records.append(row)
            print(
                f"asset={asset} seed={seed} model={name} depth={depth} "
                f"validation={row['validation_calibrated_log_loss']:.6f} "
                f"eligible={row['eligible']}",
                flush=True,
            )
    output.mkdir(parents=True, exist_ok=True)
    result = {
        "asset": asset,
        "validation_only": True,
        "splits": {
            "train": len(data.labels[data.train]),
            "validation": len(data.labels[data.validation]),
        },
        "feature_scaling": scaling,
        "records": records,
    }
    (output / f"{asset}-market-validation.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset", choices=("btc", "eth", "sol", "doge"), required=True)
    parser.add_argument("--config", type=Path, default=Path("configs/btc-replication.json"))
    parser.add_argument("--output", type=Path, default=Path("results/market-signal"))
    args = parser.parse_args()
    config = FreshConfig(**json.loads(args.config.read_text()))
    score_asset(args.asset, config, args.output)


if __name__ == "__main__":
    main()
