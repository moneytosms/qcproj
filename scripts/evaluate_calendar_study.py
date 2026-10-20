#!/usr/bin/env python3
"""Score sealed calendar/readout models on the exposed PR 8 benchmark, without selection."""

import argparse
import hashlib
from pathlib import Path

import numpy as np

from qcvol import calendar_study as cs
from qcvol.calendar_models import CalendarReadout, weekday
from qcvol.data import load_daily_csv, sha256
from qcvol.experiment import write_json
from qcvol.final_evaluation import block_indices, numbers
from qcvol.final_study import restore_baseline
from qcvol.finance_baselines import empirical_bin_quantiles, quantile_scores
from qcvol.fresh_models import make_model
from qcvol.fresh_runner import data_fingerprint, path_record
from qcvol.fresh_study import prepare_dates, window_reference
from qcvol.generation import generate
from qcvol.metrics import forecast_scores, moments

CONTRASTS = (
    ("quantum-shared", "quantum"),
    ("quantum-shared", "linear"),
    ("quantum-shared", "tanh"),
    ("quantum-shared", "sine"),
    ("quantum-shared", "legacy-softmax-har"),
    ("quantum-shared", "legacy-quantum-har"),
    ("quantum", "linear"),
    ("quantum", "tanh"),
    ("quantum", "sine"),
    ("quantum", "legacy-softmax-har"),
    ("linear", "legacy-softmax-har"),
)


def path_hash(paths):
    h = hashlib.sha256()
    for value in (paths.log_rv, paths.returns):
        h.update(np.asarray(value, dtype="<f8").tobytes())
    return h.hexdigest()


def verify_reference(data, root):
    """Verify the inherited sealed inputs, allowing this follow-up's added modules."""
    root = Path(root)
    seal = cs.read(root / "seal.json")
    manifest = cs.read(root / "manifest.json")
    if manifest["data_fingerprint"] != data_fingerprint(data):
        raise ValueError("Reference data do not match")
    for name, digest in seal["artifacts"].items():
        if sha256(root / name) != digest:
            raise ValueError(f"Reference artifact changed: {name}")
    source = Path(cs.__file__).parent
    for name, digest in seal["code"]["package_source_sha256"].items():
        if sha256(source / name) != digest:
            raise ValueError(f"Reference implementation changed: {name}")
    return {
        "seal_sha256": sha256(root / "seal.json"),
        "manifest_sha256": sha256(root / "manifest.json"),
    }


def bootstrap(losses, replicates=2000):
    rng = np.random.default_rng(610000)
    means = {k: np.asarray(v).mean(axis=0) for k, v in losses.items()}
    rows = []
    for block in (7, 30):
        indices = block_indices(len(next(iter(means.values()))), block, replicates, rng)
        for left, right in CONTRASTS:
            if left not in means or right not in means:
                continue
            delta = means[left] - means[right]
            samples = delta[indices].mean(axis=1)
            rows.append(
                {
                    "left": left,
                    "right": right,
                    "block": block,
                    "mean": float(delta.mean()),
                    "lower": float(np.quantile(samples, 0.025)),
                    "upper": float(np.quantile(samples, 0.975)),
                }
            )
    return rows


def evaluate(data, output, reference=None, integration=False, progress=print):
    out = Path(output)
    cfg = cs.check_seal(data, out)
    if (cfg.kind == "integration") != integration:
        raise ValueError("Integration mode must match the saved study kind")
    selected = cs.read(out / "selection.json")
    reference_info = verify_reference(data, reference) if reference else None
    destination = out / "evaluation"
    destination.mkdir(exist_ok=False)
    write_json(destination / "status.json", {"status": "running", "kind": cfg.kind})
    paths_count, replicates = (2, 50) if integration else (32, 2000)
    burn_in, sim_seed_base = 100, 510000
    test_y, labels = data.y[data.test], data.labels[data.test]
    dates = data.daily.index[data.target_rows][data.test]
    years = dates.astype("datetime64[Y]").astype(str)
    real_dow = weekday(dates)
    train_reference, scales = window_reference(data.y[data.train], len(test_y), count=12)
    first = data.target_rows[data.train.stop - 1] + 1
    generated_start = np.datetime64(data.daily.index[first - 1], "D") + np.timedelta64(
        1 + burn_in, "D"
    )
    generated_dow = weekday(generated_start + np.arange(len(test_y)).astype("timedelta64[D]"))
    base_models = {}
    if reference:
        bundle = cs.read(Path(reference) / "baselines.json")
        base_models = {
            r["id"]: restore_baseline(r)
            for r in bundle["models"]
            if r["id"] in ("har-quantile", "har-residual")
        }
    records, probabilities, losses = [], {}, {}
    for seed in cfg.final_seeds:
        trained = cs.read(out / f"train-seed{seed}.json")["models"]
        linear = selected["policy"]
        candidates = {
            "linear": (
                CalendarReadout(calendar=linear["calendar"]),
                linear["fit"]["parameters"],
                linear["fit"]["eligible"],
                True,
            )
        }
        for kind, row in trained.items():
            candidates[kind] = (
                CalendarReadout(**row["model"]),
                row["fit"]["parameters"],
                row["fit"]["eligible"],
                True,
            )
        if reference:
            inherited = cs.read(Path(reference) / f"train-seed{seed}.json")["models"]
            for name in ("quantum-har", "softmax-har", "network-har"):
                r = inherited[name]
                candidates[f"legacy-{name}"] = (
                    make_model(name, r["depth"]),
                    r["D"]["parameters"],
                    r["D"]["eligible"],
                    False,
                )
            candidates.update({k: (m, None, True, False) for k, m in base_models.items()})
        for name, (model, params, eligible, new) in candidates.items():
            x = cs.arrays(data, model, 0)[0][data.test] if new else data.x[data.test]
            probs = model.probabilities(x, params)
            daily_loss = -np.log(np.clip(probs[np.arange(len(labels)), labels], 1e-12, 1))
            probabilities.setdefault(name, []).append(probs)
            losses.setdefault(name, []).append(daily_loss)
            function = cs.generate_calendar if new else generate
            paths = function(
                model, params, data, len(test_y), paths_count, sim_seed_base + seed, burn_in
            )
            path = path_record(
                paths.log_rv,
                paths.returns,
                test_y,
                scales,
                train_reference,
                scales,
                data.bins.edges,
            )
            path["weekday_means"] = [
                float(paths.log_rv[:, generated_dow == day].mean()) for day in range(7)
            ]
            path["sha256"] = path_hash(paths)
            scores = forecast_scores(probs, labels)
            quantiles = empirical_bin_quantiles(probs, data.bins.pools)
            row = {
                "id": name,
                "seed": seed,
                "eligible": eligible,
                "forecast": scores,
                "quantiles": quantile_scores(quantiles, test_y),
                "paths": path,
                "years": {
                    year: forecast_scores(probs[years == year], labels[years == year])
                    for year in np.unique(years)
                },
            }
            records.append(row)
        write_json(destination / f"seed{seed}.json", records[-len(candidates) :])
        progress(f"evaluated calendar benchmark seed {seed}", flush=True)
    summaries = {}
    for name in losses:
        group = [r for r in records if r["id"] == name]
        summaries[name] = {
            "log_loss": numbers([r["forecast"]["log_loss"] for r in group]),
            "rps_normalized": numbers([r["forecast"]["rps_normalized"] for r in group]),
            "extreme_brier": numbers([r["forecast"]["extreme_brier"] for r in group]),
            "eligible": sum(r["eligible"] for r in group),
            "passing_log_loss": numbers(
                [r["forecast"]["log_loss"] for r in group if r["eligible"]]
            ),
            "coverage_90": numbers([r["quantiles"]["coverage_90"] for r in group]),
            "test_moment_distance": numbers([r["paths"]["test_moment_distance"] for r in group]),
            "moments": np.mean([r["paths"]["mean_moments"] for r in group], axis=0).tolist(),
            "weekday_means": np.mean([r["paths"]["weekday_means"] for r in group], axis=0).tolist(),
            "years": {
                year: numbers([r["years"][year]["log_loss"] for r in group])
                for year in np.unique(years)
            },
        }
    result = {
        "kind": cfg.kind,
        "seeds": len(cfg.final_seeds),
        "summary": summaries,
        "bootstrap": bootstrap(losses, replicates),
        "reference": reference_info,
        "test_counts": np.bincount(labels, minlength=4).tolist(),
        "test_moments": moments(test_y).tolist(),
        "test_weekday_means": [float(test_y[real_dow == day].mean()) for day in range(7)],
        "simulation": {
            "paths": paths_count,
            "days": len(test_y),
            "burn_in": burn_in,
            "seed_base": sim_seed_base,
        },
        "bootstrap_replicates": replicates,
        "seal_sha256": sha256(out / "seal.json"),
        "evaluation_script_sha256": sha256(__file__),
        "exposed_benchmark": True,
    }
    write_json(destination / "summary.json", result)
    np.savez_compressed(
        destination / "probabilities.npz", **{k: np.asarray(v) for k, v in probabilities.items()}
    )
    np.savez_compressed(
        destination / "daily-losses.npz", **{k: np.asarray(v) for k, v in losses.items()}
    )
    write_json(
        destination / "status.json",
        {
            "status": "complete",
            "kind": cfg.kind,
            "seeds": len(cfg.final_seeds),
            "records": len(records),
        },
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--data", type=Path, default=Path("data/bitstamp_daily.csv"))
    parser.add_argument("--reference", type=Path, default=Path("results/fresh-study"))
    args = parser.parse_args()
    print(
        evaluate(prepare_dates(load_daily_csv(args.data)), args.output, args.reference)["summary"]
    )


if __name__ == "__main__":
    main()
