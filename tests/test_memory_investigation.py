import json

import numpy as np
import pytest

from qcvol.data import DailyData, prepare, synthetic_data
from qcvol.memory_diagnostics import MemoryInvestigationConfig, run_investigation, summarize
from qcvol.quantum import MemoryCircuit, ry, rz
from qcvol.training import PointScaling, fit_point, point_initialization


@pytest.mark.parametrize("depth", [1, 2, 3, 4])
def test_memory_matches_literal_matrices_and_terminal_phase_is_inactive(depth):
    rng = np.random.default_rng(91)
    x, params = rng.normal(size=(7, 4)), rng.normal(size=6 * depth)
    expected = []
    for row in x:
        state = np.array([1, 0], complex)
        for w in params.reshape(depth, 6):
            gates = [
                ry(w[0] * row[0]),
                rz(w[1] * row[1]),
                ry(w[2] * row[2]),
                rz(w[3] * row[3]),
                ry(w[4]),
                rz(w[5]),
            ]
            for gate in gates:
                state = gate @ state
        expected.append(abs(state[0]) ** 2)
    model = MemoryCircuit(depth)
    np.testing.assert_allclose(model.predict(x, params), expected, atol=1e-14)
    changed = params.copy()
    changed[-1] += 1.37
    np.testing.assert_allclose(model.predict(x, params), model.predict(x, changed), atol=1e-14)


def test_short_memory_ignores_long_horizons_and_prior_matches_training_center():
    data = prepare(synthetic_data(240))
    scaling = PointScaling.fit(data)
    params = point_initialization("memory_b", data, scaling, 0, 3, "rv_prior")
    expected = np.mean(data.daily.rv[data.target_rows[data.train]]) / scaling.rv_scale
    assert MemoryCircuit().predict(np.zeros((1, 4)), params)[0] == pytest.approx(expected)
    x = data.x[data.validation].copy()
    changed = x.copy()
    changed[:, 1:3] += 29
    model = MemoryCircuit(short_memory=True)
    np.testing.assert_array_equal(model.predict(x, params), model.predict(changed, params))
    assert (
        np.max(
            np.abs(MemoryCircuit().predict(x, params) - MemoryCircuit().predict(changed, params))
        )
        > 1e-4
    )


def test_reduced_fit_logs_actual_calls_and_training_only_initialization():
    data = prepare(synthetic_data(240))
    cutoff = data.target_rows[data.validation.start]
    returns, rv = data.daily.returns.copy(), data.daily.rv.copy()
    returns[cutoff:] += 200
    rv[cutoff:] *= 1e4
    changed = prepare(DailyData(data.daily.index, returns, rv, data.daily.units))
    kwargs = {
        "kind": "memory_b",
        "seed": 8,
        "layers": 1,
        "max_evaluations": 40,
        "initialization": "rv_prior",
        "reduce_inactive": True,
    }
    first, scale = fit_point(data=data, **kwargs)
    second, other_scale = fit_point(data=changed, **kwargs)
    np.testing.assert_array_equal(first.parameters, second.parameters)
    assert scale == other_scale
    assert first.parameters[-1] == 0
    assert first.optimized_parameter_count == 5
    assert len(first.objective_history) == first.record()["total_objective_calls"]
    assert first.objective <= first.initial_objective
    assert first.objective == min(first.objective_history)


def test_restart_selection_uses_training_loss_even_when_validation_disagrees():
    common = {
        "phase": "budget",
        "kind": "memory_b",
        "layers": 1,
        "initialization": "rv_prior",
        "reduce_inactive": False,
        "budget": 40,
        "fit": {"success": True, "total_objective_calls": 20, "seconds": 1},
    }
    records = [
        dict(common, seed=0, id="a", train_mse_rv=0.1, validation_mse_rv=0.8),
        dict(common, seed=1, id="b", train_mse_rv=0.2, validation_mse_rv=0.01),
    ]
    result = summarize(records)[0]
    assert result["train_selected_id"] == "a"
    assert result["validation_mse_rv"] == 0.8
    assert result["total_objective_calls"] == 40


def test_investigation_does_not_use_test_values(tmp_path):
    data = prepare(synthetic_data(200))
    cutoff = data.target_rows[data.test.start]
    rv, returns = data.daily.rv.copy(), data.daily.returns.copy()
    rv[cutoff:] *= 1e5
    returns[cutoff:] += 100
    changed = prepare(DailyData(data.daily.index, returns, rv, data.daily.units))
    config = MemoryInvestigationConfig(seeds=[0], budgets=[20], layers=[1], convergence_budget=20)
    outputs = [tmp_path / "first", tmp_path / "changed"]
    for prepared, output in zip((data, changed), outputs, strict=True):
        run_investigation(prepared, config, output)
    records = [json.loads((output / "records.json").read_text()) for output in outputs]
    for a, b in zip(*records, strict=True):
        assert a["train_mse_rv"] == b["train_mse_rv"]
        assert a["validation_mse_rv"] == b["validation_mse_rv"]
        assert a["fit"]["parameters"] == b["fit"]["parameters"]
        assert not any(k.startswith("test_") for k in a)
    for path in outputs[0].glob("*.npz"):
        arrays = np.load(path)
        assert max(arrays["validation_target_rows"]) < cutoff
        assert not any(k.startswith("test_") for k in arrays.files)
    with pytest.raises(FileExistsError):
        run_investigation(data, config, outputs[0])
