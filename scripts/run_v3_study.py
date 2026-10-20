#!/usr/bin/env python3
"""Quantum v3 study (doc/v3-protocol.md): train | seal | evaluate.

Born-rule 2-qubit circuit (v2 design), ridge 0.01 and 10-restart ensemble chosen on
validation (2023-2024, seeds 900-901). Training uses train rows only.
"""

import argparse
import json
from pathlib import Path

import numpy as np

from qcvol.data import load_daily_csv, sha256
from qcvol.experiment import write_json
from qcvol.final_evaluation import block_indices
from qcvol.fresh_study import prepare_dates
from qcvol_v2 import models as v2
from qcvol_v3 import models as v3

SEEDS = range(20)
RIDGE = 0.01
RESTARTS = 10


def train(data, seeds, out):
    spec = v3.Spec("born", 6, layers=3)
    x = v2.features(data, True)
    for seed in seeds:
        fits = v3.fit_restarts(spec, x[data.train], data.labels[data.train], seed, RESTARTS, RIDGE)
        rec = {
            "seed": seed,
            "ridge": RIDGE,
            "restarts": RESTARTS,
            "fits": [
                {
                    "restart": f["restart"],
                    "objective": f["objective"],
                    "parameters": f["parameters"].tolist(),
                }
                for f in fits
            ],
        }
        write_json(out / f"train-seed{seed}.json", rec)
        print(
            f"seed {seed}: best train objective {min(f['objective'] for f in fits):.4f}", flush=True
        )


def seal(out):
    names = [f"train-seed{s}.json" for s in SEEDS]
    missing = [n for n in names if not (out / n).exists()]
    if missing:
        raise SystemExit(f"Missing: {missing}")
    src = Path(v3.__file__).read_bytes()
    write_json(
        out / "seal.json",
        {
            "artifacts": {n: sha256(out / n) for n in names},
            "qcvol_v3_models_sha256": __import__("hashlib").sha256(src).hexdigest(),
            "test_scores_computed": False,
        },
    )


def scores(P, labels, rv, level_rv):
    n = len(labels)
    h = P @ level_rv
    ratio = rv / h
    return {
        "log_loss": -np.log(np.clip(P[np.arange(n), labels], 1e-12, 1)),
        "brier": ((P - np.eye(4)[labels]) ** 2).sum(axis=1),
        "qlike": ratio - np.log(ratio) - 1,
    }


def paired_intervals(quantum, controls, blocks, rng, replicates=2000):
    intervals = []
    for block in blocks:
        idx = block_indices(len(quantum), block, replicates, rng)
        for name, losses in controls.items():
            delta = quantum - losses
            boot = delta[idx].mean(axis=1)
            intervals.append(
                {
                    "control": name,
                    "block": block,
                    "mean_difference": float(delta.mean()),
                    "lower": float(np.quantile(boot, 0.025)),
                    "upper": float(np.quantile(boot, 0.975)),
                }
            )
    return intervals


def evaluate(data, out, v2_out):
    rec = json.loads((out / "seal.json").read_text())
    for name, digest in rec["artifacts"].items():
        if sha256(out / name) != digest:
            raise ValueError(f"Artifact changed after sealing: {name}")
    v2_seal = json.loads((v2_out / "seal.json").read_text())
    for name, digest in v2_seal["artifacts"].items():
        if sha256(v2_out / name) != digest:
            raise ValueError(f"v2 artifact changed after sealing: {name}")
    test_rows = data.target_rows[data.test]
    labels, rv = data.labels[data.test], data.daily.rv[test_rows]
    level_rv = np.array([np.exp(pool).mean() for pool in data.bins.pools])
    spec = v3.Spec("born", 6, layers=3)
    x = v2.features(data, True)[data.test]

    per_seed = {}
    for seed in SEEDS:
        fits = json.loads((out / f"train-seed{seed}.json").read_text())["fits"]
        fits = [
            {"objective": f["objective"], "parameters": np.array(f["parameters"])} for f in fits
        ]
        P = v3.ensemble_probs(spec, fits, x)
        per_seed.setdefault("quantum-v3", []).append(scores(P, labels, rv, level_rv))
    # v2 reference: best-of-restarts parameters from the sealed v2 study
    v2_spec = v2.Spec("quantum", 6, layers=3)
    v2_fn, _ = v2.build(v2_spec)
    for seed in SEEDS:
        trained = json.loads((v2_out / f"train-seed{seed}.json").read_text())["models"]
        m = trained["quantum-v2"]["best"]
        P = np.asarray(v2_fn(np.array(m["parameters"]), v2.features(data, True)[data.test]))
        per_seed.setdefault("quantum-v2", []).append(scores(P, labels, rv, level_rv))
        for name in ("softmax-v2", "network-v2"):
            spec, calendar, _ = v2.MODELS[name]
            probs_fn, _ = v2.build(spec)
            model = trained[name]["best"]
            x_classical = v2.features(data, calendar)[data.test]
            P = np.asarray(probs_fn(np.array(model["parameters"]), x_classical))
            per_seed.setdefault(name, []).append(scores(P, labels, rv, level_rv))
    summary = {}
    for name, runs in per_seed.items():
        summary[name] = {
            k: float(np.mean([np.mean(r[k]) for r in runs])) for k in ("log_loss", "brier", "qlike")
        }
    ll = {k: np.mean([r["log_loss"] for r in v], axis=0) for k, v in per_seed.items()}
    rng = np.random.default_rng(620000)
    days = len(labels)
    intervals = paired_intervals(
        ll["quantum-v3"],
        {name: ll[name] for name in ("quantum-v2", "softmax-v2", "network-v2")},
        (7, 30),
        rng,
    )
    result = {
        "post_hoc": True,
        "summary": summary,
        "v3_minus_v2_log_loss": intervals,
        "test_days": days,
    }
    write_json(out / "evaluation.json", result)
    print(json.dumps(summary, indent=1))
    print(intervals)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["train", "seal", "evaluate"])
    parser.add_argument("--seed", type=int, action="append")
    parser.add_argument("--data", type=Path, default=Path("data/bitstamp_daily.csv"))
    parser.add_argument("--output", type=Path, default=Path("results/v3-study"))
    parser.add_argument("--v2", type=Path, default=Path("results/v2-study"))
    args = parser.parse_args()
    data = prepare_dates(load_daily_csv(args.data))
    args.output.mkdir(parents=True, exist_ok=True)
    if args.stage == "train":
        train(data, args.seed or list(SEEDS), args.output)
    elif args.stage == "seal":
        seal(args.output)
    else:
        evaluate(data, args.output, args.v2)


if __name__ == "__main__":
    main()
