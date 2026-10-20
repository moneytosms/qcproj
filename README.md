# Quantum Volatility Range Forecaster

A quantum computing course project extending a one-qubit Bitcoin volatility model with
**B: multi-horizon memory**, **D: a four-level probability forecast**, and **A: realism-aware
training**. Runs on a laptop using NumPy statevectors and SciPy. Quantum advantage is a
research question, not an assumed result.

The existing [`qvol/`](qvol/README.md) package contains the team's full-sample Phase 1
paper reproduction. The root `src/qcvol/` package adds the held-out B/D/A experiment
pipeline. The two use separate namespaces and entry points; the Phase 1 work is preserved.

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
Root pytest includes both packages' tests; root lint/format checks apply to the new pipeline
and leave the existing `qvol/` formatting unchanged.
The upstream dataset retains its own license, saved by the fetch script. No hardware keys
or online service credentials are required to train or run the models.

## Contribution workflow

Complete each major change on a topic branch, run the relevant checks, update the docs,
and open a pull request to `moneytosms/qcproj`. See [AGENTS.md](AGENTS.md) for the
project workflow.

## Investigating the memory point model

The [measured investigation](doc/memory-fit-investigation.md) checks the poor B-only
smoke fit with independent circuit/target audits, multiple starts, larger budgets,
training-informed initialization, and a short-memory control. It does not score the test
split or establish a final memory benefit. The historical smoke defaults remain available.

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 uv run python scripts/investigate_memory.py \
  --author-data data/raw/author --output results/memory-investigation-01
uv run python scripts/verify_memory_investigation.py results/memory-investigation-01 \
  --author-data data/raw/author
uv run python scripts/plot_memory_investigation.py results/memory-investigation-01
```

The declared grid is in `configs/memory-investigation.json`. Each output directory must
be new. Parameters, every restart, convergence histories, train/validation predictions,
search costs and source provenance stay in the ignored run folder.

## Baseline preserving memory follow-up

The [measured follow-up](doc/nested-memory-followup.md) tests a two-weight extension
that equals the original paper at zero memory weights. Its converged, regularized
comparison retains previous-day inputs for the next D stage; weekly/monthly inputs
do not beat the matched short-memory control. The full study and D/A validation remain
pending. See the [fixed protocol and precision amendment](doc/nested-memory-protocol.md).

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 uv run python scripts/run_nested_memory.py \
  --author-data data/raw/author --output results/nested-memory-01
OPENBLAS_NUM_THREADS=1 uv run python scripts/verify_nested_memory.py \
  results/nested-memory-01 --author-data data/raw/author
uv run python scripts/plot_nested_memory.py results/nested-memory-01
```

The current main Born runner still uses HAR inputs. Its D comparison must explicitly
implement the selected short-input policy before running the final study configuration.

## Step 3: short-input D → A validation study

Use this focused runner after the B follow-up. It applies previous-day inputs during
fitting, validation and recursion, fits five starts per depth, selects D depth on
validation, then tunes the A penalty at that frozen depth. Fresh simulation streams
check the selected result; no test scores are calculated. The older `qcvol run` and
`configs/study.json` still describe the original HAR-input pipeline and are not the
entry point for this short-input comparison.

Read the [fixed protocol](doc/distribution-study-protocol.md) before running:

```bash
uv run python scripts/run_distribution_study.py \
  --author-data data/raw/author --output results/distribution-study-01
uv run python scripts/verify_distribution_study.py results/distribution-study-01 \
  --author-data data/raw/author
uv run python scripts/plot_distribution_study.py results/distribution-study-01
```

The full configuration is `configs/distribution-study.json`. Source hashes must match
when auditing. It is a development comparison, not the final 20-seed study, GARCH/HAR
quantile comparison or project report. Generated output stays local and ignored.
