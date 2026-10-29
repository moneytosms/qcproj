import importlib.util
from pathlib import Path

import numpy as np
import pytest

from qcvol.data import synthetic_data

SPEC = importlib.util.spec_from_file_location("frontier", Path("scripts/run_frontier_study.py"))
frontier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(frontier)


def daily_data():
    daily = synthetic_data(1500, seed=7)
    daily.index = np.datetime64("2021-01-01") + daily.index.astype("timedelta64[D]")
    return daily


def test_head_gradient_matches_central_difference():
    rng = np.random.default_rng(4)
    design = rng.normal(size=(12, 4))
    labels = rng.integers(0, 4, 12)
    offset = rng.normal(size=(12, 4))
    p = rng.normal(size=12)
    _, actual = frontier.head_objective(p, design, labels, offset, 0.03)
    expected = np.empty_like(p)
    for i in range(len(p)):
        delta = np.zeros_like(p)
        delta[i] = 1e-6
        expected[i] = (
            frontier.head_objective(p + delta, design, labels, offset, 0.03)[0]
            - frontier.head_objective(p - delta, design, labels, offset, 0.03)[0]
        ) / 2e-6
    assert np.allclose(actual, expected, atol=1e-8)


def test_training_preprocessing_and_sealed_dates_do_not_leak():
    daily = daily_data()
    before = frontier.prepare_development(daily)
    daily.rv[daily.index >= np.datetime64("2023-01-01")] *= 10
    after = frontier.prepare_development(daily)
    assert np.array_equal(before.x[before.train], after.x[after.train])
    assert np.array_equal(before.bins.edges, after.bins.edges)
    assert np.array_equal(before.scaler.mean, after.scaler.mean)
    assert after.daily.index[-1] == np.datetime64("2024-12-31")
    daily.rv[daily.index >= np.datetime64("2025-01-01")] *= 1e6
    sealed = frontier.prepare_development(daily)
    assert np.array_equal(after.y, sealed.y)


def test_probabilities_and_failed_fit_fallback():
    p = frontier.normalized([[0, 0.3, 0.2, 0.5]])
    assert np.all(p > 0)
    assert np.allclose(p.sum(axis=1), 1)
    with pytest.raises(ValueError):
        frontier.normalized([[np.nan, 0, 0, 1]])
    with pytest.raises(ValueError):
        frontier.normalized([[0, 0, 0, 0]])
    records = {
        "failed": {"eligible": False, "calibration_nll": 0},
        "har": {"eligible": True, "calibration_nll": 1},
    }
    assert frontier.select_candidate(["failed"], records) == "har"


def test_end_to_end_synthetic(tmp_path):
    summary, probabilities, data = frontier.run_study(daily_data(), ridges=(0.01,))
    assert summary["head_fit_count"] == 8
    assert summary["eligible_head_fit_count"] == 8
    assert summary["splits"]["calibration"] == ["2023-01-01", "2023-12-31", 365]
    assert summary["splits"]["audit"] == ["2024-01-01", "2024-12-31", 366]
    for p in probabilities.values():
        assert np.allclose(p.sum(axis=1), 1)
    control = summary["metrics"]["classical-selected"]["calibration"]["nll"]
    assert summary["metrics"]["v6"]["calibration"]["nll"] <= control + 1e-12
    changed = daily_data()
    changed.rv[changed.index >= np.datetime64("2024-01-01")] *= 10
    other, _, _ = frontier.run_study(changed, ridges=(0.01,))
    assert other["selections"] == summary["selections"]
    assert other["v6"] == summary["v6"]
    for name in summary["fits"]:
        assert other["fits"][name]["parameters"] == summary["fits"][name]["parameters"]
    output = tmp_path / "run"
    frontier.write_results(output, summary, probabilities, data, {"synthetic": True})
    assert (output / "summary.json").exists()
    assert (output / "predictions.csv").exists()
    with pytest.raises(FileExistsError):
        frontier.write_results(output, summary, probabilities, data, {})
