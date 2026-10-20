#!/usr/bin/env python3
"""Quantum v2 study (doc/v2-protocol.md): train | seal | evaluate.

uv run --extra v2 python scripts/run_v2_study.py train --seed 0
uv run --extra v2 python scripts/run_v2_study.py seal
uv run --extra v2 python scripts/run_v2_study.py evaluate
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from qcvol import fresh_runner as fr
from qcvol.data import load_daily_csv, sha256
from qcvol.experiment import write_json
from qcvol.final_evaluation import block_indices, numbers
from qcvol.fresh_study import prepare_dates
from qcvol_v2 import models as v2

SEEDS = range(20)
REFERENCES = (("quantum-har", "D"), ("softmax-har", "D"))
CONTRASTS = (
    ("quantum-v2", "quantum-har-D"),
    ("quantum-v2", "softmax-v2"),
    ("quantum-v2", "network-v2"),
    ("quantum-v2", "quantum-v2-nocal"),
)


def source_hash():
    digest = hashlib.sha256()
    for path in sorted(Path(v2.__file__).parent.glob("*.py")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def train(data, seed, out):
    rows = {}
    for name, (spec, calendar, ridge) in v2.MODELS.items():
        x = v2.features(data, calendar)[data.train]
        best, fits = v2.fit(spec, x, data.labels[data.train], seed, ridge=ridge)
        rows[name] = {
            "spec": vars(spec),
            "calendar": calendar,
            "ridge": ridge,
            "best": best,
            "fits": fits,
        }
        print(
            f"seed {seed} {name}: train {best['train_log_loss']:.4f} eligible={best['eligible']}",
            flush=True,
        )
    write_json(out / f"train-seed{seed}.json", {"seed": seed, "models": rows})


def seal(out):
    names = [f"train-seed{s}.json" for s in SEEDS]
    missing = [n for n in names if not (out / n).exists()]
    if missing:
        raise SystemExit(f"Missing: {missing}")
    write_json(
        out / "seal.json",
        {
            "artifacts": {n: sha256(out / n) for n in names},
            "qcvol_v2_source_sha256": source_hash(),
            "test_scores_computed": False,
        },
    )


def check_seal(out):
    record = json.loads((out / "seal.json").read_text())
    if record["qcvol_v2_source_sha256"] != source_hash():
        raise ValueError("qcvol_v2 source changed after sealing")
    for name, digest in record["artifacts"].items():
        if sha256(out / name) != digest:
            raise ValueError(f"Artifact changed after sealing: {name}")


def scores(probabilities, labels, rv, level_rv):
    n = len(labels)
    onehot = np.eye(4)[labels]
    h = probabilities @ level_rv
    ratio = rv / h
    return {
        "log_loss": -np.log(np.clip(probabilities[np.arange(n), labels], 1e-12, 1)),
        "brier": ((probabilities - onehot) ** 2).sum(axis=1),
        "qlike": ratio - np.log(ratio) - 1,
    }


def evaluate(data, out, study, config):
    check_seal(out)
    fr.check_seal(data, study)
    test_rows = data.target_rows[data.test]
    labels, rv = data.labels[data.test], data.daily.rv[test_rows]
    level_rv = np.array([np.exp(pool).mean() for pool in data.bins.pools])
    daily = {}
    eligible = {}
    for seed in SEEDS:
        trained = json.loads((out / f"train-seed{seed}.json").read_text())["models"]
        for name, (spec, calendar, _) in v2.MODELS.items():
            probs_fn, _ = v2.build(spec)
            x = v2.features(data, calendar)[data.test]
            entry = trained[name]["best"]
            pr = np.asarray(probs_fn(np.array(entry["parameters"]), x))
            for k, v in scores(pr, labels, rv, level_rv).items():
                daily.setdefault(name, {}).setdefault(k, []).append(v)
            eligible[name] = eligible.get(name, 0) + int(entry["eligible"])
        old = json.loads((study / f"train-seed{seed}.json").read_text())["models"]
        for name, stage in REFERENCES:
            model = fr.model_for(name, old[name]["depth"])
            pr = model.probabilities(data.x[data.test], np.array(old[name][stage]["parameters"]))
            for k, v in scores(pr, labels, rv, level_rv).items():
                daily.setdefault(f"{name}-{stage}", {}).setdefault(k, []).append(v)
    summary = {
        name: {k: numbers([float(np.mean(v)) for v in vals]) for k, vals in d.items()}
        for name, d in daily.items()
    }
    rng = np.random.default_rng(620000)
    days = len(labels)
    intervals = []
    for block in config.bootstrap_blocks:
        idx = block_indices(days, block, config.bootstrap_replicates, rng)
        for left, right in CONTRASTS:
            for metric in ("log_loss", "brier", "qlike"):
                delta = np.mean(daily[left][metric], axis=0) - np.mean(daily[right][metric], axis=0)
                boot = delta[idx].mean(axis=1)
                intervals.append(
                    {
                        "left": left,
                        "right": right,
                        "metric": metric,
                        "block": block,
                        "mean_difference": float(delta.mean()),
                        "lower": float(np.quantile(boot, 0.025)),
                        "upper": float(np.quantile(boot, 0.975)),
                    }
                )
    result = {
        "post_hoc": True,
        "summary": summary,
        "intervals": intervals,
        "eligible_fits_of_20": eligible,
        "test_days": days,
    }
    write_json(out / "evaluation.json", result)
    print(json.dumps({n: round(s["log_loss"]["mean"], 4) for n, s in summary.items()}, indent=1))
    for i in intervals:
        if i["metric"] == "log_loss":
            print(
                f"{i['left']} - {i['right']} (block {i['block']}): {i['mean_difference']:+.4f} "
                f"[{i['lower']:+.4f}, {i['upper']:+.4f}]"
            )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["train", "seal", "evaluate"])
    parser.add_argument("--seed", type=int, action="append")
    parser.add_argument("--data", type=Path, default=Path("data/bitstamp_daily.csv"))
    parser.add_argument("--output", type=Path, default=Path("results/v2-study"))
    parser.add_argument("--study", type=Path, default=Path("results/fresh-study"))
    parser.add_argument("--config", type=Path, default=Path("configs/fresh-study.json"))
    args = parser.parse_args()
    data = prepare_dates(load_daily_csv(args.data))
    args.output.mkdir(parents=True, exist_ok=True)
    if args.stage == "train":
        for seed in args.seed or SEEDS:
            train(data, seed, args.output)
    elif args.stage == "seal":
        seal(args.output)
    else:
        config = fr.FreshConfig(**json.loads(args.config.read_text()))
        evaluate(data, args.output, args.study, config)


if __name__ == "__main__":
    main()
