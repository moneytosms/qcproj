#!/usr/bin/env python3
"""Audit the frozen final study, dense-gate forecasts, all draws and paired uncertainty."""

import argparse
import importlib.util
from pathlib import Path

import numpy as np

from qcvol.data import load_author_data, prepare, sha256
from qcvol.final_study import check_seal, read_json
from qcvol.finance_baselines import QUANTILES
from qcvol.training import PointScaling


def sibling(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


finance = sibling("verify_classical_comparison")
replay = finance.replay
point = sibling("verify_nested_memory")


def stats(values):
    values = np.array(values, dtype=float)
    finite = values[np.isfinite(values)]
    return {
        "count": len(values),
        "valid": len(finite),
        "mean": float(np.mean(finite)) if len(finite) else None,
        "sd": float(np.std(finite, ddof=1)) if len(finite) > 1 else None,
        "min": float(np.min(finite)) if len(finite) else None,
        "max": float(np.max(finite)) if len(finite) else None,
    }


def compare_stats(actual, expected):
    assert actual.keys() == expected.keys()
    for key, value in expected.items():
        if value is None:
            assert actual[key] is None
        else:
            np.testing.assert_allclose(actual[key], value, atol=1e-9, rtol=1e-8)


def hill(r):
    values = np.sort(np.abs(r))
    k = max(20, int(np.sqrt(len(r))))
    if len(values) < 200 or len(values) <= k or values[-k - 1] <= 0:
        return np.nan
    denominator = np.mean(np.log(values[-k:] / values[-k - 1]))
    return 1 / denominator if denominator > 0 else np.nan


def wasserstein(a, b):
    a, b = np.sort(a), np.sort(b)
    all_values = np.sort(np.r_[a, b])
    widths = np.diff(all_values)
    difference = np.searchsorted(a, all_values[:-1], side="right") / len(a) - np.searchsorted(
        b, all_values[:-1], side="right"
    ) / len(b)
    return float(np.sum(widths * np.abs(difference)))


def independent_mfdfa(values):
    values = np.asarray(values, float)
    if len(values) < 160 or not np.all(np.isfinite(values)) or np.std(values) < 1e-12:
        return None
    scales = np.unique(np.geomspace(20, len(values) // 4, 12).astype(int))
    if len(scales) < 6:
        return None
    profile = np.cumsum(values - values.mean())
    q = np.arange(-5.0, 6.0)
    logs = []
    for scale in scales:
        t = np.linspace(-1, 1, scale)
        design = np.column_stack([t**j for j in range(4)])
        variances = []
        for origin in (0, len(values) % scale):
            for start in range(origin, len(values) - scale + 1, scale):
                segment = profile[start : start + scale]
                beta = np.linalg.lstsq(design, segment, rcond=None)[0]
                variances.append(np.mean((segment - design @ beta) ** 2))
        if min(variances) <= 1e-30:
            return None
        lv = np.log(variances)
        row = []
        for power in q:
            if power == 0:
                row.append(0.5 * lv.mean())
            else:
                terms = power * 0.5 * lv
                maximum = terms.max()
                row.append((maximum + np.log(np.exp(terms - maximum).mean())) / power)
        logs.append(row)
    h = np.polyfit(np.log(scales), np.array(logs), 1)[0]
    tau = q * h - 1
    alpha = np.gradient(tau, q)
    return {
        "h": h,
        "tau": tau,
        "alpha": alpha,
        "f_alpha": q * alpha - tau,
        "h2": h[7],
        "spectrum_width": np.ptp(alpha),
        "scales": scales,
        "q": q,
    }


def check_diagnostics(record, y, r, reference, scales, seed):
    diagnostic = record["fixed_path_zero_diagnostics"]
    np.testing.assert_allclose(
        list(diagnostic["moments"].values()), replay.independent_moments(y), atol=1e-10
    )
    np.testing.assert_allclose(
        diagnostic["wasserstein_log_rv"], wasserstein(y, reference), atol=1e-10
    )
    expected = hill(r)
    if np.isnan(expected):
        assert diagnostic["hill_return_tail_index"] is None
    else:
        np.testing.assert_allclose(diagnostic["hill_return_tail_index"], expected, atol=1e-10)
    vector = replay.independent_moments(y)
    distance = np.sum(((vector - replay.independent_moments(reference)) / scales) ** 2)
    np.testing.assert_allclose(diagnostic["moment_distance"], distance, atol=1e-8)
    rng = np.random.default_rng(seed)
    changes = np.diff(y)
    for key, values in [
        ("mfdfa_log_rv_increments", changes),
        ("mfdfa_shuffled_increments", rng.permutation(changes)),
        ("mfdfa_returns", r),
        ("mfdfa_shuffled_returns", rng.permutation(r)),
    ]:
        expected = independent_mfdfa(values)
        actual = diagnostic[key]
        if expected is None:
            assert actual["available"] is False
        else:
            assert actual["available"] is True
            for name, value in expected.items():
                np.testing.assert_allclose(actual[name], value, atol=1e-8, rtol=1e-7)


def verify(root, author_data, evaluation="evaluation", allow_integration=False):
    root = Path(root)
    data = prepare(load_author_data(author_data))
    manifest, config = check_seal(root, data)
    if not allow_integration:
        assert config.kind == "final" and len(config.seeds) >= 20
    destination = root / evaluation
    status = read_json(destination / "status.json")
    assert status["status"] == "complete" and status["training_seal_sha256"] == sha256(
        root / "training-seal.json"
    )
    if manifest["source"]:
        assert manifest["source"]["sha256"] == {
            name: sha256(Path(author_data) / name) for name in ("data-rstand", "data-ystand")
        }
    baselines = read_json(root / "baselines.json")
    base = {r["id"]: r for r in baselines["models"]}
    summary = read_json(destination / "summary.json")
    records = read_json(destination / "records.json")
    paths = read_json(destination / "paths.json")
    point_records = read_json(destination / "point.json")
    model_ids = set(base) | {
        f"{family}-{stage}" for family in ("quantum", "softmax", "network") for stage in ("D", "A")
    }
    assert {(r["id"], r["seed"]) for r in records} == {
        (id_, s) for id_ in model_ids for s in config.seeds
    }
    assert len(records) == len(model_ids) * len(config.seeds) == status["forecast_records"]
    assert {(r["id"], r["seed"]) for r in paths} == {
        (id_, s) for id_ in [*model_ids, "garch-native-reference"] for s in config.seeds
    }
    assert (
        len(paths)
        == len(model_ids | {"garch-native-reference"}) * len(config.seeds)
        == status["path_records"]
    )
    assert status["output_days"] == len(paths) * config.evaluation_days * config.evaluation_paths
    assert len(point_records) == 4 * len(config.seeds)
    assert {(r["id"], r["seed"]) for r in point_records} == {
        (id_, s)
        for id_ in ("paper", "persistence", "training-mean", "raw-har")
        for s in config.seeds
    }
    assert {r["id"] for r in summary["models"]} == model_ids
    by_path = {(r["id"], r["seed"]): r for r in paths}
    by_record = {(r["id"], r["seed"]): r for r in records}
    train_y = data.y[data.train]
    reference = data.y[data.test]
    scales = np.array(manifest["moment_scales"])
    width = min(128, max(40, len(train_y) // 3))
    starts = np.unique(np.linspace(0, len(train_y) - width, 12).astype(int))
    np.testing.assert_allclose(
        scales,
        np.maximum(
            np.std([replay.independent_moments(train_y[s : s + width]) for s in starts], axis=0),
            0.02,
        ),
    )
    reference_vector = replay.independent_moments(reference)
    train_vector = replay.independent_moments(train_y)
    labels = data.labels[data.test]
    losses = {id_: [] for id_ in model_ids}
    max_error = 0.0
    probability_rows = recursive_days = 0
    # Deterministic finance models: independently certify training and reconstruct forecasts.
    controls = {}
    for id_ in ("frequency", "short-ar", "har-residual"):
        if id_ == "frequency":
            frequency = np.bincount(data.labels[data.train], minlength=4) / data.train.stop
            np.testing.assert_array_equal(base[id_]["state"]["frequencies"], frequency)
            controls[id_] = lambda x, p=None, frequency=frequency: np.tile(frequency, (len(x), 1))
        else:
            indices = [0, 3] if id_ == "short-ar" else [0, 1, 2]
            design = np.c_[data.x[data.train][:, indices], np.ones(data.train.stop)]
            beta = np.linalg.lstsq(design, train_y, rcond=None)[0]
            residuals = np.sort(train_y - design @ beta)
            np.testing.assert_allclose(base[id_]["state"]["coefficients"], beta, atol=1e-11)
            np.testing.assert_allclose(base[id_]["state"]["residuals"], residuals, atol=1e-11)

            def probability(x, p=None, indices=indices, beta=beta, residuals=residuals):
                location = np.c_[x[:, indices], np.ones(len(x))] @ beta
                cdf = (
                    np.searchsorted(
                        residuals, data.bins.edges[None, :] - location[:, None], side="right"
                    )
                    + 0.5
                ) / (len(residuals) + 1)
                return np.diff(np.c_[np.zeros(len(x)), cdf, np.ones(len(x))], axis=1)

            controls[id_] = probability
    for id_ in ("har-quantile", "short-quantile"):
        state = base[id_]["state"]
        row = {"id": id_, **state}
        controls[id_], _ = finance.finance_probability(row, data)
        indices = [0, 3] if state["short"] else [0, 1, 2]
        design = np.c_[data.x[data.train][:, indices], np.ones(data.train.stop)]
        coefficients = np.array(state["coefficients"])
        assert base[id_]["fit"]["eligible"]
        for j, fit in enumerate(base[id_]["fit"]["quantile_fits"]):
            tau = fit["quantile"]
            dual = np.array(fit["dual"])
            residual = train_y - design @ coefficients[:, j]
            primal = np.maximum(tau * residual, (tau - 1) * residual).mean()
            np.testing.assert_allclose(primal, fit["objective"], atol=1e-9)
            np.testing.assert_allclose(primal, train_y @ dual / len(train_y), atol=1e-9)
            np.testing.assert_allclose(design.T @ dual, 0, atol=1e-7)
            assert dual.min() >= tau - 1 - 1e-8 and dual.max() <= tau + 1e-8
    state = base["garch-calibrated"]["state"]
    garch = {
        "garch_parameters": state["parameters"],
        **{k: state[k] for k in ("return_scale", "backcast", "calibration", "residuals")},
    }
    expected_scale = np.sqrt(np.mean(data.daily.returns[data.target_rows[data.train]] ** 2))
    np.testing.assert_allclose(garch["return_scale"], expected_scale, atol=1e-12)
    np.testing.assert_allclose(
        garch["backcast"],
        np.mean((data.daily.returns[: data.target_rows[0]] / expected_scale) ** 2),
        atol=1e-12,
    )
    r = data.daily.returns[data.target_rows] / garch["return_scale"]

    def full_variance(parameters):
        omega, alpha, beta = parameters
        h = np.empty(len(r))
        h[0] = omega + (alpha + beta) * garch["backcast"]
        for t in range(1, len(r)):
            h[t] = omega + alpha * r[t - 1] ** 2 + beta * h[t - 1]
        return h

    variance = full_variance(garch["garch_parameters"])
    calibration_design = np.c_[
        np.ones(data.train.stop), np.log(variance[data.train] * garch["return_scale"] ** 2)
    ]
    np.testing.assert_allclose(
        garch["calibration"],
        np.linalg.lstsq(calibration_design, train_y, rcond=None)[0],
        atol=1e-10,
    )
    np.testing.assert_allclose(
        garch["residuals"],
        np.sort(train_y - calibration_design @ np.array(garch["calibration"])),
        atol=1e-10,
    )
    gfits = base["garch-calibrated"]["fit"]["fits"]
    best = min(gfits, key=lambda f: f["objective"])
    np.testing.assert_array_equal(garch["garch_parameters"], best["parameters"])
    for fit in gfits:
        h = full_variance(fit["parameters"])[data.train]
        value = 0.5 * np.mean(np.log(2 * np.pi * h) + r[data.train] ** 2 / h)
        np.testing.assert_allclose(fit["objective"] / data.train.stop, value, atol=1e-10)

        def likelihood(theta):
            h = full_variance(theta)[data.train]
            return 0.5 * np.mean(np.log(2 * np.pi * h) + r[data.train] ** 2 / h)

        parameters = np.array(fit["parameters"])
        gradient = np.array(
            [
                (likelihood(parameters + d) - likelihood(parameters - d)) / 2e-6
                for d in np.eye(3) * 1e-6
            ]
        )
        np.testing.assert_allclose(fit["kkt"]["gradient"], gradient, atol=3e-7)
        margins = np.r_[parameters, 1 - parameters[1] - parameters[2]]
        np.testing.assert_allclose(fit["kkt"]["constraint_margins"], margins, atol=1e-12)
        assert fit["kkt"]["feasible"] == bool(margins.min() >= -1e-8)
        active = margins <= 1e-6
        from scipy.optimize import nnls

        directions = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1], [0, -1, -1]])
        if active.any():
            multipliers, _ = nnls(directions[active].T, gradient)
            residual = gradient - directions[active].T @ multipliers
        else:
            residual = gradient
        np.testing.assert_allclose(
            fit["kkt"]["stationarity_inf"], np.max(np.abs(residual)), atol=3e-7
        )
    assert base["garch-calibrated"]["fit"]["eligible"] == bool(
        best["success"]
        and best["recursion_relative_error"] < 1e-8
        and best["kkt"]["feasible"]
        and best["kkt"]["stationarity_inf"] <= 1e-4
    )
    controls["garch-calibrated"] = None

    def training_loss(probability, p, ridge=0):
        pp = probability(data.x[data.train], p)
        return -np.log(
            np.maximum(pp[np.arange(len(pp)), data.labels[data.train]], 1e-12)
        ).mean() + ridge * (p @ p)

    for seed in config.seeds:
        train = read_json(root / f"training-seed{seed}.json")
        assert train["seed"] == seed
        candidates = {id_: (probability, None) for id_, probability in controls.items()}
        training_flags = {
            id_: (base[id_]["fit"]["eligible"], base[id_]["fit"]["eligible"]) for id_ in base
        }
        for family, row in train["families"].items():
            probability = replay.independent_model(
                family, config.quantum_layers if family == "quantum" else 0, {}
            )
            ridge = config.network_ridge if family == "network" else 0
            assert row["ridge"] == ridge and row["lambda"] == config.realism_weights[family]
            assert (
                len(row["D_fits"]) == config.restarts
                and len(row["A_fits"]) == config.realism_starts
            )
            for fit in row["D_fits"]:
                p = np.array(fit["parameters"])
                init_seed = 100000 + 100 * seed + fit["restart"]
                assert fit["initialization_seed"] == init_seed
                np.testing.assert_array_equal(
                    fit["initial_parameters"],
                    np.random.default_rng(init_seed).normal(0, 0.3, len(p)),
                )
                np.testing.assert_allclose(
                    fit["objective"], training_loss(probability, p, ridge), atol=1e-10
                )
                gradient = max(
                    abs(
                        (
                            training_loss(probability, p + d, ridge)
                            - training_loss(probability, p - d, ridge)
                        )
                        / 2e-5
                    )
                    for d in np.eye(len(p)) * 1e-5
                )
                np.testing.assert_allclose(fit["gradient_inf"], gradient, atol=2e-8)
                assert fit["eligible"] == bool(fit["success"] and gradient <= 1e-4)
                assert fit["total_objective_calls"] == len(fit["objective_history"])
            winner = min(row["D_fits"], key=lambda f: (f["objective"], f["restart"]))
            assert (
                winner["restart"] == row["D_restart"]
                and winner["parameters"] == row["D_parameters"]
            )
            assert winner["eligible"] == row["D_eligible"]
            for fit in row["A_fits"]:
                p = np.array(fit["parameters"])
                initial = np.array(winner["parameters"])
                if fit["restart"]:
                    initial += np.random.default_rng(300000 + 100 * seed + fit["restart"]).normal(
                        0, 0.03, len(p)
                    )
                np.testing.assert_array_equal(fit["initial_parameters"], initial)
                generated = replay.independent_rollout(
                    probability,
                    p,
                    data,
                    config.train_days,
                    config.train_paths,
                    400000 + seed,
                    config.train_burn_in,
                )[0]
                vector = np.mean([replay.independent_moments(y) for y in generated], axis=0)
                value = training_loss(probability, p, ridge) + row["lambda"] * np.sum(
                    ((vector - train_vector) / scales) ** 2
                )
                np.testing.assert_allclose(fit["objective"], value, atol=1e-8)
                assert (
                    fit["total_objective_calls"]
                    == len(fit["objective_history"])
                    == fit["evaluations"] + 1
                )
                assert (
                    fit["evaluations"] <= config.realism_max_calls
                    and fit["eligible"] == fit["success"]
                )
            winner_a = min(row["A_fits"], key=lambda f: (f["objective"], f["restart"]))
            assert (
                winner_a["restart"] == row["A_restart"]
                and winner_a["parameters"] == row["A_parameters"]
            )
            assert winner_a["eligible"] == row["A_eligible"]
            for stage in ("D", "A"):
                candidates[f"{family}-{stage}"] = (
                    probability,
                    np.array(row[f"{stage}_parameters"]),
                )
                training_flags[f"{family}-{stage}"] = (row["D_eligible"], row[f"{stage}_eligible"])
        for index, (id_, (probability, p)) in enumerate(candidates.items()):
            record = by_record[id_, seed]
            assert (record["D_eligible"], record["stage_eligible"]) == training_flags[id_]
            native = None
            if id_ == "garch-calibrated":
                actual = finance.garch_probability(garch, variance[data.test], data.bins.edges)
                native = (
                    garch["calibration"][0]
                    + garch["calibration"][1]
                    * np.log(variance[data.test, None] * garch["return_scale"] ** 2)
                    + np.quantile(garch["residuals"], QUANTILES)[None, :]
                )
            else:
                actual = probability(data.x[data.test], p)
                if id_ in ("har-quantile", "short-quantile"):
                    _, native_function = finance.finance_probability(
                        {"id": id_, **base[id_]["state"]}, data
                    )
                    native = native_function(data.x[data.test])
            with np.load(destination / f"{id_}-seed{seed}.npz", allow_pickle=False) as saved:
                error = float(np.max(np.abs(actual - saved["probabilities"])))
                assert error < 1e-11
                max_error = max(max_error, error)
                probability_rows += len(actual)
                common = finance.common_quantiles(actual, data.bins.pools)
                np.testing.assert_array_equal(saved["common_quantiles"], common)
                finance.check_quantiles(record["common_quantile_scores"], common, reference)
                if native is not None:
                    np.testing.assert_allclose(saved["native_quantiles"], native, atol=1e-10)
                    finance.check_quantiles(record["native_quantile_scores"], native, reference)
                daily = -np.log(np.maximum(actual[np.arange(len(actual)), labels], 1e-12))
                np.testing.assert_allclose(saved["daily_log_loss"], daily, atol=1e-10)
                losses[id_].append(daily)
                np.testing.assert_allclose(record["scores"]["log_loss"], daily.mean(), atol=1e-10)
                np.testing.assert_allclose(
                    record["scores"]["rps_normalized"],
                    np.mean(
                        (actual.cumsum(axis=1)[:, :3] - (labels[:, None] <= np.arange(3))) ** 2
                    ),
                )
                np.testing.assert_allclose(
                    record["scores"]["extreme_brier"], np.mean((actual[:, 3] - (labels == 3)) ** 2)
                )
                groups = np.minimum((actual[:, 3] * 10).astype(int), 9)
                for group, bucket in enumerate(record["scores"]["extreme_calibration"]):
                    mask = groups == group
                    assert bucket["count"] == int(mask.sum())
                    if mask.any():
                        np.testing.assert_allclose(
                            bucket["mean_probability"], actual[mask, 3].mean()
                        )
                        np.testing.assert_allclose(
                            bucket["observed_frequency"], (labels[mask] == 3).mean()
                        )
            if probability is None:
                c = {
                    "audit_days": config.evaluation_days,
                    "audit_paths": config.evaluation_paths,
                    "burn_in": config.evaluation_burn_in,
                }
                arrays = finance.garch_replay(garch, data, c, 500000 + seed, False)
            else:
                arrays = replay.independent_rollout(
                    probability,
                    p,
                    data,
                    config.evaluation_days,
                    config.evaluation_paths,
                    500000 + seed,
                    config.evaluation_burn_in,
                )
            with np.load(destination / f"paths-{id_}-seed{seed}.npz", allow_pickle=False) as saved:
                for key, values in zip(("log_rv", "returns", "levels"), arrays, strict=True):
                    np.testing.assert_array_equal(saved[key], values)
            record = by_path[id_, seed]
            replay.check_moments(record["summary"], arrays[0], reference_vector, scales)
            compare_stats(
                record["summary"]["wasserstein_log_rv"],
                stats([wasserstein(y, reference) for y in arrays[0]]),
            )
            compare_stats(
                record["summary"]["hill_return_tail_index"], stats([hill(r) for r in arrays[1]])
            )
            check_diagnostics(
                record, arrays[0][0], arrays[1][0], reference, scales, 700000 + 1000 * seed + index
            )
            recursive_days += arrays[0].size
        c = {
            "audit_days": config.evaluation_days,
            "audit_paths": config.evaluation_paths,
            "burn_in": config.evaluation_burn_in,
        }
        arrays = finance.garch_replay(garch, data, c, 500000 + seed, True)
        with np.load(
            destination / f"paths-garch-native-reference-seed{seed}.npz", allow_pickle=False
        ) as saved:
            for key, values in zip(("log_rv", "returns", "levels"), arrays, strict=True):
                np.testing.assert_array_equal(saved[key], values)
        record = by_path["garch-native-reference", seed]
        replay.check_moments(record["summary"], arrays[0], reference_vector, scales)
        compare_stats(
            record["summary"]["wasserstein_log_rv"],
            stats([wasserstein(y, reference) for y in arrays[0]]),
        )
        compare_stats(
            record["summary"]["hill_return_tail_index"], stats([hill(r) for r in arrays[1]])
        )
        check_diagnostics(
            record,
            arrays[0][0],
            arrays[1][0],
            reference,
            scales,
            700000 + 1000 * seed + len(candidates),
        )
        recursive_days += arrays[0].size
        # Original paper and raw-RV references stay in their own MSE panel.
        paper = train["paper"]
        scaling = PointScaling(**paper["scaling"])
        for fit in paper["fits"]:
            p = np.array(fit["parameters"])
            assert p[1] == 0 and fit["optimized_parameter_count"] == 2
            predicted = (
                point.literal_prediction(data, data.target_rows[data.train], scaling, "paper", p)
                / scaling.rv_scale
            )
            value = np.mean(
                (predicted - data.daily.rv[data.target_rows[data.train]] / scaling.rv_scale) ** 2
            )
            np.testing.assert_allclose(fit["objective"], value, atol=1e-12)
            assert (
                fit["total_objective_calls"]
                == len(fit["objective_history"])
                == fit["evaluations"] + 1
            )
            assert fit["evaluations"] <= config.paper_max_calls

            def paper_loss(parameters, scaling=scaling):
                pred = (
                    point.literal_prediction(
                        data, data.target_rows[data.train], scaling, "paper", parameters
                    )
                    / scaling.rv_scale
                )
                return np.mean(
                    (pred - data.daily.rv[data.target_rows[data.train]] / scaling.rv_scale) ** 2
                )

            gradient = max(
                abs((paper_loss(p + d) - paper_loss(p - d)) / 2e-5)
                for d in np.eye(3)[[0, 2]] * 1e-5
            )
            np.testing.assert_allclose(fit["gradient_inf"], gradient, atol=1e-9)
            assert fit["eligible"] == bool(fit["success"] and gradient <= 1e-5)
        best = min(paper["fits"], key=lambda f: (f["objective"], f["restart"]))
        assert best["parameters"] == paper["parameters"] and best["restart"] == paper["restart"]
        target = data.daily.rv[data.target_rows[data.test]]
        raw_design = lambda rows: np.array(
            [[1, *[data.daily.rv[t - lag : t].mean() for lag in (1, 7, 30)]] for t in rows]
        )
        train_design = raw_design(data.target_rows[data.train])
        beta = np.linalg.lstsq(
            train_design, data.daily.rv[data.target_rows[data.train]], rcond=None
        )[0]
        expected = {
            "paper": point.literal_prediction(
                data, data.target_rows[data.test], scaling, "paper", np.array(paper["parameters"])
            ),
            "persistence": data.daily.rv[data.target_rows[data.test] - 1],
            "training-mean": np.full(
                len(target), np.mean(data.daily.rv[data.target_rows[data.train]])
            ),
            "raw-har": np.maximum(raw_design(data.target_rows[data.test]) @ beta, 0),
        }
        with np.load(destination / f"point-seed{seed}.npz", allow_pickle=False) as saved:
            for id_, predicted in expected.items():
                np.testing.assert_allclose(saved[id_], predicted, atol=1e-11)
                row = next(r for r in point_records if r["id"] == id_ and r["seed"] == seed)
                np.testing.assert_allclose(
                    row["mse_rv"], np.mean((predicted - target) ** 2), atol=1e-12
                )
        print(f"Verified seed {seed}", flush=True)
    assert recursive_days == status["output_days"]
    for item in summary["models"]:
        group = [r for r in records if r["id"] == item["id"]]
        for key in ("log_loss", "rps_normalized", "extreme_brier"):
            compare_stats(item[key], stats([r["scores"][key] for r in group]))
        for key in ("mean_pinball", "coverage_90", "mean_width_90", "interval_score_90"):
            compare_stats(item[key], stats([r["common_quantile_scores"][key] for r in group]))
        matching = [r for r in paths if r["id"] == item["id"]]
        for key in ("distance_of_mean", "mean_path_distance"):
            compare_stats(item[key], stats([r["summary"][key] for r in matching]))
        assert item["D_training_passes"] == sum(r["D_eligible"] for r in group)
        assert item["stage_training_passes"] == sum(r["stage_eligible"] for r in group)
        compare_stats(
            item["passing_only_log_loss"],
            stats(
                [r["scores"]["log_loss"] for r in group if r["D_eligible"] and r["stage_eligible"]]
            ),
        )
    for item in summary["models"]:
        matching = [r for r in paths if r["id"] == item["id"]]
        for index, key in enumerate(("acf_1", "acf_7", "acf_30", "vol_of_vol")):
            compare_stats(item[key], stats([r["summary"]["mean_moments"][index] for r in matching]))
        for key in ("wasserstein_log_rv", "hill_return_tail_index"):
            compare_stats(item[key], stats([r["summary"][key]["mean"] for r in matching]))
        group = [r for r in records if r["id"] == item["id"] and "native_quantile_scores" in r]
        if group:
            for key in ("mean_pinball", "coverage_90", "mean_width_90", "interval_score_90"):
                compare_stats(
                    item["native_quantile_scores"][key],
                    stats([r["native_quantile_scores"][key] for r in group]),
                )
    for id_, values in summary["point_mse"].items():
        compare_stats(values, stats([r["mse_rv"] for r in point_records if r["id"] == id_]))
    assert len(summary["bootstrap_nll"]) == 8 * len(config.bootstrap_blocks)
    # Independently reconstruct the paired circular date bootstrap and its exact streams.
    rng = np.random.default_rng(600000)
    means = {k: np.mean(v, axis=0) for k, v in losses.items()}
    for block in config.bootstrap_blocks:
        starts = rng.integers(
            0, len(labels), (config.bootstrap_replicates, int(np.ceil(len(labels) / block)))
        )
        indices = np.array(
            [
                [(start + offset) % len(labels) for start in row for offset in range(block)][
                    : len(labels)
                ]
                for row in starts
            ]
        )
        for row in [r for r in summary["bootstrap_nll"] if r["block"] == block]:
            delta = means[row["left"]] - means[row["right"]]
            samples = np.mean(delta[indices], axis=1)
            np.testing.assert_allclose(
                [row["mean_difference"], row["lower"], row["upper"]],
                [delta.mean(), np.quantile(samples, 0.025), np.quantile(samples, 0.975)],
                atol=1e-11,
            )
    expected_effort = {}
    for seed in config.seeds:
        training = read_json(root / f"training-seed{seed}.json")
        for family, row in training["families"].items():
            for stage in ("D", "A"):
                expected_effort.setdefault(f"{family}-{stage}", []).extend(row[f"{stage}_fits"])
        expected_effort.setdefault("paper-point", []).extend(training["paper"]["fits"])
    for row in summary["effort"]:
        if row["id"] in expected_effort:
            fits = expected_effort[row["id"]]
            assert row["fits"] == len(fits)
            assert row["objective_calls"] == sum(f["total_objective_calls"] for f in fits)
            assert row["diagnostic_calls"] == sum(f["diagnostic_calls"] for f in fits)
            np.testing.assert_allclose(row["seconds"], sum(f["seconds"] for f in fits))
    result = {
        "verified": True,
        "kind": config.kind,
        "seeds": len(config.seeds),
        "forecast_records": len(records),
        "probability_rows": probability_rows,
        "max_dense_probability_error": max_error,
        "recursive_output_days": recursive_days,
        "independent_mfdfa": True,
        "bootstrap_verified": True,
    }
    from qcvol.experiment import write_json

    write_json(destination / "verification.json", result)
    print(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--author-data", type=Path, required=True)
    parser.add_argument("--evaluation", default="evaluation")
    parser.add_argument("--allow-integration", action="store_true")
    args = parser.parse_args()
    verify(args.run, args.author_data, args.evaluation, args.allow_integration)


if __name__ == "__main__":
    main()
