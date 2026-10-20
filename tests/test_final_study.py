import json

import numpy as np
import pytest

from qcvol.data import DailyData, prepare, synthetic_data
from qcvol.final_evaluation import block_indices, evaluate_final, numbers, paired_bootstrap
from qcvol.final_study import FinalConfig, check_seal, train_final, training_seed


def small_config(**kwargs):
    values = {
        "kind": "integration",
        "seeds": [0],
        "restarts": 1,
        "forecast_max_calls": 40,
        "forecast_max_iterations": 2,
        "network_max_calls": 40,
        "network_max_iterations": 2,
        "paper_max_calls": 5,
        "realism_starts": 1,
        "realism_max_calls": 32,
        "train_days": 64,
        "train_paths": 1,
        "train_burn_in": 0,
        "evaluation_days": 64,
        "evaluation_paths": 1,
        "evaluation_burn_in": 0,
        "bootstrap_replicates": 20,
        "bootstrap_blocks": [7, 30],
    }
    values.update(kwargs)
    return FinalConfig(**values)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"kind": "final", "seeds": [0]},
        {"seeds": [0, 0]},
        {"network_ridge": float("nan")},
        {"realism_weights": {"quantum": 0.1}},
        {"restarts": 0},
        {"realism_max_calls": 4},
        {"bootstrap_blocks": [0]},
        {"train_days": 30},
    ],
)
def test_final_config_guards(kwargs):
    with pytest.raises(ValueError):
        small_config(**kwargs)


def test_paired_bootstrap_and_missing_variability():
    indices = block_indices(31, 7, 20, np.random.default_rng(2))
    assert indices.shape == (20, 31)
    for offset in (0, 7, 14, 21):
        np.testing.assert_array_equal(
            np.diff(indices[:, offset : offset + 7], axis=1) % 31, np.ones((20, 6), int)
        )
    assert numbers([1])["sd"] is None
    assert numbers([np.nan])["valid"] == 0
    losses = {
        "quantum-D": np.tile(np.arange(31), (2, 1)),
        "quantum-A": np.tile(np.arange(31) + 2, (2, 1)),
    }
    result = paired_bootstrap(losses, [7, 30], 20)
    assert len(result) == 2
    for row in result:
        assert row["mean_difference"] == row["lower"] == row["upper"] == 2


def test_training_selection_cannot_use_future_observations():
    data = prepare(synthetic_data(220))
    daily = DailyData(
        data.daily.index.copy(), data.daily.returns.copy(), data.daily.rv.copy(), data.daily.units
    )
    end = data.target_rows[data.train.stop - 1] + 1
    daily.returns[end:] += 50
    daily.rv[end:] *= 100
    changed = prepare(daily)
    config = small_config()
    a = training_seed(data, config, 0, progress=lambda *a, **kw: None)
    b = training_seed(changed, config, 0, progress=lambda *a, **kw: None)
    for family in a["families"]:
        for stage in ("D", "A"):
            assert (
                a["families"][family][stage + "_parameters"]
                == b["families"][family][stage + "_parameters"]
            )
            assert (
                a["families"][family][stage + "_restart"]
                == b["families"][family][stage + "_restart"]
            )
    assert a["paper"]["parameters"] == b["paper"]["parameters"]


def test_sealed_two_stage_evaluation_and_tamper_guards(tmp_path):
    pytest.importorskip("arch")
    data = prepare(synthetic_data(220))
    config = small_config()
    output = tmp_path / "study"
    seal = train_final(data, config, output, progress=lambda *a, **kw: None)
    assert seal["test_scores_computed"] is False
    assert not (output / "evaluation").exists()
    manifest, checked = check_seal(output, data)
    assert checked == config and manifest["test_scores_computed"] is False
    # Frozen source/config/data/parameters must be identical at evaluation time.
    daily = DailyData(
        data.daily.index.copy(), data.daily.returns.copy(), data.daily.rv.copy(), data.daily.units
    )
    daily.rv[-1] *= 2
    with pytest.raises(ValueError, match="data mismatch"):
        check_seal(output, prepare(daily))
    path = output / "training-seed0.json"
    original = path.read_text()
    row = json.loads(original)
    row["families"]["quantum"]["D_parameters"][0] += 0.1
    path.write_text(json.dumps(row))
    with pytest.raises(ValueError, match="artifact changed"):
        evaluate_final(data, output)
    path.write_text(original)
    result = evaluate_final(data, output, progress=lambda *a, **kw: None)
    assert len(result["models"]) == 12
    status = json.loads((output / "evaluation/status.json").read_text())
    assert (
        status["kind"] == "integration"
        and status["forecast_records"] == 12
        and status["path_records"] == 13
    )
    assert (
        result["reference"]["test_return_hill"] is not None
    )  # NaN stays internal until serialization
    saved = json.loads((output / "evaluation/summary.json").read_text())
    assert saved["reference"]["test_return_hill"] is None
    assert len(saved["bootstrap_nll"]) == 16
    with pytest.raises(FileExistsError):
        evaluate_final(data, output)
    # Phase-two execution never changes the frozen training artifacts.
    check_seal(output, data)


def final_verifier():
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "scripts/verify_final_study.py"
    spec = importlib.util.spec_from_file_location("verify_final", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_independent_mfdfa_matches_saved_conventions():
    from qcvol.metrics import mfdfa

    verifier = final_verifier()
    rng = np.random.default_rng(50)
    for values in (rng.normal(size=1024), np.diff(np.cumsum(rng.normal(size=1025)))):
        expected = verifier.independent_mfdfa(values)
        actual = mfdfa(values)
        assert actual["available"]
        for name, value in expected.items():
            np.testing.assert_allclose(actual[name], value, atol=1e-8)


def test_independent_final_replay_and_corrupt_bootstrap(tmp_path):
    from qcvol.data import load_author_data, sha256

    pytest.importorskip("arch")
    raw = tmp_path / "author"
    raw.mkdir()
    daily = synthetic_data(220)
    for name, values in [("data-rstand", daily.returns), ("data-ystand", daily.rv)]:
        np.savetxt(raw / name, np.c_[np.arange(len(values)), values])
    data = prepare(load_author_data(raw))
    output = tmp_path / "run"
    source = {"sha256": {name: sha256(raw / name) for name in ("data-rstand", "data-ystand")}}
    train_final(data, small_config(), output, source, progress=lambda *a, **kw: None)
    evaluate_final(data, output, progress=lambda *a, **kw: None)
    verifier = final_verifier()
    assert verifier.verify(output, raw, allow_integration=True)["verified"]
    with pytest.raises(AssertionError):
        verifier.verify(output, raw)
    path = output / "evaluation/summary.json"
    original = path.read_text()
    summary = json.loads(original)
    summary["bootstrap_nll"][0]["lower"] += 1
    path.write_text(json.dumps(summary))
    with pytest.raises(AssertionError):
        verifier.verify(output, raw, allow_integration=True)
