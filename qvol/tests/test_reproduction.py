import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qvol.multifractal import (
    analyze_batch,
    rolling_h2,
    rolling_starts,
    scale_grid,
    spectrum,
)
from qvol.reproduction import (
    independent_mfdfa_check,
    transformed_series,
    validate_config,
)

from qvol import paper_audit as audit
from qvol import paper_model


def test_vectorized_circuit_matches_independent_matrix_and_bloch():
    rng = np.random.default_rng(16)
    r, v = rng.uniform(-1, 1, 50), rng.uniform(0, 1, 50)
    for _ in range(4):
        p = rng.normal(size=3)
        np.testing.assert_allclose(
            audit.predict(p, r, v), paper_model.predict(p, r, v), atol=1e-14
        )
        np.testing.assert_allclose(
            np.linalg.norm(audit.encoded_bloch(r, v), axis=1), 1, atol=1e-14
        )


def reference_log_fluctuations(x, q, scales):
    profile = np.cumsum(x - np.mean(x))
    result = []
    for s in scales:
        n = len(x) // s
        segments = [profile[i * s : (i + 1) * s] for i in range(n)]
        segments += [profile[len(x) - (i + 1) * s : len(x) - i * s] for i in range(n)]
        f2 = np.array(
            [
                np.mean(
                    (seg - np.polyval(np.polyfit(np.arange(s), seg, 3), np.arange(s)))
                    ** 2
                )
                for seg in segments
            ]
        )
        result.append(
            [
                0.5 * np.log(f2).mean()
                if power == 0
                else np.log(np.mean(f2 ** (power / 2))) / power
                for power in q
            ]
        )
    return np.array(result)


def test_mfdfa_matches_direct_polynomial_reference_including_q_zero():
    rng = np.random.default_rng(33)
    x = rng.normal(size=913)
    q = np.array([-5.0, -2.0, 0.0, 2.0, 5.0])
    scales = scale_grid(913)
    actual = analyze_batch(x, q=q, scales=scales)
    np.testing.assert_allclose(
        actual["log_f"][0], reference_log_fluctuations(x, q, scales), atol=1e-11
    )
    shifted = analyze_batch(x + 7, q=q, scales=scales)
    np.testing.assert_allclose(actual["h"], shifted["h"], atol=1e-12)
    spec = spectrum(x, q=q, scales=scales)
    np.testing.assert_allclose(spec["tau"], q * spec["h"] - 1)


def test_independent_package_matches_fluctuation_functions():
    pytest.importorskip("MFDFA")
    rng = np.random.default_rng(4)
    result = independent_mfdfa_check(
        {"gaussian": rng.normal(size=913)}, scale_grid(913)
    )
    assert result["series"]["gaussian"]["max_abs_log_fluctuation_error"] < 1e-10


def test_complete_rolling_grid_and_independently_shuffled_controls():
    starts = rolling_starts(50_000, 913, 365)
    assert len(starts) == 135
    assert starts[1] - starts[0] == 365
    assert starts[-1] + 913 <= 50000 < starts[-1] + 365 + 913
    x = np.random.default_rng(37).normal(size=1200)
    first = rolling_h2(
        x, window=200, step=100, shuffles=3, seed=5, scales=scale_grid(200)
    )
    second = rolling_h2(
        x, window=200, step=100, shuffles=3, seed=5, scales=scale_grid(200)
    )
    np.testing.assert_array_equal(first["shuffled_h2"], second["shuffled_h2"])
    assert first["shuffled_h2"].shape == (11, 3)


def test_generation_returns_obey_equation_34_and_counts_domain_safeguards():
    # theta=0 gives a sufficiently large variance to force Gaussian domain escapes.
    v, r, counts = audit.generate([0.0, 0.0, 0.0], 1000, 0.1, 0.5, seed=7)
    np.testing.assert_allclose(
        r / np.sqrt(v), np.random.default_rng(7).standard_normal(1000), atol=1e-14
    )
    assert counts["return_encoding_clips"] > 0
    with pytest.raises(ValueError, match="left encoding domain"):
        audit.generate([0.0, 0.0, 0.0], 1000, 0.1, 0.5, seed=7, policy="strict")


def test_full_sample_fit_restarts_are_logged_reproducible_and_converge():
    loaded, _ = audit.load_verified(
        Path(__file__).resolve().parents[1] / "data/takaishi"
    )
    r, v = loaded["data-rstand"], loaded["data-ystand"]
    a = audit.fit(r, v, restarts=2, max_evaluations=2000)
    b = audit.fit(r, v, restarts=2, max_evaluations=2000)
    assert all(row["success"] for row in a["restarts"])
    np.testing.assert_array_equal(a["parameters"], b["parameters"])
    assert a["mse"] < min(row["objective_history"][0] for row in a["restarts"])
    assert a["training_pairs"] == len(v) - 1


def test_zero_returns_are_finite_only_with_explicit_transform_convention():
    result = transformed_series(np.ones(100), np.r_[0.0, np.ones(99)])
    assert np.all(np.isfinite(result["iar"]))
    assert result["iar"][0] == pytest.approx(-np.log(1e-12))


def test_degenerate_mfdfa_and_unknown_config_are_rejected():
    with pytest.raises(ValueError, match="nonconstant"):
        analyze_batch(np.ones(913))
    with pytest.raises(ValueError, match="Unknown"):
        validate_config({"unnoticed_typo": 3})
    with pytest.raises(ValueError, match="positive integers"):
        validate_config({"shuffles": 0})
