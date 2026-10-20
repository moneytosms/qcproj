#!/usr/bin/env python3
"""Verify saved D/A probabilities, choices, objectives and recursive draws offline."""

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.special import softmax

from qcvol.classical import FrequencyModel, HARModel
from qcvol.data import load_author_data, prepare, sha256
from qcvol.distribution_models import ShortAR, distribution_model
from qcvol.experiment import code_revision


def literal_born(x, compact, depth):
    """Independent dense Kronecker operators, no fused gates or _rotate helper."""
    x = np.asarray(x)[:, [0, 0, 0, 3]]
    full = np.zeros(8 * depth)
    active = np.ones(len(full), bool)
    active[[-3, -1]] = False
    full[active] = compact
    state = np.zeros((len(x), 4), complex)
    state[:, 0] = 1
    identity = np.broadcast_to(np.eye(2), (len(x), 2, 2))
    cnot = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]])
    for w in full.reshape(depth, 8):
        for q in (0, 1):
            j = 2 * q
            for axis, angle in [
                ("y", w[j] * x[:, j]),
                ("z", w[j + 1] * x[:, j + 1]),
                ("y", np.full(len(x), w[4 + j])),
                ("z", np.full(len(x), w[5 + j])),
            ]:
                gate = np.zeros((len(x), 2, 2), complex)
                if axis == "y":
                    c, s = np.cos(angle / 2), np.sin(angle / 2)
                    gate[:, 0, 0], gate[:, 0, 1], gate[:, 1, 0], gate[:, 1, 1] = c, -s, s, c
                else:
                    gate[:, 0, 0], gate[:, 1, 1] = np.exp(-0.5j * angle), np.exp(0.5j * angle)
                a, b = (gate, identity) if q == 0 else (identity, gate)
                operator = np.einsum("nab,ncd->nacbd", a, b).reshape(-1, 4, 4)
                state = np.einsum("nij,nj->ni", operator, state)
        state = state @ cnot.T
    p = np.abs(state) ** 2
    return p / p.sum(axis=1, keepdims=True)


def independent_model(family, depth, controls):
    if family in controls:
        return controls[family].probabilities
    if family == "quantum":
        return lambda x, p: literal_born(x, p, depth)
    if family == "softmax":

        def probability(x, p):
            features = np.column_stack([x[:, 0], x[:, 3], np.ones(len(x))])
            return softmax(np.column_stack([features @ p.reshape(3, 3), np.zeros(len(x))]), axis=1)

        return probability

    def probability(x, p):
        inputs = x[:, [0, 3]]
        hidden = np.tanh(inputs @ p[:6].reshape(2, 3) + p[6:9])
        logits = hidden @ p[9:18].reshape(3, 3) + p[18:21] + inputs[:, :1] * p[21:24]
        return softmax(np.column_stack([logits, np.zeros(len(x))]), axis=1)

    return probability


def independent_moments(y):
    return np.array([np.corrcoef(y[:-k], y[k:])[0, 1] for k in (1, 7, 30)] + [np.std(np.diff(y))])


def independent_rollout(probability, p, data, days, paths, seed, burn):
    rng = np.random.default_rng(seed)
    steps = days + burn
    uniform, within = rng.random((steps, paths)), rng.random((steps, paths))
    normal = rng.normal(size=(steps, paths))
    end = data.target_rows[data.train.stop - 1] + 1
    y = np.empty((paths, 30 + steps))
    r = np.empty_like(y)
    y[:, :30] = np.log(data.daily.rv[end - 30 : end])
    r[:, :30] = data.daily.returns[end - 30 : end]
    levels = np.empty((paths, steps), int)
    for step in range(steps):
        t = 30 + step
        features = np.column_stack(
            [y[:, t - 1], y[:, t - 7 : t].mean(axis=1), y[:, t - 30 : t].mean(axis=1), r[:, t - 1]]
        )
        x = (features - data.scaler.mean) / data.scaler.scale
        cumulative = np.cumsum(probability(x, p), axis=1)
        k = np.minimum((uniform[step, :, None] >= cumulative).sum(axis=1), 3)
        levels[:, step] = k
        for path in range(paths):
            pool = data.bins.pools[k[path]]
            index = min(int(within[step, path] * len(pool)), len(pool) - 1)
            y[path, t] = pool[index]
        r[:, t] = np.exp(y[:, t] / 2) * normal[step]
    return y[:, 30 + burn :], r[:, 30 + burn :], levels[:, burn:]


def check_moments(summary, paths, reference, scales):
    vectors = np.array([independent_moments(y) for y in paths])
    distances = np.sum(((vectors - reference) / scales) ** 2, axis=1)
    np.testing.assert_allclose(summary["mean_moments"], vectors.mean(axis=0), atol=1e-11)
    np.testing.assert_allclose(
        summary["distance_of_mean"],
        np.sum(((vectors.mean(axis=0) - reference) / scales) ** 2),
        atol=1e-9,
    )
    np.testing.assert_allclose(summary["mean_path_distance"], distances.mean(), atol=1e-9)
    assert summary["finite_paths"] == int(np.isfinite(distances).sum())
    if len(paths) > 1:
        np.testing.assert_allclose(summary["path_distance_sd"], distances.std(ddof=1), atol=1e-9)


def verify(root, author_data):
    root = Path(root)
    read = lambda name: json.loads((root / name).read_text())
    manifest = read("manifest.json")
    records = read("records.json")
    decision = read("decision.json")
    assert manifest["status"] == "complete" and manifest["test_scored"] is False
    assert manifest["code"]["package_source_sha256"] == code_revision()["package_source_sha256"]
    assert manifest["source"]["sha256"] == {
        name: sha256(Path(author_data) / name) for name in ("data-rstand", "data-ystand")
    }
    data = prepare(load_author_data(author_data))
    assert manifest["data"] == data.metadata()
    c = manifest["config"]
    scales = np.array(manifest["moment_scales"])
    train_ref, valid_ref = (
        independent_moments(data.y[data.train]),
        independent_moments(data.y[data.validation]),
    )
    np.testing.assert_allclose(manifest["train_moments"], train_ref)
    np.testing.assert_allclose(manifest["validation_moments"], valid_ref)
    width = min(128, max(40, len(data.y[data.train]) // 3))
    starts = np.unique(np.linspace(0, len(data.y[data.train]) - width, 12).astype(int))
    expected = np.maximum(
        np.std([independent_moments(data.y[data.train][s : s + width]) for s in starts], axis=0),
        0.02,
    )
    np.testing.assert_allclose(scales, expected)
    controls = {
        "frequency": FrequencyModel.fit(data.labels[data.train]),
        "short-ar": ShortAR.fit(data.x[data.train], data.y[data.train], data.bins.edges),
        "har-reference": HARModel.fit(data.x[data.train], data.y[data.train], data.bins.edges),
    }
    assert (
        len(records)
        == manifest["record_count"]
        == (len(c["depths"]) + 2) * len(c["starts"])
        + 3 * (len(c["lambdas"]) - 1) * c["realism_starts"]
        + 3
    )
    assert len({r["id"] for r in records}) == len(records)
    probability_rows = rollout_days = 0
    max_error = 0.0
    for row in records:
        p = np.array(row["fit"]["parameters"]) if "fit" in row else None
        probability = independent_model(row["family"], row["depth"], controls)
        with np.load(root / f"{row['id']}.npz", allow_pickle=False) as saved:
            assert not any("test" in k for k in saved.files)
            for split in ("train", "validation"):
                actual = probability(data.x[getattr(data, split)], p)
                error = np.max(np.abs(actual - saved[f"{split}_probabilities"]))
                assert error < 1e-11
                max_error = max(max_error, float(error))
                probability_rows += len(actual)
            if p is not None:
                np.testing.assert_array_equal(p, saved["parameters"])
            else:
                assert saved["parameters"].size == 0
            valid_p = saved["validation_probabilities"]
            labels = data.labels[data.validation]
            nll = float(-np.log(np.maximum(valid_p[np.arange(len(labels)), labels], 1e-12)).mean())
            rps = float(
                np.mean((valid_p.cumsum(axis=1)[:, :3] - (labels[:, None] <= np.arange(3))) ** 2)
            )
            np.testing.assert_allclose(row["validation"]["log_loss"], nll)
            np.testing.assert_allclose(row["validation"]["rps_normalized"], rps)
            np.testing.assert_allclose(
                row["validation"]["extreme_brier"], np.mean((valid_p[:, 3] - (labels == 3)) ** 2)
            )
            groups = np.minimum((valid_p[:, 3] * 10).astype(int), 9)
            for j, bin_ in enumerate(row["validation"]["extreme_calibration"]):
                mask = groups == j
                assert bin_["count"] == int(mask.sum())
                if mask.any():
                    np.testing.assert_allclose(bin_["mean_probability"], valid_p[mask, 3].mean())
                    np.testing.assert_allclose(
                        bin_["observed_frequency"], (labels[mask] == 3).mean()
                    )
            simulation = independent_rollout(
                probability, p, data, c["selection_days"], c["selection_paths"], 20000, c["burn_in"]
            )
            for key, actual in zip(
                ("selection_log_rv", "selection_returns", "selection_levels"),
                simulation,
                strict=True,
            ):
                np.testing.assert_array_equal(saved[key], actual)
            rollout_days += simulation[0].size
            check_moments(row["selection_paths"], simulation[0], valid_ref, scales)
            np.testing.assert_allclose(
                row["selection_score"],
                nll + c["selection_weight"] * row["selection_paths"]["distance_of_mean"],
            )
        if "fit" in row:
            fit = row["fit"]
            train_p = probability(data.x[data.train], p)
            train_nll = -np.log(
                np.maximum(train_p[np.arange(len(train_p)), data.labels[data.train]], 1e-12)
            ).mean()
            assert fit["optimized_parameter_count"] == len(p)
            assert len(fit["objective_history"]) == fit["total_objective_calls"]
            if row["stage"] == "D":
                np.testing.assert_allclose(fit["objective"], train_nll, atol=1e-10)
                model = distribution_model(row["family"], row["depth"])

                def loss(theta, model=model):
                    pp = model.probabilities(data.x[data.train], theta)
                    return -np.log(
                        np.maximum(pp[np.arange(len(pp)), data.labels[data.train]], 1e-12)
                    ).mean()

                gradient = max(
                    abs((loss(p + d) - loss(p - d)) / 2e-5) for d in np.eye(len(p)) * 1e-5
                )
                np.testing.assert_allclose(fit["gradient_inf"], gradient, atol=1e-10)
                assert fit["eligible"] == bool(
                    fit["success"] and gradient <= c["gradient_tolerance"]
                )
                np.testing.assert_array_equal(
                    fit["initial_parameters"],
                    np.random.default_rng(row["start"]).normal(0, 0.3, len(p)),
                )
            else:
                assert fit["evaluations"] <= c["realism_max_calls"]
                base = next(r for r in records if r["id"] == fit["warm_start_id"])
                initial = np.array(base["fit"]["parameters"])
                if row["start"]:
                    initial += np.random.default_rng(row["start"]).normal(0, 0.03, len(p))
                np.testing.assert_array_equal(initial, fit["initial_parameters"])
                generated = independent_rollout(
                    probability, p, data, c["train_days"], c["train_paths"], 10000, c["burn_in"]
                )[0]
                vector = np.mean([independent_moments(y) for y in generated], axis=0)
                objective = train_nll + row["lambda"] * np.sum(((vector - train_ref) / scales) ** 2)
                np.testing.assert_allclose(fit["objective"], objective, atol=1e-8)
                assert fit["objective"] <= fit["initial_objective"] + 1e-10
                rollout_days += generated.size
    # Rebuild both selection stages without importing the study's selector.
    expected = {}
    by_id = {r["id"]: r for r in records}
    for family in ("quantum", "softmax", "network"):
        forecasts = [r for r in records if r["family"] == family and r["stage"] == "D"]
        winners = [
            min(
                [r for r in forecasts if r["depth"] == d],
                key=lambda r: (r["fit"]["objective"], r["start"]),
            )
            for d in sorted({r["depth"] for r in forecasts})
        ]
        forecast = min(winners, key=lambda r: (r["validation"]["log_loss"], r["depth"]))
        lambdas = [forecast]
        for weight in c["lambdas"]:
            if weight:
                group = [
                    r
                    for r in records
                    if r["family"] == family and r["stage"] == "A" and r["lambda"] == weight
                ]
                winner = min(group, key=lambda r: (r["fit"]["objective"], r["start"]))
                assert winner["depth"] == forecast["depth"]
                lambdas.append(winner)
        selected = min(lambdas, key=lambda r: (r["selection_score"], r["lambda"]))
        expected[family] = {
            "forecast_id": forecast["id"],
            "selected_id": selected["id"],
            "depth": forecast["depth"],
            "lambda": selected["lambda"],
            "depth_winners": [r["id"] for r in winners],
            "lambda_winners": [r["id"] for r in lambdas],
            "forecast_training_adequate": all(r["fit"]["eligible"] for r in winners),
        }
    assert expected == decision
    frozen = read("forecast-selection.json")
    for family in expected:
        for key in ("forecast_id", "depth", "depth_winners", "forecast_training_adequate"):
            assert frozen[family][key] == expected[family][key]
    audit = read("audit.json")
    expected_ids = set(controls)
    for d in expected.values():
        expected_ids.update(d["lambda_winners"])
    assert {(r["id"], r["seed"]) for r in audit} == {
        (i, s) for i in expected_ids for s in (30000, 40000)
    }
    assert len(audit) == len(expected_ids) * 2
    for summary in audit:
        row = by_id[summary["id"]]
        p = np.array(row["fit"]["parameters"]) if "fit" in row else None
        probability = independent_model(row["family"], row["depth"], controls)
        paths = independent_rollout(
            probability, p, data, c["audit_days"], c["audit_paths"], summary["seed"], c["burn_in"]
        )
        with np.load(
            root / f"audit-{row['id']}-{summary['seed']}.npz", allow_pickle=False
        ) as saved:
            for key, actual in zip(("log_rv", "returns", "levels"), paths, strict=True):
                np.testing.assert_array_equal(saved[key], actual)
        check_moments(summary, paths[0], valid_ref, scales)
        rollout_days += paths[0].size
    for key, fit_key in [
        ("objective_calls", "total_objective_calls"),
        ("diagnostic_calls", "diagnostic_calls"),
        ("fit_seconds", "seconds"),
    ]:
        np.testing.assert_allclose(
            manifest[key], sum(r["fit"][fit_key] for r in records if "fit" in r)
        )
    result = {
        "verified": True,
        "records": len(records),
        "probability_rows": probability_rows,
        "max_probability_error": max_error,
        "recursive_output_days": rollout_days,
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
