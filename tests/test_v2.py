import numpy as np
import pytest

pytest.importorskip("jax")

from qcvol_v2 import models as v2


@pytest.mark.parametrize("layers,inputs", [(1, 4), (2, 6), (3, 6)])
def test_fast_circuit_matches_plain_statevector(layers, inputs):
    spec = v2.Spec("quantum", inputs, layers=layers)
    rng = np.random.default_rng(layers)
    x = rng.normal(size=(7, inputs))
    p = rng.normal(size=spec.n_params)
    fast, _ = v2.build(spec)
    np.testing.assert_allclose(
        np.asarray(fast(p, x)), v2.reference_probabilities(spec, x, p), atol=1e-12
    )


def test_gradient_matches_finite_difference():
    spec = v2.Spec("quantum", 6, layers=2)
    rng = np.random.default_rng(0)
    x, labels = rng.normal(size=(20, 6)), rng.integers(0, 4, 20)
    p = rng.normal(size=spec.n_params)
    _, vg = v2.build(spec)
    grad = np.asarray(vg(p, x, labels)[1])
    e = np.zeros_like(p)
    e[5] = 1e-6
    fd = (float(vg(p + e, x, labels)[0]) - float(vg(p - e, x, labels)[0])) / 2e-6
    assert abs(fd - grad[5]) < 1e-6


def test_parameter_counts():
    assert v2.MODELS["quantum-v2"][0].n_params == 84
    assert v2.MODELS["softmax-v2"][0].n_params == 28
    assert v2.MODELS["network-v2"][0].n_params == 26


def test_calendar_flags_use_target_weekday():
    class Daily:
        index = np.arange(np.datetime64("2024-01-01"), np.datetime64("2024-01-15"))

    class Data:
        daily = Daily()
        target_rows = np.arange(14)
        x = np.zeros((14, 4))
        train = slice(0, 14)

    f = v2.features(Data())
    assert f.shape == (14, 6)
    # 2024-01-01 is a Monday; 6th and 7th are the weekend
    assert f[0, 5] > 0 and f[5, 4] > 0 and f[6, 4] > 0 and f[1, 4] < 0
    np.testing.assert_allclose(f[:, 4:].mean(axis=0), 0, atol=1e-12)
