import numpy as np
import pytest

from qcvol.metrics import kupiec_test, log_loss, mfdfa, ranked_probability_score, return_quantiles


def test_proper_scores_reward_truth_and_ordered_near_misses():
    perfect = np.eye(4)
    labels = np.arange(4)
    assert log_loss(perfect, labels) == 0
    assert ranked_probability_score(perfect, labels) == 0
    near, far = np.array([[0, 0, 1, 0]]), np.array([[1, 0, 0, 0]])
    assert ranked_probability_score(near, np.array([3])) == pytest.approx(1 / 3)
    assert ranked_probability_score(far, np.array([3])) == 1
    assert np.isfinite(log_loss(far, np.array([3])))


def test_invalid_probabilities_fail_instead_of_hiding_errors():
    with pytest.raises(ValueError, match="sum to one"):
        log_loss(np.array([[0.1, 0.1, 0.1, 0.1]]), np.array([0]))


def test_mfdfa_white_noise_and_integrated_noise_have_expected_slopes():
    noise = np.random.default_rng(29).normal(size=4096)
    white = mfdfa(noise)
    integrated = mfdfa(np.cumsum(noise))
    assert white["available"] and integrated["available"]
    assert 0.35 < white["h2"] < 0.65
    assert 1.3 < integrated["h2"] < 1.7
    assert not mfdfa(np.ones(200))["available"]


def test_kupiec_handles_zero_and_all_exceedances():
    for violations in (np.zeros(100, bool), np.ones(100, bool)):
        result = kupiec_test(violations)
        assert np.isfinite(result["lr"])
        assert 0 <= result["p_value"] <= 1
    result = kupiec_test(np.arange(100) < 5)
    assert result["lr"] == pytest.approx(0)


def test_mixture_var_matches_single_gaussian_case():
    pools = tuple(np.zeros(5) for _ in range(4))
    actual = return_quantiles(np.full((2, 4), 0.25), pools)
    np.testing.assert_allclose(actual, -1.6448536269514729, atol=1e-10)
