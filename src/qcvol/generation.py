"""Recursive simulation from the shared categorical/empirical-bin observation model."""

from dataclasses import dataclass

import numpy as np

from .data import PreparedData


@dataclass
class Paths:
    log_rv: np.ndarray  # (paths, days), excludes seed history and burn-in
    returns: np.ndarray
    levels: np.ndarray


def generate(model, parameters, data: PreparedData, days=256, paths=4, seed=1000, burn_in=60):
    if days < 32 or paths < 1 or burn_in < 0:
        raise ValueError("Need days >= 32, paths >= 1 and nonnegative burn-in")
    rng = np.random.default_rng(seed)
    horizon = days + burn_in
    # Draw a fixed count of uniforms/normals regardless of chosen bins, so repeated
    # objective evaluations use common random numbers even when the path changes.
    level_u = rng.random((horizon, paths))
    within_u = rng.random((horizon, paths))
    innovation = rng.normal(size=(horizon, paths))
    first_target = data.target_rows[data.train.stop - 1] + 1
    start_y = np.log(data.daily.rv[first_target - 30 : first_target])
    start_r = data.daily.returns[first_target - 30 : first_target]
    history_y = np.empty((paths, 30 + horizon))
    history_r = np.empty_like(history_y)
    history_y[:, :30], history_r[:, :30] = start_y, start_r
    levels = np.empty((paths, horizon), dtype=int)
    for step in range(horizon):
        t = 30 + step
        raw = np.column_stack(
            [
                history_y[:, t - 1],
                history_y[:, t - 7 : t].mean(axis=1),
                history_y[:, t - 30 : t].mean(axis=1),
                history_r[:, t - 1],
            ]
        )
        probs = model.probabilities(data.scaler.transform(raw), parameters)
        k = np.minimum((level_u[step, :, None] >= probs.cumsum(axis=1)).sum(axis=1), 3)
        levels[:, step] = k
        for level, pool in enumerate(data.bins.pools):
            mask = k == level
            indexes = np.minimum((within_u[step, mask] * len(pool)).astype(int), len(pool) - 1)
            history_y[mask, t] = pool[indexes]
        history_r[:, t] = np.exp(history_y[:, t] / 2) * innovation[step]
    return Paths(history_y[:, 30 + burn_in :], history_r[:, 30 + burn_in :], levels[:, burn_in:])
