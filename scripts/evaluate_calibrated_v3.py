#!/usr/bin/env python3
"""One-time evaluation for doc/calibrated-v3-protocol.md."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.optimize import minimize_scalar
from scipy.special import logsumexp

from qcvol.data import load_daily_csv, sha256
from qcvol.final_evaluation import block_indices
from qcvol.fresh_study import prepare_dates
from qcvol_v2 import models as v2
from qcvol_v3 import models as v3


def fit_temperature(probabilities, labels):
    logp = np.log(np.clip(probabilities, 1e-12, 1))
    rows = np.arange(len(labels))

    def objective(temperature):
        scaled = logp / temperature
        return float(np.mean(logsumexp(scaled, axis=1) - scaled[rows, labels]))

    result = minimize_scalar(objective, bounds=(0.2, 5.0), method="bounded")
    scaled = logp / result.x
    scaled -= logsumexp(scaled, axis=1, keepdims=True)
    return float(result.x), np.exp(scaled)


def _scores(probabilities, labels, rv, level_rv):
    rows = np.arange(len(labels))
    expected_rv = probabilities @ level_rv
    ratio = rv / expected_rv
    return {
        "log_loss": -np.log(np.clip(probabilities[rows, labels], 1e-12, 1)),
        "brier": ((probabilities - np.eye(4)[labels]) ** 2).sum(axis=1),
        "qlike": ratio - np.log(ratio) - 1,
    }


def _v2_source_hash():
    digest = hashlib.sha256()
    for path in sorted(Path(v2.__file__).parent.glob("*.py")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def evaluate(data_path, v2_dir, v3_dir, output, config_path):
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite one-time evaluation: {output}")
    config = json.loads(config_path.read_text())
    data_name = data_path.as_posix()
    if sha256(data_path) != config["data"].get(data_name):
        raise ValueError(f"Data hash differs from frozen config: {data_path}")
    for name, digest in config["code_sha256"].items():
        if sha256(Path(name)) != digest:
            raise ValueError(f"Source hash differs from frozen config: {name}")
    data = prepare_dates(load_daily_csv(data_path))
    daily = data.daily
    target_dates = np.asarray(daily.index, dtype="datetime64[D]")[data.target_rows]
    calibration_rows = (target_dates >= np.datetime64("2023-01-01")) & (
        target_dates < np.datetime64("2024-01-01")
    )
    test_rows = data.test
    labels, rv = data.labels[test_rows], daily.rv[data.target_rows[test_rows]]
    level_rv = np.array([np.exp(pool).mean() for pool in data.bins.pools])
    x = v2.features(data, True)
    spec = v3.Spec("born", 6, layers=3)

    v2_seal = json.loads((v2_dir / "seal.json").read_text())
    v3_seal = json.loads((v3_dir / "seal.json").read_text())
    if v2_seal["qcvol_v2_source_sha256"] != _v2_source_hash():
        raise ValueError("v2 model source changed after sealing")
    if v3_seal["qcvol_v3_models_sha256"] != sha256(Path(v3.__file__)):
        raise ValueError("v3 model source changed after sealing")
    for directory, seal in ((v2_dir, v2_seal), (v3_dir, v3_seal)):
        for name, digest in seal["artifacts"].items():
            if sha256(directory / name) != digest:
                raise ValueError(f"Sealed artifact changed: {directory / name}")

    daily_scores = {
        name: {metric: [] for metric in ("log_loss", "brier", "qlike")}
        for name in ("quantum-v3", "softmax-v2", "network-v2")
    }
    temperatures = {name: [] for name in daily_scores}
    for seed in range(20):
        qfits = json.loads((v3_dir / f"train-seed{seed}.json").read_text())["fits"]
        qfits = [
            {"objective": fit["objective"], "parameters": np.asarray(fit["parameters"])}
            for fit in qfits
        ]
        qval = np.asarray(v3.ensemble_probs(spec, qfits, x[calibration_rows]))
        qtest = np.asarray(v3.ensemble_probs(spec, qfits, x[test_rows]))
        predictions = {"quantum-v3": (qval, qtest)}

        trained = json.loads((v2_dir / f"train-seed{seed}.json").read_text())["models"]
        for name in ("softmax-v2", "network-v2"):
            model_spec, calendar, _ = v2.MODELS[name]
            probability_fn, _ = v2.build(model_spec)
            parameters = np.asarray(trained[name]["best"]["parameters"])
            features = v2.features(data, calendar)
            predictions[name] = (
                np.asarray(probability_fn(parameters, features[calibration_rows])),
                np.asarray(probability_fn(parameters, features[test_rows])),
            )

        for name, (validation, test) in predictions.items():
            temperature, _ = fit_temperature(validation, data.labels[calibration_rows])
            temperatures[name].append(temperature)
            scaled = np.log(np.clip(test, 1e-12, 1)) / temperature
            scaled -= logsumexp(scaled, axis=1, keepdims=True)
            for metric, values in _scores(np.exp(scaled), labels, rv, level_rv).items():
                daily_scores[name][metric].append(values)

    means = {
        name: {metric: np.mean(values, axis=0) for metric, values in metrics.items()}
        for name, metrics in daily_scores.items()
    }
    summary = {
        name: {metric: float(values.mean()) for metric, values in metrics.items()}
        for name, metrics in means.items()
    }
    rng = np.random.default_rng(620000)
    intervals = []
    for block in (7, 30):
        indices = block_indices(len(labels), block, 2000, rng)
        for control in ("softmax-v2", "network-v2"):
            delta = means["quantum-v3"]["log_loss"] - means[control]["log_loss"]
            bootstrap = delta[indices].mean(axis=1)
            intervals.append(
                {
                    "control": control,
                    "block": block,
                    "mean_difference": float(delta.mean()),
                    "lower": float(np.quantile(bootstrap, 0.025)),
                    "upper": float(np.quantile(bootstrap, 0.975)),
                }
            )
    result = {
        "post_hoc_cross_asset": True,
        "config_sha256": sha256(config_path),
        "data_sha256": sha256(data_path),
        "test_days": len(labels),
        "calibration_days": int(calibration_rows.sum()),
        "summary": summary,
        "mean_temperature": {name: float(np.mean(values)) for name, values in temperatures.items()},
        "intervals": intervals,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--v2", type=Path, required=True)
    parser.add_argument("--v3", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    evaluate(args.data, args.v2, args.v3, args.output, args.config)


if __name__ == "__main__":
    main()
