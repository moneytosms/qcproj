import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qvol import paper_model as pm
from qvol import metrics


def test_phi_has_no_effect():
    rng = np.random.default_rng(0)
    for _ in range(50):
        r, s = rng.uniform(-0.9, 0.9), rng.uniform(0.01, 0.99)
        th, lam = rng.uniform(-3, 3, 2)
        assert abs(pm.p0(r, s, th, 0.0, lam) - pm.p0(r, s, th, 2.7, lam)) < 1e-12


def test_closed_form_matches_circuit():
    rng = np.random.default_rng(1)
    for _ in range(50):
        r, s = rng.uniform(-0.9, 0.9), rng.uniform(0.01, 0.99)
        th, ph, lam = rng.uniform(-3, 3, 3)
        assert abs(pm.p0(r, s, th, ph, lam) - pm.p0_closed_form(r, s, th, lam)) < 1e-12


def test_probability_in_range():
    v, r = pm.generate((1.0, 0.3, -0.5), 500, 0.0, 0.5, seed=2)
    assert np.all((v > 0) & (v < 1)) and np.all(np.abs(r) < 1)


def test_mfdfa_white_noise_is_half():
    x = np.random.default_rng(3).standard_normal(20000)
    assert abs(metrics.hurst2(x) - 0.5) < 0.05


def test_scores():
    P = np.array([[0.7, 0.2, 0.1, 0.0], [0.1, 0.1, 0.1, 0.7]])
    assert metrics.log_loss(P, np.array([0, 3])) < 0.4
    assert metrics.rps(P, np.array([0, 3])) < metrics.rps(P, np.array([3, 0]))
