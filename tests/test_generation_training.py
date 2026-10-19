import numpy as np

from qcvol.classical import FrequencyModel, HARModel, SoftmaxModel, TinyNetwork
from qcvol.data import DailyData, prepare, synthetic_data
from qcvol.generation import generate
from qcvol.quantum import BornCircuit
from qcvol.training import fit_distribution


def test_rollout_reproducible_and_only_uses_training_observations():
    data = prepare(synthetic_data(360))
    model = BornCircuit(1)
    parameters = np.random.default_rng(5).normal(size=8)
    first = generate(model, parameters, data, days=64, paths=3, seed=37)
    daily = data.daily
    rv, returns = daily.rv.copy(), daily.returns.copy()
    cutoff = data.target_rows[data.validation.start]
    rv[cutoff:] *= 1e5
    returns[cutoff:] += 1000
    changed = prepare(DailyData(daily.index, returns, rv, daily.units))
    second = generate(model, parameters, changed, days=64, paths=3, seed=37)
    np.testing.assert_array_equal(first.log_rv, second.log_rv)
    np.testing.assert_array_equal(first.returns, second.returns)
    for k in range(4):
        assert np.all(np.isin(first.log_rv[first.levels == k], data.bins.pools[k]))
    other = generate(model, parameters, data, days=64, paths=3, seed=38)
    assert not np.array_equal(first.log_rv, other.log_rv)


def test_realism_objective_is_deterministic_and_keeps_best_solution():
    data = prepare(synthetic_data(240))
    model = SoftmaxModel()
    kwargs = {
        "seed": 4,
        "max_evaluations": 26,
        "realism_weight": 0.01,
        "path_days": 40,
        "paths": 1,
        "burn_in": 0,
    }
    first = fit_distribution(model, data, **kwargs)
    second = fit_distribution(model, data, **kwargs)
    np.testing.assert_array_equal(first.parameters, second.parameters)
    assert first.objective <= first.initial_objective
    assert first.objective == second.objective


def test_classical_comparators_return_normalized_probabilities():
    data = prepare(synthetic_data(360))
    rng = np.random.default_rng(88)
    models = [
        SoftmaxModel(),
        TinyNetwork(),
        FrequencyModel.fit(data.labels[data.train]),
        HARModel.fit(data.x[data.train], data.y[data.train], data.bins.edges),
    ]
    for model in models:
        p = model.probabilities(data.x[data.test], rng.normal(size=model.n_params))
        assert p.shape == (len(data.y[data.test]), 4)
        assert np.min(p) >= 0
        np.testing.assert_allclose(p.sum(axis=1), 1)
