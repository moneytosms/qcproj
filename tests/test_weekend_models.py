from pathlib import Path

import numpy as np

from qcvol.data import synthetic_data
from qcvol.fresh_runner import FreshConfig
from qcvol_next.eth_upgrade import (
    calibrated_probabilities,
    code_hashes,
    final_models,
    fit_one,
    fit_temperature,
    weekend_data,
)
from qcvol_next.weekend_models import (
    WeekendBorn,
    WeekendHAR,
    WeekendNetwork,
    WeekendQuantumReadout,
    WeekendSoftmax,
)


def ry(angle):
    c, s = np.cos(angle / 2), np.sin(angle / 2)
    return np.array([[c, -s], [s, c]])


def rz(angle):
    return np.diag([np.exp(-0.5j * angle), np.exp(0.5j * angle)])


def reference(x, parameters, layers, axis="z", alternating=False):
    cnot = np.eye(4, dtype=complex)[[0, 1, 3, 2]]
    reverse_cnot = np.eye(4, dtype=complex)[[0, 3, 2, 1]]
    weekend_rotation = ry if axis == "y" else rz
    out = []
    for row in x:
        state = np.array([1, 0, 0, 0], dtype=complex)
        for index, layer in enumerate(np.asarray(parameters).reshape(layers, 10)):
            u0 = (
                weekend_rotation(layer[8] * row[4])
                @ rz(layer[5])
                @ ry(layer[4])
                @ rz(layer[1] * row[1])
                @ ry(layer[0] * row[0])
            )
            u1 = (
                weekend_rotation(layer[9] * row[4])
                @ rz(layer[7])
                @ ry(layer[6])
                @ rz(layer[3] * row[3])
                @ ry(layer[2] * row[2])
            )
            entangler = reverse_cnot if alternating and index % 2 else cnot
            state = entangler @ np.kron(u0, u1) @ state
        out.append(np.abs(state) ** 2)
    return np.asarray(out)


def test_weekend_born_matches_independent_statevector():
    rng = np.random.default_rng(4)
    x = rng.normal(size=(7, 5))
    for layers in (1, 3):
        p = rng.normal(size=10 * layers)
        for axis, alternating in (("z", False), ("y", False), ("z", True)):
            model = WeekendBorn(layers, axis, alternating)
            expected = reference(x, p, layers, axis, alternating)
            assert np.allclose(model.probabilities(x, p), expected, atol=1e-12)


def test_classical_weekend_models_return_four_probabilities():
    rng = np.random.default_rng(5)
    x = rng.normal(size=(12, 5))
    assert WeekendSoftmax().probabilities(x, rng.normal(size=24)).shape == (12, 4)
    p = WeekendNetwork().probabilities(x, rng.normal(size=27))
    assert p.shape == (12, 4)
    assert np.allclose(p.sum(axis=1), 1)


def test_quantum_readout_starts_at_har_and_normalizes():
    class Base:
        def probabilities(self, x):
            return np.tile([0.1, 0.2, 0.3, 0.4], (len(x), 1))

    x = np.random.default_rng(12).normal(size=(8, 5))
    model = WeekendQuantumReadout(Base())
    parameters = np.zeros(model.n_params)
    assert model.n_params == 25
    assert np.allclose(model.probabilities(x, parameters), Base().probabilities(x))
    fitted = model.probabilities(x, np.random.default_rng(13).normal(size=25))
    assert fitted.shape == (8, 4)
    assert np.allclose(fitted.sum(axis=1), 1)


def test_temperature_calibration_preserves_probabilities_and_fit_bounds():
    probabilities = np.array([[0.8, 0.1, 0.05, 0.05], [0.1, 0.2, 0.3, 0.4]])
    labels = np.array([0, 3])
    assert np.allclose(calibrated_probabilities(probabilities, 1), probabilities)
    temperature = fit_temperature(probabilities, labels)
    assert 0.2 <= temperature <= 5
    calibrated = calibrated_probabilities(probabilities, temperature)
    assert np.allclose(calibrated.sum(axis=1), 1)


def test_fixed_replication_panel_uses_preregistered_models():
    panel = [
        "hybrid-quantum-weekend-ry",
        "softmax-weekend",
        "network-weekend",
        "hybrid-softmax-weekend",
    ]
    assert final_models({"final_model_panel": panel}) == tuple(panel)


def test_replication_seal_hashes_sources_and_locked_environment():
    hashes = code_hashes()
    assert {str(path) for path in Path("src/qcvol").rglob("*.py")} <= hashes.keys()
    assert {
        "doc/sol-doge-replication-protocol.md",
        "pyproject.toml",
        "uv.lock",
    } <= hashes.keys()


def test_weekend_feature_scaling_uses_training_targets_only():
    daily = synthetic_data(days=1200)
    daily.index = np.datetime64("2020-01-01") + daily.index.astype("timedelta64[D]")
    data, scaling = weekend_data(daily, "2021-06-30", "2021-12-31")
    changed = synthetic_data(days=1200)
    changed.index = daily.index.copy()
    changed.rv[-100:] *= 50
    other, other_scaling = weekend_data(changed, "2021-06-30", "2021-12-31")
    assert data.x.shape[1] == 5
    assert scaling == other_scaling
    assert np.allclose(data.x[data.train], other.x[other.train])


def test_weekend_quantum_forecast_fit_runs_on_synthetic_history():
    daily = synthetic_data(days=900, seed=12)
    daily.index = np.datetime64("2020-01-01") + daily.index.astype("timedelta64[D]")
    data, _ = weekend_data(daily, "2021-06-30", "2021-12-31")
    config = FreshConfig(
        development_seeds=[900],
        final_seeds=[0],
        restarts=1,
        forecast_max_calls=100,
        forecast_max_iterations=30,
    )
    har = WeekendHAR.fit(data.x[data.train], data.y[data.train], data.bins.edges)
    base = har.probabilities(data.x[data.train])
    for name in (
        "quantum-weekend",
        "quantum-weekend-ry",
        "quantum-weekend-alternating",
        "hybrid-quantum-weekend-ry",
        "hybrid-quantum-readout-ry",
    ):
        row = fit_one(name, 1, data, config, 900, har, base)
        assert row["fit"]["parameters"]
        assert np.isfinite(row["validation"]["log_loss"])
    control = fit_one("quantum-har", 1, data, config, 900, har, base)
    assert np.isfinite(control["validation"]["log_loss"])
