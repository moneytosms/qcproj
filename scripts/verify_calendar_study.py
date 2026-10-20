#!/usr/bin/env python3
"""Independent dense-gate replay of calendar/readout development and final fits."""

import argparse
import hashlib
import importlib.util
from pathlib import Path

import numpy as np

from qcvol import calendar_study as cs
from qcvol.calendar_models import CalendarReadout
from qcvol.data import load_daily_csv
from qcvol.experiment import write_json
from qcvol.final_study import restore_baseline
from qcvol.fresh_models import make_model
from qcvol.fresh_study import prepare_dates
from qcvol.metrics import forecast_scores


def independent_inputs(data, calendar):
    dates = data.daily.index[data.target_rows].astype("datetime64[D]")
    day = (dates.astype(int) + 3) % 7
    return np.column_stack([data.x, np.eye(7)[day, 1:]]) if calendar else data.x.copy()


def dense_probabilities(spec, x, parameters):
    """Build explicit 4x4 gates; no forward-sensitivity/model probability code used."""
    x, p = np.asarray(x), np.asarray(parameters)
    count = 3 * (x.shape[1] + 1)
    logits = np.c_[x, np.ones(len(x))] @ p[:count].reshape(-1, 3)
    kind, size = spec["kind"], spec["size"]
    a = np.arctan(x[:, :4])
    if kind.startswith("quantum"):
        active = [i for i in range(8 * size) if i not in (8 * size - 3, 8 * size - 1)]
        angles = np.zeros(8 * size)
        angles[active] = p[count : count + len(active)]
        extra = (
            p[count + len(active) : count + len(active) + size]
            if kind == "quantum-shared"
            else np.zeros(size)
        )
        stop = count + len(active) + (size if kind == "quantum-shared" else 0)
        state = np.zeros((len(x), 4), complex)
        state[:, 0] = 1
        identity = np.eye(2)
        cnot = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]])
        for layer, w in enumerate(angles.reshape(size, 8)):
            for q in (0, 1):
                sequence = [
                    ("y", w[2 * q] * a[:, 2 * q]),
                    ("z", w[2 * q + 1] * a[:, 2 * q + 1]),
                    ("y", np.full(len(x), w[4 + 2 * q]) + (extra[layer] * a[:, 0] if q else 0)),
                    ("z", np.full(len(x), w[5 + 2 * q])),
                ]
                for axis, angle in sequence:
                    gate = np.zeros((len(x), 2, 2), complex)
                    if axis == "y":
                        c, s = np.cos(angle / 2), np.sin(angle / 2)
                        gate[:, 0, 0] = gate[:, 1, 1] = c
                        gate[:, 0, 1], gate[:, 1, 0] = -s, s
                    else:
                        gate[:, 0, 0], gate[:, 1, 1] = np.exp(-0.5j * angle), np.exp(0.5j * angle)
                    full = (
                        np.einsum("nab,cd->nacbd", gate, identity)
                        if q == 0
                        else np.einsum("ab,ncd->nacbd", identity, gate)
                    ).reshape(len(x), 4, 4)
                    state = np.einsum("nij,nj->ni", full, state)
            state = state @ cnot.T
        probabilities = np.abs(state) ** 2
        probabilities /= probabilities.sum(axis=1, keepdims=True)
        features = probabilities[:, :3] - 0.25
        logits += features @ p[stop:].reshape(3, 3)
    elif kind != "linear":
        stop = count + 5 * size
        feature_p = p[count:stop]
        z = a @ feature_p[: 4 * size].reshape(4, size) + feature_p[4 * size :]
        features = np.tanh(z) if kind == "tanh" else np.sin(z)
        logits += features @ p[stop:].reshape(size, 3)
    full = np.c_[logits, np.zeros(len(x))]
    full -= full.max(axis=1, keepdims=True)
    probabilities = np.exp(full)
    return probabilities / probabilities.sum(axis=1, keepdims=True)


def verify(data, output):
    out = Path(output)
    cfg = cs.check_context(data, out)
    records = cs.read(out / "development.json")
    selection = cs.read(out / "selection.json")
    expected_linear = len(cfg.calendars) * len(cfg.half_lives) * len(cfg.base_ridges)
    expected_nonlinear = 4 * len(cfg.depths) * len(cfg.feature_ridges) * len(cfg.development_seeds)
    if len(records["linear"]) != expected_linear or len(records["nonlinear"]) != expected_nonlinear:
        raise ValueError("Incomplete development grid")
    rows, fits, max_error = 0, 0, 0.0
    train_dates = data.daily.index[data.target_rows][data.train].astype("datetime64[D]")

    def check(row, policy, feature_ridge, validation=True):
        nonlocal rows, fits, max_error
        spec = row.get("model", {"kind": "linear", "size": 2, "calendar": policy["calendar"]})
        model = CalendarReadout(**spec)
        x = independent_inputs(data, model.calendar)
        age = (train_dates[-1] - train_dates).astype(float)
        weights = (
            np.ones(len(age)) if policy["half_life"] == 0 else np.exp2(-age / policy["half_life"])
        )
        weights /= weights.sum()
        candidates = row.get("fits", [row["fit"]])
        best = min(candidates, key=lambda f: (f["objective"], f.get("restart", 0)))
        np.testing.assert_array_equal(best["parameters"], row["fit"]["parameters"])
        for fit in candidates:
            p = np.asarray(fit["parameters"])
            probs = dense_probabilities(spec, x[data.train], p)
            reference = model.probabilities(x[data.train], p)
            error = float(np.max(np.abs(probs - reference)))
            max_error = max(max_error, error)
            np.testing.assert_allclose(probs, reference, atol=1e-12, rtol=1e-12)
            objective = -np.dot(
                weights, np.log(probs[np.arange(len(weights)), data.labels[data.train]])
            )
            objective += policy["ridge"] * np.dot(p[: model.base_count], p[: model.base_count])
            objective += feature_ridge * np.dot(p[model.base_count :], p[model.base_count :])
            np.testing.assert_allclose(objective, fit["objective"], atol=1e-8, rtol=1e-8)
            if fit["eligible"] != (
                fit["success"] and fit["gradient_inf"] <= cfg.gradient_tolerance
            ):
                raise ValueError("Incorrect fit status")
            rows += len(probs)
            fits += 1
        if validation:
            probs = dense_probabilities(spec, x[data.validation], best["parameters"])
            scores = forecast_scores(probs, data.labels[data.validation])
            for k in ("log_loss", "rps_normalized", "extreme_brier"):
                np.testing.assert_allclose(scores[k], row["validation"]["pooled"][k], atol=1e-12)
            years = (
                data.daily.index[data.target_rows][data.validation]
                .astype("datetime64[Y]")
                .astype(str)
            )
            for year in np.unique(years):
                expected = forecast_scores(
                    probs[years == year], data.labels[data.validation][years == year]
                )
                np.testing.assert_allclose(
                    expected["log_loss"], row["validation"]["years"][year]["log_loss"], atol=1e-12
                )

    for row in records["linear"].values():
        check(row, row, 0)
    key = min(
        records["linear"],
        key=lambda k: (records["linear"][k]["validation"]["pooled"]["log_loss"], k),
    )
    assert key == selection["linear_key"]
    assert records["linear"][key] == selection["policy"]
    policy = selection["policy"]
    for row in records["nonlinear"].values():
        check(row, policy, row["feature_ridge"])
    for kind, chosen in selection["choices"].items():
        groups = {}
        for row in records["nonlinear"].values():
            if row["kind"] == kind:
                groups.setdefault((row["depth"], row["feature_ridge"]), []).append(
                    row["validation"]["pooled"]["log_loss"]
                )
        winner = min(groups, key=lambda k: (np.mean(groups[k]), k[0], k[1]))
        assert winner == (chosen["depth"], chosen["feature_ridge"])
        np.testing.assert_allclose(np.mean(groups[winner]), chosen["validation_nll"], atol=1e-14)
    final_seeds = []
    if (out / "seal.json").exists():
        cs.check_seal(data, out)
        for seed in cfg.final_seeds:
            entry = cs.read(out / f"train-seed{seed}.json")
            for row in entry["models"].values():
                check(row, policy, row["feature_ridge"], validation=False)
            final_seeds.append(seed)
    result = {
        "verified": True,
        "kind": cfg.kind,
        "fits_replayed": fits,
        "training_probability_rows": rows,
        "max_dense_error": max_error,
        "final_seeds": final_seeds,
        "scope": "dense probabilities, training objectives, restart/setting selection, validation scores; gradients checked independently during fitting",
    }
    name = "verification-training.json" if final_seeds else "verification-development.json"
    write_json(out / name, result)
    return result


def independent_paths(data, spec, p, days, paths, seed, burn_in):
    rng = np.random.default_rng(seed)
    n = days + burn_in
    u, within, innovation = (
        rng.random((n, paths)),
        rng.random((n, paths)),
        rng.normal(size=(n, paths)),
    )
    end = data.target_rows[data.train.stop - 1] + 1
    yy, rr = np.zeros((paths, n + 30)), np.zeros((paths, n + 30))
    yy[:, :30], rr[:, :30] = (
        np.log(data.daily.rv[end - 30 : end]),
        data.daily.returns[end - 30 : end],
    )
    date = np.datetime64(data.daily.index[end - 1], "D") + np.timedelta64(1, "D")
    for t in range(n):
        history = yy[:, t : t + 30]
        raw = np.stack(
            [history[:, -1], history[:, -7:].mean(axis=1), history.mean(axis=1), rr[:, t + 29]],
            axis=1,
        )
        x = (raw - data.scaler.mean) / data.scaler.scale
        if spec["calendar"]:
            day = (int((date + np.timedelta64(t, "D")).astype(int)) + 3) % 7
            x = np.c_[x, np.tile(np.eye(7)[day, 1:], (paths, 1))]
        cdf = dense_probabilities(spec, x, p).cumsum(axis=1)
        for k in range(paths):
            level = min(np.searchsorted(cdf[k], u[t, k], side="right"), 3)
            pool = data.bins.pools[level]
            yy[k, t + 30] = pool[min(int(within[t, k] * len(pool)), len(pool) - 1)]
        rr[:, t + 30] = np.exp(yy[:, t + 30] / 2) * innovation[t]
    return yy[:, 30 + burn_in :], rr[:, 30 + burn_in :]


def verify_evaluation(data, output, reference=None):
    out = Path(output)
    cfg = cs.check_seal(data, out)
    directory = out / "evaluation"
    summary = cs.read(directory / "summary.json")
    selected = cs.read(out / "selection.json")
    probs_file = np.load(directory / "probabilities.npz")
    loss_file = np.load(directory / "daily-losses.npz")
    evaluator_spec = importlib.util.spec_from_file_location(
        "calendar_evaluation", Path(__file__).with_name("evaluate_calendar_study.py")
    )
    evaluator = importlib.util.module_from_spec(evaluator_spec)
    evaluator_spec.loader.exec_module(evaluator)
    if reference:
        assert evaluator.verify_reference(data, reference) == summary["reference"]
        inherited_baselines = {
            r["id"]: restore_baseline(r)
            for r in cs.read(Path(reference) / "baselines.json")["models"]
            if r["id"] in ("har-quantile", "har-residual")
        }
    labels = data.labels[data.test]
    probability_rows, path_days = 0, 0
    all_rows = []
    for index, seed in enumerate(cfg.final_seeds):
        trained = cs.read(out / f"train-seed{seed}.json")["models"]
        policy = selected["policy"]
        candidates = {
            "linear": (
                {"kind": "linear", "size": 2, "calendar": policy["calendar"]},
                policy["fit"]["parameters"],
            )
        }
        candidates.update({k: (v["model"], v["fit"]["parameters"]) for k, v in trained.items()})
        records = cs.read(directory / f"seed{seed}.json")
        all_rows.extend(records)
        if reference:
            inherited = cs.read(Path(reference) / f"train-seed{seed}.json")["models"]
            for row in [r for r in records if r["id"] not in candidates]:
                name = row["id"]
                if name.startswith("legacy-"):
                    family = name.removeprefix("legacy-")
                    fit = inherited[family]
                    old = make_model(family, fit["depth"])
                    expected = old.probabilities(data.x[data.test], fit["D"]["parameters"])
                else:
                    expected = inherited_baselines[name].probabilities(data.x[data.test])
                np.testing.assert_allclose(expected, probs_file[name][index], atol=1e-12)
                old_loss = -np.log(np.clip(expected[np.arange(len(labels)), labels], 1e-12, 1))
                np.testing.assert_allclose(old_loss, loss_file[name][index], atol=1e-12)
        for name, (spec, p) in candidates.items():
            row = next(r for r in records if r["id"] == name)
            x = independent_inputs(data, spec["calendar"])[data.test]
            probs = dense_probabilities(spec, x, p)
            np.testing.assert_allclose(probs, probs_file[name][index], atol=1e-12, rtol=1e-12)
            losses = -np.log(np.clip(probs[np.arange(len(labels)), labels], 1e-12, 1))
            np.testing.assert_allclose(losses, loss_file[name][index], atol=1e-10, rtol=1e-10)
            np.testing.assert_allclose(losses.mean(), row["forecast"]["log_loss"], atol=1e-12)
            rps = np.mean((probs.cumsum(axis=1)[:, :3] - (labels[:, None] <= np.arange(3))) ** 2)
            np.testing.assert_allclose(rps, row["forecast"]["rps_normalized"], atol=1e-12)
            sim = summary["simulation"]
            y, returns = independent_paths(
                data, spec, p, sim["days"], sim["paths"], sim["seed_base"] + seed, sim["burn_in"]
            )
            h = hashlib.sha256()
            for a in (y, returns):
                h.update(np.asarray(a, dtype="<f8").tobytes())
            assert h.hexdigest() == row["paths"]["sha256"], (
                seed,
                name,
                "recursive history mismatch",
            )
            empirical = np.mean(
                [
                    [np.corrcoef(path[:-lag], path[lag:])[0, 1] for lag in (1, 7, 30)]
                    + [np.diff(path).std()]
                    for path in y
                ],
                axis=0,
            )
            np.testing.assert_allclose(empirical, row["paths"]["mean_moments"], atol=1e-12)
            probability_rows += len(probs)
            path_days += y.size
        print(f"independently verified calendar seed {seed}", flush=True)
    # Summary aggregation is checked for every model, including inherited controls.
    for name, result in summary["summary"].items():
        rows = [r for r in all_rows if r["id"] == name]
        assert len(rows) == len(cfg.final_seeds)
        np.testing.assert_allclose(np.mean(loss_file[name]), result["log_loss"]["mean"], atol=1e-12)
        np.testing.assert_allclose(
            [r["forecast"]["log_loss"] for r in rows], loss_file[name].mean(axis=1), atol=1e-12
        )
        np.testing.assert_allclose(
            np.mean([r["paths"]["test_moment_distance"] for r in rows]),
            result["test_moment_distance"]["mean"],
            atol=1e-12,
        )
    # Reconstruct the circular-block random indices independently.
    rng = np.random.default_rng(610000)
    for block in (7, 30):
        n, rep = len(labels), summary["bootstrap_replicates"]
        starts = rng.integers(n, size=(rep, (n + block - 1) // block))
        indices = (
            np.concatenate([(starts + j)[..., None] for j in range(block)], axis=-1).reshape(
                rep, -1
            )[:, :n]
            % n
        )
        for interval in [r for r in summary["bootstrap"] if r["block"] == block]:
            delta = loss_file[interval["left"]].mean(axis=0) - loss_file[interval["right"]].mean(
                axis=0
            )
            boot = delta[indices].mean(axis=1)
            np.testing.assert_allclose(
                [interval["mean"], interval["lower"], interval["upper"]],
                [delta.mean(), *np.quantile(boot, [0.025, 0.975])],
                atol=1e-12,
            )
    result = {
        "verified": True,
        "kind": cfg.kind,
        "seeds": len(cfg.final_seeds),
        "new_model_probability_rows": probability_rows,
        "new_model_output_days": path_days,
        "bootstrap_verified": True,
        "scope": "independent dense new-model forecasts and all new-model recursive paths; all-model loss aggregation and bootstrap; inherited training seal checked",
    }
    write_json(directory / "verification.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--data", type=Path, default=Path("data/bitstamp_daily.csv"))
    parser.add_argument("--evaluation", action="store_true")
    parser.add_argument("--reference", type=Path, default=Path("results/fresh-study"))
    args = parser.parse_args()
    data = prepare_dates(load_daily_csv(args.data))
    print(
        verify_evaluation(data, args.output, args.reference)
        if args.evaluation
        else verify(data, args.output)
    )


if __name__ == "__main__":
    main()
