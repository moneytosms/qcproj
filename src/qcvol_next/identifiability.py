"""Count how many circuit parameters actually change the forecast (Jacobian rank).

A parameter direction is inactive when nudging it leaves every output probability
unchanged, for example an RZ just before a Z-basis measurement. Stacking the derivatives
of all outputs over many inputs gives a Jacobian whose numerical rank is the number of
locally active directions. Nominal minus rank is the number of wasted parameters.
"""

from dataclasses import dataclass

import numpy as np


def jacobian(outputs, parameters, step=1e-5):
    """Central-difference Jacobian of the flattened outputs(parameters), shape (outputs, params)."""
    p = np.asarray(parameters, float)
    columns = []
    for i in range(len(p)):
        e = np.zeros_like(p)
        e[i] = step
        columns.append((np.ravel(outputs(p + e)) - np.ravel(outputs(p - e))) / (2 * step))
    return np.column_stack(columns)


@dataclass(frozen=True)
class RankReport:
    nominal: int
    effective: int
    singular_values: np.ndarray  # relative to the largest, descending

    @property
    def inactive(self):
        return self.nominal - self.effective


def effective_parameters(outputs, n_params, seed=0, points=3, rtol=1e-7, step=1e-5):
    """Largest Jacobian rank over random parameter points drawn from N(0, 1).

    Real directions sit near 1e-2 relative singular value or above, while inactive ones
    sit at finite-difference noise (about 1e-11), so the default tolerance has wide margin
    on both sides. Using the largest rank over several points avoids an unlucky point.
    """
    rng = np.random.default_rng(seed)
    best = None
    for _ in range(points):
        s = np.linalg.svd(jacobian(outputs, rng.normal(size=n_params), step), compute_uv=False)
        s = s / s[0]
        rank = int(np.sum(s > rtol))
        if best is None or rank > best.effective:
            best = RankReport(n_params, rank, s)
    return best
