# Original-paper reproduction: measured report

19 October 2026. This is a full-sample descriptive reproduction of Takaishi's
[original paper](https://arxiv.org/html/2609.04569v1), using the author's published
standardized data. It is separate from the project's held-out B/D/A study.

**Outcome:** the circuit, fitted curve and central stochastic/scaling behavior are
reproduced. Exact numerical replication of every table entry or generated series is
**not established**. The return-tail and zero-return discrepancies below remain visible.
This report completes the planned baseline comparison with documented assumptions;
it does not establish that our later forecasting upgrades improve on the baseline.

## What was run

The audited entry point is `qvol/experiments/04_reproduce_audit.py`, configured by
`qvol/configs/reproduction.json`. Verified local output:
`qvol/reproduction-runs/verified-2026-10-19/` (ignored by Git).

- All 913 observed daily rows; 912 consecutive next-day input/target pairs, no holdout.
- Ten independent COBYLA initializations, each with a 2,000-evaluation ceiling and
  tolerance 1e-8. All ten converged, using 77–114 evaluations each.
- Three 50,000-day generated series, generation seeds 0, 1, 2, using the stated
  zero-mean Gaussian return law. No burn-in; initialize from the last observed day.
- Cubic, two-ended MFDFA; all complete 913-day rolling windows at 365-day steps:
  135 windows per generated series and feature. Twenty shuffled controls per window.
- h(q), tau(q), alpha, f(alpha) for the preselected first window, q from −5 to 5 in
  steps of .02, with 20 shuffles. Two hundred independent 913-point Gaussian controls.
- Explicit geometric scale grid, 24 distinct integer scales from 20 to 182. The paper
  gives the lower fit cutoff, but not the exact scale grid/upper cutoff. Report scale
  sensitivity instead of selecting a grid to force the paper's reported numbers.
- The empirical record has only 912 increments. Use those 912 as the empirical IRV/IAR
  window rather than manufacture an observation to obtain 913 increments.

The four bundled source files match revision
`2fec7ee621006bcbe1b7860d05b9589a7276a8f6` of
[takaishi-physics/QCL-volatility](https://github.com/takaishi-physics/QCL-volatility).
The run validates their SHA-256 hashes, shapes, row IDs and encoding domains. Both
observed files contain 913 rows; both published generated files contain 50,000.
The files are already rescaled; this is not a reconstruction from intraday prices.

## 1. Fit and circuit check

Full-sample training MSE: **0.0020477757088474932**.
One-step fitted/observed RV correlation: **0.4490343**.
Selected `(theta, phi, lambda)`:
`(-1.7264407479, 2.2068028419, 4.8412474232)`.
Equivalent angle representations and arbitrary phi can produce identical predictions.

The new optimizer uses a vectorized Bloch expression for speed. A separate literal
matrix implementation verifies the result on all 913 observed input pairs:

| Check | Maximum absolute discrepancy |
| --- | ---: |
| Matrix circuit vs vectorized prediction | 3.07e-16 |
| Matrix circuit vs classical twin | 3.33e-16 |
| Changing final phi | 0 |
| Readout direction length | 1.0 |

`figures/fit-and-convergence.png` compares with paper Figures 3 and 4. The loss plateau
is approximately the same order as the plotted paper plateau (~0.002). The fitted
curve follows the same broad high/low periods and misses several largest spikes.
The plot is visually compared with the source PDF; no digitized source fit curve is
available, so this is not a pointwise curve-equality claim.

## 2. Main scaling results

Generated rows are mean h(2) over all 135 overlapping windows. Each shuffled result
averages the corresponding 20 surrogate estimates per window. Empirical results use
one available record. Numbers below come from `analysis.json` and `scorecard.csv`.

| Source | Return h(2) | IRV h(2) | IAR h(2) | Shuffled return / IRV / IAR |
| --- | ---: | ---: | ---: | --- |
| Empirical Bitcoin | .52664 | .16657 | .02404 | .50688 / .49863 / .51167 |
| Author's published output | .49365 | .07937 | .05743 | .50396 / .50370 / .50253 |
| Rebuild seed 0 | .49177 | .05288 | .04765 | .50372 / .50258 / .50349 |
| Rebuild seed 1 | .50278 | .05220 | .04778 | .50549 / .50319 / .50224 |
| Rebuild seed 2 | .49821 | .05239 | .04705 | .50403 / .50404 / .50389 |

Across the three generation seeds, the mean (sample standard deviation of these
three means) is:

- Return h(2): **.49759 (.00553)**.
- IRV h(2): **.05249 (.00035)**.
- IAR h(2): **.04749 (.00039)**.

These reproduce the central behaviors: approximately random returns; strong
anti-persistence of log-RV increments; and shuffled increments returning near .5.
They also agree with the behavior measured on the published generated data. Generation
seeds share the same fitted circuit; overlapping windows are not independent samples.
Neither window spread nor three seeds supplies a reliable significance claim.

The 200 finite-size Gaussian controls have mean h(2) **.50574**, sample SD **.04241**.
Their mean alpha-spectrum width is **.11181**, showing why a nonzero width alone is
not evidence of genuine multifractality. Full spectra, original/shuffled comparisons,
and fit-regression diagnostics remain available for inspection.

## 3. Numerical differences and assumptions

### Empirical h(2) differs from the published table

The paper's Table 1 gives central estimates .504 (returns), .155 (IRV), .030 (IAR).
Our declared main grid gives .52664, .16657, .02404. The exact fitting grid is not
specified publicly. A sensitivity run gives:

| Minimum scale | Empirical return h(2) | IRV h(2) | IAR h(2) |
| --- | ---: | ---: | ---: |
| 10 (diagnostic only) | .52535 | .20018 | .07460 |
| 20 (main analysis) | .52664 | .16657 | .02404 |
| 30 (diagnostic only) | .50411 | .15628 | .01497 |

The main grid remains 20–182 even though another cutoff brings some entries closer.
A different scale grid can change finite-sample estimates. The legacy quick experiment
included scales below 20 and used only its first 20 non-overlapping windows; its table
should not be cited as an exact implementation of the full paper protocol.

### Zero return makes IAR undefined without a convention

The empirical returns contain **one exact zero**, affecting two adjacent log-absolute-
return increments. The main path uses `log(max(abs(return), 1e-12))`; this choice is
explicit and does not alter IRV or return h(2). Its empirical IAR Pearson kurtosis is
41.7028, whereas the paper reports 4.40. Sensitivity:

| Absolute-return floor | IAR h(2) | IAR Pearson kurtosis |
| --- | ---: | ---: |
| 1e-12 | .02404 | 41.7028 |
| 1e-8 | .03139 | 11.5243 |
| 1e-6 | .03452 | 5.8827 |
| 1e-4 | .03689 | 4.4130 |

Computing kurtosis only on the 910 mathematically defined adjacent pairs gives
4.39285. This helps localize the discrepancy; it does not prove which zero convention
the author used. We retain the floor-based primary result and report both conventions.
Do not silently delete/bridge days for a time-scaling calculation.

### Generated tails and return normalization do not match exactly

Whole-series Pearson kurtoses:

| Series | Empirical data | Author's published output | Rebuild seed 0 |
| --- | ---: | ---: | ---: |
| Return | 5.8009 | 15.6998 | 6.7765 |
| IRV | 4.4376 | 4.5481 | 4.6010 |
| IAR (declared floor) | 41.7028 | 4.3520 | 4.2237 |

The author's output reproduces the generated Table 2 central kurtoses closely;
our rebuilt return tails are materially lighter. Its return/sqrt(RV) standard deviation
is .245421; the equation-based rebuilt seed 0 gives 1.001413, as expected for unit
Gaussian innovations. Scaling both output series or using different recurrence inputs
could matter; the available files do not identify the full original preprocessing.
No scaling factor was tuned to make our generated history resemble the author's.

Mean RV is .027900 empirical, .010234 author, .007297 rebuilt seed 0. Lag-1/7/30 log-RV
correlations are .749/.580/.315 empirical, .142/.055/−.006 author, and
−.019/.006/−.002 rebuilt seed 0. The baseline therefore does not reproduce long volatility
memory, which remains a motivation for part B rather than a property we should assume.

### Encoding-domain protection was inactive in the reported generation

A Gaussian return can leave the arcsin domain. The new generator leaves the reported
return unchanged and clips only an out-of-domain encoding input, recording each event.
It also logs any variance floor/cap. **All three 50,000-step runs had zero return-input
clips and zero variance clips.** Their reported findings therefore do not depend on
these guards. A strict policy is available to fail on return-domain escape.

## 4. Reproduce and verify this run

From the repository root, create an environment (Python 3.12 used here):

```bash
uv venv qvol/.venv --python 3.12
uv pip install --python qvol/.venv/bin/python -r qvol/requirements-reproduction.txt
qvol/.venv/bin/python -m pytest -q qvol/tests
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 qvol/.venv/bin/python qvol/experiments/04_reproduce_audit.py --output qvol/reproduction-runs/my-run
OPENBLAS_NUM_THREADS=1 qvol/.venv/bin/python qvol/experiments/05_verify_reproduction.py qvol/reproduction-runs/my-run
```

Choose a fresh output directory; previous runs are never overwritten. The config runs
the full protocol rather than the project's forecast smoke settings. All commands use
local bundled data and require no network after dependency installation.

Files produced:

| Artifact | Evidence |
| --- | --- |
| manifest.json | configuration, versions, data hashes, code hashes, assumptions; complete only after plotting |
| fit.json / fit-arrays.npz | every restart, convergence, loss histories, fitted/actual pairs, circuit audit |
| generated-seedN.npz | all 50,000 RV/return pairs for each seed |
| analysis.json | every original/shuffled rolling estimate, spectra, statistics and fit diagnostics |
| independent-mfdfa.json | empirical fluctuation checks against MFDFA 0.4.3 |
| gaussian-controls.json | all 200 control spectra, not just an average |
| sensitivity.json | cutoff and zero-floor effects |
| scorecard.csv | directly inspectable h(2), control and kurtosis table |
| figures/ | seven comparison figures covering fit, histories, scaling, spectra, controls and memory |
| verification.json | recomputed recurrence/rolling/spectrum integrity checks |

Verification actually passed: **150,000 recurrence steps**, **1,623 original rolling
estimates recomputed**, source hashes matched, Gaussian-control/spectrum dimensions
checked, seven figure files present. Maximum recurrence discrepancy is 2.78e-16.
The independent MFDFA package's maximum log-fluctuation discrepancy is 2.22e-15 on
empirical returns/IRV/IAR at q −5, −2, 2, 5. q=0 is checked separately against direct
polynomial fitting because the package removes q=0.

Tests: **13 reproduction/legacy Phase 1 tests passed**; the combined suites with the
held-out pipeline passed **40 tests**. New reproduction code passed Ruff and formatting;
source PDFs, bundled datasets, legacy experiment scripts and their saved results were
preserved. Generated run files stay local; this measured report is the tracked evidence.

## 5. Completion boundary

The project's Phase 1 gate—rebuild the stated circuit, obtain converged full-sample
fits, compare curves and h(2), verify the classical twin, and explain scaling differences—
has concrete evidence. Equation-level and main qualitative-statistic reproduction is
complete. Exact author parameter/seed recovery, equality to every published number,
and reconstruction from raw intraday prices are not claimed. The unpublished scale grid,
zero-return handling and output normalization prevent stronger numerical claims without
additional source material. No author contact has been sent.

The next scientific milestone is the memory ablation, after addressing its poor
small-budget fit and adding capacity-matched controls. It is outside this reproduction PR.
