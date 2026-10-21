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
the [research and verification ledger](doc/research-ledger.md), and [current progress](doc/progress.md). The two PDFs in this repository are the source
specification and explanatory guide; their pilot numbers are not results from this code.

## Project site and paper

The [landing page](https://moneytosms.github.io/qcproj/) explains the result with charts and animations (source in `site/`, usage guide in `docs/`). The [research paper](paper/main.typ) is a 6-page Typst paper with BibTeX citations; build with `typst compile --font-path report/fonts --root . paper/main.typ paper/quantum-volatility-paper.pdf`. Figures come from `paper/results.json` via `paper/figures.py`.

## IEG 313 report

The [implementation-based project report](report/README.md) provides editable Typst
sources, reproducible vector figures, the required 13-section structure, and
scientific/writing review records. Build it with the commands in that directory.
It reports completed studies and distinguishes post-hoc findings and limitations.
Historical milestone notes below retain their original experiment boundaries.

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
after checking convergence and the open research gates in the plan. Eight-level circuits, hardware, transfer, remain planned; the report source is now in `report/`.
Direct HAR quantile regression and GARCH are evaluated by the focused Step 4 runner below;
the additional paper audit lives in PR #2.
The historical three-layer circuit has 24 nominal parameters with two inactive final phase directions;
see the architecture notes before describing a parameter-matched comparison.

## Layout

```text
doc/                  Plan, decisions, conceptual guide, verified progress
src/qcvol/            Core reusable pipeline and early study models
src/qcvol_v2/         Quantum v2 forecasting models
src/qcvol_v3/         Quantum v3 forecasting models
src/qcvol_next/       Weekend-aware models and later development runners
qvol/                 Separate audited reproduction of the original paper
tests/                Circuit, leakage, metric and deterministic training checks
scripts/              Data builders, experiment runners, verifiers and plots
configs/              Smoke, study and preregistered experiment settings
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
do not beat the matched short-memory control. The full study remains pending. The measured D/A development comparison is linked below. See the [fixed protocol and precision amendment](doc/nested-memory-protocol.md).

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 uv run python scripts/run_nested_memory.py \
  --author-data data/raw/author --output results/nested-memory-01
OPENBLAS_NUM_THREADS=1 uv run python scripts/verify_nested_memory.py \
  results/nested-memory-01 --author-data data/raw/author
uv run python scripts/plot_nested_memory.py results/nested-memory-01
```

The historical main Born runner uses HAR inputs. The dedicated Step 3 runner below
implements the selected short-input policy; the old final-study configuration still needs updating.

## Step 3: short-input D → A validation study

Use this focused runner after the B follow-up. It applies previous-day inputs during
fitting, validation and recursion, fits five starts per depth, selects D depth on
validation, then tunes the A penalty at that frozen depth. Fresh simulation streams
check the selected result; no test scores are calculated. The older `qcvol run` and
`configs/study.json` still describe the original HAR-input pipeline and are not the
entry point for this short-input comparison.

Read the [measured findings](doc/distribution-study.md) and
[fixed protocol](doc/distribution-study-protocol.md) before running:

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

## Step 4: classical comparisons and training checks

The [measured comparison](doc/classical-comparison.md) adds direct HAR quantile
regression, a short quantile control, explicitly calibrated GARCH(1,1), and a stable
regularized neural comparator. It records active parameter limits, full training effort,
native/common-law quantile scores and seeded path audits. The
[protocol](doc/classical-comparison-protocol.md) preserves the first capped-network
attempt and the regularization refinement. This remains validation development evidence.

```bash
uv sync --all-extras
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 uv run python scripts/run_classical_comparison.py \
  --author-data data/raw/author --prior results/distribution-study-2026-10-20 \
  --output results/classical-comparison-01
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 uv run python scripts/verify_classical_comparison.py \
  results/classical-comparison-01 --author-data data/raw/author
uv run python scripts/plot_classical_comparison.py results/classical-comparison-01
```

The prior is a completed Step 3 run with unchanged original model/data source hashes.
Finance dependencies are optional until this runner is used (`--all-extras` includes them).
Use `--previous-attempt PATH` to record an earlier comparison's provenance and cost.
The completed final-study runner below integrates these choices.

## Frozen 20-seed study

Use `configs/final-study.json` with the new runner; the earlier `configs/study.json`
remains historical. Read [the frozen protocol](doc/final-study-protocol.md) and
[the measured 20-seed results](doc/final-study.md). All training
is sealed before any test scores are computed. Hyperparameters are fixed from development;
validation is not re-used for selection inside this run. The original paper point circuit
has a separate RV-MSE panel. The project report is now available in `report/`.

```bash
uv sync --all-extras
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 uv run python scripts/run_final_study.py \
  --author-data data/raw/author --output results/final-study-01
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 uv run python scripts/verify_final_study.py \
  results/final-study-01 --author-data data/raw/author
uv run python scripts/plot_final_study.py results/final-study-01 --author-data data/raw/author
```

`--stage train` only fits/seals; `--stage evaluate` scores an existing sealed run without
refitting. Source, config, raw-data fingerprint and training-file hashes must match.
Completed evaluation directories cannot be overwritten; `--evaluation-name NAME` can
save a deterministic re-evaluation separately. A resumed evaluation does not change choices.
A new training run always requires a new output folder. Outputs stay local and ignored.
Seed variability and date-block uncertainty are distinct; earlier smoke work already
inspected this test block, and a single period cannot establish universal superiority.

The completed run favors HAR forecasts on test NLL. Quantum realism training worsens
both test NLL and test moment distance; its validation gains do not carry over. All
selected fits pass training checks, and independent replay verifies the complete run.
No quantum advantage is demonstrated. The report source is in `report/`; slides remain outside this milestone.

## Calendar and quantum-readout follow-up

The [improvement plan](doc/improvement-plan.md) builds on Nidhi's fresh-data PR #8.
It tests target-weekday inputs, recent-training weights, and a learned quantum feature
readout against the same-input linear/tanh/sine controls. A separate quantum variant
gives the second qubit a direct yesterday-volatility input; the original routing remains
an ablation. These are hybrid models, and the previously scored 2025–2026 period is
an exposed benchmark. The [completed development sweep](doc/calendar-development.md)
improves forecasts with calendar/readout changes, but updated classical controls still
lead. No new quantum advantage is claimed; final fitting/scoring remains pending.

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 uv run python scripts/run_calendar_study.py initialize --output results/calendar-study-repeat
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 uv run python scripts/run_calendar_study.py develop --output results/calendar-study-repeat
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 uv run python scripts/verify_calendar_study.py results/calendar-study-repeat
```

Inspect validation and convergence evidence before the final stages. With fixed choices,
run `train`, then `seal` using the same training runner/output. Score with
`scripts/evaluate_calendar_study.py OUTPUT --reference results/fresh-study`; verify using
`scripts/verify_calendar_study.py OUTPUT --evaluation`, then export figures with
`scripts/plot_calendar_study.py OUTPUT`. Output directories cannot be overwritten by
initialization/evaluation. All new experiment output stays ignored.

The subsequent [matched ensemble experiment](doc/ensemble-results.md) rejects the
quantum-complementarity hypothesis in this development grid. Both classical and quantum
ensembles choose only calendar-linear and sine forecasts (validation NLL .604802).
Follow [its protocol](doc/ensemble-protocol.md) and reproduce it with
`scripts/ensemble_complementarity.py --source OUTPUT --output NEW_OUTPUT`.
Its progression gate fails, so no twenty-seed run or new benchmark scores are claimed
for that ensemble candidate.
