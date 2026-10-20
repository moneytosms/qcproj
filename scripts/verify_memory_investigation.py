#!/usr/bin/env python3
"""Recompute saved point predictions and losses; check provenance and restart selection."""

import argparse
import json
from pathlib import Path

import numpy as np

from qcvol.data import load_author_data, prepare, sha256
from qcvol.experiment import code_revision
from qcvol.memory_diagnostics import summarize
from qcvol.training import PointScaling, point_prediction


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--author-data", type=Path, required=True)
    args = parser.parse_args()
    root = args.run
    manifest = json.loads((root / "manifest.json").read_text())
    if manifest["status"] != "complete":
        raise ValueError("Incomplete investigation")
    if manifest["source"]["sha256"] != {
        name: sha256(args.author_data / name) for name in ("data-rstand", "data-ystand")
    }:
        raise ValueError("Source data hashes changed")
    if manifest["code"]["package_source_sha256"] != code_revision()["package_source_sha256"]:
        raise ValueError("Package source hashes changed")
    data = prepare(load_author_data(args.author_data))
    if manifest["data"] != data.metadata():
        raise ValueError("Preparation metadata changed")
    scaling = PointScaling.fit(data)
    records = json.loads((root / "records.json").read_text())
    if len(records) != manifest["fits"] or len({r["id"] for r in records}) != len(records):
        raise ValueError("Incorrect record count or duplicate fit IDs")
    max_error = 0.0
    checked_values = 0
    for record in records:
        with np.load(root / f"{record['id']}.npz") as arrays:
            fit = record["fit"]
            params = np.asarray(fit["parameters"])
            np.testing.assert_array_equal(params, arrays["parameters"])
            np.testing.assert_array_equal(fit["objective_history"], arrays["objective_history"])
            assert (
                len(fit["objective_history"])
                == fit["total_objective_calls"]
                == fit["evaluations"] + 1
            )
            assert fit["objective"] == min(fit["objective_history"])
            assert fit["evaluations"] <= record["budget"]
            inactive = 1 if record["kind"] == "paper" else -1
            if record["reduce_inactive"]:
                assert params[inactive] == 0
            assert fit["optimized_parameter_count"] == len(params) - int(record["reduce_inactive"])
            for split in ("train", "validation"):
                rows = data.target_rows[getattr(data, split)]
                np.testing.assert_array_equal(rows, arrays[f"{split}_target_rows"])
                actual = data.daily.rv[rows]
                np.testing.assert_array_equal(actual, arrays[f"{split}_actual_rv"])
                predicted = point_prediction(record["kind"], params, data, rows, scaling)
                error = float(np.max(np.abs(predicted - arrays[f"{split}_predicted_rv"])))
                max_error = max(max_error, error)
                checked_values += len(rows)
                np.testing.assert_allclose(
                    predicted, arrays[f"{split}_predicted_rv"], atol=1e-14, rtol=0
                )
                np.testing.assert_allclose(
                    np.mean((predicted - actual) ** 2),
                    record[f"{split}_mse_rv"],
                    atol=1e-14,
                    rtol=0,
                )
                if split == "train":
                    np.testing.assert_allclose(
                        record["train_mse_rv"] / scaling.rv_scale**2,
                        fit["objective"],
                        atol=1e-14,
                        rtol=0,
                    )
            assert not any(k.startswith("test_") for k in arrays.files)
    assert summarize(records) == json.loads((root / "summary.json").read_text())
    selected = json.loads((root / "selection.json").read_text())
    assert selected["group"] == min(summarize(records), key=lambda r: r["validation_mse_rv"])
    print(
        json.dumps(
            {
                "verified": True,
                "fits": len(records),
                "predictions_recomputed": checked_values,
                "max_prediction_error": max_error,
                "test_scores_computed": False,
                "scope": "Numerical artifact integrity; validation remains exploratory",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
