"""Run the pre-registered weekend-aware quantum upgrade stages on ETH data."""

import argparse
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
from scipy.optimize import minimize_scalar

from qcvol.classical import SoftmaxModel, TinyNetwork
from qcvol.data import load_daily_csv, sha256
from qcvol.final_evaluation import block_indices
from qcvol.fresh_models import FastBorn, Hybrid
from qcvol.fresh_runner import FreshConfig
from qcvol.fresh_study import fit_lbfgs, prepare_dates, split_dates
from qcvol.metrics import forecast_scores, log_loss
from qcvol_next.weekend_models import (
    WeekendBorn,
    WeekendHAR,
    WeekendNetwork,
    WeekendQuantumReadout,
    WeekendSoftmax,
)

DEPTHS = (1, 2, 3)
WEEKEND_QUANTUM = (
    "quantum-weekend",
    "quantum-weekend-ry",
    "quantum-weekend-alternating",
)
HYBRID_QUANTUM = (
    "hybrid-quantum-weekend",
    "hybrid-quantum-weekend-ry",
    "hybrid-quantum-readout-ry",
)
QUANTUM = ("quantum-har", *WEEKEND_QUANTUM, *HYBRID_QUANTUM)
VARIANT_MODELS = (*WEEKEND_QUANTUM[1:], "hybrid-quantum-weekend-ry")
MODELS = (
    "quantum-har",
    *WEEKEND_QUANTUM,
    "softmax-har",
    "softmax-weekend",
    "network-har",
    "network-weekend",
    "har-weekend",
    "hybrid-quantum-weekend",
    "hybrid-quantum-weekend-ry",
    "hybrid-quantum-readout-ry",
    "hybrid-softmax-weekend",
)


def weekend_data(daily, train_end="2022-12-31", validation_end="2024-12-31"):
    data = prepare_dates(daily, train_end, validation_end)
    target_dates = np.asarray(daily.index, dtype="datetime64[D]")[data.target_rows]
    weekday = (target_dates.astype(np.int64) + 3) % 7
    raw = np.isin(weekday, (5, 6)).astype(float)
    mean, scale = raw[data.train].mean(), raw[data.train].std()
    x = np.column_stack([data.x, (raw - mean) / (scale if scale > 1e-12 else 1)])
    return replace(data, x=x), {"mean": float(mean), "scale": float(scale)}


def model_for(name, depth, har):
    if name == "quantum-har":
        return FastBorn(depth)
    if name == "quantum-weekend":
        return WeekendBorn(depth)
    if name == "quantum-weekend-ry":
        return WeekendBorn(depth, weekend_axis="y")
    if name == "quantum-weekend-alternating":
        return WeekendBorn(depth, alternate_entangler=True)
    if name == "softmax-har":
        return SoftmaxModel()
    if name == "softmax-weekend":
        return WeekendSoftmax()
    if name == "network-har":
        return TinyNetwork()
    if name == "network-weekend":
        return WeekendNetwork()
    if name == "hybrid-quantum-weekend":
        return Hybrid(har, WeekendBorn(depth))
    if name == "hybrid-quantum-weekend-ry":
        return Hybrid(har, WeekendBorn(depth, weekend_axis="y"))
    if name == "hybrid-quantum-readout-ry":
        return WeekendQuantumReadout(har, depth)
    if name == "hybrid-softmax-weekend":
        return Hybrid(har, WeekendSoftmax())
    raise ValueError(f"Unknown model: {name}")


def model_depths(name):
    return DEPTHS if name in QUANTUM else (0,)


def calibrated_probabilities(probabilities, temperature):
    logits = np.log(np.clip(probabilities, 1e-12, 1)) / temperature
    logits -= logits.max(axis=1, keepdims=True)
    values = np.exp(logits)
    return values / values.sum(axis=1, keepdims=True)


def fit_temperature(probabilities, labels):
    result = minimize_scalar(
        lambda temperature: log_loss(calibrated_probabilities(probabilities, temperature), labels),
        bounds=(0.2, 5.0),
        method="bounded",
        options={"xatol": 1e-4},
    )
    return float(result.x)


def final_models(selection):
    if "final_model_panel" in selection:
        return tuple(selection["final_model_panel"])
    return tuple(
        dict.fromkeys(
            (
                selection["best_quantum_model"],
                "quantum-har",
                "quantum-weekend-ry",
                "softmax-weekend",
                "network-weekend",
                "hybrid-softmax-weekend",
            )
        )
    )


def fit_one(name, depth, data, config, seed, har, base_train):
    model = model_for(name, depth, har)
    uses_weekend = name in {
        *WEEKEND_QUANTUM,
        "softmax-weekend",
        "network-weekend",
        "hybrid-quantum-weekend",
        "hybrid-quantum-weekend-ry",
        "hybrid-quantum-readout-ry",
        "hybrid-softmax-weekend",
    }
    width = 5 if uses_weekend else 4
    x, labels = data.x[data.train, :width], data.labels[data.train]
    ridge = (
        config.network_ridge
        if name.startswith("network") or name == "hybrid-quantum-readout-ry"
        else 0.0
    )
    hybrid = name.startswith("hybrid-")

    def objective(parameters):
        p = (
            model.pooled(base_train, x, parameters)
            if hybrid
            else model.probabilities(x, parameters)
        )
        return log_loss(p, labels) + ridge * float(np.dot(parameters, parameters))

    fits = []
    for restart in range(config.restarts):
        init_seed = 300000 + 100 * seed + 10 * depth + restart
        initial = None
        if hybrid:
            rng = np.random.default_rng(init_seed)
            initial = np.r_[0.0, rng.normal(0, 0.3, model.n_params - 1)]
        fit = fit_lbfgs(
            objective,
            model.n_params,
            init_seed,
            config.forecast_max_calls,
            config.forecast_max_iterations,
            initial,
        )
        fit.update({"restart": restart, "initialization_seed": init_seed})
        fits.append(fit)
    best = min(fits, key=lambda row: (row["objective"], row["restart"]))
    base_validation = har.probabilities(data.x[data.validation])
    validation_x = data.x[data.validation, :width]
    validation_p = (
        model.pooled(base_validation, validation_x, np.asarray(best["parameters"]))
        if hybrid
        else model.probabilities(validation_x, np.asarray(best["parameters"]))
    )
    return {
        "name": name,
        "depth": depth,
        "seed": seed,
        "fit": best,
        "fits": fits,
        "validation": forecast_scores(validation_p, data.labels[data.validation]),
        "validation_probabilities": validation_p.tolist(),
    }


def develop(data, config, seed, output):
    har = WeekendHAR.fit(data.x[data.train], data.y[data.train], data.bins.edges)
    base_train = har.probabilities(data.x[data.train])
    rows = []
    for name in MODELS:
        if name == "har-weekend":
            continue
        for depth in model_depths(name):
            row = fit_one(name, depth, data, config, seed, har, base_train)
            rows.append(row)
            print(
                f"dev seed={seed} model={name} depth={depth} "
                f"train={row['fit']['objective']:.5f} "
                f"validation={row['validation']['log_loss']:.5f} "
                f"eligible={row['fit']['eligible']}",
                flush=True,
            )
    write_json(output / f"upgrade-develop-seed{seed}.json", {"seed": seed, "rows": rows})


def develop_variants(data, config, seed, output):
    har = WeekendHAR.fit(data.x[data.train], data.y[data.train], data.bins.edges)
    base_train = har.probabilities(data.x[data.train])
    destination = output / f"upgrade-variants-seed{seed}.json"
    rows = json.loads(destination.read_text())["rows"] if destination.is_file() else []
    completed = {row["name"] for row in rows}
    for name in VARIANT_MODELS:
        if name in completed:
            continue
        for depth in DEPTHS:
            row = fit_one(name, depth, data, config, seed, har, base_train)
            rows.append(row)
            print(
                f"dev variant seed={seed} model={name} depth={depth} "
                f"train={row['fit']['objective']:.5f} "
                f"validation={row['validation']['log_loss']:.5f} "
                f"eligible={row['fit']['eligible']}",
                flush=True,
            )
    write_json(destination, {"seed": seed, "rows": rows})


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def select(data, config, output):
    rows = []
    for seed in config.development_seeds:
        rows.extend(json.loads((output / f"upgrade-develop-seed{seed}.json").read_text())["rows"])
        rows.extend(json.loads((output / f"upgrade-variants-seed{seed}.json").read_text())["rows"])
    selection = {}
    for name in MODELS:
        if name == "har-weekend":
            probabilities = WeekendHAR.fit(
                data.x[data.train], data.y[data.train], data.bins.edges
            ).probabilities(data.x[data.validation])
            temperature = fit_temperature(probabilities, data.labels[data.validation])
            selection[name] = {
                "depth": 0,
                "source": "train-only OLS residual law",
                "mean_validation_calibrated_log_loss": log_loss(
                    calibrated_probabilities(probabilities, temperature),
                    data.labels[data.validation],
                ),
                "temperature_by_seed": {
                    str(seed): temperature for seed in config.development_seeds
                },
            }
            continue
        depths = model_depths(name)
        means, temperatures = {}, {}
        for depth in depths:
            candidate_rows = [r for r in rows if r["name"] == name and r["depth"] == depth]
            temperatures[str(depth)] = {}
            calibrated_losses = []
            for row in candidate_rows:
                if "validation_probabilities" in row:
                    p = np.asarray(row["validation_probabilities"])
                else:
                    har = WeekendHAR.fit(data.x[data.train], data.y[data.train], data.bins.edges)
                    model = model_for(name, depth, har)
                    width = (
                        5
                        if name
                        in {
                            *WEEKEND_QUANTUM,
                            "softmax-weekend",
                            "network-weekend",
                            "hybrid-quantum-weekend",
                            "hybrid-quantum-weekend-ry",
                            "hybrid-quantum-readout-ry",
                            "hybrid-softmax-weekend",
                        }
                        else 4
                    )
                    p = model.probabilities(
                        data.x[data.validation, :width],
                        np.asarray(row["fit"]["parameters"]),
                    )
                temp = fit_temperature(p, data.labels[data.validation])
                temperatures[str(depth)][str(row["seed"])] = temp
                calibrated_losses.append(
                    log_loss(calibrated_probabilities(p, temp), data.labels[data.validation])
                )
            means[depth] = float(np.mean(calibrated_losses))
        best_depth = min(depths, key=lambda depth: (means[depth], depth))
        selection[name] = {
            "depth": best_depth,
            "mean_validation_calibrated_log_loss_by_depth": means,
            "temperature_by_depth_and_seed": temperatures,
            "temperature_by_seed": temperatures[str(best_depth)],
            "mean_validation_calibrated_log_loss": means[best_depth],
        }
    selection["best_quantum_model"] = min(
        (*WEEKEND_QUANTUM, *HYBRID_QUANTUM),
        key=lambda name: (
            selection[name]["mean_validation_calibrated_log_loss_by_depth"][
                selection[name]["depth"]
            ],
            selection[name]["depth"],
        ),
    )
    write_json(output / "upgrade-selection.json", selection)
    return selection


def train_seed(data, config, seed, output):
    selection = json.loads((output / "upgrade-selection.json").read_text())
    har = WeekendHAR.fit(data.x[data.train], data.y[data.train], data.bins.edges)
    base_train = har.probabilities(data.x[data.train])
    models = {}
    models_to_train = final_models(selection)
    for name in models_to_train:
        if name == "har-weekend":
            continue
        depth = selection[name]["depth"]
        row = fit_one(name, depth, data, config, seed, har, base_train)
        temperature = fit_temperature(
            np.asarray(row["validation_probabilities"]), data.labels[data.validation]
        )
        models[name] = {
            "depth": depth,
            "fit": row["fit"],
            "fits": row["fits"],
            "validation_temperature": temperature,
            "raw_validation_log_loss": row["validation"]["log_loss"],
            "calibrated_validation_log_loss": log_loss(
                calibrated_probabilities(np.asarray(row["validation_probabilities"]), temperature),
                data.labels[data.validation],
            ),
        }
        print(f"train seed={seed} model={name} eligible={row['fit']['eligible']}", flush=True)
    write_json(output / f"upgrade-train-seed{seed}.json", {"seed": seed, "models": models})


def files_to_seal(config, output):
    names = ["upgrade-manifest.json", "upgrade-selection.json"]
    manifest = json.loads((output / "upgrade-manifest.json").read_text())
    if not manifest.get("fixed_replication", False):
        names += [f"upgrade-develop-seed{s}.json" for s in config.development_seeds]
        names += [f"upgrade-variants-seed{s}.json" for s in config.development_seeds]
    names += [f"upgrade-train-seed{s}.json" for s in config.final_seeds]
    return names


def code_hashes():
    source_files = [
        *Path("src/qcvol").rglob("*.py"),
        *Path("src/qcvol_next").rglob("*.py"),
        Path("scripts/run_eth_quantum_upgrade.py"),
        Path("scripts/build_binance_daily.py"),
    ]
    environment_files = [Path("pyproject.toml"), Path("uv.lock")]
    return {str(path): sha256(path) for path in sorted(source_files + environment_files)}


def seal(data_path, config_path, output, config):
    names = files_to_seal(config, output)
    missing = [name for name in names if not (output / name).is_file()]
    if missing:
        raise ValueError(f"Cannot seal; missing {missing}")
    record = {
        "artifacts": {name: sha256(output / name) for name in names},
        "data": {
            str(data_path): sha256(data_path),
            str(data_path.with_suffix(".json")): sha256(data_path.with_suffix(".json")),
        },
        "config": {str(config_path): sha256(config_path)},
        "code": code_hashes(),
        "test_scores_computed": False,
    }
    write_json(output / "upgrade-seal.json", record)
    print("Sealed forecast models; test scores not computed")


def check_seal(data_path, config_path, output, config):
    record = json.loads((output / "upgrade-seal.json").read_text())
    if code_hashes() != record["code"]:
        raise ValueError("Upgrade code changed after sealing")
    for name, digest in record["artifacts"].items():
        if sha256(output / name) != digest:
            raise ValueError(f"Upgrade artifact changed after sealing: {name}")
    for name, digest in record["data"].items():
        if sha256(name) != digest:
            raise ValueError(f"ETH data changed after sealing: {name}")
    if record["config"] != {str(config_path): sha256(config_path)}:
        raise ValueError("Upgrade config changed after sealing")
    if files_to_seal(config, output) != list(record["artifacts"]):
        raise ValueError("Sealed artifact list differs from configured stages")


def daily_losses(probabilities, labels, rv, level_means):
    observed = labels[:, None] <= np.arange(3)
    return {
        "log_loss": -np.log(np.clip(probabilities[np.arange(len(labels)), labels], 1e-12, 1)),
        "rps_normalized": np.mean((probabilities.cumsum(axis=1)[:, :3] - observed) ** 2, axis=1),
        "extreme_brier": (probabilities[:, 3] - (labels == 3)) ** 2,
        "qlike": rv / np.maximum(probabilities @ level_means, 1e-12)
        - np.log(rv / np.maximum(probabilities @ level_means, 1e-12))
        - 1,
    }


def evaluate(data, data_path, config_path, output, config):
    check_seal(data_path, config_path, output, config)
    (output / "upgrade-evaluation.started").touch(exist_ok=False)
    selection = json.loads((output / "upgrade-selection.json").read_text())
    har = WeekendHAR.fit(data.x[data.train], data.y[data.train], data.bins.edges)
    x, labels = data.x[data.test], data.labels[data.test]
    test_rows = data.target_rows[data.test]
    rv = data.daily.rv[test_rows]
    level_means = np.asarray([np.exp(pool).mean() for pool in data.bins.pools])
    model_names = final_models(selection)
    all_losses = {
        name: {
            mode: {
                metric: [] for metric in ("log_loss", "rps_normalized", "extreme_brier", "qlike")
            }
            for mode in ("raw", "calibrated")
        }
        for name in model_names
    }

    for seed in config.final_seeds:
        record = json.loads((output / f"upgrade-train-seed{seed}.json").read_text())["models"]
        for name in model_names:
            entry = record[name]
            model = model_for(name, entry["depth"], har)
            width = 5 if name != "quantum-har" else 4
            probabilities = model.probabilities(
                x[:, :width], np.asarray(entry["fit"]["parameters"])
            )
            for mode, values in (
                ("raw", probabilities),
                (
                    "calibrated",
                    calibrated_probabilities(probabilities, entry["validation_temperature"]),
                ),
            ):
                for metric, daily in daily_losses(values, labels, rv, level_means).items():
                    all_losses[name][mode][metric].append(daily)

    summary = {}
    for name, modes in all_losses.items():
        summary[name] = {}
        for mode, metrics in modes.items():
            summary[name][mode] = {
                metric: {
                    "mean": float(np.mean([np.mean(v) for v in values])),
                    "seed_sd": float(np.std([np.mean(v) for v in values], ddof=1))
                    if len(values) > 1
                    else 0,
                }
                for metric, values in metrics.items()
            }
    rng = np.random.default_rng(604221)
    intervals = []
    selected_quantum = selection["best_quantum_model"]
    for baseline in (
        "softmax-weekend",
        "network-weekend",
        "hybrid-softmax-weekend",
    ):
        for block in config.bootstrap_blocks:
            delta = np.mean(
                all_losses[selected_quantum]["calibrated"]["log_loss"], axis=0
            ) - np.mean(all_losses[baseline]["calibrated"]["log_loss"], axis=0)
            indices = block_indices(len(delta), block, config.bootstrap_replicates, rng)
            boot = delta[indices].mean(axis=1)
            intervals.append(
                {
                    "left": selected_quantum,
                    "right": baseline,
                    "block": block,
                    "mean_difference": float(delta.mean()),
                    "lower": float(np.quantile(boot, (1 - config.bootstrap_confidence) / 2)),
                    "upper": float(np.quantile(boot, 1 - (1 - config.bootstrap_confidence) / 2)),
                }
            )
    result = {
        "split_dates": split_dates(data),
        "selected_quantum_model": selected_quantum,
        "quantum_selected_depth": selection[selected_quantum]["depth"],
        "summary": summary,
        "intervals": intervals,
        "marked_improvement": bool(
            summary[selected_quantum]["calibrated"]["log_loss"]["mean"]
            <= 0.95
            * min(
                summary["softmax-weekend"]["calibrated"]["log_loss"]["mean"],
                summary["network-weekend"]["calibrated"]["log_loss"]["mean"],
                summary["hybrid-softmax-weekend"]["calibrated"]["log_loss"]["mean"],
            )
            and all(row["upper"] < 0 for row in intervals)
        ),
        "quantum_seed_daily_losses": {
            mode: {
                metric: [np.asarray(rows).tolist() for rows in values]
                for metric, values in metrics.items()
            }
            for mode, metrics in all_losses[selected_quantum].items()
        },
    }
    write_json(output / "upgrade-evaluation.json", result)
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "stage",
        choices=(
            "manifest",
            "develop",
            "develop-variants",
            "select",
            "train",
            "seal",
            "evaluate",
        ),
    )
    parser.add_argument("--data", type=Path, default=Path("data/ethusdt_daily.csv"))
    parser.add_argument("--config", type=Path, default=Path("configs/fresh-study.json"))
    parser.add_argument("--output", type=Path, default=Path("results/eth-study/upgrade"))
    parser.add_argument("--seed", type=int, action="append", default=[])
    parser.add_argument("--fixed-replication", action="store_true")
    args = parser.parse_args()
    config = FreshConfig(**json.loads(args.config.read_text()))
    daily = load_daily_csv(args.data)
    data, weekend_scaling = weekend_data(daily)
    if args.stage == "manifest":
        write_json(
            args.output / "upgrade-manifest.json",
            {
                "data_sha256": sha256(args.data),
                "source_metadata_sha256": sha256(args.data.with_suffix(".json")),
                "config_sha256": sha256(args.config),
                "config": config.__dict__,
                "splits": split_dates(data),
                "weekend_standardization": weekend_scaling,
                "models": (
                    final_models(json.loads((args.output / "upgrade-selection.json").read_text()))
                    if args.fixed_replication
                    else MODELS
                ),
                "fixed_replication": args.fixed_replication,
                "depths": DEPTHS,
                "test_scores_computed": False,
            },
        )
    elif args.stage == "develop":
        for seed in args.seed:
            if seed not in config.development_seeds:
                raise ValueError(f"Development seed {seed} is not in config")
            develop(data, config, seed, args.output)
    elif args.stage == "develop-variants":
        for seed in args.seed:
            if seed not in config.development_seeds:
                raise ValueError(f"Development seed {seed} is not in config")
            develop_variants(data, config, seed, args.output)
    elif args.stage == "select":
        select(data, config, args.output)
    elif args.stage == "train":
        for seed in args.seed:
            if seed not in config.final_seeds:
                raise ValueError(f"Final seed {seed} is not in config")
            train_seed(data, config, seed, args.output)
    elif args.stage == "seal":
        seal(args.data, args.config, args.output, config)
    else:
        evaluate(data, args.data, args.config, args.output, config)


if __name__ == "__main__":
    main()
