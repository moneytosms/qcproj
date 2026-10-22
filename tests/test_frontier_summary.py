import copy
import csv
import importlib.util
import json
import shutil
from pathlib import Path

import numpy as np
import pytest

from qcvol.data import sha256, synthetic_data

spec = importlib.util.spec_from_file_location(
    "frontier_summary", Path(__file__).parents[1] / "scripts/summarize_frontier_study.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

runner_spec = importlib.util.spec_from_file_location(
    "frontier_runner", Path(__file__).parents[1] / "scripts/run_frontier_study.py"
)
runner = importlib.util.module_from_spec(runner_spec)
runner_spec.loader.exec_module(runner)


@pytest.fixture(scope="module")
def saved_run(tmp_path_factory):
    root = tmp_path_factory.mktemp("frontier-replay")
    daily = synthetic_data(1500, seed=7)
    daily.index = np.datetime64("2021-01-01") + daily.index.astype("timedelta64[D]")
    source_path = root / "daily.csv"
    with source_path.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["date", "return", "rv"])
        writer.writerows(zip(daily.index, daily.returns, daily.rv, strict=True))
    summary, probabilities, data = runner.run_study(daily, ridges=(0.01,))
    runner_path = Path(runner.__file__).resolve()
    source = {
        "data_path": str(source_path),
        "data_sha256": sha256(source_path),
        "code_hashes": {"scripts/run_frontier_study.py": sha256(runner_path)},
    }
    output = root / "run"
    runner.write_results(output, summary, probabilities, data, source)
    return output


def test_saved_forecasts_replay_all_metrics(saved_run):
    summary, losses, identity = module.read_run(saved_run)
    assert len(identity[0]) == 366
    for model in module.MODELS:
        for metric in module.METRICS:
            assert losses[model][metric].mean() == pytest.approx(
                summary["metrics"][model]["audit"][metric], abs=1e-12
            )


@pytest.mark.parametrize("field, error", [("p0", ValueError), ("nll", AssertionError)])
def test_saved_forecast_corruption_is_rejected(saved_run, tmp_path, field, error):
    output = tmp_path / "corrupt"
    shutil.copytree(saved_run, output)
    path = output / "predictions.csv"
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    row = next(r for r in rows if r["model"] == "v4" and r["split"] == "audit")
    row[field] = str(float(row[field]) + 0.1)
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(error):
        module.read_run(output)


@pytest.mark.parametrize("source_field", ["data_sha256", "code_hashes"])
def test_changed_source_fingerprint_is_rejected(saved_run, tmp_path, source_field):
    output = tmp_path / "changed-source"
    shutil.copytree(saved_run, output)
    path = output / "summary.json"
    summary = json.loads(path.read_text())
    summary["source"][source_field] = (
        "wrong" if source_field == "data_sha256" else {"scripts/run_frontier_study.py": "wrong"}
    )
    path.write_text(json.dumps(summary))
    with pytest.raises(ValueError, match="changed since fitting"):
        module.read_run(output)


@pytest.mark.parametrize("mismatch", ["duplicate-seed", "config"])
def test_incompatible_runs_are_rejected(saved_run, monkeypatch, mismatch):
    summary, losses, identity = module.read_run(saved_run)
    other = copy.deepcopy(summary)
    if mismatch == "config":
        other["seed"] += 1
        other["config"]["maxiter"] += 1
    monkeypatch.setattr(
        module, "read_run", lambda path: (summary if path == "first" else other, losses, identity)
    )
    message = "distinct seeds" if mismatch == "duplicate-seed" else "Configuration or source"
    with pytest.raises(ValueError, match=message):
        module.summarize(["first", "second"])


def test_effective_quantum_weight_excludes_har_fallback(saved_run, monkeypatch):
    summary, losses, identity = module.read_run(saved_run)
    summary["selections"].update({"v4": "quantum-ridge-0.01", "v5": "har"})
    summary["v6"]["selected"].update({"quantum_weight": 0.75, "v4_weight": 0.25})
    monkeypatch.setattr(module, "read_run", lambda path: (summary, losses, identity))
    monkeypatch.setattr(module, "paired_intervals", lambda delta: [])
    report = module.summarize([saved_run])
    asset = report["assets"][summary["source"]["data_path"]]
    assert asset["effective_quantum_weights"] == [0.1875]


@pytest.mark.parametrize("difference", [0.0, -0.2, 0.3])
def test_paired_intervals_preserve_constant_differences(difference):
    result = module.paired_intervals(np.full(90, difference), replicates=30)
    for row in result:
        assert row["mean_difference"] == pytest.approx(difference)
        assert row["lower"] == pytest.approx(difference)
        assert row["upper"] == pytest.approx(difference)


def test_paired_intervals_reject_nonfinite_or_short_series():
    for delta in (np.zeros(29), np.full(40, np.nan), np.ones((30, 2))):
        with pytest.raises(ValueError):
            module.paired_intervals(delta)
