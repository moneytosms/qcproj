# Frontier forecasting research plan

Date: 2026-10-22. Status: executable research roadmap, not preregistered results.
The [literature review](frontier-literature.md) gives primary sources and their
limits. The [previous research note](next-approaches-literature.md) records work
already proposed; this plan turns that work into bounded experiments.

## Goal

Find a reproducible, practically meaningful improvement in next-day volatility
forecasting, then identify whether a quantum circuit's structure contributes
beyond information, classical nonlinearities, calibration and compute budget.
Publish either a validated improvement or a well-controlled negative result.
Success is not defined as finding a favorable asset after enough searches.

## Constraints

- Preserve source PDFs, existing protocols, sealed runs and historical scores.
  Downloaded data and generated experiments stay uncommitted; retain hashes,
  manifests and a documented retrievable artifact location.
- Daily data are scarce even when constructed from millions of intraday bars.
  Seeds are optimization repetitions, not independent market observations.
- All previously examined dates and assets are development evidence. A new
  split name, fresh seed or correlated new asset does not undo exposure.
- Use the existing NumPy/SciPy/JAX stack and surrounding model/data conventions.
  Read `ctx7` docs before introducing or changing external-library API usage.
  No Qiskit/PennyLane rewrite is required for small exact simulations.
- Match inputs, target definitions, eligible dates, tuning opportunities,
  calibration policy, aggregation policy and history across model families.
  Report both equal-trial and equal-measured-compute comparisons; neither
  nominal parameter count nor optimizer iterations alone measures fairness.
- No new paid compute, hardware job or external data license is assumed.

## Acceptance criteria

1. A replayable development benchmark with leakage tests, independent prediction
   replay, full fit diagnostics and strongest feasible classical controls.
2. A locked candidate that improves pooled development NLL by at least 1% over
   the development-selected classical champion, wins at least two of three
   outer folds, and has no asset more than 2% worse. These are screening rules,
   not statistical confirmation or promises of achievable performance.
3. On a separately frozen prospective evaluation, at least 5% lower pooled NLL
   than the preselected classical champion, a paired 95% interval entirely
   below zero for the loss difference, and no material deterioration in the
   prespecified guardrails below. Report results against every frozen control.
4. A quantum-structure interpretation additionally survives no-entangler,
   trainable-frequency, capacity and budget controls. It still cannot establish
   computational advantage over the exact classical simulator at two qubits.

## Unresolved questions

- Actual compute costs and available local artifacts must be measured in WP0;
  estimates below are caps/planning ranges, not benchmark results.
- Prospective sample length needed to detect 5% is unknown. Estimate power from
  development loss blocks and freeze the horizon before collecting outcomes.
- Licensing/retrievability of any second-venue dataset must be checked before
  selecting it. Same-market multi-venue results share shocks.
- Whether more information, learned quantum features or quantum memory helps
  is the research question. No branch advances by assertion.

## Starting evidence and the current v4–v6 experiment

The [research ledger](research-ledger.md), [v3 study](v3-study.md),
[controlled ensemble](ensemble-results.md) and
[cross-market results](calibrated-v3-results.md) do not establish transferable
quantum superiority. AVAX's reported 5.68% NLL gain accompanies worse QLIKE;
the registered three-asset rule failed. Quantum and classical restart/ensemble
budgets also differed in prior v3 panels. Earlier validation mixture fits
sometimes assigned quantum zero weight.

This iteration's `scripts/run_frontier_study.py` is the bounded initial rung:
v4 frozen quantum features with a regularized softmax head; v5 a HAR-offset
correction; v6 calibration-period mixtures. Matched-input sine/tanh random
features and linear/HAR controls test simple explanations. Training through
2022, calibration/selection in 2023 and audit in 2024 remain globally exposed
development, including when 2024 is untouched by this particular script.
The measured summary is `results/frontier-20261022/scorecard.json`: 15 runs,
240 eligible head fits, no broad advantage. All v6 paired intervals cross zero.
Its detailed outcomes belong in the companion run report. Before another
fit, close four design gaps: an equally flexible classical mixture, a native
raw-log HAR reference, independent feature-seed banks, and the distinction
between frozen and trainable circuit features. Current feature seeds 42/43/44
produce overlapping banks 42–44/43–45/44–46; these are not independent ensembles.
The classical mixture must receive the same 15 weight-grid combinations/constraints
and calibration information as the quantum-containing mixture. Confirm the
actual mixture dimensionality from the saved design rather than changing it
after seeing audit loss. The current transformed-HAR reference must not be
reported as canonical raw-log HAR. These fixes are a new registered development
round, not a reason to overwrite or retune the now-scored 2024 experiment.
Frozen random features do not test joint circuit learning, an exact Fourier
twin, recurrent quantum memory, or superiority over the stronger controls below.

## Protocol to freeze before further fitting

### Dates, targets and causal information

Use BTC, ETH, SOL and DOGE as the fixed development panel, with any fifth
already-audited dataset clearly secondary. Use only common eligible target
dates for pooled comparisons. Initial outer folds: train through 2021, select
on 2022, audit 2023; train through 2022, select 2023, audit 2024; train through
2023, select 2024, audit 2025. Minimum 365 training targets per asset/fold;
if any fails, register a revised common panel before seeing new scores.
These folds are robustness checks on exposed history, not fresh confirmation.

Within each selection year, use January–June for hyperparameters and
July–December for calibration/mixture weights. Do not fit a mixture and report
its same-period loss as an out-of-sample gain. All transforms, thresholds,
within-bin severity estimates and feature-selection choices come from the
appropriate earlier training data. Keep class thresholds fixed within each
outer audit. Freeze target units: `RV = sum(log return squared)`, unannualized
daily variance, versus `log(RV)` for transformed modeling.

Forecast day t+1 only from complete observations available by the registered
origin after day t closes, with a declared data-publication delay. Target-day
calendar indicators are known in advance; target-day returns/volume are not.
Use strict UTC interval boundaries, exchange timestamps and previous-day close
for the boundary increment. Incomplete days or outage-spanning increments
cannot silently become complete five-minute observations. Require complete
feature histories; do not compress a missing calendar day out of a 30-day HAR
window. Audit zero RV explicitly before logarithms. For future multi-day
targets, purge overlapping target intervals at boundaries and use dependence
blocks at least as long as the horizon; one-day targets need no arbitrary
30-day purge merely because their past-only features overlap.

### Metrics and selection

Primary categorical endpoint: per-day NLL of the **actual deployed probability
forecast**. An ensemble's loss is loss after averaging probabilities, not mean
loss of its members. Pool by first averaging each date's loss over the fixed
asset panel, then averaging dates. Preserve paired per-asset, per-date losses.
NLL comparisons use the same fold's training-defined bins for all families.

Guardrails: RPS, extreme-bin Brier, calibration, positive-RV QLIKE and interval
score where defined. Freeze a 2% maximum relative degradation in RPS and QLIKE
against the selected classical champion as a screening/confirmation guardrail;
report uncertainty, do not portray a point threshold as a noninferiority test.
Use nonnegative normalized QLIKE `y/mu - log(y/mu) - 1` for positive y and mu;
do not use a percentage of a potentially negative log-likelihood-like variant.
If a comparator guardrail score is near zero, preregister an absolute tolerance
from development data instead. Continuous-distribution work gets its own
prespecified CRPS endpoint and cannot replace NLL after seeing failures.

Fit/calibration failure rules are fixed in advance: nonfinite predictions are
invalid; exhausted optimizers remain recorded; a forecast procedure uses its
prespecified HAR fallback rather than deleting hard dates or failed seeds.
Report fallback frequency. Do not average failed models as if they converged.

### Budgets, uncertainty and multiplicity

Development screening: three seeds, at most 12 registered configurations per
family per fold, common input sets, and the same selection metric. Full follow-up:
ten fixed seeds for candidates that pass, identically sized probability
ensembles for every eligible family. Log all restart fits, early stops,
hyperparameter proposals, feature selection and failed runs. A family that
trains cheaply may receive more trials only in the separately labeled
equal-compute experiment. Avoid 20-seed sweeps of already-rejected designs.

Use synchronized date-block resampling across assets with a prespecified
30-day primary block and 7/60-day sensitivity analyses; report 10,000 bootstrap
replicates and the random seed. Preserve temporal ordering inside blocks and
paired predictions. Seeds are averaged within the deployed procedure before
date uncertainty. Check sensitivity to crisis blocks and leave-one-asset-out
pooling without selecting winners from those slices.

Historical selection intervals are descriptive. For a prospective study freeze
one primary quantum candidate, one classical champion, one pooled endpoint and
one final analysis. If multiple candidates/endpoints are confirmatory, use
Holm adjustment over the registered family; use a Model Confidence Set as a
secondary model-uncertainty analysis. Corrections cannot recover unlogged prior
searches. Do not report one favorable interval among many as the primary result.

## Work packages and ownership

Paths below are ownership boundaries for future agents, not claims that all
modules already exist. One integrator owns shared runners/config schemas and
documentation integration. Agents must not revert concurrent work. Each handoff
contains changed files, commands/results, artifact hashes, failed experiments
and an explicit gate decision. Every substantive milestone gets its own topic
branch, checks, documentation, commit, push and PR to `moneytosms/qcproj`; leave
merging to the owner.

| ID / priority | Owner and files | Dependencies | Deliverable, check and stop rule | Estimated work / compute cap |
| --- | --- | --- | --- | --- |
| WP0 / mandatory | Integrator: `scripts/run_frontier_study.py`, new `scripts/verify_frontier_study.py`, `configs/frontier-*.json`, `doc/frontier-protocol.md` | Current v4–v6 runner | Preserve scored run; register equal-flexibility classical mixtures, disjoint feature banks and native HAR. Freeze protocol, inspect artifacts, benchmark one fit per family; save hashes, dates, diagnostics, seeds and costs. Independent score replay must agree within 1e-10. Stop on missing provenance or target mismatch. | 0.5–1 engineering day; ≤1 CPU-hour profiling |
| WP1 / mandatory | Data agent: `src/qcvol_next/binance_data.py`, new `src/qcvol_next/intraday_features.py`, `tests/test_intraday_features.py` | WP0 schema | Add complete-day downside share, quarticity and quality metadata without changing legacy defaults; synthetic identity/boundary/gap tests; identical eligible dates across families. Stop on any unresolved interval or timestamp ambiguity. | 1–2 days; ≤4 CPU-hours plus measured downloads |
| WP2 / mandatory | Controls agent: new `src/qcvol_next/frontier_baselines.py`, `tests/test_frontier_baselines.py` | WP0; WP1 for enriched controls | Implement/reuse strong controls below, same information and calibration; known synthetic-process and probability checks. Stop quantum promotion if it loses to the frozen development champion. | 1–3 days; ≤24 CPU-hours total screening |
| WP3 / mandatory | Circuit audit agent: new `src/qcvol_next/frontier_twins.py`, `tests/test_frontier_twins.py`; targeted diagnostics in `src/qcvol_v3/models.py` | WP0 | Exact independent classical twin, no-entangler/readout ablations, effective rank and dead-coordinate audit; 1e-10 probability agreement and finite-difference gradient checks. Stop on mismatch before interpreting scores. | 1–2 days; ≤2 CPU-hours |
| WP4 / first quantum bet | Quantum agent: new `src/qcvol_next/frontier_trainable.py`, `tests/test_frontier_trainable.py` | WP0–WP3 | Trainable residual circuit with exact baseline fallback; matched trainable sine/tanh controls. Pass the 1%/two-fold development gate and guardrails, otherwise close this branch. | 2–3 days; ≤24 CPU-hours screening, ≤72 follow-up |
| WP5 / target bet | Distribution agent: new `src/qcvol_next/frontier_distribution.py`, `tests/test_frontier_distribution.py` | WP0–WP2; WP4 optional | Same continuous head on classical/quantum features; analytic moment/CDF/quantile tests, score replay. Pass registered CRPS screening and QLIKE guardrail; failure cannot be hidden behind category NLL. | 2–3 days; ≤24 CPU-hours |
| WP6 / memory bet | Memory agent: new `src/qcvol_next/frontier_reservoir.py`, `tests/test_frontier_reservoir.py` | WP0–WP3; WP5 if continuous | Small recurrent quantum reservoir with ESN/NVAR/reset-memory controls; trace/positivity, causality and independent update tests. Advance only if retained memory beats every equal-history control under the same gate. | 3–5 days; ≤24 CPU-hours pilot, ≤72 follow-up |
| WP7 / conditional kernel bet | Kernel agent: new `src/qcvol_next/frontier_kernels.py`, `tests/test_frontier_kernels.py` | WP0–WP3; only after representation diagnostics | Projected kernel against RBF, polynomial and Fourier kernels. PSD/numerical checks, train-only centering, concentration/shot audit. Stop when no development advantage or budget is consumed. | 2–4 days; ≤24 CPU-hours; no hardware |
| WP8 / confirmation | Evaluation agent: new `scripts/run_frontier_prospective.py`, `scripts/verify_frontier_prospective.py`, `tests/test_frontier_prospective.py`, `doc/frontier-confirmation-protocol.md` | One locked survivor plus WP0–WP3 | Prospective timestamped predictions; immutable freeze and independent replay; single final endpoint and complete negative results. Insufficient power means inconclusive, not success. | 2–3 engineering days; ≥1 year elapsed data collection if needed |

Estimated total is roughly 2–4 engineering weeks if all branches are warranted,
with branches run sequentially through gates. Caps are limits, not permission
to fill all available compute. Extend a cap only through a dated protocol
amendment before additional scoring; preserve the capped run. Within the initial
20-minute task, only the small v4–v6 development rung and this plan are feasible.

### WP1: information before architecture

Use complete five-minute increments to compute `RSminus = sum(r*r for r < 0)`,
`RSplus = sum(r*r for r >= 0)`, and `RQ = M/3 * sum(r**4)`, with M equal to
the complete scheduled interval count. Assert `RSminus + RSplus == RV` within
floating-point tolerance. Fit any floors/scales from training data only.
First compare base six inputs versus base plus downside share. Next, separately
test log-quarticity and the documented HARQ interaction. Only combine features
after their separate gates. A 5/10/15-minute sensitivity audit is prespecified;
do not choose the best frequency after audit results. All models receive the
same extra inputs. Jump estimators are deferred until bad-tick/gap handling and
these simpler decompositions are validated.

### WP2: controls that make the claim meaningful

Keep existing HAR residual/quantile, softmax, small network and sine controls.
Add canonical HARQ when quarticity exists; GARCH(1,1), GJR/EGARCH with Student-t
innovations using the existing optional `arch` dependency; an RBF kernel model;
and a properly regularized boosted-tree control. A new tree dependency requires
a specific implementation decision and lockfile update, not a hand-written
boosting framework. Include a modest sequence network only if WP6 advances.

Controls solve the same task: GARCH's conditional return variance is not itself
a four-bin distribution over tomorrow's measured RV. Fit any residual severity
distribution or probability adapter on training-only chronological residuals
and apply the same adapter policy to variance-only competitors. Record both the
native variance QLIKE and adapted categorical score. No future residuals may
enter that adapter. Capacity-matched controls support mechanism attribution;
unrestricted but fairly tuned strong controls support practical usefulness.

### WP3–WP4: identify and train useful quantum structure

Start with the exact current two-qubit model. Construct an independent NumPy
matrix or real-valued recurrence twin with identical parameters and outputs.
Compare random/edge inputs, depths 1–4, stored fits, and objective derivatives.
An exact twin must tie; it establishes equivalence and affordable classical
execution. It is not a rival expected to lose. Separately compare independently
trained sine/Fourier models, including learned affine frequencies and interaction
features, with both matched capacity and a wider regularized control.

The existing Born circuit has unobservable final RZ angles before a CNOT and
Z-basis measurement; the phase-sensitive Pauli readout does not share that
blanket invariance. Remove coordinates only after a readout-specific proof and
regression test; replay old parameters before refitting. Save `success`, status,
message, iterations, evaluations, final objective, gradient norm and timing for
every restart. Inspect probability-Jacobian singular values on training inputs.

Extend v5 to `softmax(log(p_HAR) + g_theta(x))`, with positive baseline
probabilities and a regularized quantum residual. Zero correction must reproduce
HAR exactly. Initialize circuit weights with a small bounded scale; train the
readout first, then unfreeze circuit parameters under a fixed budget. A zero
readout initially blocks circuit gradients, so the staged schedule is explicit.
Use the same residual form for learned sine/tanh and no-entangler controls.
Compare depths 1/2/3 only; avoid increasing qubits until this question is settled.
Keep frozen-feature v4 as an ablation. Any improvement from readout fitting alone
is not evidence that trained quantum dynamics helped.

### WP5: resolve the NLL–QLIKE disconnect

Current four-bin probabilities plus fixed within-bin means cannot identify
within-bin severity. Start with a Gaussian distribution for `log(RV)` using HAR
location and positive scale, then add the same small residual correction to
classical and quantum feature heads. Its implied mean RV is `exp(mu+s²/2)`;
`exp(mu)` is the median and must not silently become the QLIKE mean forecast.
Derive all bin probabilities, quantiles and mean from that same distribution.

Register CRPS in RV units, mean quantile pinball, 90% interval score/coverage and
QLIKE; evaluate category NLL secondarily on the original bins. Test numerically
against independent integration/sampling. A Student-t distribution on log-RV
does not generally have a finite exponentiated mean; do not add it as an easy
heavy-tail substitution without changing the model. Add conformal adaptation
only as a separate causal wrapper shared by all families, after static scoring.
Coverage gains alone do not imply a better distribution or narrower intervals.

### WP6: real memory with classical memory controls

Adapt the Li et al. retained-state mechanism, not its market claims. Pilot
3–6 total qubits, a fixed seeded Hamiltonian, input replacement, partial trace
and local Z readouts. Begin with a fixed three-day window reset at its start;
compare a streaming retained-state extension only as a separately registered
variant with causal warmup. If inputs are compressed to fit the input qubits,
fit compression on training data and provide exactly that representation to
classical controls as well as unrestricted same-information controls.

Train a ridge/softmax readout only in the first pass. Compare ESN, delayed linear
HAR, degree-two delay-polynomial/NVAR, random Fourier delay features, no-memory
reset and no-interaction reservoirs. Match lag availability, readout size,
regularization search and ensemble members. Test invariance of earlier
predictions to perturbing future rows, state-reset semantics, trace one,
Hermiticity and eigenvalues within numerical tolerance. Report simulator cost
and state dimension. Stop if gains disappear with an equal-history classical
control; that result identifies memory/information rather than quantum dynamics.

### WP7: kernel search only after a cheap rejection test

Use projected local-observable features from a fixed shallow circuit and an RBF
over those features before a full fidelity-kernel expansion. Record feature
variance, kernel off-diagonal variance, effective rank, conditioning and train-only
alignment. Use at most 512 registered training landmarks for a first diagnostic;
then compare exact versus Nyström approximations on a small shared fixture.
Apply the same approximation and tuning budget to classical kernels. Stop if the
representation is constant to numerical/shot precision or cannot outperform
RBF/Fourier on development folds. Geometry is diagnostic, not a success endpoint.
At two qubits this is a classical nonlinear feature method with quantum origins.

### WP8: confirmation and publication gates

Freeze source commit, environment, assets, candidate/controls, features, forecast
origin, refit schedule, bins, aggregation, endpoint, failure fallback and fixed
end date before prospective predictions. Begin no earlier than the UTC day
after that freeze, not automatically 2026-10-23 if implementation finishes later.
Use development block simulations to select a horizon with reasonable power for
5%; plan at least 365 daily origins, disclose if even that is insufficient.
Do not extend the evaluation because the observed p-value narrowly misses.
Record forecasts before outcomes and keep the evaluation process read-only
until the final analysis. A monthly expanding refit, if selected, is a fixed
algorithm using only then-available outcomes; it is not discretionary retuning.

Publication gate P0: tests and artifacts reproducible; P1: complete development
comparison and all stopped branches; P2: prospective effect, uncertainty and
guardrails; P3: ablations identify what contributes. A negative P2 is publishable
as a controlled benchmark. A positive P2 without P3 supports a forecasting
procedure, not attribution to entanglement. No result here implies trading
profitability, tail-risk validity or computational speedup. Hardware/scaling
work is a separate later project requiring measured data loading, measurement,
optimization, mitigation, queue and inference costs against the best classical
implementation, not gate count alone.

## Execution and verification commands

Run from the repository root. Existing required checks, wrapped for this
environment:

```bash
rtk err uv run ruff check .
rtk err uv run ruff format --check .
rtk test uv run pytest -q
rtk git diff --check
```

Each WP creates its named focused test file; after implementation its command is:

```bash
rtk test uv run pytest -q tests/test_frontier_twins.py
rtk test uv run pytest -q tests/test_intraday_features.py
```

These are examples for WP3/WP1, not claims that those files already exist.
The integrator must document the actual runner's `--help` before constructing a
run command. Do not invent unsupported CLI flags. Add a minimal config-driven
development/evaluation interface only where the existing runner cannot express
the frozen protocol. Proposed verifier entry point, to implement in WP0:

```bash
uv run python scripts/verify_frontier_study.py --manifest output/frontier/manifest.json
```

The verifier independently reconstructs target alignment, transformations,
probabilities, all scores, selections, hashes and budget counts. It must fail
if test rows entered fitting/calibration, artifacts were overwritten, arrays
misalign, normalization fails, or recorded scores differ. Tests also deliberately
alter future data and labels to prove earlier forecasts remain unchanged.

At every gate update `doc/progress.md`, `doc/implementation.md` and
`doc/architecture.md` where architecture changed. PR descriptions separate
software verification, development measurements and scientific confirmation.

Skipped for now: hardware, larger circuits, arbitrary asset searches, automatic
feature combinatorics and claims of superiority. Main risk: a carefully
controlled study may still find no useful quantum contribution.
