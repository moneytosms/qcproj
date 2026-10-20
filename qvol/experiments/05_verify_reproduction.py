"""Verify saved arrays, all rolling unshuffled estimates and protocol dimensions."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qvol.multifractal import analyze_batch, rolling_starts  # noqa: E402
from qvol.reproduction import transformed_series, write_json  # noqa: E402

from qvol import paper_audit as audit  # noqa: E402


def verify(output, data_directory):
    output = Path(output)
    manifest = json.loads((output / "manifest.json").read_text())
    if manifest["status"] != "complete":
        raise ValueError("Run is incomplete, including figure export")
    loaded, _ = audit.load_verified(data_directory)
    c = manifest["config"]
    fit = json.loads((output / "fit.json").read_text())
    analysis = json.loads((output / "analysis.json").read_text())
    p = fit["parameters"]
    source_root = ROOT / "src/qvol"
    for name, expected in manifest["source_code_sha256"].items():
        actual = hashlib.sha256((source_root / name).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"Analysis code changed since run: {name}")
    if (
        fit["training_pairs"] != 912
        or not fit["restarts"][fit["best_restart"]]["success"]
    ):
        raise ValueError("Wrong training alignment or unconverged selected fit")
    rv, ret = loaded["data-ystand"], loaded["data-rstand"]
    pairs = np.load(output / "fit-arrays.npz")
    np.testing.assert_array_equal(pairs["observation_ids"], np.arange(2, 914))
    np.testing.assert_array_equal(pairs["actual"], rv[1:])
    np.testing.assert_allclose(
        pairs["predicted"], audit.predict(p, ret[:-1], rv[:-1]), atol=1e-14
    )
    np.testing.assert_allclose(
        np.mean((pairs["actual"] - pairs["predicted"]) ** 2), fit["mse"], atol=1e-14
    )
    series = {
        "empirical": (rv, ret),
        "author": (
            loaded["data-predicted-volatility"],
            loaded["data-predicted-return"],
        ),
    }
    recurrence_errors = {}
    for seed in c["generation_seeds"]:
        arrays = np.load(output / f"generated-seed{seed}.npz")
        v, r = arrays["rv"], arrays["returns"]
        assert v.shape == r.shape == (c["generated_steps"],)
        assert np.all(np.isfinite(v)) and np.all(v > 0) and np.all(np.isfinite(r))
        np.testing.assert_allclose(
            r / np.sqrt(v),
            np.random.default_rng(seed).standard_normal(len(v)),
            atol=1e-14,
        )
        expected = audit.predict(
            p, np.clip(np.r_[ret[-1], r[:-1]], -1, 1), np.r_[rv[-1], v[:-1]]
        )
        expected = np.clip(expected, 1e-12, 1 - 1e-12)
        error = float(np.max(np.abs(expected - v)))
        assert error < 1e-12
        recurrence_errors[str(seed)] = error
        series[f"rebuild_seed{seed}"] = (v, r)
    rolling_estimates = 0
    q = np.linspace(c["q_min"], c["q_max"], c["q_count"])
    for name, (v, r) in series.items():
        for feature, values in transformed_series(v, r).items():
            record = analysis[name]["series"][feature]
            window = min(c["window"], len(values))
            starts = rolling_starts(len(values), window, c["step"])
            np.testing.assert_array_equal(record["rolling"]["starts"], starts)
            windows = np.stack([values[start : start + window] for start in starts])
            own = analyze_batch(windows, scales=record["spectrum"]["scales"])
            np.testing.assert_allclose(
                own["h"][:, 0], record["rolling"]["h2"], atol=1e-11
            )
            assert np.asarray(record["rolling"]["shuffled_h2"]).shape == (
                len(starts),
                c["shuffles"],
            )
            np.testing.assert_allclose(
                np.mean(record["rolling"]["shuffled_h2"], axis=1),
                record["rolling"]["shuffled_mean"],
                atol=1e-14,
            )
            spec = record["spectrum"]
            np.testing.assert_allclose(spec["q"], q, atol=1e-14)
            assert np.asarray(spec["h"]).shape == (c["shuffles"] + 1, len(q))
            np.testing.assert_allclose(
                spec["tau"], q * np.asarray(spec["h"]) - 1, atol=1e-14
            )
            alpha = np.gradient(np.asarray(spec["tau"]), q, axis=1)
            np.testing.assert_allclose(spec["alpha"], alpha, atol=1e-12)
            np.testing.assert_allclose(
                spec["f_alpha"], q * alpha - np.asarray(spec["tau"]), atol=1e-12
            )
            rolling_estimates += len(starts)
    controls = json.loads((output / "gaussian-controls.json").read_text())
    assert np.asarray(controls["h"]).shape == (c["gaussian_controls"], c["q_count"])
    assert len(manifest["figures"]) == 7
    for name in manifest["figures"]:
        assert (output / "figures" / name).stat().st_size > 1000
    result = {
        "verified": True,
        "rolling_unshuffled_estimates_recomputed": rolling_estimates,
        "generated_steps_checked": c["generated_steps"] * len(c["generation_seeds"]),
        "max_generation_recurrence_errors": recurrence_errors,
        "spectra_and_gaussian_controls_dimensions_checked": True,
        "source_hashes_match": True,
        "scope": "Numerical artifacts and protocol integrity, not equality to every paper number",
    }
    write_json(output / "verification.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--data", type=Path, default=ROOT / "data/takaishi")
    args = parser.parse_args()
    print(json.dumps(verify(args.output, args.data), indent=2))


if __name__ == "__main__":
    main()
