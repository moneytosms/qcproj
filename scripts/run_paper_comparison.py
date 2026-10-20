#!/usr/bin/env python3
"""Race 2: our sealed quantum models versus the paper's 1-qubit model on the same test days.

Protocol: doc/paper-comparison-protocol.md (committed before this was run).
"""

import argparse
import json
from pathlib import Path

import numpy as np

from qcvol import fresh_runner as fr
from qcvol.data import load_daily_csv
from qcvol.distribution_study import central_gradient
from qcvol.experiment import write_json
from qcvol.final_evaluation import block_indices, numbers
from qcvol.final_study import restore_baseline
from qcvol.fresh_study import prepare_dates, window_reference
from qcvol.training import fit_point, generate_point, point_prediction

RESTARTS, MAX_CALLS = 5, 10000


def fit_paper(data, seed):
    """Same restart scheme and checks as the frozen study's paper panel."""
    rows = data.target_rows[data.train]
    fits = []
    for restart in range(RESTARTS):
        init = 200000 + 100 * seed + restart
        fit, scaling = fit_point(
            "paper",
            data,
            seed=init,
            max_evaluations=MAX_CALLS,
            initialization="uniform",
            reduce_inactive=True,
        )
        p = fit.parameters.copy()

        def objective(active, p=p, scaling=scaling):
            q = p.copy()
            q[[0, 2]] = active
            pred = point_prediction("paper", q, data, rows, scaling) / scaling.rv_scale
            return float(np.mean((pred - data.daily.rv[rows] / scaling.rv_scale) ** 2))

        gradient = float(np.max(np.abs(central_gradient(objective, p[[0, 2]]))))
        fits.append(
            {
                "restart": restart,
                "parameters": p.tolist(),
                "objective": fit.objective,
                "success": fit.success,
                "gradient_inf": gradient,
                "eligible": bool(fit.success and gradient <= 1e-5),
            }
        )
    best = min(fits, key=lambda f: (f["objective"], f["restart"]))
    return best, fits, scaling


def residual_law(data, scaling, parameters):
    """Paper forecast plus its empirical training errors in log RV (like HAR residual)."""
    rows = data.target_rows[data.train]
    h = np.maximum(point_prediction("paper", parameters, data, rows, scaling), 1e-12)
    residuals = np.sort(data.y[data.train] - np.log(h))

    def probabilities(h_test):
        thresholds = data.bins.edges[None, :] - np.log(np.maximum(h_test, 1e-12))[:, None]
        cdf = (np.searchsorted(residuals, thresholds, side="right") + 0.5) / (len(residuals) + 1)
        return np.diff(np.column_stack([np.zeros(len(cdf)), cdf, np.ones(len(cdf))]), axis=1)

    return probabilities


def losses(rv, h, probabilities, labels):
    h = np.maximum(h, 1e-12)
    ratio = rv / h
    return {
        "squared_error": (rv - h) ** 2,
        "qlike": ratio - np.log(ratio) - 1,
        "log_loss": -np.log(np.clip(probabilities[np.arange(len(labels)), labels], 1e-12, 1)),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data/bitstamp_daily.csv"))
    parser.add_argument("--config", type=Path, default=Path("configs/fresh-study.json"))
    parser.add_argument("--study", type=Path, default=Path("results/fresh-study"))
    parser.add_argument("--output", type=Path, default=Path("doc/fresh-study-results"))
    args = parser.parse_args()
    config = fr.FreshConfig(**json.loads(args.config.read_text()))
    data = prepare_dates(load_daily_csv(args.data))
    fr.check_seal(data, args.study)

    test_rows = data.target_rows[data.test]
    rv, labels, x = data.daily.rv[test_rows], data.labels[data.test], data.x[data.test]
    days = len(rv)
    level_rv = np.array([np.exp(pool).mean() for pool in data.bins.pools])
    train_reference, scales = window_reference(data.y[data.train], days, count=12)
    bundle = json.loads((args.study / "baselines.json").read_text())
    baselines = {r["id"]: restore_baseline(r) for r in bundle["models"]}
    base = baselines["har-quantile"]

    daily, fits, paths = {}, {}, {}
    for seed in config.final_seeds:
        best, all_fits, scaling = fit_paper(data, seed)
        fits[seed] = {"best": best, "fits": all_fits, "scaling": vars(scaling)}
        p = np.array(best["parameters"])
        h = point_prediction("paper", p, data, test_rows, scaling)
        probs = residual_law(data, scaling, p)(h)
        for k, v in losses(rv, h, probs, labels).items():
            daily.setdefault("paper", {}).setdefault(k, []).append(v)
        y, r, clipped = generate_point(
            "paper",
            p,
            data,
            scaling,
            days,
            config.evaluation_paths,
            500000 + seed,
            config.evaluation_burn_in,
        )
        row = fr.path_record(
            y, r, data.y[data.test], scales, train_reference, scales, data.bins.edges
        )
        row["clipped_inputs"] = clipped
        paths.setdefault("paper", []).append(row)

        trained = json.loads((args.study / f"train-seed{seed}.json").read_text())["models"]
        for name, stage in (
            ("quantum-har", "D"),
            ("quantum-har", "A"),
            ("quantum-short", "D"),
            ("softmax-har", "D"),
        ):
            entry = trained[name]
            model = fr.model_for(name, entry["depth"], base)
            pr = model.probabilities(x, np.array(entry[stage]["parameters"]))
            for k, v in losses(rv, pr @ level_rv, pr, labels).items():
                daily.setdefault(f"{name}-{stage}", {}).setdefault(k, []).append(v)
        print(f"seed {seed}: paper eligible={best['eligible']}", flush=True)

    pr = baselines["har-residual"].probabilities(x)
    for k, v in losses(rv, pr @ level_rv, pr, labels).items():
        daily.setdefault("har-residual", {})[k] = [v]
    persistence = data.daily.rv[test_rows - 1]
    for k, v in losses(rv, persistence, np.full((days, 4), 0.25), labels).items():
        if k != "log_loss":
            daily.setdefault("persistence", {})[k] = [v]

    records = json.loads((args.study / "evaluation" / "records.json").read_text())["paths"]
    realism = {"paper": numbers([r["test_moment_distance"] for r in paths["paper"]])}
    moments = {"paper": np.mean([r["mean_moments"] for r in paths["paper"]], axis=0).tolist()}
    for id_ in (
        "quantum-har-D",
        "quantum-har-A",
        "quantum-short-D",
        "softmax-har-D",
        "har-residual",
    ):
        rows = [r for r in records if r["id"] == id_]
        realism[id_] = numbers([r["test_moment_distance"] for r in rows])
        moments[id_] = np.mean([r["mean_moments"] for r in rows], axis=0).tolist()

    summary = {
        name: {k: numbers([np.mean(v) for v in vals]) for k, vals in d.items()}
        for name, d in daily.items()
    }
    rng = np.random.default_rng(610000)
    intervals = []
    for block in config.bootstrap_blocks:
        idx = block_indices(days, block, config.bootstrap_replicates, rng)
        for left in ("quantum-har-D", "quantum-har-A"):
            for metric in ("squared_error", "qlike", "log_loss"):
                delta = np.mean(daily[left][metric], axis=0) - np.mean(
                    daily["paper"][metric], axis=0
                )
                boot = delta[idx].mean(axis=1)
                intervals.append(
                    {
                        "left": left,
                        "right": "paper",
                        "metric": metric,
                        "block": block,
                        "mean_difference": float(delta.mean()),
                        "lower": float(np.quantile(boot, 0.025)),
                        "upper": float(np.quantile(boot, 0.975)),
                    }
                )
    result = {
        "summary": summary,
        "realism": realism,
        "mean_moments": moments,
        "test_moments": fr.moments(data.y[data.test]).tolist(),
        "intervals": intervals,
        "paper_fits_eligible": sum(f["best"]["eligible"] for f in fits.values()),
        "paper_parameters_by_seed": {s: f["best"]["parameters"] for s, f in fits.items()},
        "paper_clipped_inputs": numbers([r["clipped_inputs"] for r in paths["paper"]]),
    }
    out = args.study / "paper-comparison"
    out.mkdir(exist_ok=True)
    write_json(out / "fits.json", fits)
    write_json(out / "paths.json", paths)
    args.output.mkdir(parents=True, exist_ok=True)
    write_json(args.output / "paper-comparison.json", result)
    print(
        json.dumps(
            {k: {m: round(v["mean"], 6) for m, v in s.items()} for k, s in summary.items()},
            indent=1,
        )
    )


if __name__ == "__main__":
    main()
