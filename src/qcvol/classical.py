"""Classical comparators share inputs, binning, loss and generation with the Born model."""

from dataclasses import dataclass

import numpy as np
from scipy.special import softmax


@dataclass(frozen=True)
class SoftmaxModel:
    n_params: int = 20

    def probabilities(self, x, parameters):
        x = np.atleast_2d(x)
        design = np.column_stack([x, np.ones(len(x))])
        return softmax(design @ np.asarray(parameters).reshape(5, 4), axis=1)


@dataclass(frozen=True)
class TinyNetwork:
    """24 parameters: 4→2 tanh (10), 2→3 reference logits (9), five skip weights.

    Class 3 is the fixed reference logit. Skip connections: all inputs→logit0,
    previous-day log RV→logit1. This is a deliberately specified small comparator.
    """

    n_params: int = 24

    def probabilities(self, x, parameters):
        x, p = np.atleast_2d(x), np.asarray(parameters)
        hidden = np.tanh(x @ p[:8].reshape(4, 2) + p[8:10])
        logits = hidden @ p[10:16].reshape(2, 3) + p[16:19]
        logits[:, 0] += x @ p[19:23]
        logits[:, 1] += x[:, 0] * p[23]
        return softmax(np.column_stack([logits, np.zeros(len(x))]), axis=1)


@dataclass
class FrequencyModel:
    frequencies: np.ndarray
    n_params: int = 3

    @classmethod
    def fit(cls, labels):
        return cls(np.bincount(labels, minlength=4) / len(labels))

    def probabilities(self, x, parameters=None):
        return np.tile(self.frequencies, (len(np.atleast_2d(x)), 1))


@dataclass
class HARModel:
    """OLS log-HAR plus empirical residual CDF, a distributional finance baseline."""

    coefficients: np.ndarray
    residuals: np.ndarray
    edges: np.ndarray
    n_params: int = 4

    @classmethod
    def fit(cls, x, y, edges):
        design = np.column_stack([np.atleast_2d(x)[:, :3], np.ones(len(x))])
        coefficients = np.linalg.lstsq(design, y, rcond=None)[0]
        residuals = np.sort(y - design @ coefficients)
        return cls(coefficients, residuals, edges.copy())

    def predict(self, x):
        x = np.atleast_2d(x)
        return np.column_stack([x[:, :3], np.ones(len(x))]) @ self.coefficients

    def probabilities(self, x, parameters=None):
        thresholds = self.edges[None, :] - self.predict(x)[:, None]
        # Half-observation smoothing prevents zero probabilities without using future data.
        cdf = (np.searchsorted(self.residuals, thresholds, side="right") + 0.5) / (
            len(self.residuals) + 1
        )
        return np.diff(np.column_stack([np.zeros(len(cdf)), cdf, np.ones(len(cdf))]), axis=1)

    def quantiles(self, x, quantiles=(0.05, 0.5, 0.95)):
        return self.predict(x)[:, None] + np.quantile(self.residuals, quantiles)[None, :]
