import json

import numpy as np
import pytest

from qcvol.data import DailyData, prepare, synthetic_data
from qcvol.nested_memory import (
    HARPointModel,
    NestedMemoryCircuit,
    fit_nested,
    har_features,
    nested_inputs,
    warm_initial,
)
from qcvol.nested_study import NestedStudyConfig, decide, run_followup, summarize
from qcvol.quantum import paper_probability, ry, rz, u3
from qcvol.training import fit_point


@pytest.mark.parametrize("short", [False, True])
def test_nested_circuit_matches_literal_gates_and_contains_paper(short):
    rng = np.random.default_rng(531)
    r, v, x = rng.uniform(-1, 1, 23), rng.uniform(0, 1, 23), rng.normal(size=(23, 4))
    p = rng.normal(size=4)
    expected = []
    for ret, rv, features in zip(r, v, x, strict=True):
        state = np.array([1, 0], complex)
        week, month = (0, 0) if short else (1, 2)
        gates = [
            ry(np.arcsin(ret)),
            rz(np.arccos(ret**2)),
            ry(np.arcsin(2 * rv - 1)),
            rz(np.arccos(rv**2)),
            ry(p[2] * features[week]),
            rz(p[3] * features[month]),
            u3(p[0], 0, p[1]),
        ]
        for gate in gates:
            state = gate @ state
        expected.append(abs(state[0]) ** 2)
    model = NestedMemoryCircuit(short)
    np.testing.assert_allclose(model.predict(r, v, x, p), expected, atol=1e-14)
    for _ in range(8):
        paper = rng.uniform(-np.pi, np.pi, 3)
        zero = np.r_[paper[[0, 2]], [0.0, 0.0]]
        np.testing.assert_allclose(
            model.predict(r, v, x, zero), paper_probability(r, v, paper), atol=1e-14
        )


def test_memory_weights_are_the_only_source_of_long_horizon_information():
    rng = np.random.default_rng(54)
    x = rng.normal(size=(10, 4))
    changed = x.copy()
    changed[:, 1:3] += 2
    r, v, p = rng.uniform(-1, 1, 10), rng.uniform(0, 1, 10), np.array([0.7, -0.4, 0.3, 0.5])
    for short in (True, False):
        a = NestedMemoryCircuit(short).predict(r, v, x, p)
        b = NestedMemoryCircuit(short).predict(r, v, changed, p)
        if short:
            np.testing.assert_array_equal(a, b)
        else:
            assert np.max(np.abs(a - b)) > 0.01


def test_warm_start_and_regularizer_use_training_only_and_keep_zero_candidate():
    data = prepare(synthetic_data(240))
    baseline, scaling = fit_point(
        "paper", data, max_evaluations=1500, initialization="uniform", reduce_inactive=True
    )
    fit, _, gradient = fit_nested(data, baseline.parameters, 0.1, max_evaluations=1500)
    assert fit.initial_objective == pytest.approx(baseline.objective, abs=1e-14)
    assert fit.objective <= baseline.objective
    assert np.all(np.isfinite(gradient))
    np.testing.assert_array_equal(warm_initial(baseline.parameters, 0)[2:], [0, 0])
    np.testing.assert_array_equal(
        warm_initial(baseline.parameters, 4), warm_initial(baseline.parameters, 4)
    )
    cutoff = data.target_rows[data.validation.start]
    rv, r = data.daily.rv.copy(), data.daily.returns.copy()
    rv[cutoff:] *= 1e4
    r[cutoff:] += 100
    changed = prepare(DailyData(data.daily.index, r, rv, data.daily.units))
    second, other_scale, _ = fit_nested(changed, baseline.parameters, 0.1, max_evaluations=1500)
    np.testing.assert_array_equal(fit.parameters, second.parameters)
    assert scaling == other_scale
    encoded, x, _ = nested_inputs(data, data.target_rows[data.train], scaling)
    f, _, _ = fit_nested(data, baseline.parameters, 0.1, seed=2, max_evaluations=6)
    initial = warm_initial(baseline.parameters, 2)
    prediction = NestedMemoryCircuit().predict_encoded(encoded, x, initial)
    expected = np.mean(
        (prediction - data.daily.rv[data.target_rows[data.train]] / scaling.rv_scale) ** 2
    ) + 0.1 * np.sum(initial[2:] ** 2)
    assert f.initial_objective == pytest.approx(expected)
    assert len(f.objective_history) == f.evaluations + 1


def test_har_is_past_only_and_matches_independent_ols():
    data = prepare(synthetic_data(240))
    model = HARPointModel.fit(data)

    def manual(rows):
        rv = data.daily.rv
        return np.array(
            [[1, rv[t - 1], np.sum(rv[t - 7 : t]) / 7, np.sum(rv[t - 30 : t]) / 30] for t in rows]
        )

    tr, va = data.target_rows[data.train], data.target_rows[data.validation]
    beta = np.linalg.lstsq(manual(tr), data.daily.rv[tr], rcond=None)[0]
    np.testing.assert_allclose(
        model.predict(data.daily.rv, va), np.maximum(manual(va) @ beta, 0), atol=1e-12
    )
    assert model.rank == 4
    changed = data.daily.rv.copy()
    changed[va[0] :] *= 100
    np.testing.assert_array_equal(
        har_features(changed, va[:1]), har_features(data.daily.rv, va[:1])
    )


def test_selection_preserves_penalized_restart_rule_and_requires_convergence():
    config = NestedStudyConfig()
    baseline = {
        "kind": "paper",
        "regularization": None,
        "eligible": True,
        "validation_mse_rv": 0.5,
        "winner": "paper",
    }
    full = {
        "kind": "nested_memory",
        "regularization": 0.1,
        "eligible": True,
        "validation_mse_rv": 0.4,
        "winner": "full",
    }
    short = {
        "kind": "nested_short",
        "regularization": 0.1,
        "eligible": True,
        "validation_mse_rv": 0.3,
        "winner": "short",
    }
    assert decide([baseline, full, short], config)["feature_policy_for_D"] == "previous_day_only"
    assert (
        decide([baseline, dict(full, validation_mse_rv=0.2), short], config)["feature_policy_for_D"]
        == "HAR"
    )
    assert decide([baseline, dict(full, eligible=False), short], config)["status"] == "inconclusive"
    assert (
        decide([baseline, dict(full, validation_mse_rv=0.298), short], config)[
            "feature_policy_for_D"
        ]
        == "previous_day_only"
    )
    fallback = decide(
        [baseline, dict(full, validation_mse_rv=0.7), dict(short, validation_mse_rv=0.6)], config
    )
    assert fallback["selections"]["nested_memory"]["kind"] == "paper"
    common = {
        "kind": "nested_memory",
        "regularization": 0.1,
        "eligible": True,
        "seed": 0,
        "stationarity_objective_calls": 8,
        "train_mse_rv": 0.1,
        "validation_mse_rv": 0.6,
    }
    a = dict(common, id="a", fit={"objective": 0.2, "total_objective_calls": 9, "seconds": 1})
    b = dict(
        common,
        id="b",
        validation_mse_rv=0.01,
        fit={"objective": 0.3, "total_objective_calls": 8, "seconds": 1},
    )
    assert summarize([a, b])[0]["winner"] == "a"


def test_followup_never_scores_test_or_uses_it_for_selection(tmp_path):
    data = prepare(synthetic_data(200))
    cutoff = data.target_rows[data.test.start]
    rv, r = data.daily.rv.copy(), data.daily.returns.copy()
    rv[cutoff:] *= 1e6
    r[cutoff:] += 1000
    changed = prepare(DailyData(data.daily.index, r, rv, data.daily.units))
    config = NestedStudyConfig(seeds=[0], regularization=[0, 0.1], max_evaluations=1500)
    outputs = [tmp_path / "original", tmp_path / "changed"]
    decisions = [run_followup(d, config, p) for d, p in zip((data, changed), outputs, strict=True)]
    # Timing differs; selected candidates and all numeric fit/score results must agree.
    assert decisions[0]["status"] == decisions[1]["status"]
    records = [json.loads((p / "records.json").read_text()) for p in outputs]
    for a, b in zip(*records, strict=True):
        assert a["train_mse_rv"] == b["train_mse_rv"]
        assert a["validation_mse_rv"] == b["validation_mse_rv"]
        if "fit" in a:
            assert a["fit"]["parameters"] == b["fit"]["parameters"]
    for path in outputs[0].glob("*.npz"):
        with np.load(path) as arrays:
            assert max(arrays["validation_rows"]) < cutoff
            assert not any("test" in key for key in arrays.files)
    with pytest.raises(FileExistsError):
        run_followup(data, config, outputs[0])
