import importlib.util
from pathlib import Path

import numpy as np
import pytest


@pytest.fixture
def ensemble(monkeypatch):
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location(
        "ensemble_complementarity", scripts / "ensemble_complementarity.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_recovers_interior_simplex_optimum(ensemble):
    p = np.array([[[0.9, 0.1], [0.9, 0.1]], [[0.1, 0.9], [0.1, 0.9]]])
    fit = ensemble.fit_weights(p, np.array([0, 1]))
    np.testing.assert_allclose(fit["weights"], [0.5, 0.5], atol=1e-7)
    assert fit["nll"] == pytest.approx(np.log(2))
    assert fit["kkt_residual"] < 1e-8


def test_recovers_boundary_and_is_member_order_invariant(ensemble):
    p = np.array([[[0.9, 0.1], [0.1, 0.9]], [[0.6, 0.4], [0.4, 0.6]]])
    y = np.array([0, 1])
    fit = ensemble.fit_weights(p, y)
    np.testing.assert_allclose(fit["weights"], [1, 0], atol=1e-7)
    shuffled = ensemble.fit_weights(p[::-1], y)
    np.testing.assert_allclose(shuffled["weights"][::-1], fit["weights"], atol=1e-7)
    assert ensemble.mixture_nll(p, y, fit["weights"]) == pytest.approx(-np.log(0.9))


def test_rejects_invalid_probabilities_and_weights(ensemble):
    p = np.array([[[0.9, 0.1]], [[0.6, 0.4]]])
    for bad in (p * 2, p * np.nan, -p, np.zeros_like(p)):
        with pytest.raises(ValueError):
            ensemble.fit_weights(bad, np.array([0]))
    for weights in ([2, -1], [0.1, 0.2], [1]):
        with pytest.raises(ValueError):
            ensemble.mixture_nll(p, np.array([0]), weights)


def test_declared_counts_match(ensemble):
    from qcvol.calendar_models import CalendarReadout

    counts = {}
    for name, (kind, depth) in ensemble.MEMBERS.items():
        size = depth if kind.startswith("quantum") else depth + 1
        counts[name] = CalendarReadout(kind, size, True).n_params
    assert sum(counts[m] for m in ensemble.GROUPS["base"]) == 163
    for name in ("quantum", "classical"):
        assert sum(counts[m] for m in ensemble.GROUPS[name]) == 277
