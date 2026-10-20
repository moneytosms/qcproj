"""Validate saved study evidence and export reproducible report vector figures.

Run from repository root: uv run python report/tools/build_evidence.py
No model is trained and no study artifact is modified.
"""

import hashlib
import json
import platform
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.special import softmax

from qcvol.data import load_daily_csv
from qcvol.fresh_runner import code_revision, paired_intervals
from qcvol.fresh_study import prepare_dates
from qcvol.quantum import BornCircuit

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "report/assets"
QA = ROOT / "report/qa"
ASSETS.mkdir(exist_ok=True)
QA.mkdir(exist_ok=True)
run = ROOT / "results/fresh-study"
source = ROOT / "doc/fresh-study-results/results.json"
result = json.loads(source.read_text())
seal = json.loads((run / "seal.json").read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert result == json.loads((run / "evaluation/results.json").read_text())
for name, expected in seal["artifacts"].items():
    assert digest(run / name) == expected, name
manifest = json.loads((run / "manifest.json").read_text())
assert digest(ROOT / "data/bitstamp_daily.csv") == manifest["source"]["data_sha256"]
assert digest(ROOT / "configs/fresh-study.json") == manifest["source"]["config_sha256"]
data = prepare_dates(load_daily_csv(ROOT / "data/bitstamp_daily.csv"))
losses = np.load(run / "evaluation/daily-losses.npz")
errors = {}
for name in ("quantum-har", "softmax-har"):
    replay = []
    for seed in range(20):
        fit = json.loads((run / f"train-seed{seed}.json").read_text())["models"][name]
        parameters = np.asarray(fit["D"]["parameters"])
        if name == "quantum-har":
            p = BornCircuit(fit["depth"]).probabilities(data.x[data.test], parameters)
        else:
            # Independent multinomial logistic implementation; no model helper used.
            x = np.column_stack([data.x[data.test], np.ones(len(data.x[data.test]))])
            p = softmax(x @ parameters.reshape(5, 4), axis=1)
        replay.append(-np.log(np.clip(p[np.arange(len(p)), data.labels[data.test]], 1e-12, 1)))
    error = float(np.max(np.abs(np.asarray(replay) - losses[name + "-D"])))
    assert error < 1e-10, (name, error)
    errors[name] = error
intervals = paired_intervals({k: losses[k] for k in losses.files}, [7, 30], 2000)
assert np.allclose(
    [[r[k] for k in ("mean_difference", "lower", "upper")] for r in intervals],
    [[r[k] for k in ("mean_difference", "lower", "upper")] for r in result["intervals"]],
    atol=1e-12,
)
for name, summary in result["summary"].items():
    assert np.isclose(losses[name].mean(), summary["log_loss"]["mean"])
assert np.bincount(data.labels[data.test], minlength=4).tolist() == result["test_level_counts"]

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "svg.fonttype": "none",
        "axes.labelcolor": "#182a3c",
        "text.color": "#182a3c",
        "axes.edgecolor": "#9ba9b6",
        "savefig.bbox": "tight",
        "svg.hashsalt": "qvrf-report-v1",
    }
)
BLUE, TEAL, GREY = "#235b86", "#16847d", "#8d9ba6"


def save(fig, name):
    fig.savefig(ASSETS / (name + ".svg"), metadata={"Date": None})
    path = ASSETS / (name + ".svg")
    path.write_text("\n".join(line.rstrip() for line in path.read_text().splitlines()) + "\n")
    plt.close(fig)


summary = result["summary"]
names = [
    "softmax-har-D",
    "har-residual",
    "network-har-D",
    "har-quantile",
    "hybrid-quantum",
    "quantum-har-D",
    "quantum-har-A",
    "quantum-short-D",
    "garch-calibrated",
]
fig, ax = plt.subplots(figsize=(7.0, 3.2))
y = np.arange(len(names))
values = [summary[n]["log_loss"]["mean"] for n in names]
ax.barh(
    y,
    values,
    color=[
        BLUE if "quantum" in n else TEAL if "softmax" in n or "network" in n else GREY
        for n in names
    ],
    height=0.65,
)
ax.errorbar(
    values,
    y,
    xerr=[summary[n]["log_loss"]["sd"] for n in names],
    fmt="none",
    ecolor="#182a3c",
    capsize=2,
)
ax.set_yticks(y, names)
ax.invert_yaxis()
ax.set_xlim(0, 0.72)
ax.set_xlabel("Test negative log likelihood (nats per day; lower is better)")
for j, v in enumerate(values):
    ax.text(v + 0.008, j, f"{v:.4f}", va="center", fontsize=8)
ax.grid(axis="x", alpha=0.15)
ax.set_axisbelow(True)
fig.tight_layout()
save(fig, "forecast-scores")

fig, axs = plt.subplots(1, 2, figsize=(7, 2.65))
for ax, key, label in zip(
    axs,
    ["log_loss", "test_moment_distance"],
    ["Test log loss (nats/day)", "Test moment distance (dimensionless)"],
):
    for i, family in enumerate(["quantum", "softmax", "network"]):
        vals = [summary[f"{family}-har-{s}"][key]["mean"] for s in ["D", "A"]]
        ax.plot([0, 1], vals, "o-", label=family, color=[BLUE, TEAL, "#b27632"][i])
        ax.text(
            1.03,
            vals[-1],
            f"{vals[-1]:.3f}" if key == "log_loss" else f"{vals[-1]:.1f}",
            fontsize=8,
            va="center",
        )
    ax.set_xticks([0, 1], ["Forecast only (D)", "Realism trained (A)"])
    ax.set_xlim(-0.15, 1.35)
    ax.set_ylabel(label)
    ax.grid(alpha=0.15)
axs[0].legend(frameon=False, fontsize=8)
fig.tight_layout()
save(fig, "realism-tradeoff")

fig, ax = plt.subplots(figsize=(7, 2.8))
series = [
    ("Observed test", result["test_moments"], "#182a3c"),
    ("Quantum short D", summary["quantum-short-D"]["mean_moments"], GREY),
    ("Quantum HAR D", summary["quantum-har-D"]["mean_moments"], BLUE),
    ("Softmax HAR D", summary["softmax-har-D"]["mean_moments"], TEAL),
]
for i, (label, vals, c) in enumerate(series):
    ax.bar(np.arange(3) + (i - 1.5) * 0.18, vals[:3], width=0.18, label=label, color=c)
ax.set_xticks(np.arange(3), ["1 day", "7 days", "30 days"])
ax.set_ylabel("Log-RV autocorrelation")
ax.set_ylim(-0.05, 0.72)
ax.legend(ncol=2, frameon=False, fontsize=8)
ax.grid(axis="y", alpha=0.15)
ax.set_axisbelow(True)
fig.tight_layout()
save(fig, "memory-acf")

fig, ax = plt.subplots(figsize=(7, 2.7))
dates = np.asarray(data.daily.index, dtype="datetime64[D]")
logrv = np.log(data.daily.rv)
ax.plot(dates, logrv, lw=0.35, color=BLUE)
for begin, end, color, label in [
    ("2016-12-31", "2023-01-01", "#16847d", "Training"),
    ("2023-01-01", "2025-01-01", "#b27632", "Validation"),
    ("2025-01-01", "2026-10-20", "#235b86", "Test"),
]:
    ax.axvspan(np.datetime64(begin), np.datetime64(end), alpha=0.08, color=color, label=label)
for v in data.bins.edges:
    ax.axhline(v, color=GREY, lw=0.6, ls="--")
ax.set_ylabel("Daily log realized variance")
ax.set_xlabel("UTC date")
ax.legend(ncol=3, frameon=False, fontsize=8)
fig.tight_layout()
save(fig, "observed-data")

# Native Lilaq plot consumes the original numerical interval rows directly.
(ASSETS / "contrasts.json").write_text(
    json.dumps(
        [r for r in result["intervals"] if r["block"] == 30][:1]
        + [
            r
            for r in result["intervals"]
            if r["block"] == 30
            and (r["left"], r["right"])
            in [("quantum-har-D", "quantum-short-D"), ("quantum-har-D", "softmax-har-D")]
        ],
        indent=2,
    )
    + "\n"
)
# Later panels retain aggregate reports only. Validate transcription/arithmetic;
# do not present this as seed-level replay or raw-data verification.
secondary = []
for filename, assets in [
    ("multimarket-v3-results.md", {"LTC", "BNB", "ADA"}),
    ("calibrated-v3-results.md", {"LINK", "DOT", "AVAX"}),
]:
    for line in (ROOT / "doc" / filename).read_text().splitlines():
        cells = [cell.strip().replace("*", "") for cell in line.split("|")[1:-1]]
        if len(cells) != 6 or cells[0] not in assets:
            continue
        asset = cells[0]
        quantum, best = float(cells[1]), float(cells[4])
        gain = float(cells[5].replace("%", "").replace("−", "-"))
        assert abs(100 * (best - quantum) / best - gain) < 0.011
        for value in (quantum, best):
            assert f"{value:.6f}" in (ROOT / "report/main.typ").read_text()
        secondary.append(
            {
                "asset": asset,
                "quantum_nll": quantum,
                "best_classical_nll": best,
                "reported_gain_percent": gain,
                "source": "doc/" + filename,
            }
        )
assert len(secondary) == 6
for filename in ("scripts/run_v3_study.py", "scripts/evaluate_calibrated_v3.py"):
    code = (ROOT / filename).read_text()
    assert "0.025" in code and "0.975" in code
for filename in ("multimarket-v3-protocol.md", "calibrated-v3-protocol.md"):
    assert "97.5%" in (ROOT / "doc" / filename).read_text()
original_source = seal["code"]["package_source_sha256"]
current_source = code_revision()["package_source_sha256"]
changed_source = [
    name for name, value in original_source.items() if current_source.get(name) != value
]
added_source = sorted(current_source.keys() - original_source.keys())
assert changed_source == ["fresh_runner.py"]
assert added_source == ["calendar_models.py", "calendar_study.py"]

qa = {
    "implementation_commit": "0aeab94",
    "python": platform.python_version(),
    "sealed_training_artifacts_checked": len(seal["artifacts"]),
    "tracked_matches_local_evaluation": True,
    "data_and_configuration_hashes_match": True,
    "independent_daily_loss_max_error": errors,
    "paired_bootstrap_rows_recomputed": len(intervals),
    "test_level_counts": result["test_level_counts"],
    "current_package_matches_historical_source_seal": False,
    "changed_historical_package_files": changed_source,
    "added_package_files_since_seal": added_source,
    "later_panel_aggregate_checks": secondary,
    "later_panel_interval_confidence": {"protocol": 0.975, "implemented": 0.95},
    "later_panel_per_seed_replay_available": False,
    "sources": {
        str(p.relative_to(ROOT)): digest(p)
        for p in [
            source,
            ROOT / "data/bitstamp_daily.csv",
            ROOT / "configs/fresh-study.json",
            run / "seal.json",
            run / "evaluation/daily-losses.npz",
        ]
    },
}
(QA / "evidence-checks.json").write_text(json.dumps(qa, indent=2) + "\n")
print(json.dumps(qa, indent=2))
