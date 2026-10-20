from dataclasses import replace

import numpy as np
import pytest

from qcvol.data import DailyData, prepare, synthetic_data
from qcvol.distribution_models import (
    ShortAR,
    ShortBorn,
    ShortNetwork,
    ShortSoftmax,
)
from qcvol.distribution_study import (
    DistributionConfig,
    central_gradient,
    fit_forecast,
    run_distribution_study,
    study_selection,
)
from qcvol.generation import generate
from qcvol.quantum import BornCircuit


def test_short_policy_and_phase_removal():
    rng = np.random.default_rng(23)
    x = rng.normal(size=(17, 4))
    changed = x.copy()
    changed[:, 1:3] += 1000
    for depth in range(1, 5):
        model = ShortBorn(depth)
        p = rng.normal(size=model.n_params)
        actual = model.probabilities(x, p)
        expanded = model.expand(p)
        expanded[[-3, -1]] = [2.3, -5.6]
        np.testing.assert_allclose(
            actual, BornCircuit(depth).probabilities(x[:, [0, 0, 0, 3]], expanded), atol=1e-14
        )
        np.testing.assert_array_equal(actual, model.probabilities(changed, p))
    for model in (ShortSoftmax(), ShortNetwork()):
        p = rng.normal(size=model.n_params)
        np.testing.assert_array_equal(model.probabilities(x, p), model.probabilities(changed, p))


def test_short_policy_in_rollouts_and_future_isolation():
    data = prepare(synthetic_data(360))
    # Exaggerate the unused weekly/monthly normalization at simulation time.
    altered = replace(data, scaler=replace(data.scaler, mean=data.scaler.mean.copy()))
    altered.scaler.mean[1:3] += 1000
    model = ShortBorn(2)
    p = np.random.default_rng(4).normal(size=model.n_params)
    a = generate(model, p, data, days=64, paths=2)
    b = generate(model, p, altered, days=64, paths=2)
    np.testing.assert_array_equal(a.log_rv, b.log_rv)
    end = data.target_rows[data.train.stop - 1] + 1
    changed_daily = DailyData(
        data.daily.index.copy(), data.daily.returns.copy(), data.daily.rv.copy(), data.daily.units
    )
    changed_daily.rv[end:] *= 50
    changed_daily.returns[end:] += 20
    future = prepare(changed_daily)
    np.testing.assert_array_equal(a.log_rv, generate(model, p, future, days=64, paths=2).log_rv)


def test_softmax_fit_stationarity_and_ar():
    data = prepare(synthetic_data(360))
    config = DistributionConfig()
    fit = fit_forecast(ShortSoftmax(), data, 0, config)
    assert fit["eligible"]
    assert fit["objective"] < fit["initial_objective"]
    assert len(fit["objective_history"]) == fit["total_objective_calls"]
    assert fit["diagnostic_calls"] == 18
    x = np.array([2.0, 3.0])
    np.testing.assert_allclose(central_gradient(lambda p: p @ p, x), 2 * x)
    ar = ShortAR.fit(data.x[data.train], data.y[data.train], data.bins.edges)
    probs = ar.probabilities(data.x[data.validation])
    assert np.all(probs >= 0)
    np.testing.assert_allclose(probs.sum(axis=1), 1)


def test_selection_training_restart_then_validation_and_zero_fallback():
    records = []
    for family in ("quantum", "softmax", "network"):
        for depth in (1, 2):
            for start in (0, 1):
                records.append(
                    {
                        "id": f"{family}-{depth}-{start}",
                        "family": family,
                        "depth": depth,
                        "stage": "D",
                        "start": start,
                        "lambda": 0,
                        "fit": {"objective": start + 1, "eligible": True},
                        "validation": {"log_loss": 3 - depth if start == 0 else 0},
                        "selection_score": 3 - depth if start == 0 else 0,
                    }
                )
        records.append(
            {
                "id": f"{family}-A",
                "family": family,
                "depth": 2,
                "stage": "A",
                "start": 0,
                "lambda": 0.01,
                "fit": {"objective": 0.1},
                "selection_score": 5,
            }
        )
    selections = study_selection(records, DistributionConfig())
    for family, row in selections.items():
        assert row["forecast_id"] == row["selected_id"] == f"{family}-2-0"
        assert row["lambda"] == 0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"depths": [0]},
        {"lambdas": [0.1]},
        {"starts": [0, 0]},
        {"realism_max_calls": 2},
        {"selection_weight": float("nan")},
        {"train_days": 30},
    ],
)
def test_config_rejects_invalid(kwargs):
    with pytest.raises(ValueError):
        DistributionConfig(**kwargs)


def test_small_validation_only_study(tmp_path):
    data = prepare(synthetic_data(220))
    config = DistributionConfig(
        starts=[0],
        depths=[1],
        lambdas=[0, 0.01],
        realism_starts=1,
        forecast_max_calls=80,
        forecast_max_iterations=2,
        realism_max_calls=32,
        selection_days=64,
        selection_paths=1,
        audit_days=64,
        audit_paths=1,
        burn_in=0,
    )
    decisions = run_distribution_study(
        data, config, tmp_path / "run", progress=lambda *a, **kw: None
    )
    assert len(decisions) == 3
    import json

    manifest = json.loads((tmp_path / "run" / "manifest.json").read_text())
    assert manifest["status"] == "complete"
    assert manifest["test_scored"] is False
    for path in (tmp_path / "run").glob("*.npz"):
        with np.load(path, allow_pickle=False) as arrays:
            assert not any("test" in key for key in arrays.files)


def test_independent_dense_gates_and_artifact_tampering(tmp_path):
    import importlib.util
    import json
    from pathlib import Path

    from qcvol.data import load_author_data, sha256

    path = Path(__file__).resolve().parents[1] / "scripts/verify_distribution_study.py"
    spec = importlib.util.spec_from_file_location("verify_distribution", path)
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    rng = np.random.default_rng(6)
    x = rng.normal(size=(23, 4))
    for depth in range(1, 5):
        model = ShortBorn(depth)
        parameters = rng.normal(size=model.n_params)
        np.testing.assert_allclose(
            model.probabilities(x, parameters),
            verifier.literal_born(x, parameters, depth),
            atol=1e-14,
        )
    author_data = path.parents[1] / "qvol/data/takaishi"
    data = prepare(load_author_data(author_data))
    config = DistributionConfig(
        starts=[0],
        depths=[1],
        lambdas=[0, 0.01],
        realism_starts=1,
        forecast_max_calls=80,
        forecast_max_iterations=2,
        realism_max_calls=32,
        train_days=64,
        train_paths=1,
        selection_days=64,
        selection_paths=1,
        audit_days=64,
        audit_paths=1,
        burn_in=0,
    )
    source = {
        "sha256": {name: sha256(author_data / name) for name in ("data-rstand", "data-ystand")}
    }
    root = tmp_path / "run"
    run_distribution_study(data, config, root, source, progress=lambda *a, **kw: None)
    assert verifier.verify(root, author_data)["verified"]
    decisions = json.loads((root / "decision.json").read_text())
    decisions["quantum"]["selected_id"] = "tampered"
    (root / "decision.json").write_text(json.dumps(decisions))
    with pytest.raises(AssertionError):
        verifier.verify(root, author_data)
