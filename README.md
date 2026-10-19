# Quantum Volatility Range Forecaster

A quantum computing course project extending a one-qubit Bitcoin volatility model with
**B: multi-horizon memory**, **D: a four-level probability forecast**, and **A: realism-aware
training**. Runs on a laptop using NumPy statevectors and SciPy. Quantum advantage is a
research question, not an assumed result.

Start with [the project guide and repository reading order](doc/project-guide.md), then
[the implementation plan](doc/implementation.md), [architecture decisions](doc/architecture.md),
and [current progress](doc/progress.md). The two PDFs in this repository are the source
specification and explanatory guide; their pilot numbers are not results from this code.

## Quick start

Python 3.11+; the locked setup uses Python 3.12 and uv:

```bash
uv sync --locked --extra dev --extra plots --python 3.12
uv run qcvol verify-paper
uv run pytest -q
uv run qcvol demo --config configs/smoke.json --output results/demo-01
```

The demo uses synthetic data and works offline once dependencies are installed. Always
choose a new output directory. To use the author's revision-pinned data (network and Git
needed only during acquisition):

```bash
uv run python scripts/fetch_author_data.py
uv run qcvol run --author-data data/raw/author --config configs/smoke.json --output results/btc-01
uv run python scripts/plot_results.py results/btc-01
```

For independently prepared daily data:

```bash
uv run qcvol run --csv data/my_daily.csv --config configs/smoke.json --output results/custom-01
```

CSV schema: `date,return,rv`; consecutive ascending daily ISO dates; finite returns and
strictly positive RV, in mutually compatible units. Use enough data for three chronological
splits and the 30-day warm-up (at least 190 rows for default fractions).

## Included

- Past-only HAR features; train-fitted scaling, quantile bins, empirical sampling pools.
- Paper one-qubit circuit and exact Bloch twin, B-only memory ablation, 1–4-layer Born circuit.
- Forecast and realism training; seeded recursive generation; validation-only selection.
- Frequency, softmax, 24-parameter tiny NN, and HAR empirical-residual distribution baseline.
- Forecast, calibration, ACF, Wasserstein, tail and MFDFA diagnostics with shuffled controls.
- Return-mixture VaR/Kupiec diagnostics for compatible inputs; disabled for upstream
  author-standardized data with unknown original scaling.
- Saved manifests, candidate fits, per-seed records, prediction/path arrays, summaries and plots.

`configs/smoke.json` verifies the workflow using one seed and a small budget. It does not
establish model performance. `configs/study.json` proposes a larger 20-seed sweep; run it
after checking convergence and the open research gates in the plan. GARCH, eight-level
circuits, paper-figure reproduction, hardware, transfer, and the final report remain planned.
The supplied circuit has 24 nominal parameters with two inactive final phase directions;
see the architecture notes before describing a parameter-matched comparison.

## Layout

```text
doc/                  Plan, decisions, conceptual guide, verified progress
src/qcvol/            Reusable mathematics, data, models and experiment runner
tests/                Circuit, leakage, metric and deterministic training checks
scripts/              Explicit upstream acquisition and optional figures
configs/              Small smoke run and proposed study budget
uv.lock               Locked Python dependencies
data/raw/             Downloaded source + license + provenance (gitignored)
results/              Local experiment artifacts (gitignored)
```

Check changes with `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pytest -q`.
The upstream dataset retains its own license, saved by the fetch script. No hardware keys
or online service credentials are required to train or run the models.

## Contribution workflow

Complete each major change on a topic branch, run the relevant checks, update the docs,
and open a pull request to `moneytosms/qcproj`. See [AGENTS.md](AGENTS.md) for the
project workflow.
