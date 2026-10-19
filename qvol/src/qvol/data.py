"""Load Takaishi's Bitcoin data and build model inputs."""
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "takaishi"


def _col(name):
    path = DATA / name
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run scripts/get_data.sh first.")
    return np.loadtxt(path)[:, 1]


def load_bitcoin():
    """Daily realized volatility and returns, as published by the author.

    Both series are rescaled by the author so their largest absolute value is 0.833,
    which keeps them inside the angle-encoding ranges of the circuit.
    """
    return _col("data-ystand"), _col("data-rstand")


def load_author_generated():
    """The author's own 50,000-step generated series from his trained circuit."""
    return _col("data-predicted-volatility"), _col("data-predicted-return")


def har_features(logrv, ret, lags=(1, 7, 30)):
    """Inputs for each day t: log RV yesterday, 7-day mean, 30-day mean, yesterday's return.

    Returns (X, idx) where X[k] is the feature row for day idx[k].
    """
    start = max(lags)
    idx = np.arange(start, len(logrv))
    rows = [[logrv[t - 1], logrv[t - lags[1]:t].mean(), logrv[t - lags[2]:t].mean(), ret[t - 1]] for t in idx]
    return np.array(rows), idx


def time_split(n, train=0.7, val=0.0):
    """Index slices for a chronological train / validation / test split."""
    a = int(train * n)
    b = int((train + val) * n)
    return slice(0, a), slice(a, b), slice(b, n)


def standardize(X, fit_rows):
    mu, sd = X[fit_rows].mean(0), X[fit_rows].std(0)
    return (X - mu) / sd, mu, sd


def level_cuts(y_train, quantiles=(0.30, 0.70, 0.95)):
    """Cut points that split log RV into calm / normal / wild / extreme."""
    return np.quantile(y_train, quantiles)


def to_levels(y, cuts):
    return np.digitize(y, cuts)
