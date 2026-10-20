#!/usr/bin/env python3
"""Independently audit finance forecasts, LP certificates, training selection and draws."""

import argparse
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import numpy as np

from qcvol.classical import FrequencyModel, HARModel
from qcvol.data import load_author_data, prepare, sha256
from qcvol.distribution_models import ShortAR
from qcvol.experiment import code_revision
from qcvol.finance_baselines import QUANTILES

spec = importlib.util.spec_from_file_location(
    "dense_replay", Path(__file__).with_name("verify_distribution_study.py")
)
replay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(replay)


def source_check(code):
    current = code_revision()["package_source_sha256"]
    if current == code["package_source_sha256"]:
        return
    # Historical attempts remain verifiable after additive refinements, using committed blobs.
    assert not code["dirty"], "Historical dirty source cannot be certified from Git"
    head = code["head"]
    assert isinstance(head, str) and len(head) == 40 and all(c in "0123456789abcdef" for c in head)
    for name, digest in code["package_source_sha256"].items():
        assert Path(name).name == name and name.endswith(".py")
        blob = subprocess.check_output(["git", "show", f"{head}:src/qcvol/{name}"])
        assert hashlib.sha256(blob).hexdigest() == digest


def finance_probability(row, data):
    if row["id"] in ("har-quantile", "short-quantile"):
        beta = np.array(row["coefficients"])
        taus = np.array(row["quantiles"])

        def native(x):
            inputs = x[:, [0, 3]] if row["id"] == "short-quantile" else x[:, :3]
            return np.sort(np.c_[inputs, np.ones(len(x))] @ beta, axis=1)

        frequency = np.bincount(data.labels[data.train], minlength=4) / data.train.stop

        def probability(x, p=None):
            result = []
            for quantiles in native(x):
                cdf = []
                keep = np.r_[quantiles[1:] != quantiles[:-1], True]
                values, levels = quantiles[keep], taus[keep]
                low_scale = max(
                    (quantiles[1] - quantiles[0]) / np.log(taus[1] / taus[0]), row["tail_floor"]
                )
                high_scale = max(
                    (quantiles[-1] - quantiles[-2]) / np.log((1 - taus[-2]) / (1 - taus[-1])),
                    row["tail_floor"],
                )
                for edge in data.bins.edges:
                    if edge < quantiles[0]:
                        value = taus[0] * np.exp((edge - quantiles[0]) / low_scale)
                    elif edge > quantiles[-1]:
                        value = 1 - (1 - taus[-1]) * np.exp(-(edge - quantiles[-1]) / high_scale)
                    else:
                        k = np.searchsorted(values, edge, side="right")
                        if k == len(values):
                            value = levels[-1]
                        elif k == 0:
                            value = levels[0]
                        else:
                            fraction = (edge - values[k - 1]) / (values[k] - values[k - 1])
                            value = levels[k - 1] + fraction * (levels[k] - levels[k - 1])
                    cdf.append(value)
                result.append((1 - 1e-6) * np.diff([0, *cdf, 1]) + 1e-6 * frequency)
            return np.array(result)

        return probability, native
    raise ValueError("Unknown quantile family")


def garch_state(row, data):
    omega, alpha, beta = row["garch_parameters"]
    scale = row["return_scale"]
    returns = data.daily.returns[data.target_rows[: data.validation.stop]] / scale
    h = np.empty(len(returns))
    h[0] = omega + (alpha + beta) * row["backcast"]
    for t in range(1, len(h)):
        h[t] = omega + alpha * returns[t - 1] ** 2 + beta * h[t - 1]
    return h


def garch_probability(row, variance, edges):
    location = row["calibration"][0] + row["calibration"][1] * np.log(
        np.asarray(variance) * row["return_scale"] ** 2
    )
    residuals = np.array(row["residuals"])
    cdf = (np.searchsorted(residuals, edges[None, :] - location[:, None], side="right") + 0.5) / (
        len(residuals) + 1
    )
    return np.diff(np.c_[np.zeros(len(cdf)), cdf, np.ones(len(cdf))], axis=1)


def garch_replay(row, data, c, seed, native):
    horizon = c["audit_days"] + c["burn_in"]
    paths = c["audit_paths"]
    rng = np.random.default_rng(seed)
    u = rng.random((horizon, paths))
    v = rng.random((horizon, paths))
    z = rng.normal(size=(horizon, paths))
    h = np.full(paths, garch_state(row, data)[data.train.stop])
    omega, alpha, beta = row["garch_parameters"]
    y = np.empty((paths, horizon))
    r = np.empty_like(y)
    levels = np.empty((paths, horizon), int)
    residuals = np.array(row["residuals"])
    for t in range(horizon):
        if native:
            location = row["calibration"][0] + row["calibration"][1] * np.log(
                h * row["return_scale"] ** 2
            )
            for j in range(paths):
                y[j, t] = (
                    location[j] + residuals[min(int(v[t, j] * len(residuals)), len(residuals) - 1)]
                )
            r[:, t] = row["return_scale"] * np.sqrt(h) * z[t]
            levels[:, t] = np.searchsorted(data.bins.edges, y[:, t], side="right")
        else:
            probabilities = garch_probability(row, h, data.bins.edges)
            for j in range(paths):
                k = min(np.searchsorted(probabilities[j].cumsum(), u[t, j], side="right"), 3)
                pool = data.bins.pools[k]
                levels[j, t] = k
                y[j, t] = pool[min(int(v[t, j] * len(pool)), len(pool) - 1)]
            r[:, t] = np.exp(y[:, t] / 2) * z[t]
        h = omega + alpha * (r[:, t] / row["return_scale"]) ** 2 + beta * h
    return y[:, c["burn_in"] :], r[:, c["burn_in"] :], levels[:, c["burn_in"] :]


def check_quantiles(scores, q, y):
    residual = y[:, None] - q
    pinball = np.maximum(QUANTILES * residual, (QUANTILES - 1) * residual).mean(axis=0)
    np.testing.assert_allclose(scores["pinball_by_quantile"], pinball, atol=1e-11)
    np.testing.assert_allclose(scores["mean_pinball"], pinball.mean(), atol=1e-11)
    low = q[:, 2]
    high = q[:, -3]  # .05/.95 in the declared grid
    np.testing.assert_allclose(scores["coverage_90"], np.mean((low <= y) & (y <= high)))
    np.testing.assert_allclose(scores["mean_width_90"], np.mean(high - low))
    np.testing.assert_allclose(
        scores["interval_score_90"],
        np.mean(high - low + 20 * np.maximum(low - y, 0) + 20 * np.maximum(y - high, 0)),
    )


def common_quantiles(p, pools):
    # Explicit discrete distribution and left inverse, independent of the package helper.
    ordered = np.sort(np.concatenate(pools))
    categories = np.array(
        [next(k for k, pool in enumerate(pools) if np.any(pool == value)) for value in ordered]
    )
    counts = np.array([len(pool) for pool in pools])
    output = []
    for probabilities in p:
        cumulative = np.cumsum(probabilities[categories] / counts[categories])
        output.append(
            ordered[
                np.minimum(np.searchsorted(cumulative, QUANTILES, side="left"), len(ordered) - 1)
            ]
        )
    return np.array(output)


def verify(root, author_data):
    root = Path(root)
    read = lambda n: json.loads((root / n).read_text())
    manifest = read("manifest.json")
    assert manifest["status"] == "complete" and manifest["test_scored"] is False
    source_check(manifest["code"])
    assert manifest["source"]["sha256"] == {
        name: sha256(Path(author_data) / name) for name in ("data-rstand", "data-ystand")
    }
    data = prepare(load_author_data(author_data))
    assert manifest["data"] == data.metadata()
    prior = Path(manifest["prior_directory"])
    assert sha256(prior / "manifest.json") == manifest["prior_manifest_sha256"]
    assert sha256(prior / "records.json") == manifest["prior_records_sha256"]
    old_manifest = json.loads((prior / "manifest.json").read_text())
    source_check(old_manifest["code"])
    old = {r["id"]: r for r in json.loads((prior / "records.json").read_text())}
    for name, digest in manifest["prior_import_sha256"].items():
        assert sha256(prior / name) == digest
    previous = manifest["source"].get("previous_attempt")
    if previous:
        assert sha256(Path(previous["directory"]) / "manifest.json") == previous["manifest_sha256"]
    rows = read("records.json")
    by_id = {r["id"]: r for r in rows}
    assert len(rows) == len(by_id) == manifest["record_count"]
    controls = {
        "frequency": FrequencyModel.fit(data.labels[data.train]),
        "short-ar": ShortAR.fit(data.x[data.train], data.y[data.train], data.bins.edges),
        "har-residual": HARModel.fit(data.x[data.train], data.y[data.train], data.bins.edges),
    }
    probabilities_by_id = {}
    functions = {}
    probability_count = 0
    max_error = 0.0
    reference = replay.independent_moments(data.y[data.validation])
    scales = np.array(manifest["moment_scales"])
    np.testing.assert_allclose(reference, manifest["validation_moments"])
    train = data.y[data.train]
    width = min(128, max(40, len(train) // 3))
    starts = np.unique(np.linspace(0, len(train) - width, 12).astype(int))
    np.testing.assert_allclose(
        scales,
        np.maximum(
            np.std([replay.independent_moments(train[s : s + width]) for s in starts], axis=0), 0.02
        ),
    )
    garch = by_id["garch-calibrated"]
    variance = garch_state(garch, data)
    with np.load(root / "garch-state.npz") as saved:
        np.testing.assert_allclose(saved["variance"], variance, atol=1e-12)
    scale = np.sqrt(np.mean(data.daily.returns[data.target_rows[data.train]] ** 2))
    np.testing.assert_allclose(garch["return_scale"], scale)
    np.testing.assert_allclose(
        garch["backcast"], np.mean((data.daily.returns[: data.target_rows[0]] / scale) ** 2)
    )
    design = np.c_[np.ones(data.train.stop), np.log(variance[data.train] * scale**2)]
    beta = np.linalg.lstsq(design, train, rcond=None)[0]
    np.testing.assert_allclose(garch["calibration"], beta, atol=1e-11)
    np.testing.assert_allclose(garch["residuals"], np.sort(train - design @ beta), atol=1e-11)
    for fit in garch["fit"]["fits"]:

        def likelihood(p):
            copy = dict(garch)
            copy["garch_parameters"] = p
            h = garch_state(copy, data)[data.train]
            r = data.daily.returns[data.target_rows[data.train]] / scale
            return 0.5 * np.mean(np.log(2 * np.pi * h) + r * r / h)

        p = np.array(fit["parameters"])
        np.testing.assert_allclose(fit["objective"] / data.train.stop, likelihood(p), atol=1e-10)
        # A smaller numerical step avoids differencing curvature in persistent GARCH.
        gradient = np.array(
            [(likelihood(p + d) - likelihood(p - d)) / 2e-6 for d in np.eye(3) * 1e-6]
        )
        np.testing.assert_allclose(fit["kkt"]["gradient"], gradient, atol=3e-7)
        omega, alpha, beta = p
        margins = np.array([omega, alpha, beta, 1 - alpha - beta])
        np.testing.assert_allclose(fit["kkt"]["constraint_margins"], margins)
        assert fit["kkt"]["feasible"] == bool(np.min(margins) >= -1e-8)
        from scipy.optimize import nnls

        active = margins <= 1e-6
        directions = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1], [0, -1, -1]])
        if active.any():
            multipliers, _ = nnls(directions[active].T, gradient)
            residual = gradient - directions[active].T @ multipliers
        else:
            residual = gradient
        assert fit["kkt"]["active_constraints"] == np.flatnonzero(active).tolist()
        np.testing.assert_allclose(
            fit["kkt"]["stationarity_inf"], np.max(np.abs(residual)), atol=3e-7
        )
    winner = min(garch["fit"]["fits"], key=lambda f: f["objective"])
    assert garch["fit"]["selected_start"] == garch["fit"]["fits"].index(winner)
    assert garch["fit"]["eligible"] == bool(
        winner["success"]
        and winner["recursion_relative_error"] < 1e-8
        and winner["kkt"]["feasible"]
        and winner["kkt"]["stationarity_inf"] <= 1e-4
    )
    np.testing.assert_array_equal(garch["garch_parameters"], winner["parameters"])
    for row in rows:
        id_ = row["id"]
        p = None
        native = None
        if row["origin"] == "prior":
            original = old[row["prior_id"]]
            p = np.array(original["fit"]["parameters"])
            probability = replay.independent_model(row["family"], original["depth"], {})
        elif id_ in controls:
            probability = controls[id_].probabilities
        elif id_ in ("har-quantile", "short-quantile"):
            probability, native = finance_probability(row, data)
            inputs = (
                data.x[data.train][:, [0, 3]]
                if id_ == "short-quantile"
                else data.x[data.train][:, :3]
            )
            design = np.c_[inputs, np.ones(data.train.stop)]
            coefficients = np.array(row["coefficients"])
            for column, fit in enumerate(row["fit"]["quantile_fits"]):
                tau = fit["quantile"]
                dual = np.array(fit["dual"])
                residual = train - design @ coefficients[:, column]
                primal = np.maximum(tau * residual, (tau - 1) * residual).mean()
                assert fit["success"]
                np.testing.assert_allclose(primal, fit["objective"], atol=1e-9)
                np.testing.assert_allclose(primal, train @ dual / len(train), atol=1e-9)
                np.testing.assert_allclose(design.T @ dual, 0, atol=1e-7)
                assert dual.min() >= tau - 1 - 1e-8 and dual.max() <= tau + 1e-8
            inputs = (
                data.x[data.validation][:, [0, 3]]
                if id_ == "short-quantile"
                else data.x[data.validation][:, :3]
            )
            raw = np.c_[inputs, np.ones(len(inputs))] @ coefficients
            assert row["raw_crossing_rows"] == int(np.sum(np.any(np.diff(raw, axis=1) < 0, axis=1)))
        elif id_ == "garch-calibrated":
            probability = None
            native = lambda x: (
                garch["calibration"][0]
                + garch["calibration"][1] * np.log(variance[data.validation, None] * scale**2)
                + np.quantile(np.array(garch["residuals"]), QUANTILES)[None, :]
            )
        else:
            probability = replay.independent_model("network", 0, {})
            p = np.array(row["fit"]["parameters"])
        actual = (
            garch_probability(row, variance[data.validation], data.bins.edges)
            if probability is None
            else probability(data.x[data.validation], p)
        )
        functions[id_] = (probability, p)
        probabilities_by_id[id_] = actual
        with np.load(root / f"{id_}.npz", allow_pickle=False) as saved:
            assert not any("test" in key for key in saved.files)
            error = float(np.max(np.abs(saved["validation_probabilities"] - actual)))
            assert error < 1e-11
            max_error = max(max_error, error)
            probability_count += len(actual)
            if p is not None:
                np.testing.assert_array_equal(saved["parameters"], p)
            q = common_quantiles(actual, data.bins.pools)
            np.testing.assert_array_equal(saved["common_quantiles"], q)
            check_quantiles(row["common_quantile_scores"], q, data.y[data.validation])
            if native:
                predictions = native(data.x[data.validation])
                np.testing.assert_allclose(saved["native_quantiles"], predictions, atol=1e-11)
                check_quantiles(row["native_quantile_scores"], predictions, data.y[data.validation])
        labels = data.labels[data.validation]
        scores = row["validation"]
        np.testing.assert_allclose(
            scores["log_loss"],
            -np.log(np.maximum(actual[np.arange(len(actual)), labels], 1e-12)).mean(),
        )
        np.testing.assert_allclose(
            scores["rps_normalized"],
            np.mean((actual.cumsum(axis=1)[:, :3] - (labels[:, None] <= np.arange(3))) ** 2),
        )
        np.testing.assert_allclose(
            scores["extreme_brier"], np.mean((actual[:, 3] - (labels == 3)) ** 2)
        )
        for k, entry in enumerate(scores["extreme_calibration"]):
            mask = np.minimum((actual[:, 3] * 10).astype(int), 9) == k
            assert entry["count"] == int(mask.sum())
            if mask.any():
                np.testing.assert_allclose(entry["mean_probability"], actual[mask, 3].mean())
                np.testing.assert_allclose(entry["observed_frequency"], (labels[mask] == 3).mean())
        if "sensitivity" in row:
            summary = row["sensitivity"]
            eye = np.eye(len(p)) * 1e-5
            jac = np.column_stack(
                [
                    (
                        (
                            probability(data.x[data.train], p + d)[:, :3]
                            - probability(data.x[data.train], p - d)[:, :3]
                        )
                        / 2e-5
                    ).ravel()
                    for d in eye
                ]
            )
            singular = np.linalg.svd(jac, compute_uv=False)
            np.testing.assert_allclose(summary["singular_values"], singular, atol=1e-8, rtol=1e-5)
            assert summary["local_rank"] == int(np.sum(singular > max(1e-10, 1e-6 * singular[0])))
    continuations = read("network-continuations.json")
    assert len(continuations) == len(old_manifest["config"]["starts"])
    network = replay.independent_model("network", 0, {})

    def train_loss(p, ridge=0):
        pp = network(data.x[data.train], p)
        return -np.log(
            np.maximum(pp[np.arange(len(pp)), data.labels[data.train]], 1e-12)
        ).mean() + ridge * (p @ p)

    def check_fit(fit, ridge=0):
        p = np.array(fit["parameters"])
        np.testing.assert_allclose(fit["objective"], train_loss(p, ridge), atol=1e-10)
        gradient = max(
            abs((train_loss(p + d, ridge) - train_loss(p - d, ridge)) / 2e-5)
            for d in np.eye(len(p)) * 1e-5
        )
        np.testing.assert_allclose(fit["gradient_inf"], gradient, atol=1e-8)
        assert fit["eligible"] == bool(fit["success"] and gradient <= 1e-4)
        assert (
            fit["objective_calls"] == fit["gradient_evaluations"] == len(fit["objective_history"])
        )
        assert fit["objective"] <= fit["initial_objective"] + 1e-10

    for fit in continuations:
        np.testing.assert_array_equal(
            fit["initial_parameters"], old[fit["prior_id"]]["fit"]["parameters"]
        )
        check_fit(fit)
    winner = min(continuations, key=lambda f: (f["objective"], f["start"]))
    np.testing.assert_array_equal(
        by_id["network-continued-D"]["fit"]["parameters"], winner["parameters"]
    )
    ridge = 0
    if (root / "network-ridge-fits.json").exists():
        fits = read("network-ridge-fits.json")
        selection = read("network-ridge-selection.json")
        assert len(fits) == len(manifest["config"]["ridge_penalties"]) * len(
            old_manifest["config"]["starts"]
        )
        winners = [{"fit": winner, "ridge": 0, "start": winner["start"]}]
        for row in fits:
            np.testing.assert_array_equal(
                row["fit"]["initial_parameters"],
                np.random.default_rng(row["start"]).normal(0, 0.3, 24),
            )
            check_fit(row["fit"], row["ridge"])
        for alpha in manifest["config"]["ridge_penalties"]:
            group = [r for r in fits if r["ridge"] == alpha]
            winners.append(min(group, key=lambda r: (r["fit"]["objective"], r["start"])))
        for row in winners:
            p = np.array(row["fit"]["parameters"])
            pp = network(data.x[data.validation], p)
            row["validation_nll"] = float(
                -np.log(
                    np.maximum(pp[np.arange(len(pp)), data.labels[data.validation]], 1e-12)
                ).mean()
            )
        chosen = min(winners, key=lambda r: (r["validation_nll"], r["ridge"]))
        assert selection["ridge"] == chosen["ridge"] and selection["start"] == chosen["start"]
        for a, b in zip(selection["winners"], winners, strict=True):
            assert a["ridge"] == b["ridge"] and a["start"] == b["start"]
            np.testing.assert_allclose(a["validation_nll"], b["validation_nll"])
        ridge = chosen["ridge"]
        winner = chosen["fit"]
        np.testing.assert_array_equal(
            by_id["network-refined-D"]["fit"]["parameters"], winner["parameters"]
        )
    candidates = read("network-candidates.json")
    decision = read("decision.json")
    base = np.array(winner["parameters"])
    assert (
        decision["network_forecast_start"] == winner["start"]
        and decision["network_forecast_eligible"] == winner["eligible"]
    )
    if "network_ridge" in decision:
        assert decision["network_ridge"] == ridge
    old_c = old_manifest["config"]
    train_ref = replay.independent_moments(train)
    for row in candidates:
        p = np.array(row["parameters"])
        if row["lambda"]:
            initial = base.copy()
            if row["start"]:
                initial += np.random.default_rng(row["start"]).normal(0, 0.03, len(initial))
            np.testing.assert_array_equal(row["fit"]["initial_parameters"], initial)
            paths = replay.independent_rollout(
                network, p, data, old_c["train_days"], old_c["train_paths"], 10000, old_c["burn_in"]
            )[0]
            vector = np.mean([replay.independent_moments(y) for y in paths], axis=0)
            objective = train_loss(p, ridge) + row["lambda"] * np.sum(
                ((vector - train_ref) / scales) ** 2
            )
            np.testing.assert_allclose(row["fit"]["objective"], objective, atol=1e-8)
        paths = replay.independent_rollout(
            network,
            p,
            data,
            old_c["selection_days"],
            old_c["selection_paths"],
            20000,
            old_c["burn_in"],
        )[0]
        replay.check_moments(row["selection_paths"], paths, reference, scales)
        pp = network(data.x[data.validation], p)
        nll = -np.log(
            np.maximum(pp[np.arange(len(pp)), data.labels[data.validation]], 1e-12)
        ).mean()
        np.testing.assert_allclose(row["validation_nll"], nll)
        np.testing.assert_allclose(
            row["selection_score"],
            nll + old_c["selection_weight"] * row["selection_paths"]["distance_of_mean"],
        )
    winners = [candidates[0]] + [
        min(
            [r for r in candidates if r["lambda"] == weight],
            key=lambda r: (r["fit"]["objective"], r["start"]),
        )
        for weight in old_c["lambdas"]
        if weight
    ]
    selected = min(winners, key=lambda r: (r["selection_score"], r["lambda"]))
    assert decision["lambda_winners"] == [r["id"] for r in winners]
    assert (
        decision["selected_network_candidate"] == selected["id"]
        and decision["selected_lambda"] == selected["lambda"]
    )
    audit = read("audit.json")
    c = manifest["config"]
    recursive_days = 0
    assert {(r["id"], r["summary"]["seed"]) for r in audit} == {
        (id_, seed) for id_ in [*by_id, "garch-native-reference"] for seed in (50000, 60000)
    }
    for row in audit:
        id_ = row["id"]
        summary = row["summary"]
        seed = summary["seed"]
        if id_ in ("garch-calibrated", "garch-native-reference"):
            paths = garch_replay(garch, data, c, seed, id_ == "garch-native-reference")
        else:
            probability, p = functions[id_]
            paths = replay.independent_rollout(
                probability, p, data, c["audit_days"], c["audit_paths"], seed, c["burn_in"]
            )
        with np.load(root / f"audit-{id_}-{seed}.npz", allow_pickle=False) as saved:
            for key, values in zip(("log_rv", "returns", "levels"), paths, strict=True):
                np.testing.assert_array_equal(saved[key], values)
        replay.check_moments(summary, paths[0], reference, scales)
        recursive_days += paths[0].size
    assert manifest["prior_training_objective_calls"] == old_manifest["objective_calls"]
    assert manifest["new_network_objective_calls"] == sum(
        f["objective_calls"] for f in continuations
    )
    assert manifest["new_network_diagnostic_calls"] == sum(
        f["diagnostic_calls"] for f in continuations
    )
    assert manifest["new_realism_objective_calls"] == sum(
        r["fit"]["total_objective_calls"] for r in candidates if r["lambda"]
    )
    result = {
        "verified": True,
        "records": len(rows),
        "probability_rows": probability_count,
        "max_probability_error": max_error,
        "recursive_output_days": recursive_days,
        "test_scored": False,
    }
    print(json.dumps(result, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--author-data", type=Path, required=True)
    args = parser.parse_args()
    verify(args.run, args.author_data)


if __name__ == "__main__":
    main()
