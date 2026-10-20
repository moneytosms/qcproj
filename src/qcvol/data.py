"""Past-only features and train-fitted preprocessing for daily observations."""

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np

FEATURE_NAMES = ("log_rv_day", "log_rv_week", "log_rv_month", "return_day")
LEVEL_NAMES = ("calm", "normal", "wild", "extreme")


@dataclass
class DailyData:
    index: np.ndarray
    returns: np.ndarray
    rv: np.ndarray
    units: str

    def __post_init__(self):
        self.index = np.asarray(self.index)
        self.returns = np.asarray(self.returns, dtype=float)
        self.rv = np.asarray(self.rv, dtype=float)
        if self.rv.ndim != 1 or self.returns.shape != self.rv.shape:
            raise ValueError("RV and returns must be aligned one-dimensional arrays")
        if self.index.shape != self.rv.shape or len(self.rv) < 150:
            raise ValueError("Need at least 150 aligned daily observations")
        if not np.all(np.isfinite(self.rv)) or not np.all(np.isfinite(self.returns)):
            raise ValueError("RV and returns must be finite; do not silently impute missing days")
        if np.any(self.rv <= 0):
            raise ValueError("RV must be strictly positive for log RV")
        if len(np.unique(self.index)) != len(self.index):
            raise ValueError("Duplicate observation indexes")


def load_daily_csv(path: str | Path) -> DailyData:
    """Require sorted, consecutive ISO dates; never sort a misaligned file silently."""
    with Path(path).open(newline="") as stream:
        reader = csv.DictReader(stream)
        if not {"date", "return", "rv"}.issubset(reader.fieldnames or []):
            raise ValueError("CSV requires date,return,rv columns")
        rows = list(reader)
    dates = np.array([r["date"] for r in rows], dtype="datetime64[D]")
    if np.any(np.isnat(dates)) or np.any(np.diff(dates).astype(int) != 1):
        raise ValueError("Dates must be unique, ascending and consecutive daily observations")
    return DailyData(dates, [r["return"] for r in rows], [r["rv"] for r in rows], "csv-input-units")


def load_author_data(directory: str | Path) -> DailyData:
    """The upstream files are two columns (row ID, standardized value), not folders."""
    root = Path(directory)
    r, v = (np.loadtxt(root / name) for name in ("data-rstand", "data-ystand"))
    if r.ndim != 2 or v.ndim != 2 or r.shape[1] != 2 or r.shape != v.shape:
        raise ValueError("Expected aligned two-column author data")
    if not np.array_equal(r[:, 0], v[:, 0]) or np.any(np.diff(r[:, 0]) != 1):
        raise ValueError("Author observation IDs must agree and be consecutive")
    return DailyData(r[:, 0].astype(int), r[:, 1], v[:, 1], "author-standardized")


def sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def history_features(log_rv, returns):
    """Forecast t using observations strictly before t; requires 30 completed days."""
    y, r = np.asarray(log_rv), np.asarray(returns)
    if len(y) < 30 or len(r) != len(y):
        raise ValueError("Need 30 aligned past observations")
    return np.array([y[-1], y[-7:].mean(), y[-30:].mean(), r[-1]])


@dataclass
class Standardizer:
    mean: np.ndarray
    scale: np.ndarray

    @classmethod
    def fit(cls, x):
        scale = np.std(x, axis=0)
        return cls(np.mean(x, axis=0), np.where(scale > 1e-12, scale, 1.0))

    def transform(self, x):
        return (np.asarray(x) - self.mean) / self.scale


@dataclass
class VolatilityBins:
    edges: np.ndarray
    pools: tuple[np.ndarray, ...]

    @classmethod
    def fit(cls, train_y):
        y = np.asarray(train_y)
        edges = np.quantile(y, [0.30, 0.70, 0.95])
        if np.any(np.diff(edges) <= 0):
            raise ValueError("Quantiles coincide; four distinct volatility levels cannot be fitted")
        labels = np.searchsorted(edges, y, side="right")
        pools = tuple(y[labels == k].copy() for k in range(4))
        if any(len(pool) == 0 for pool in pools):
            raise ValueError("Empty training volatility bin; use more varied data")
        return cls(edges, pools)

    def label(self, y):
        return np.searchsorted(self.edges, y, side="right")


@dataclass
class PreparedData:
    daily: DailyData
    target_rows: np.ndarray
    raw_x: np.ndarray
    x: np.ndarray
    y: np.ndarray
    labels: np.ndarray
    train: slice
    validation: slice
    test: slice
    scaler: Standardizer
    bins: VolatilityBins

    def metadata(self):
        return {
            "units": self.daily.units,
            "feature_names": list(FEATURE_NAMES),
            "split_counts": {
                k: len(self.y[getattr(self, k)]) for k in ("train", "validation", "test")
            },
            "split_target_rows": {
                k: self.target_rows[getattr(self, k)].tolist()
                for k in ("train", "validation", "test")
            },
            "feature_mean": self.scaler.mean.tolist(),
            "feature_scale": self.scaler.scale.tolist(),
            "log_rv_bin_edges": self.bins.edges.tolist(),
            "training_bin_counts": [len(p) for p in self.bins.pools],
        }


def prepare(daily: DailyData, train_fraction=0.6, validation_fraction=0.2) -> PreparedData:
    if not (
        0 < train_fraction < 1
        and 0 < validation_fraction < 1
        and train_fraction + validation_fraction < 1
    ):
        raise ValueError("Positive train/validation fractions must sum to less than one")
    log_rv = np.log(daily.rv)
    rows = np.arange(30, len(log_rv))
    raw_x = np.array(
        [history_features(log_rv[t - 30 : t], daily.returns[t - 30 : t]) for t in rows]
    )
    y = log_rv[rows]
    a, b = int(len(y) * train_fraction), int(len(y) * (train_fraction + validation_fraction))
    if min(a, b - a, len(y) - b) < 32:
        raise ValueError("Each split needs at least 32 eligible targets for lag-30 evaluation")
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


def synthetic_data(days=360, seed=42):
    """Offline demonstration data; never described as empirical Bitcoin."""
    rng = np.random.default_rng(seed)
    y = np.empty(days)
    y[0] = -3
    for t in range(1, days):
        y[t] = -3 + 0.93 * (y[t - 1] + 3) + rng.normal(0, 0.28)
    rv = np.exp(y)
    return DailyData(np.arange(days), rng.normal(size=days) * np.sqrt(rv), rv, "synthetic-demo")
