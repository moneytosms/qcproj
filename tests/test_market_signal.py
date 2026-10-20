import importlib.util
from pathlib import Path

import numpy as np

spec = importlib.util.spec_from_file_location(
    "develop_market_quantum", Path("scripts/develop_market_quantum.py")
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
MarketBorn = module.MarketBorn
MarketHAR = module.MarketHAR
MarketNetwork = module.MarketNetwork


def ry(angle):
    c, s = np.cos(angle / 2), np.sin(angle / 2)
    return np.array([[c, -s], [s, c]])


def rz(angle):
    return np.diag([np.exp(-0.5j * angle), np.exp(0.5j * angle)])


def test_market_born_matches_independent_statevector():
    x = np.random.default_rng(15).normal(size=(4, 6))
    parameters = np.random.default_rng(16).normal(size=12)
    cnot = np.eye(4, dtype=complex)[[0, 1, 3, 2]]
    expected = []
    for row in x:
        u0 = rz(parameters[10] * row[5]) @ ry(parameters[8] * row[4])
        u0 = u0 @ rz(parameters[5]) @ ry(parameters[4])
        u0 = u0 @ rz(parameters[1] * row[1]) @ ry(parameters[0] * row[0])
        u1 = rz(parameters[11] * row[5]) @ ry(parameters[9] * row[4])
        u1 = u1 @ rz(parameters[7]) @ ry(parameters[6])
        u1 = u1 @ rz(parameters[3] * row[3]) @ ry(parameters[2] * row[2])
        state = cnot @ np.kron(u0, u1) @ np.array([1, 0, 0, 0], complex)
        expected.append(np.abs(state) ** 2)
    probabilities = MarketBorn(1).probabilities(x, parameters)
    assert np.allclose(probabilities, expected, atol=1e-12)
    assert np.allclose(probabilities.sum(axis=1), 1)


def test_market_born_rejects_wrong_feature_width():
    try:
        MarketBorn(1).probabilities(np.zeros((2, 5)), np.zeros(12))
    except ValueError as error:
        assert "six" in str(error)
    else:
        raise AssertionError("wrong feature width accepted")


def test_market_har_design_uses_all_shared_features():
    x = np.arange(24, dtype=float).reshape(4, 6)
    assert np.array_equal(MarketHAR.design(x), np.column_stack([x, np.ones(4)]))


def test_market_network_returns_four_class_probabilities():
    x = np.random.default_rng(22).normal(size=(7, 6))
    parameters = np.random.default_rng(23).normal(size=MarketNetwork.n_params)
    probabilities = MarketNetwork().probabilities(x, parameters)
    assert probabilities.shape == (7, 4)
    assert np.allclose(probabilities.sum(axis=1), 1)
