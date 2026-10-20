"""Calendar-aware hybrid readouts and analytic derivatives, without changing old models."""

from dataclasses import dataclass

import numpy as np
from scipy.special import logsumexp, softmax


def weekday(dates):
    dates = np.asarray(dates, dtype="datetime64[D]")
    if np.any(np.isnat(dates)):
        raise ValueError("Finite UTC dates required")
    return (dates.astype("int64") + 3) % 7  # Monday 0; 1970-01-01 was Thursday.


def calendar_inputs(har, dates, calendar=True):
    har = np.atleast_2d(np.asarray(har, float))
    dow = np.atleast_1d(weekday(dates))
    if har.shape[1] != 4 or len(har) != len(dow) or not np.all(np.isfinite(har)):
        raise ValueError("Need four finite HAR inputs and one date per row")
    if not calendar:
        return har.copy()
    return np.column_stack([har, (dow[:, None] == np.arange(1, 7)).astype(float)])


def recency_weights(dates, half_life=0):
    """Use completed training dates only; normalized weights sum to one."""
    dates = np.asarray(dates, dtype="datetime64[D]")
    if dates.ndim != 1 or len(dates) < 1 or np.any(np.isnat(dates)):
        raise ValueError("Need finite training dates")
    if np.any(np.diff(dates).astype(int) <= 0) or half_life < 0 or not np.isfinite(half_life):
        raise ValueError("Dates must ascend and half life must be nonnegative")
    age = (dates[-1] - dates).astype(float)
    w = np.ones(len(age)) if half_life == 0 else np.exp2(-age / half_life)
    return w / w.sum()


def active_angles(layers):
    if type(layers) is not int or layers not in (1, 2, 3, 4):
        raise ValueError("Choose circuit layers 1..4")
    return np.delete(np.arange(8 * layers), [8 * (layers - 1) + 5, 8 * (layers - 1) + 7])


def stored_angles(parameters, layers):
    p = np.zeros(8 * layers)
    p[active_angles(layers)] = parameters
    return p


def born_features(x, parameters, layers, derivative=False, shared_day=False):
    """Original Born gate order, bounded inputs; forward state sensitivities per angle.

    Sensitivities differentiate gate angles themselves, including the input multiplier.
    Shifting a shared encoding weight by pi/2 would not implement parameter shift here.
    """
    x = np.arctan(np.atleast_2d(x)[:, :4])
    active = active_angles(layers)
    p = stored_angles(parameters[: len(active)], layers).reshape(layers, 8)
    day_weights = np.asarray(parameters[len(active) :]) if shared_day else np.zeros(layers)
    if shared_day:
        active = np.r_[active, np.arange(8 * layers, 9 * layers)]
    n, count = len(x), (9 if shared_day else 8) * layers
    state = np.zeros((n, 4), complex)
    state[:, 0] = 1
    tangent = np.zeros((n, 4, count), complex) if derivative else None
    for depth, w in enumerate(p):
        for qubit, j in ((0, 0), (1, 2)):
            low = np.array([0, 1]) if qubit == 0 else np.array([0, 2])
            high = low + (2 if qubit == 0 else 1)
            for axis, coordinate, multiplier in (
                ("y", j, x[:, j]),
                ("z", j + 1, x[:, j + 1]),
                ("y", 4 + 2 * qubit, np.ones(n)),
                ("z", 5 + 2 * qubit, np.ones(n)),
            ):
                angle = w[coordinate] * multiplier
                direct_day = shared_day and qubit == 1 and coordinate == 6
                if direct_day:
                    angle = angle + day_weights[depth] * x[:, 0]
                a, b = state[:, low].copy(), state[:, high].copy()
                if axis == "y":
                    c, s = np.cos(angle / 2)[:, None], np.sin(angle / 2)[:, None]
                    state[:, low], state[:, high] = c * a - s * b, s * a + c * b
                    da, db = (-s * a - c * b) / 2, (c * a - s * b) / 2
                    if derivative:
                        ta, tb = tangent[:, low].copy(), tangent[:, high].copy()
                        tangent[:, low] = c[..., None] * ta - s[..., None] * tb
                        tangent[:, high] = s[..., None] * ta + c[..., None] * tb
                else:
                    c, s = np.exp(-0.5j * angle)[:, None], np.exp(0.5j * angle)[:, None]
                    state[:, low], state[:, high] = c * a, s * b
                    da, db = -0.5j * c * a, 0.5j * s * b
                    if derivative:
                        tangent[:, low] *= c[..., None]
                        tangent[:, high] *= s[..., None]
                if derivative:
                    k = 8 * depth + coordinate
                    tangent[:, low, k] += da * multiplier[:, None]
                    tangent[:, high, k] += db * multiplier[:, None]
                    if direct_day:
                        tangent[:, low, 8 * layers + depth] += da * x[:, 0, None]
                        tangent[:, high, 8 * layers + depth] += db * x[:, 0, None]
        state = state[:, [0, 1, 3, 2]]
        if derivative:
            tangent = tangent[:, [0, 1, 3, 2]]
    probabilities = np.abs(state) ** 2
    norm = probabilities.sum(axis=1, keepdims=True)
    features = probabilities[:, :3] / norm - 0.25
    if not derivative:
        return features, None
    jac = 2 * np.real(state.conj()[..., None] * tangent[:, :, active])
    jac = jac - probabilities[..., None] * jac.sum(axis=1)[:, None, :] / norm[..., None]
    jac /= norm[..., None]
    return features, jac[:, :3]


@dataclass(frozen=True)
class CalendarReadout:
    """Reference-logit linear skip plus optional quantum, tanh or sine features."""

    kind: str = "linear"
    size: int = 2
    calendar: bool = True

    def __post_init__(self):
        if self.kind not in ("linear", "quantum", "quantum-shared", "tanh", "sine"):
            raise ValueError("Unknown feature family")
        if self.kind.startswith("quantum"):
            active_angles(self.size)
        elif type(self.size) is not int or self.size < 1:
            raise ValueError("Positive feature width required")

    @property
    def base_count(self):
        return 3 * (11 if self.calendar else 5)

    @property
    def feature_count(self):
        if self.kind == "linear":
            return 0
        if self.kind.startswith("quantum"):
            return (9 if self.kind == "quantum-shared" else 8) * self.size - 2
        return 5 * self.size

    @property
    def hidden_count(self):
        return 0 if self.kind == "linear" else (3 if self.kind.startswith("quantum") else self.size)

    @property
    def n_params(self):
        return self.base_count + self.feature_count + 3 * self.hidden_count

    def features(self, x, p, derivative=False):
        if self.kind.startswith("quantum"):
            return born_features(x, p, self.size, derivative, self.kind == "quantum-shared")
        a, h = np.arctan(x[:, :4]), self.size
        z = a @ p[: 4 * h].reshape(4, h) + p[4 * h :]
        if self.kind == "tanh":
            f = np.tanh(z)
            slope = 1 - f * f
        else:
            f, slope = np.sin(z), np.cos(z)
        if not derivative:
            return f, None
        design = np.column_stack([a, np.ones(len(x))])
        jac = slope[:, :, None, None] * design[:, None, :, None] * np.eye(h)[None, :, None, :]
        return f, jac.reshape(len(x), h, 5 * h)

    def logits(self, x, parameters, derivative=False):
        x, p = np.atleast_2d(np.asarray(x, float)), np.asarray(parameters, float)
        if x.shape[1] != (10 if self.calendar else 4) or not np.all(np.isfinite(x)):
            raise ValueError("Input columns must match the calendar policy")
        if p.shape != (self.n_params,) or not np.all(np.isfinite(p)):
            raise ValueError("Wrong or nonfinite parameter vector")
        design = np.column_stack([x, np.ones(len(x))])
        logits = design @ p[: self.base_count].reshape(-1, 3)
        f, jac = None, None
        if self.kind != "linear":
            stop = self.base_count + self.feature_count
            f, jac = self.features(x, p[self.base_count : stop], derivative)
            logits += f @ p[stop:].reshape(self.hidden_count, 3)
        return np.column_stack([logits, np.zeros(len(x))]), design, f, jac

    def probabilities(self, x, parameters):
        return softmax(self.logits(x, parameters)[0], axis=1)

    def loss_gradient(self, x, labels, parameters, weights, base_ridge=0, feature_ridge=0):
        p, weights = np.asarray(parameters), np.asarray(weights)
        logits, design, features, jac = self.logits(x, p, derivative=True)
        rows = np.arange(len(labels))
        loss = np.dot(weights, logsumexp(logits, axis=1) - logits[rows, labels])
        delta = softmax(logits, axis=1)
        delta[rows, labels] -= 1
        delta = delta[:, :3] * weights[:, None]
        gradient = np.empty_like(p)
        gradient[: self.base_count] = (design.T @ delta).ravel()
        if features is not None:
            stop = self.base_count + self.feature_count
            head = p[stop:].reshape(self.hidden_count, 3)
            gradient[self.base_count : stop] = np.einsum("nhi,nh->i", jac, delta @ head.T)
            gradient[stop:] = (features.T @ delta).ravel()
        penalties = np.r_[
            np.full(self.base_count, base_ridge),
            np.full(self.n_params - self.base_count, feature_ridge),
        ]
        return float(loss + np.dot(penalties, p * p)), gradient + 2 * penalties * p
