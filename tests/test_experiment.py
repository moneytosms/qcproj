import json

import pytest

from qcvol.experiment import ExperimentConfig, summarize, write_json


def test_config_rejects_invalid_or_misleading_budget():
    with pytest.raises(ValueError, match="budget"):
        ExperimentConfig(max_evaluations=20)
    with pytest.raises(ValueError, match="include zero"):
        ExperimentConfig(lambdas=[0.05])
    with pytest.raises(ValueError, match="seeds"):
        ExperimentConfig(seeds=[0, 0])


def test_json_undefined_metrics_are_null_and_single_seed_spread_unknown(tmp_path):
    path = tmp_path / "out.json"
    write_json(path, {"undefined": float("nan")})
    assert json.loads(path.read_text()) == {"undefined": None}
    records = [
        {
            "name": "test",
            "panel": "distribution",
            "forecast": {"log_loss": 1.0},
            "realism": {"mean_per_path": {"moment_distance": 3.0, "wasserstein_log_rv": 2.0}},
        }
    ]
    assert summarize(records)[0]["metrics"]["log_loss"]["std"] is None


def test_complete_offline_experiment_saves_reviewable_artifacts(tmp_path):
    import numpy as np

    from qcvol.data import prepare, synthetic_data
    from qcvol.experiment import run_experiment

    data = prepare(synthetic_data(200))
    config = ExperimentConfig(
        layers=[1],
        lambdas=[0.0],
        max_evaluations=26,
        train_path_days=32,
        train_paths=1,
        evaluation_days=40,
        evaluation_paths=1,
        burn_in=0,
    )
    output = tmp_path / "run"
    summary = run_experiment(data, config, output, source={"kind": "synthetic-demo"})
    assert len(summary) == 10
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["status"] == "complete"
    assert manifest["code"]["package_source_sha256"]["quantum.py"]
    records = json.loads((output / "records.json").read_text())
    assert len(records) == 10
    assert all(r["risk"]["available"] for r in records if r["panel"] == "distribution")
    artifacts = list(output.glob("*.npz"))
    assert len(artifacts) == 10
    predictions = np.load(output / "quantum_selected-seed0.npz")
    assert predictions["probabilities"].shape == (len(data.y[data.test]), 4)
    np.testing.assert_allclose(predictions["probabilities"].sum(axis=1), 1)
    assert predictions["log_rv_paths"].shape == (1, 40)
    with pytest.raises(FileExistsError):
        run_experiment(data, config, output)
