import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from qcvol.classical_training import continue_network, network_loss_gradient, sensitivity_rank
from qcvol.comparison_study import ComparisonConfig, garch_paths, load_prior
from qcvol.data import DailyData, load_author_data, prepare, synthetic_data
from qcvol.distribution_models import ShortSoftmax
from qcvol.distribution_study import central_gradient
from qcvol.finance_baselines import (
    QUANTILES,
    CalibratedGARCH,
    QuantileHAR,
    empirical_bin_quantiles,
    garch_likelihood_gradient,
    garch_variance,
    quantile_scores,
)


def test_analytic_network_gradient_and_continuation():
    data = prepare(synthetic_data(220))
    p = np.random.default_rng(7).normal(0, 0.3, 24)
    loss, gradient = network_loss_gradient(p, data.x[data.train], data.labels[data.train])
    objective = lambda theta: network_loss_gradient(
        theta, data.x[data.train], data.labels[data.train]
    )[0]
    assert np.isfinite(loss)
    np.testing.assert_allclose(gradient, central_gradient(objective, p), atol=1e-8)
    fit = continue_network(p, data, max_calls=100, max_iterations=20)
    assert fit["objective"] <= fit["initial_objective"]
    assert len(fit["objective_history"]) == fit["objective_calls"] == fit["gradient_evaluations"]
    rank = sensitivity_rank(ShortSoftmax(), np.zeros(9), data.x[data.train])
    assert rank["local_rank"] == 9


def test_quantile_lp_certificates_and_rearrangement():
    data = prepare(synthetic_data(220))
    for short in (False, True):
        model, fit = QuantileHAR.fit(
            data.x[data.train], data.y[data.train], data.bins.edges, short=short
        )
        assert fit["eligible"]
        assert fit["optimized_parameter_count"] == (45 if short else 60)
        design = np.column_stack(
            [
                data.x[data.train][:, [0, 3]] if short else data.x[data.train][:, :3],
                np.ones(data.train.stop),
            ]
        )
        for column, record in enumerate(fit["quantile_fits"]):
            tau = record["quantile"]
            residual = data.y[data.train] - design @ model.coefficients[:, column]
            primal = np.maximum(tau * residual, (tau - 1) * residual).mean()
            dual = np.array(record["dual"])
            np.testing.assert_allclose(primal, data.y[data.train] @ dual / len(dual), atol=1e-8)
            np.testing.assert_allclose(design.T @ dual, 0, atol=1e-8)
            assert np.min(dual) >= tau - 1 - 1e-8 and np.max(dual) <= tau + 1e-8
        quantiles = model.predict_quantiles(data.x[data.validation])
        assert np.all(np.diff(quantiles, axis=1) >= 0)
        p = model.probabilities(data.x[data.validation])
        assert np.all(p > 0)
        np.testing.assert_allclose(p.sum(axis=1), 1)
        score = quantile_scores(quantiles, data.y[data.validation])
        assert score["mean_pinball"] >= 0
        assert 0 <= score["coverage_90"] <= 1
        changed = data.x[data.validation].copy()
        changed[:, 1:3] += 500
        if short:
            np.testing.assert_array_equal(p, model.probabilities(changed))
    # Crossing repair and extreme-tail conversion must remain a proper distribution.
    tied = replace(model, coefficients=np.zeros_like(model.coefficients))
    p = tied.probabilities(data.x[data.validation])
    assert np.all(p > 0)
    np.testing.assert_allclose(p.sum(axis=1), 1)


def test_empirical_bin_quantile_law_and_pinball():
    pools = (np.array([1.0, 2.0]), np.array([3.0]), np.array([4.0]), np.array([5.0]))
    p = np.array([[1.0, 0, 0, 0], [0, 0, 0, 1.0]])
    q = empirical_bin_quantiles(p, pools)
    np.testing.assert_array_equal(q[1], np.full(len(QUANTILES), 5.0))
    assert np.all(q[0, :8] == 1.0) and np.all(q[0, 8:] == 2.0)
    perfect = np.tile(np.array([1.0, 2.0])[:, None], (1, len(QUANTILES)))
    assert quantile_scores(perfect, np.array([1.0, 2.0]))["mean_pinball"] == 0


def test_garch_gradient_alignment_and_past_only():
    rng = np.random.default_rng(4)
    r = rng.normal(size=100)
    p = np.array([0.1, 0.15, 0.7])
    backcast = 0.8
    value, gradient = garch_likelihood_gradient(r, p, backcast)
    numeric = central_gradient(lambda theta: garch_likelihood_gradient(r, theta, backcast)[0], p)
    np.testing.assert_allclose(gradient, numeric, atol=1e-6)
    h = garch_variance(r, p, backcast)
    assert h[0] == pytest.approx(p[0] + (p[1] + p[2]) * backcast)
    altered = r.copy()
    altered[50:] += 100
    np.testing.assert_array_equal(h[:51], garch_variance(altered, p, backcast)[:51])
    assert np.isfinite(value)


def test_garch_fit_library_check_and_future_isolation():
    pytest.importorskip("arch")
    data = prepare(synthetic_data(220))
    model, fit = CalibratedGARCH.fit(data)
    assert fit["eligible"]
    assert all(r["recursion_relative_error"] < 1e-8 for r in fit["fits"])
    end = data.target_rows[data.train.stop - 1] + 1
    daily = DailyData(
        data.daily.index.copy(), data.daily.returns.copy(), data.daily.rv.copy(), data.daily.units
    )
    daily.returns[end:] += 15
    daily.rv[end:] *= 10
    changed = prepare(daily)
    other, other_fit = CalibratedGARCH.fit(changed)
    np.testing.assert_allclose(model.parameters, other.parameters, atol=1e-12)
    np.testing.assert_array_equal(model.calibration, other.calibration)
    np.testing.assert_array_equal(
        model.filter(data)[: data.train.stop + 1], other.filter(changed)[: data.train.stop + 1]
    )
    config = ComparisonConfig(audit_days=64, audit_paths=2, burn_in=3)
    for native in (False, True):
        a = garch_paths(model, data, config, 50000, native)
        b = garch_paths(other, changed, config, 50000, native)
        np.testing.assert_array_equal(a.log_rv, b.log_rv)
        assert np.all(np.isfinite(a.log_rv))
    assert other_fit["eligible"]


def test_prior_provenance_rejects_changes(tmp_path):
    data = prepare(synthetic_data(220))
    (tmp_path / "manifest.json").write_text(json.dumps({"status": "running"}))
    with pytest.raises(ValueError):
        load_prior(tmp_path, data)
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "status": "complete",
                "data": data.metadata(),
                "code": {"package_source_sha256": {"distribution_models.py": "tampered"}},
            }
        )
    )
    with pytest.raises(ValueError, match="implementation changed"):
        load_prior(tmp_path, data)


def test_quantile_training_unchanged_by_future_targets():
    data = prepare(synthetic_data(220))
    daily = DailyData(
        data.daily.index.copy(), data.daily.returns.copy(), data.daily.rv.copy(), data.daily.units
    )
    end = data.target_rows[data.train.stop - 1] + 1
    daily.rv[end:] *= 20
    daily.returns[end:] += 30
    changed = prepare(daily)
    for short in (False, True):
        a, _ = QuantileHAR.fit(data.x[data.train], data.y[data.train], data.bins.edges, short=short)
        b, _ = QuantileHAR.fit(
            changed.x[changed.train], changed.y[changed.train], changed.bins.edges, short=short
        )
        np.testing.assert_array_equal(a.coefficients, b.coefficients)


def test_prior_on_actual_artifacts_if_present():
    prior = Path("results/distribution-study-2026-10-20")
    if not prior.exists():
        pytest.skip("Local ignored study artifacts not present")
    data = prepare(load_author_data("qvol/data/takaishi"))
    manifest, records, decisions = load_prior(prior, data)
    assert len(records) == 60 and manifest["test_scored"] is False
    assert decisions["quantum"]["depth"] == 2
