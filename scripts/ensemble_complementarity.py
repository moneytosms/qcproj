#!/usr/bin/env python3
"""Audit and fit the fixed, matched-capacity validation ensemble follow-up."""

import argparse
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from verify_calendar_study import dense_probabilities, independent_inputs

from qcvol import calendar_study as cs
from qcvol.calendar_models import CalendarReadout
from qcvol.data import load_daily_csv, sha256
from qcvol.experiment import write_json
from qcvol.fresh_study import prepare_dates

MEMBERS = {
    "linear": ("linear", 0),
    "tanh": ("tanh", 3),
    "sine": ("sine", 3),
    "tanh-small": ("tanh", 2),
    "sine-small": ("sine", 2),
    "quantum": ("quantum", 2),
    "quantum-shared": ("quantum-shared", 2),
}
GROUPS = {
    "base": ["linear", "tanh", "sine"],
    "classical": ["linear", "tanh", "sine", "tanh-small", "sine-small"],
    "quantum": ["linear", "tanh", "sine", "quantum", "quantum-shared"],
}
# Treat differences below optimizer accuracy as ties, never as research improvements.
NUMERICAL_TIE = 1e-7


def label_probabilities(probabilities, labels):
    """Input shape members x dates x classes; return dates x members."""
    p, y = np.asarray(probabilities, float), np.asarray(labels)
    if (
        p.ndim != 3
        or y.shape != (p.shape[1],)
        or not np.issubdtype(y.dtype, np.integer)
        or np.any(y < 0)
        or np.any(y >= p.shape[2])
        or not np.all(np.isfinite(p))
        or np.any(p <= 0)
        or not np.allclose(p.sum(axis=2), 1, atol=1e-10, rtol=0)
    ):
        raise ValueError("Expected strictly positive normalized probabilities and class labels")
    return p[:, np.arange(len(y)), y].T


def fit_weights(probabilities, labels):
    q = label_probabilities(probabilities, labels)

    def objective(w):
        values = q @ w
        return -np.log(values).mean(), -(q / values[:, None]).mean(axis=0)

    result = minimize(
        objective,
        np.full(q.shape[1], 1 / q.shape[1]),
        jac=True,
        method="SLSQP",
        bounds=[(0, 1)] * q.shape[1],
        constraints={"type": "eq", "fun": lambda w: w.sum() - 1, "jac": np.ones_like},
        options={"ftol": 1e-13, "maxiter": 10000},
    )
    w = np.maximum(result.x, 0)
    w /= w.sum()
    loss, gradient = objective(w)
    # At the simplex optimum, active partial derivatives equal -1; inactive >= -1.
    residual = max(
        float(np.max(np.abs(gradient[w > 1e-8] + 1))),
        float(np.max(np.maximum(-1 - gradient, 0))),
    )
    if not result.success or residual > 1e-5:
        raise ValueError(f"Mixture failed stationarity: {result.message}, KKT={residual}")
    return {
        "weights": w.tolist(),
        "nll": float(loss),
        "kkt_residual": residual,
        "iterations": int(result.nit),
    }


def mixture_nll(probabilities, labels, weights):
    q = label_probabilities(probabilities, labels)
    w = np.asarray(weights)
    if w.shape != (q.shape[1],) or np.any(w < 0) or not np.isclose(w.sum(), 1):
        raise ValueError("Weights must lie on the simplex")
    return float(-np.log(q @ w).mean())


def develop(data, source, output):
    source, output = Path(source), Path(output)
    cfg = cs.check_context(data, source)
    selection, records = cs.read(source / "selection.json"), cs.read(source / "development.json")
    if sha256(source / "development.json") != selection["development_sha256"]:
        raise ValueError("Development records changed")
    policy = selection["policy"]
    if not policy["calendar"] or policy["half_life"] != 730 or policy["ridge"] != 0:
        raise ValueError("This protocol requires the declared calendar development policy")
    if cfg.development_seeds != [910, 911]:
        raise ValueError("Unexpected development seeds")
    probabilities, counts, fits, max_error = {}, {}, {}, 0.0
    x = independent_inputs(data, True)[data.validation]
    for name, (kind, depth) in MEMBERS.items():
        if kind == "linear":
            model = CalendarReadout(calendar=True)
            rows = [{"model": vars(model), "fit": policy["fit"]}]
        else:
            rows = [
                records["nonlinear"][f"{kind}-depth{depth}-ridge0.001-seed{seed}"]
                for seed in cfg.development_seeds
            ]
        ps = []
        for row in rows:
            if not row["fit"]["eligible"]:
                raise ValueError(f"Ineligible member: {name}")
            model = CalendarReadout(**row["model"])
            p = model.probabilities(x, row["fit"]["parameters"])
            independent = dense_probabilities(row["model"], x, row["fit"]["parameters"])
            max_error = max(max_error, float(np.max(np.abs(p - independent))))
            np.testing.assert_allclose(p, independent, atol=1e-12, rtol=0)
            ps.append(independent)
        probabilities[name] = np.mean(ps, axis=0)
        counts[name] = model.n_params
        fits[name] = {
            "model": rows[0]["model"],
            "feature_ridge": 0 if kind == "linear" else 0.001,
        }
    labels = data.labels[data.validation]
    years = data.daily.index[data.target_rows][data.validation].astype("datetime64[Y]").astype(str)
    if set(years) != {"2023", "2024"}:
        raise ValueError("Expected the declared 2023–2024 validation dates")
    result = {}
    for name, members in GROUPS.items():
        p = np.asarray([probabilities[k] for k in members])
        pooled = fit_weights(p, labels)
        early = fit_weights(p[:, years == "2023"], labels[years == "2023"])
        late = mixture_nll(p[:, years == "2024"], labels[years == "2024"], early["weights"])
        result[name] = {
            "members": members,
            "member_parameters": sum(counts[k] for k in members),
            "weight_degrees_of_freedom": len(members) - 1,
            "pooled": pooled,
            "weights_fit_2023": early,
            "nll_2024_with_2023_weights": late,
        }
    if result["quantum"]["member_parameters"] != result["classical"]["member_parameters"]:
        raise ValueError("Model parameter counts differ")
    pooled_delta = result["quantum"]["pooled"]["nll"] - result["classical"]["pooled"]["nll"]
    chronological_delta = (
        result["quantum"]["nll_2024_with_2023_weights"]
        - result["classical"]["nll_2024_with_2023_weights"]
    )
    pooled_gain = pooled_delta < -NUMERICAL_TIE
    chronological_gain = chronological_delta < -NUMERICAL_TIE
    report = {
        "stage": "post-hoc validation only",
        "source_artifacts": {
            name: sha256(source / name)
            for name in ("manifest.json", "development.json", "selection.json")
        },
        "script_sha256": sha256(Path(__file__)),
        "protocol_sha256": sha256(Path(__file__).resolve().parents[1] / "doc/ensemble-protocol.md"),
        "members": fits,
        "counts": counts,
        "single_model_nll": {
            k: mixture_nll(v[None], labels, [1.0]) for k, v in probabilities.items()
        },
        "ensembles": result,
        "max_independent_probability_error": max_error,
        "gate": {
            "numerical_tie_tolerance": NUMERICAL_TIE,
            "pooled_quantum_minus_classical": pooled_delta,
            "chronological_quantum_minus_classical": chronological_delta,
            "pooled_improves": pooled_gain,
            "chronological_improves": chronological_gain,
            "proceed_to_final_seeds": pooled_gain and chronological_gain,
        },
    }
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "development.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data/bitstamp_daily.csv"))
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = develop(prepare_dates(load_daily_csv(args.data)), args.source, args.output)
    for name, row in report["ensembles"].items():
        print(name, row["pooled"]["nll"], row["nll_2024_with_2023_weights"])
    print(report["gate"])


if __name__ == "__main__":
    main()
