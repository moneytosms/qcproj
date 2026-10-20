"""Fixed evaluation and paired uncertainty after all training artifacts are sealed."""

import time
from pathlib import Path

import numpy as np
from scipy.stats import wasserstein_distance

from .comparison_study import ComparisonConfig, garch_paths, summarize_paths
from .data import sha256
from .distribution_models import distribution_model
from .experiment import write_json
from .final_study import check_seal, read_json, restore_baseline
from .finance_baselines import empirical_bin_quantiles, garch_variance, quantile_scores
from .generation import generate
from .metrics import forecast_scores, hill_tail_index, moment_scales, moments, path_diagnostics
from .nested_memory import har_features
from .training import PointScaling, point_prediction


def numbers(values):
    values = np.asarray(values, float)
    valid = values[np.isfinite(values)]
    return {
        "count": len(values),
        "valid": len(valid),
        "mean": float(valid.mean()) if len(valid) else None,
        "sd": float(valid.std(ddof=1)) if len(valid) > 1 else None,
        "min": float(valid.min()) if len(valid) else None,
        "max": float(valid.max()) if len(valid) else None,
    }


def block_indices(length, block, replicates, rng):
    if not 1 <= block <= length:
        raise ValueError("Block must fit the test period")
    starts = rng.integers(0, length, size=(replicates, int(np.ceil(length / block))))
    return ((starts[:, :, None] + np.arange(block)) % length).reshape(replicates, -1)[:, :length]


def paired_bootstrap(losses, blocks, replicates, seed=600000):
    """Date uncertainty on seed-averaged paired losses, not a seed-as-dataset interval."""
    contrasts = [
        ("quantum-A", "quantum-D"),
        ("softmax-A", "softmax-D"),
        ("network-A", "network-D"),
        ("quantum-D", "softmax-D"),
        ("quantum-D", "network-D"),
        ("quantum-D", "har-quantile"),
        ("quantum-A", "softmax-A"),
        ("quantum-A", "network-A"),
    ]
    means = {k: np.asarray(v).mean(axis=0) for k, v in losses.items()}
    result = []
    rng = np.random.default_rng(seed)
    for block in blocks:
        indices = block_indices(len(next(iter(means.values()))), block, replicates, rng)
        for left, right in contrasts:
            if left not in means or right not in means:
                continue
            delta = means[left] - means[right]
            boot = delta[indices].mean(axis=1)
            result.append(
                {
                    "left": left,
                    "right": right,
                    "block": block,
                    "mean_difference": float(delta.mean()),
                    "lower": float(np.quantile(boot, 0.025)),
                    "upper": float(np.quantile(boot, 0.975)),
                    "replicates": replicates,
                    "seed": seed,
                }
            )
    return result


def summarize_records(records, path_records, point_records):
    output = []
    for id_ in sorted({r["id"] for r in records}):
        group = [r for r in records if r["id"] == id_]
        paths = [r for r in path_records if r["id"] == id_]
        item = {
            "id": id_,
            "seeds": len(group),
            "D_training_passes": sum(r["D_eligible"] for r in group),
            "stage_training_passes": sum(r["stage_eligible"] for r in group),
        }
        for key in ("log_loss", "rps_normalized", "extreme_brier"):
            item[key] = numbers([r["scores"][key] for r in group])
        for key in ("mean_pinball", "coverage_90", "mean_width_90", "interval_score_90"):
            item[key] = numbers([r["common_quantile_scores"][key] for r in group])
        for key in ("distance_of_mean", "mean_path_distance"):
            item[key] = numbers([r["summary"][key] for r in paths])
        for index, key in enumerate(("acf_1", "acf_7", "acf_30", "vol_of_vol")):
            item[key] = numbers([r["summary"]["mean_moments"][index] for r in paths])
        item["wasserstein_log_rv"] = numbers(
            [r["summary"]["wasserstein_log_rv"]["mean"] for r in paths]
        )
        item["hill_return_tail_index"] = numbers(
            [r["summary"]["hill_return_tail_index"]["mean"] for r in paths]
        )
        native = [r for r in group if "native_quantile_scores" in r]
        if native:
            item["native_quantile_scores"] = {
                key: numbers([r["native_quantile_scores"][key] for r in native])
                for key in ("mean_pinball", "coverage_90", "mean_width_90", "interval_score_90")
            }
        passing = [r for r in group if r["D_eligible"] and r["stage_eligible"]]
        item["passing_only_log_loss"] = numbers([r["scores"]["log_loss"] for r in passing])
        output.append(item)
    point = {
        id_: numbers([r["mse_rv"] for r in point_records if r["id"] == id_])
        for id_ in sorted({r["id"] for r in point_records})
    }
    return {"models": output, "point_mse": point}


def effort(output):
    output = Path(output)
    manifest = read_json(output / "manifest.json")
    base = read_json(output / "baselines.json")
    groups = {}
    for seed in manifest["config"]["seeds"]:
        row = read_json(output / f"training-seed{seed}.json")
        for family, v in row["families"].items():
            for stage in ("D", "A"):
                groups.setdefault(f"{family}-{stage}", []).extend(v[f"{stage}_fits"])
        groups.setdefault("paper-point", []).extend(row["paper"]["fits"])
    table = []
    for name, fits in groups.items():
        table.append(
            {
                "id": name,
                "fits": len(fits),
                "successes": sum(f["success"] for f in fits),
                "eligible": sum(f["eligible"] for f in fits),
                "objective_calls": sum(f["total_objective_calls"] for f in fits),
                "diagnostic_calls": sum(f["diagnostic_calls"] for f in fits),
                "seconds": sum(f["seconds"] for f in fits),
            }
        )
    for row in base["models"]:
        fit = row["fit"]
        table.append(
            {
                "id": row["id"],
                "fits": len(fit.get("fits", [fit])),
                "eligible": int(fit["eligible"]),
                "objective_calls": fit.get("objective_calls", 0),
                "seconds": fit["seconds"],
                "lp_solves": len(fit.get("quantile_fits", [])),
                "lp_iterations": sum(f["iterations"] for f in fit.get("quantile_fits", [])),
            }
        )
    return table


def evaluate_final(data, output, evaluation_name="evaluation", progress=print):
    output = Path(output)
    _manifest, config = check_seal(output, data)
    if Path(evaluation_name).name != evaluation_name:
        raise ValueError("Evaluation name must be one folder")
    destination = output / evaluation_name
    destination.mkdir(exist_ok=False)
    write_json(
        destination / "status.json",
        {
            "status": "evaluating",
            "training_seal_sha256": sha256(output / "training-seal.json"),
        },
    )
    baselines = read_json(output / "baselines.json")
    models = {r["id"]: restore_baseline(r) for r in baselines["models"]}
    base_eligible = {r["id"]: r["fit"]["eligible"] for r in baselines["models"]}
    scales = moment_scales(data.y[data.train])
    reference = data.y[data.test]
    reference_moments = moments(reference)
    labels = data.labels[data.test]
    x = data.x[data.test]
    garch = models["garch-calibrated"]
    # Explicitly evaluation-only filtering through test; h[t] uses r[t-1], never r[t].
    variance = garch_variance(
        data.daily.returns[data.target_rows] / garch.return_scale, garch.parameters, garch.backcast
    )
    records = []
    path_records = []
    point_records = []
    losses = {}
    started = time.perf_counter()
    native_models = {"har-quantile", "short-quantile", "garch-calibrated"}
    for seed in config.seeds:
        train = read_json(output / f"training-seed{seed}.json")
        candidates = {
            id_: (model, None, base_eligible[id_], base_eligible[id_])
            for id_, model in models.items()
        }
        for family, row in train["families"].items():
            model = distribution_model(family, config.quantum_layers if family == "quantum" else 0)
            for stage in ("D", "A"):
                candidates[f"{family}-{stage}"] = (
                    model,
                    np.array(row[f"{stage}_parameters"]),
                    row["D_eligible"],
                    row[f"{stage}_eligible"],
                )
        for index, (id_, (model, p, d_ok, stage_ok)) in enumerate(candidates.items()):
            native = None
            if id_ == "garch-calibrated":
                probabilities = model.probabilities_from_variance(variance[data.test])
                native = model.predict_quantiles(variance[data.test])
            else:
                probabilities = model.probabilities(x, p)
                if id_ in native_models:
                    native = model.predict_quantiles(x)
            common = empirical_bin_quantiles(probabilities, data.bins.pools)
            daily_loss = -np.log(np.clip(probabilities[np.arange(len(labels)), labels], 1e-12, 1))
            losses.setdefault(id_, []).append(daily_loss)
            record = {
                "id": id_,
                "seed": seed,
                "D_eligible": d_ok,
                "stage_eligible": stage_ok,
                "scores": forecast_scores(probabilities, labels),
                "common_quantile_scores": quantile_scores(common, reference),
            }
            if native is not None:
                record["native_quantile_scores"] = quantile_scores(native, reference)
            records.append(record)
            np.savez_compressed(
                destination / f"{id_}-seed{seed}.npz",
                parameters=np.array([]) if p is None else p,
                probabilities=probabilities,
                common_quantiles=common,
                native_quantiles=np.array([]) if native is None else native,
                daily_log_loss=daily_loss,
            )
            if id_ == "garch-calibrated":
                simconfig = ComparisonConfig(
                    audit_days=config.evaluation_days,
                    audit_paths=config.evaluation_paths,
                    burn_in=config.evaluation_burn_in,
                )
                paths = garch_paths(model, data, simconfig, 500000 + seed)
            else:
                paths = generate(
                    model,
                    p,
                    data,
                    config.evaluation_days,
                    config.evaluation_paths,
                    500000 + seed,
                    config.evaluation_burn_in,
                )
            summary = summarize_paths(paths, reference_moments, scales, 500000 + seed)
            summary["wasserstein_log_rv"] = numbers(
                [wasserstein_distance(y, reference) for y in paths.log_rv]
            )
            summary["hill_return_tail_index"] = numbers([hill_tail_index(r) for r in paths.returns])
            path_records.append(
                {
                    "id": id_,
                    "seed": seed,
                    "law": "common-bin",
                    "summary": summary,
                    "fixed_path_zero_diagnostics": path_diagnostics(
                        paths.log_rv[0],
                        paths.returns[0],
                        reference,
                        scales,
                        700000 + 1000 * seed + index,
                    ),
                }
            )
            np.savez_compressed(
                destination / f"paths-{id_}-seed{seed}.npz",
                log_rv=paths.log_rv,
                returns=paths.returns,
                levels=paths.levels,
            )
        native_paths = garch_paths(garch, data, simconfig, 500000 + seed, native=True)
        native_summary = summarize_paths(native_paths, reference_moments, scales, 500000 + seed)
        native_summary["wasserstein_log_rv"] = numbers(
            [wasserstein_distance(y, reference) for y in native_paths.log_rv]
        )
        native_summary["hill_return_tail_index"] = numbers(
            [hill_tail_index(r) for r in native_paths.returns]
        )
        path_records.append(
            {
                "id": "garch-native-reference",
                "seed": seed,
                "law": "native-garch",
                "summary": native_summary,
                "fixed_path_zero_diagnostics": path_diagnostics(
                    native_paths.log_rv[0],
                    native_paths.returns[0],
                    reference,
                    scales,
                    700000 + 1000 * seed + len(candidates),
                ),
            }
        )
        np.savez_compressed(
            destination / f"paths-garch-native-reference-seed{seed}.npz",
            log_rv=native_paths.log_rv,
            returns=native_paths.returns,
            levels=native_paths.levels,
        )
        target = data.daily.rv[data.target_rows[data.test]]
        har = baselines["point_har"]
        raw = har_features(data.daily.rv, data.target_rows[data.test])
        standardized = (raw - np.array(har["feature_mean"])) / np.array(har["feature_scale"])
        point_predictions = {
            "paper": point_prediction(
                "paper",
                np.array(train["paper"]["parameters"]),
                data,
                data.target_rows[data.test],
                PointScaling(**train["paper"]["scaling"]),
            ),
            "persistence": data.daily.rv[data.target_rows[data.test] - 1],
            "training-mean": np.full(len(target), baselines["point_mean"]),
            "raw-har": np.maximum(
                np.c_[np.ones(len(raw)), standardized] @ np.array(har["coefficients"]), 0
            )
            * har["rv_scale"],
        }
        for id_, prediction in point_predictions.items():
            point_records.append(
                {
                    "id": id_,
                    "seed": seed,
                    "mse_rv": float(np.mean((prediction - target) ** 2)),
                    "training_eligible": train["paper"]["eligible"] if id_ == "paper" else True,
                }
            )
        np.savez_compressed(destination / f"point-seed{seed}.npz", **point_predictions)
        write_json(destination / "records.json", records)
        write_json(destination / "paths.json", path_records)
        write_json(destination / "point.json", point_records)
        progress(
            f"Evaluated seed {seed}: {len(candidates)} forecasts + native GARCH paths", flush=True
        )
    summary = summarize_records(records, path_records, point_records)
    summary["bootstrap_nll"] = paired_bootstrap(
        losses, config.bootstrap_blocks, config.bootstrap_replicates
    )
    summary["effort"] = effort(output)
    summary["reference"] = {
        "test_target_rows": data.target_rows[data.test].tolist(),
        "test_bin_counts": np.bincount(labels, minlength=4).tolist(),
        "test_moments": reference_moments.tolist(),
        "test_return_hill": hill_tail_index(data.daily.returns[data.target_rows[data.test]]),
        "native_return_risk_available": False,
        "historical_test_smoke_was_inspected": True,
    }
    write_json(destination / "summary.json", summary)
    write_json(
        destination / "status.json",
        {
            "status": "complete",
            "kind": config.kind,
            "seeds": len(config.seeds),
            "forecast_records": len(records),
            "path_records": len(path_records),
            "output_days": len(path_records) * config.evaluation_days * config.evaluation_paths,
            "evaluation_seconds": time.perf_counter() - started,
            "training_seal_sha256": sha256(output / "training-seal.json"),
        },
    )
    return summary
