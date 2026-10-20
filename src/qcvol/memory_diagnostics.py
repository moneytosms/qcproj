"""Training/validation investigation of B-only fits; never score or select on test targets."""

import platform
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import numpy as np

from .experiment import code_revision, write_json
from .quantum import MemoryCircuit, ry, rz
from .training import PointScaling, fit_point, point_initialization, point_prediction


@dataclass
class MemoryInvestigationConfig:
    seeds: list[int] = field(default_factory=lambda: [0, 1, 2])
    budgets: list[int] = field(default_factory=lambda: [40, 500, 3000])
    layers: list[int] = field(default_factory=lambda: [1, 3])
    convergence_budget: int = 12000

    def __post_init__(self):
        for values in (self.seeds, self.budgets, self.layers):
            if (
                not values
                or len(set(values)) != len(values)
                or any(type(v) is not int for v in values)
            ):
                raise ValueError("Need nonempty distinct integer configuration lists")
        if min(self.seeds) < 0 or any(v not in (1, 2, 3, 4) for v in self.layers):
            raise ValueError("Invalid seed or memory circuit depth")
        if min(self.budgets) < max(6 * max(self.layers) + 2, 5):
            raise ValueError("Budget must cover the largest circuit simplex")
        if type(self.convergence_budget) is not int or self.convergence_budget < max(self.budgets):
            raise ValueError("Convergence budget must be at least the largest grid budget")


def circuit_audit(data, layers):
    """Independent literal matrices, inactive phase, and raw-RV target alignment."""
    x = data.x[data.train][:32]
    errors, phase_errors = {}, {}
    for depth in layers:
        p = np.random.default_rng(773 + depth).normal(size=6 * depth)
        expected = []
        for row in x:
            state = np.array([1, 0], complex)
            for w in p.reshape(depth, 6):
                for j in range(4):
                    gate = ry(w[j] * row[j]) if j % 2 == 0 else rz(w[j] * row[j])
                    state = gate @ state
                state = rz(w[5]) @ ry(w[4]) @ state
            expected.append(abs(state[0]) ** 2)
        model = MemoryCircuit(depth)
        actual = model.predict(x, p)
        errors[str(depth)] = float(np.max(np.abs(actual - expected)))
        changed = p.copy()
        changed[-1] += 2.47
        phase_errors[str(depth)] = float(np.max(np.abs(actual - model.predict(x, changed))))
    targets = data.daily.rv[data.target_rows[data.train]]
    scaling = PointScaling.fit(data)
    normalized = targets / scaling.rv_scale
    return {
        "matrix_max_errors": errors,
        "terminal_rz_max_errors": phase_errors,
        "target_is_raw_rv_not_log_rv_max_error": float(
            np.max(np.abs(np.exp(data.y[data.train]) - targets))
        ),
        "point_scaling": asdict(scaling),
        "training_target_rv": {
            "min": float(targets.min()),
            "mean": float(targets.mean()),
            "median": float(np.median(targets)),
            "max": float(targets.max()),
        },
        "normalized_targets_outside_readout": int(((normalized < 0) | (normalized > 1)).sum()),
        "warning": "Author preprocessing may use full-sample information; raw financial units remain unknown",
    }


def _score(data, prediction, split):
    actual = data.daily.rv[data.target_rows[getattr(data, split)]]
    return float(np.mean((prediction - actual) ** 2))


def _candidates(config):
    for budget in config.budgets:
        for seed in config.seeds:
            yield "budget", "paper", 1, "legacy", False, budget, seed
            for depth in config.layers:
                for kind in ("memory_b", "memory_short"):
                    for initialization in ("legacy", "rv_prior"):
                        yield "budget", kind, depth, initialization, False, budget, seed
    for seed in config.seeds:
        # Broad paper starts and phase-free fits are distinct from legacy smoke replay.
        yield "convergence", "paper", 1, "uniform", True, config.convergence_budget, seed
        for depth in config.layers:
            for kind in ("memory_b", "memory_short"):
                yield "convergence", kind, depth, "rv_prior", True, config.convergence_budget, seed
        # Same budget/initial values as the grid: isolate inactive-coordinate removal.
        for kind in ("memory_b", "memory_short"):
            yield (
                "phase_control",
                kind,
                max(config.layers),
                "rv_prior",
                True,
                max(config.budgets[:2]),
                seed,
            )


def summarize(records):
    grouped = {}
    for r in records:
        key = (
            r["phase"],
            r["kind"],
            r["layers"],
            r["initialization"],
            r["reduce_inactive"],
            r["budget"],
        )
        grouped.setdefault(key, []).append(r)
    summaries = []
    for group in grouped.values():
        best = min(group, key=lambda r: r["train_mse_rv"])
        row = {
            k: best[k]
            for k in ("phase", "kind", "layers", "initialization", "reduce_inactive", "budget")
        }
        row.update(
            {
                "starts": len(group),
                "converged_starts": sum(r["fit"]["success"] for r in group),
                "total_objective_calls": sum(r["fit"]["total_objective_calls"] for r in group),
                "total_seconds": sum(r["fit"]["seconds"] for r in group),
                "train_selected_seed": best["seed"],
                "train_selected_id": best["id"],
                "train_selected_mse_rv": best["train_mse_rv"],
                "validation_mse_rv": best["validation_mse_rv"],
                "validation_mean_all_starts": float(
                    np.mean([r["validation_mse_rv"] for r in group])
                ),
                "validation_sd_all_starts": float(
                    np.std([r["validation_mse_rv"] for r in group], ddof=1)
                )
                if len(group) > 1
                else None,
            }
        )
        summaries.append(row)
    return summaries


def run_investigation(data, config, output, source=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    audit = circuit_audit(data, config.layers)
    if (
        max(audit["matrix_max_errors"].values()) > 1e-12
        or max(audit["terminal_rz_max_errors"].values()) > 1e-12
    ):
        raise ValueError("Independent memory circuit audit failed")
    if audit["normalized_targets_outside_readout"]:
        raise ValueError("Training RV targets exceed the circuit readout range")
    # No test target values or scores are serialized. metadata contains only test row IDs/counts.
    manifest = {
        "created_utc": datetime.now(UTC).isoformat(),
        "config": asdict(config),
        "data": data.metadata(),
        "source": source,
        "code": code_revision(),
        "versions": {
            "python": platform.python_version(),
            **{name: version(name) for name in ("qcvol", "numpy", "scipy")},
        },
        "audit": audit,
        "protocol": "Fresh deterministic starts for each budget. Choose restart by training MSE; compare group winners on validation only. Test scores are not computed.",
        "initialization": "legacy=N(0,.3); rv_prior=data weights N(0,.05), other angles zero, final RY=2 arccos sqrt(training normalized mean RV); uniform=U(-pi,pi)",
        "parameter_notes": "6L stored memory angles; at most 6L-1 active. Short-memory repeats standardized yesterday RV in day/week/month gate slots. Same nominal ansatz does not prove equal effective capacity. Phase-free paper fits optimize 2 angles.",
        "status": "running",
    }
    write_json(output / "manifest.json", manifest)
    mean = float(np.mean(data.daily.rv[data.target_rows[data.train]]))
    controls = {}
    for split in ("train", "validation"):
        rows = data.target_rows[getattr(data, split)]
        controls[split] = {
            "training_mean_mse_rv": _score(data, np.full(len(rows), mean), split),
            "persistence_mse_rv": _score(data, data.daily.rv[rows - 1], split),
        }
    write_json(output / "controls.json", controls)
    scaling = PointScaling.fit(data)
    records = []
    for phase, kind, depth, initialization, reduced, budget, seed in _candidates(config):
        name = f"{phase}-{kind}-L{depth}-{initialization}-reduced{int(reduced)}-b{budget}-s{seed}"
        initial = point_initialization(kind, data, scaling, seed, depth, initialization)
        initial_pred = point_prediction(kind, initial, data, data.target_rows[data.train], scaling)
        fit, scaling = fit_point(
            kind,
            data,
            seed=seed,
            layers=depth,
            max_evaluations=budget,
            initialization=initialization,
            reduce_inactive=reduced,
        )
        row = {
            "id": name,
            "phase": phase,
            "kind": kind,
            "layers": depth,
            "initialization": initialization,
            "reduce_inactive": reduced,
            "budget": budget,
            "seed": seed,
            "initial_mean_rv_prediction": float(initial_pred.mean()),
            "fit": fit.record(),
        }
        arrays = {
            "parameters": fit.parameters,
            "objective_history": np.array(fit.objective_history),
        }
        for split in ("train", "validation"):
            rows = data.target_rows[getattr(data, split)]
            pred = point_prediction(kind, fit.parameters, data, rows, scaling)
            row[f"{split}_mse_rv"] = _score(data, pred, split)
            arrays[f"{split}_target_rows"] = rows
            arrays[f"{split}_predicted_rv"] = pred
            arrays[f"{split}_actual_rv"] = data.daily.rv[rows]
        records.append(row)
        np.savez_compressed(output / f"{name}.npz", **arrays)
        write_json(output / "records.json", records)
        print(
            f"{name} train={row['train_mse_rv']:.7f} validation={row['validation_mse_rv']:.7f} nfev={fit.evaluations} converged={fit.success}",
            flush=True,
        )
    summary = summarize(records)
    write_json(output / "summary.json", summary)
    # Selection is for future study design. All validation comparisons remain exploratory.
    selected = min(summary, key=lambda r: r["validation_mse_rv"])
    write_json(
        output / "selection.json",
        {
            "group": selected,
            "scope": "Exploratory training/validation selection; no independent test claim",
            "all_search_objective_calls": sum(r["fit"]["total_objective_calls"] for r in records),
            "all_fit_seconds": sum(r["fit"]["seconds"] for r in records),
        },
    )
    manifest["status"] = "complete"
    manifest["fits"] = len(records)
    write_json(output / "manifest.json", manifest)
    return summary
