import json

import numpy as np
import pytest

from qcvol.calendar_models import (
    CalendarReadout,
    born_features,
    calendar_inputs,
    recency_weights,
    stored_angles,
    weekday,
)
from qcvol.calendar_study import (
    CalendarConfig,
    check_seal,
    fit_model,
    generate_calendar,
    initialize,
    seal,
)
from qcvol.data import sha256, synthetic_data
from qcvol.fresh_study import prepare_dates
from qcvol.quantum import BornCircuit


def dated():
    daily = synthetic_data(900, seed=81)
    daily.index = np.datetime64("2020-01-01") + daily.index.astype("timedelta64[D]")
    return daily


def prepared():
    return prepare_dates(dated(), "2021-06-30", "2021-12-31")


@pytest.mark.parametrize("depth", [1, 2, 3, 4])
def test_bounded_circuit_matches_existing_gates_and_sensitive_parameters(depth):
    rng = np.random.default_rng(depth)
    x = rng.normal(size=(7, 4))
    p = rng.normal(0, 0.4, 8 * depth - 2)
    f, jac = born_features(x, p, depth, True)
    expected = BornCircuit(depth).probabilities(np.arctan(x), stored_angles(p, depth))[:, :3] - 0.25
    np.testing.assert_allclose(f, expected, atol=1e-13)
    numeric = np.stack(
        [
            (born_features(x, p + d * 1e-5, depth)[0] - born_features(x, p - d * 1e-5, depth)[0])
            / 2e-5
            for d in np.eye(len(p))
        ],
        axis=-1,
    )
    np.testing.assert_allclose(jac, numeric, atol=1e-9)


@pytest.mark.parametrize(
    "kind,size", [("linear", 1), ("quantum", 2), ("quantum-shared", 3), ("tanh", 3), ("sine", 4)]
)
@pytest.mark.parametrize("calendar", [False, True])
def test_joint_objective_gradient_against_finite_difference(kind, size, calendar):
    rng = np.random.default_rng(51)
    x = rng.normal(size=(9, 10 if calendar else 4))
    labels = rng.integers(0, 4, 9)
    weights = np.arange(1.0, 10.0) / 45
    model = CalendarReadout(kind, size, calendar)
    p = rng.normal(0, 0.4, model.n_params)
    fun = lambda q: model.loss_gradient(x, labels, q, weights, 0.001, 0.01)
    _, gradient = fun(p)
    numeric = np.array(
        [(fun(p + d * 1e-5)[0] - fun(p - d * 1e-5)[0]) / 2e-5 for d in np.eye(len(p))]
    )
    np.testing.assert_allclose(gradient, numeric, atol=1e-8)


def test_zero_feature_readout_contains_linear_model_exactly():
    rng = np.random.default_rng(8)
    x = rng.normal(size=(12, 10))
    linear = CalendarReadout()
    base = rng.normal(size=linear.n_params)
    for kind, size in [("quantum", 2), ("tanh", 3), ("sine", 3)]:
        model = CalendarReadout(kind, size)
        p = np.r_[base, rng.normal(size=model.feature_count), np.zeros(model.hidden_count * 3)]
        np.testing.assert_allclose(
            model.probabilities(x, p), linear.probabilities(x, base), atol=1e-14
        )


def test_second_qubit_has_direct_day_input_even_when_first_qubit_is_fixed():
    x = np.zeros((2, 4))
    x[1, 0] = 2
    original = np.zeros(6)
    f, _ = born_features(x, original, 1)
    np.testing.assert_array_equal(f[0], f[1])
    shared = np.r_[original, 1.0]
    f, _ = born_features(x, shared, 1, shared_day=True)
    assert not np.allclose(f[0], f[1])
    angle = np.arctan(2)
    np.testing.assert_allclose(
        f[1] + 0.25, [np.cos(angle / 2) ** 2, np.sin(angle / 2) ** 2, 0], atol=1e-14
    )


def test_calendar_uses_target_date_and_weights_use_only_supplied_past_dates():
    dates = np.arange(np.datetime64("2024-01-01"), np.datetime64("2024-01-08"))
    np.testing.assert_array_equal(weekday(dates), np.arange(7))
    x = calendar_inputs(np.zeros((7, 4)), dates)
    np.testing.assert_array_equal(x[0, 4:], np.zeros(6))
    np.testing.assert_array_equal(x[1:, 4:], np.eye(6))
    w = recency_weights(dates, 2)
    assert w[-1] / w[-3] == pytest.approx(2)
    assert w.sum() == pytest.approx(1)
    with pytest.raises(ValueError):
        recency_weights(dates[::-1], 2)


def test_future_targets_do_not_change_fit_and_dates_advance_in_recursion():
    data = prepared()
    daily = dated()
    first_future = data.target_rows[data.train.stop]
    daily.rv[first_future:] *= 100
    daily.returns[first_future:] += 3
    other = prepare_dates(daily, "2021-06-30", "2021-12-31")
    cfg = CalendarConfig(kind="integration", final_seeds=[0], max_calls=1000)
    model = CalendarReadout()
    fit = fit_model(model, data, cfg, 365, 0.001, 0, 0, np.zeros(model.n_params))
    fit_other = fit_model(model, other, cfg, 365, 0.001, 0, 0, np.zeros(model.n_params))
    np.testing.assert_array_equal(fit["parameters"], fit_other["parameters"])
    a = generate_calendar(model, fit["parameters"], data, 40, 2, 12, 10)
    b = generate_calendar(model, fit["parameters"], other, 40, 2, 12, 10)
    np.testing.assert_array_equal(a.log_rv, b.log_rv)

    class Capture:
        calendar = True

        def __init__(self):
            self.seen = []

        def probabilities(self, x, p):
            self.seen.append(x[:, 4:].copy())
            return np.tile([1.0, 0, 0, 0], (len(x), 1))

    capture = Capture()
    generate_calendar(capture, None, data, 32, 1, 12, 0)
    dates = np.datetime64("2021-07-01") + np.arange(32).astype("timedelta64[D]")
    expected = calendar_inputs(np.zeros((32, 4)), dates)[:, 4:]
    np.testing.assert_array_equal(np.concatenate(capture.seen), expected)


def test_seal_rejects_date_and_parameter_changes(tmp_path):
    data = prepared()
    output = tmp_path / "study"
    config = CalendarConfig(kind="integration", final_seeds=[0])
    initialize(data, config, output)
    for name in ("development.json", "selection.json"):
        (output / name).write_text("{}")
    trained = output / "train-seed0.json"
    trained.write_text(
        json.dumps({"selection_sha256": sha256(output / "selection.json"), "models": {}})
    )
    seal(data, output)
    assert check_seal(data, output).kind == "integration"
    data.daily.index = data.daily.index + np.timedelta64(7, "D")
    with pytest.raises(ValueError, match="data or dates"):
        check_seal(data, output)
    trained.write_text("{}")
    with pytest.raises(ValueError, match="artifact changed"):
        check_seal(prepared(), output)


def test_final_requires_twenty_fresh_seeds():
    with pytest.raises(ValueError, match="20 seeds"):
        CalendarConfig(final_seeds=[0])
    with pytest.raises(ValueError, match="must differ"):
        CalendarConfig(development_seeds=[0])
