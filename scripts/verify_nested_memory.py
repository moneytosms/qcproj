#!/usr/bin/env python3
"""Audit all follow-up predictions with literal gates and recompute selection independently."""

import argparse
import json
from pathlib import Path

import numpy as np

from qcvol.data import load_author_data, prepare, sha256
from qcvol.experiment import code_revision
from qcvol.nested_memory import warm_initial
from qcvol.quantum import ry, rz, u3
from qcvol.training import PointScaling


def literal_prediction(data, rows, scaling, kind, p):
    result = []
    for t in rows:
        r = np.clip(data.daily.returns[t - 1] / scaling.return_scale, -1, 1)
        v = np.clip(data.daily.rv[t - 1] / scaling.rv_scale, 0, 1)
        state = np.array([1, 0], complex)
        gates = [
            ry(np.arcsin(r)),
            rz(np.arccos(r * r)),
            ry(np.arcsin(2 * v - 1)),
            rz(np.arccos(v * v)),
        ]
        if kind == "paper":
            gates.append(u3(*p))
        else:
            x = data.x[t - 30]
            a, b = (0, 0) if kind == "nested_short" else (1, 2)
            gates += [ry(p[2] * x[a]), rz(p[3] * x[b]), u3(p[0], 0, p[1])]
        for gate in gates:
            state = gate @ state
        result.append(abs(state[0]) ** 2 * scaling.rv_scale)
    return np.array(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--author-data", type=Path, required=True)
    args = parser.parse_args()
    root = args.run
    manifest = json.loads((root / "manifest.json").read_text())
    if manifest["status"] != "complete":
        raise ValueError("Follow-up is incomplete")
    assert manifest["code"]["package_source_sha256"] == code_revision()["package_source_sha256"]
    assert manifest["source"]["sha256"] == {
        name: sha256(args.author_data / name) for name in ("data-rstand", "data-ystand")
    }
    data = prepare(load_author_data(args.author_data))
    assert manifest["data"] == data.metadata()
    scaling = PointScaling.fit(data)
    config = manifest["config"]
    records = json.loads((root / "records.json").read_text())
    summary = json.loads((root / "summary.json").read_text())
    decision = json.loads((root / "decision.json").read_text())
    assert len(records) == manifest["record_count"]
    assert len({r["id"] for r in records}) == len(records)
    fits = [r for r in records if "fit" in r]
    assert (
        len(fits)
        == manifest["fit_count"]
        == len(config["seeds"]) * (1 + 2 * len(config["regularization"]))
    )
    baseline = min(
        [r for r in fits if r["kind"] == "paper"], key=lambda r: (r["fit"]["objective"], r["seed"])
    )
    assert baseline["id"] == manifest["baseline_fit_id"]
    train_rows = data.target_rows[data.train]

    # Independent unstandardized HAR OLS reference, in original RV units.
    def design(rows):
        v = data.daily.rv
        return np.array(
            [[1.0, v[t - 1], np.sum(v[t - 7 : t]) / 7, np.sum(v[t - 30 : t]) / 30] for t in rows]
        )

    beta = np.linalg.lstsq(design(train_rows), data.daily.rv[train_rows], rcond=None)[0]
    count, max_error, zero_error = 0, 0.0, 0.0
    by_id = {}
    for row in records:
        by_id[row["id"]] = row
        with np.load(root / f"{row['id']}.npz") as saved:
            assert not any("test" in key for key in saved.files)
            if "fit" in row:
                fit = row["fit"]
                params = np.array(fit["parameters"])
                np.testing.assert_array_equal(params, saved["parameters"])
                np.testing.assert_array_equal(fit["objective_history"], saved["objective_history"])
                assert (
                    len(fit["objective_history"])
                    == fit["evaluations"] + 1
                    == fit["total_objective_calls"]
                )
                assert fit["objective"] == min(fit["objective_history"])
                assert fit["evaluations"] <= config["max_evaluations"]
                assert fit["optimized_parameter_count"] == (2 if row["kind"] == "paper" else 4)
                assert row["eligible"] == bool(
                    fit["success"] and row["gradient_inf"] <= config["gradient_tolerance"]
                )

                def objective_at(parameters, row=row):
                    predicted = literal_prediction(
                        data, train_rows, scaling, row["kind"], parameters
                    )
                    residual = (predicted - data.daily.rv[train_rows]) / scaling.rv_scale
                    penalty = (
                        0
                        if row["kind"] == "paper"
                        else row["regularization"] * np.sum(parameters[2:] ** 2)
                    )
                    return float(np.mean(residual**2) + penalty)

                indices = (0, 2) if row["kind"] == "paper" else range(4)
                gradient = []
                for j in indices:
                    direction = np.eye(len(params))[j] * 1e-5
                    gradient.append(
                        (objective_at(params + direction) - objective_at(params - direction)) / 2e-5
                    )
                np.testing.assert_allclose(
                    np.max(np.abs(gradient)), row["gradient_inf"], atol=1e-8, rtol=0
                )
                if row["kind"] != "paper":
                    assert row["baseline_fit_id"] == baseline["id"]
                    initial = warm_initial(
                        baseline["fit"]["parameters"], row["seed"], config["jitter"]
                    )
                    np.testing.assert_array_equal(initial, row["initial_parameters"])
                    pred = literal_prediction(data, train_rows, scaling, row["kind"], initial)
                    initial_obj = np.mean(
                        ((pred - data.daily.rv[train_rows]) / scaling.rv_scale) ** 2
                    ) + row["regularization"] * np.sum(initial[2:] ** 2)
                    np.testing.assert_allclose(
                        initial_obj, fit["initial_objective"], atol=1e-14, rtol=0
                    )
            for split in ("train", "validation"):
                rows = data.target_rows[getattr(data, split)]
                actual = data.daily.rv[rows]
                np.testing.assert_array_equal(rows, saved[f"{split}_rows"])
                np.testing.assert_array_equal(actual, saved[f"{split}_actual_rv"])
                if "fit" in row:
                    predicted = literal_prediction(data, rows, scaling, row["kind"], params)
                elif row["kind"] == "har_rv":
                    predicted = np.maximum(design(rows) @ beta, 0)
                elif row["kind"] == "training_mean":
                    predicted = np.full(len(rows), np.mean(data.daily.rv[train_rows]))
                else:
                    assert row["kind"] == "persistence"
                    predicted = data.daily.rv[rows - 1]
                max_error = max(
                    max_error, float(np.max(np.abs(predicted - saved[f"{split}_predicted_rv"])))
                )
                count += len(rows)
                np.testing.assert_allclose(
                    predicted, saved[f"{split}_predicted_rv"], atol=1e-13, rtol=0
                )
                loss = float(np.mean((predicted - actual) ** 2))
                np.testing.assert_allclose(loss, row[f"{split}_mse_rv"], atol=1e-14, rtol=0)
                if split == "train" and "fit" in row:
                    penalty = (
                        0
                        if row["kind"] == "paper"
                        else row["regularization"] * np.sum(params[2:] ** 2)
                    )
                    np.testing.assert_allclose(
                        loss / scaling.rv_scale**2 + penalty, fit["objective"], atol=1e-14, rtol=0
                    )
            if row["kind"] == "paper":
                for split in ("train", "validation"):
                    rows = data.target_rows[getattr(data, split)]
                    old = literal_prediction(data, rows, scaling, "paper", params)
                    zero = literal_prediction(
                        data, rows, scaling, "nested_memory", warm_initial(params, 0)
                    )
                    zero_error = max(zero_error, float(np.max(np.abs(old - zero))))
    assert zero_error <= 1e-13
    for candidate in summary:
        group = [
            r
            for r in fits
            if r["kind"] == candidate["kind"] and r["regularization"] == candidate["regularization"]
        ]
        selected = min(group, key=lambda r: (r["fit"]["objective"], r["seed"]))
        assert candidate["winner"] == selected["id"]
        assert candidate["validation_mse_rv"] == selected["validation_mse_rv"]
        assert candidate["eligible"] == selected["eligible"]
        assert candidate["starts"] == len(group)
    if all(s["eligible"] for s in summary):
        paper = next(s for s in summary if s["kind"] == "paper")
        winners = {}
        for kind in ("nested_memory", "nested_short"):
            candidates = [paper] + [s for s in summary if s["kind"] == kind]
            winners[kind] = min(
                candidates,
                key=lambda s: (
                    s["validation_mse_rv"],
                    s["kind"] != "paper",
                    -(s["regularization"] or 0),
                ),
            )
        assert winners == decision["selections"]
        reference = min(paper["validation_mse_rv"], winners["nested_short"]["validation_mse_rv"])
        gain = (reference - winners["nested_memory"]["validation_mse_rv"]) / reference
        np.testing.assert_allclose(
            gain, decision["relative_gain_over_best_short_or_paper"], atol=1e-14
        )
        keep = (
            gain >= config["minimum_relative_gain"]
            and gain > 0
            and winners["nested_memory"]["kind"] == "nested_memory"
        )
        assert decision["feature_policy_for_D"] == ("HAR" if keep else "previous_day_only")
    else:
        assert decision["status"] == "inconclusive"
    assert manifest["optimizer_objective_calls"] == sum(
        r["fit"]["total_objective_calls"] for r in fits
    )
    assert manifest["stationarity_objective_calls"] == sum(
        r["stationarity_objective_calls"] for r in fits
    )
    print(
        json.dumps(
            {
                "verified": True,
                "fits": len(fits),
                "records": len(records),
                "predictions_recomputed": count,
                "literal_matrix_max_prediction_error": max_error,
                "zero_weight_identity_max_error": zero_error,
                "test_scores_computed": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
