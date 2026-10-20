"""Complete, separately logged full-sample reproduction of the paper's main analyses."""

import hashlib
import json
import platform
import subprocess
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import numpy as np
from scipy.stats import kurtosis

from . import metrics
from . import paper_audit as audit
from .multifractal import analyze_batch, rolling_h2, scale_grid, spectrum

DEFAULT_CONFIG = {
    "restarts": 10,
    "fit_seed": 0,
    "max_evaluations": 2000,
    "optimizer_tolerance": 1e-8,
    "generated_steps": 50_000,
    "generation_seeds": [0, 1, 2],
    "window": 913,
    "step": 365,
    "shuffles": 20,
    "shuffle_seed": 20261019,
    "q_min": -5.0,
    "q_max": 5.0,
    "q_count": 501,
    "min_scale": 20,
    "max_scale": 182,
    "scale_count": 24,
    "gaussian_controls": 200,
    "representative_window": 0,
}


def serialize(value):
    if isinstance(value, dict):
        return {str(k): serialize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serialize(v) for v in value]
    if isinstance(value, np.ndarray):
        return serialize(value.tolist())
    if isinstance(value, np.generic):
        return serialize(value.item())
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def write_json(path, value):
    Path(path).write_text(
        json.dumps(serialize(value), indent=2, allow_nan=False) + "\n"
    )


def validate_config(overrides):
    unknown = set(overrides) - set(DEFAULT_CONFIG)
    if unknown:
        raise ValueError(f"Unknown configuration keys: {sorted(unknown)}")
    c = {**DEFAULT_CONFIG, **overrides}
    integer_positive = [
        "restarts",
        "max_evaluations",
        "generated_steps",
        "window",
        "step",
        "shuffles",
        "q_count",
        "scale_count",
        "gaussian_controls",
    ]
    if any(type(c[key]) is not int or c[key] < 1 for key in integer_positive):
        raise ValueError("Counts and budgets must be positive integers")
    if not 100 <= c["window"] <= 913 or c["generated_steps"] < c["window"]:
        raise ValueError("Window must fit empirical and generated observations")
    if c["shuffles"] < 2 or c["gaussian_controls"] < 2:
        raise ValueError("Need at least two controls to report their spread")
    if not c["generation_seeds"] or len(set(c["generation_seeds"])) != len(
        c["generation_seeds"]
    ):
        raise ValueError("Need unique generation seeds")
    if any(type(s) is not int or s < 0 for s in c["generation_seeds"]):
        raise ValueError("Generation seeds must be nonnegative integers")
    if not c["q_min"] < 0 < c["q_max"] or c["q_count"] < 3:
        raise ValueError("q grid must span zero")
    if not 0 < c["optimizer_tolerance"] < 1 or c["max_evaluations"] < 5:
        raise ValueError("Invalid optimizer settings")
    scale_grid(c["window"], c["min_scale"], c["max_scale"], c["scale_count"])
    return c


def transformed_series(rv, ret, return_floor=1e-12):
    if np.any(np.asarray(rv) <= 0):
        raise ValueError("Log RV requires positive variance")
    return {
        "returns": np.asarray(ret),
        "irv": np.diff(np.log(rv)),
        "iar": np.diff(np.log(np.maximum(np.abs(ret), return_floor))),
    }


def independent_mfdfa_check(series, scales):
    from MFDFA import MFDFA

    q = np.array(
        [-5.0, -2.0, 2.0, 5.0]
    )  # package omits q=0; independently tested separately
    records = {}
    for name, values in series.items():
        lag, reference = MFDFA(values, lag=scales, q=q, order=3)
        own = analyze_batch(values, q=q, scales=scales)
        if not np.array_equal(lag, scales):
            raise ValueError("Independent implementation changed requested scales")
        error = float(np.max(np.abs(np.log(reference) - own["log_f"][0])))
        if error > 1e-9:
            raise ValueError(f"Independent MFDFA mismatch for {name}: {error}")
        records[name] = {"q": q, "max_abs_log_fluctuation_error": error}
    return {"package": "MFDFA", "version": version("MFDFA"), "series": records}


def basic_statistics(rv, ret):
    series = transformed_series(rv, ret)
    innovations = ret / np.sqrt(rv)
    return {
        "observations": len(rv),
        "mean_rv": float(np.mean(rv)),
        "std_rv": float(np.std(rv)),
        "acf_log_rv": metrics.realism_moments(np.log(rv))[:3],
        "std_diff_log_rv": float(np.std(series["irv"])),
        "hill_return_tail_index_top_5_percent": float(metrics.hill_tail_index(ret)),
        "pearson_kurtosis": {
            k: float(kurtosis(v, fisher=False, bias=True)) for k, v in series.items()
        },
        "return_over_sqrt_rv_mean": float(np.mean(innovations)),
        "return_over_sqrt_rv_std": float(np.std(innovations)),
        "zero_returns": int(np.sum(ret == 0)),
        "iar_kurtosis_defined_adjacent_pairs": float(
            kurtosis(
                series["iar"][(ret[:-1] != 0) & (ret[1:] != 0)], fisher=False, bias=True
            )
        ),
        "iar_undefined_adjacent_pair_count": int(
            np.sum((ret[:-1] == 0) | (ret[1:] == 0))
        ),
    }


def analyze_source(name, rv, ret, c, scales, q, seed):
    series = transformed_series(rv, ret)
    result = {"statistics": basic_statistics(rv, ret), "series": {}}
    for feature, x in series.items():
        print(f"    {name}: {feature}", flush=True)
        # Differencing 913 real observations gives 912 increments. Never invent an
        # extra increment. Use all 912 for that one empirical window and record it.
        window = min(c["window"], len(x))
        roll = rolling_h2(
            x,
            window=window,
            step=c["step"],
            shuffles=c["shuffles"],
            seed=seed,
            scales=scales,
        )
        rep_index = c["representative_window"]
        if not 0 <= rep_index < len(roll["starts"]):
            raise ValueError(
                "Representative window index is outside the complete rolling grid"
            )
        start = roll["starts"][rep_index]
        segment = x[start : start + window]
        rng = np.random.default_rng(seed + 1)
        representative = spectrum(
            np.vstack(
                [segment, *[rng.permutation(segment) for _ in range(c["shuffles"])]]
            ),
            q=q,
            scales=scales,
        )
        # Large fluctuation arrays remain in NPZ artifacts; summary curves remain in JSON.
        representative.pop("log_f")
        result["series"][feature] = {
            "length": len(x),
            "window": window,
            "rolling": roll,
            "representative_window_start": int(start),
            "spectrum": representative,
            "h2_mean": float(np.mean(roll["h2"])),
            "h2_std_across_overlapping_windows": float(np.std(roll["h2"], ddof=1))
            if len(roll["h2"]) > 1
            else None,
            "shuffled_h2_mean": float(np.mean(roll["shuffled_mean"])),
        }
    return result


def run(output, data_directory, overrides=None):
    c = validate_config(overrides or {})
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    loaded, provenance = audit.load_verified(data_directory)
    rv, ret = loaded["data-ystand"], loaded["data-rstand"]
    av, ar = loaded["data-predicted-volatility"], loaded["data-predicted-return"]
    package_root = Path(__file__).parent
    code_hashes = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in package_root.glob("*.py")
    }
    root = Path(__file__).resolve().parents[3]
    head = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()
    manifest = {
        "status": "running",
        "created_utc": datetime.now(UTC).isoformat(),
        "config": c,
        "source_data": provenance,
        "source_code_sha256": code_hashes,
        "git_head": head,
        "versions": {
            "python": platform.python_version(),
            **{p: version(p) for p in ("numpy", "scipy", "matplotlib", "MFDFA")},
        },
        "protocol": "full-sample descriptive reproduction, no forecasting holdout",
        "assumptions": {
            "encoding_domain": "clip only inputs, count each event",
            "variance_floor": 1e-12,
            "absolute_return_log_floor": 1e-12,
            "initial_state": "last observed return and RV",
            "burn_in": 0,
            "scale_grid": "geometric integer grid; exact grid/upper cutoff unspecified in paper",
            "empirical_increment_window": "912, from 913 observations; no fabricated increment",
            "window_std": "descriptive; overlapping windows are not independent",
        },
    }
    write_json(output / "manifest.json", manifest)
    print("Fitting full-sample circuit with multiple COBYLA starts", flush=True)
    fitted = audit.fit(
        ret,
        rv,
        restarts=c["restarts"],
        seed=c["fit_seed"],
        max_evaluations=c["max_evaluations"],
        tolerance=c["optimizer_tolerance"],
    )
    check = audit.audit_circuit(fitted["parameters"], ret, rv)
    if (
        max(
            check["vectorized_max_error"],
            check["phi_max_error"],
            check["twin_max_error"],
        )
        > 1e-12
    ):
        raise ValueError("Circuit audit failed")
    predictions = audit.predict(fitted["parameters"], ret[:-1], rv[:-1])
    fit = {
        **fitted,
        "algebra": check,
        "prediction_correlation": float(np.corrcoef(predictions, rv[1:])[0, 1]),
    }
    write_json(output / "fit.json", fit)
    if not fitted["restarts"][fitted["best_restart"]]["success"]:
        raise ValueError(
            "Best full-sample fit did not converge; inspect fit.json and increase budget"
        )
    scales = scale_grid(c["window"], c["min_scale"], c["max_scale"], c["scale_count"])
    q = np.linspace(c["q_min"], c["q_max"], c["q_count"])
    independent = independent_mfdfa_check(transformed_series(rv, ret), scales)
    write_json(output / "independent-mfdfa.json", independent)
    sources = [("empirical", rv, ret, {}), ("author", av, ar, {})]
    for seed in c["generation_seeds"]:
        print(f"Generating {c['generated_steps']} days, seed {seed}", flush=True)
        v, r, clips = audit.generate(
            fitted["parameters"], c["generated_steps"], ret[-1], rv[-1], seed=seed
        )
        np.savez_compressed(output / f"generated-seed{seed}.npz", rv=v, returns=r)
        sources.append((f"rebuild_seed{seed}", v, r, {"seed": seed, "clipping": clips}))
    np.savez_compressed(
        output / "fit-arrays.npz",
        actual=rv[1:],
        predicted=predictions,
        observation_ids=np.arange(2, len(rv) + 1),
    )
    results = {}
    for i, (name, v, r, metadata) in enumerate(sources):
        results[name] = {
            "generation": metadata,
            **analyze_source(
                name, v, r, c, scales, q, seed=c["shuffle_seed"] + i * 10000
            ),
        }
        write_json(output / "analysis.json", results)
    print(
        f"Analyzing {c['gaussian_controls']} finite-size Gaussian controls", flush=True
    )
    rng = np.random.default_rng(c["shuffle_seed"] + 999)
    controls = spectrum(
        rng.standard_normal((c["gaussian_controls"], c["window"])), q=q, scales=scales
    )
    controls.pop("log_f")
    write_json(output / "gaussian-controls.json", controls)
    # Cutoff sensitivity is reported for empirical data instead of tuning the grid to a target h(2).
    sensitivity = {}
    for minimum in (10, 20, 30):
        grid = scale_grid(912, minimum, c["max_scale"], c["scale_count"])
        sensitivity[f"min_scale_{minimum}"] = {
            k: float(analyze_batch(v, scales=grid)["h"][0, 0])
            for k, v in transformed_series(rv, ret).items()
        }
    sensitivity["iar_log_floor"] = {
        str(floor): float(
            analyze_batch(
                transformed_series(rv, ret, return_floor=floor)["iar"], scales=scales
            )["h"][0, 0]
        )
        for floor in (1e-12, 1e-8, 1e-6, 1e-4)
    }
    sensitivity["iar_kurtosis_log_floor"] = {
        str(floor): float(
            kurtosis(
                transformed_series(rv, ret, return_floor=floor)["iar"],
                fisher=False,
                bias=True,
            )
        )
        for floor in (1e-12, 1e-8, 1e-6, 1e-4)
    }
    write_json(output / "sensitivity.json", sensitivity)
    manifest["status"] = "analysis_complete"
    write_json(output / "manifest.json", manifest)
    return {
        "fit": fit,
        "analysis": results,
        "config": c,
        "gaussian_controls": controls,
        "scales": scales,
        "q": q,
        "output": output,
        "sources": sources,
        "sensitivity": sensitivity,
    }
