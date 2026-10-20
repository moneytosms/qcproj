# Baseline preserving memory experiment

This follow-up tests whether weekly/monthly information helps after preserving the
paper's original circuit as an exact zero-weight case. It follows the earlier
[memory-fit investigation](memory-fit-investigation.md), and its protocol and
convergence amendment are in [nested-memory-protocol.md](nested-memory-protocol.md).

The experiment uses the author's standardized series, a 30-day warm-up and the
same 529/177/177 chronological split. All comparisons here use training and
validation only. Prior upstream rescaling may use full-sample information; this
is exploratory model development, not a clean raw-data forecasting study or a
final independent test claim. The full 20-seed study remains pending.

## Measured decision

**Retain previous-day inputs for D. This baseline-preserving memory extension does
not demonstrate a benefit from weekly/monthly information.** All 65 fits in the
precision-corrected sweep pass optimizer and independent stationarity checks. The
validation-selected longer-memory extension is about 12.3% worse than the matched
short-memory control, despite its small improvement over the original paper alone.
Persistence has the lowest validation MSE among the point references in this sweep.

Select each restart on training objective, then its regularization on validation.
The table reports the corresponding raw-RV MSEs; these are not the previous smoke
test scores and are not interchangeable with them.

| Model | Selected alpha | Train MSE | Validation MSE |
| --- | ---: | ---: | ---: |
| Paper | — | 0.00318485 | 0.00072042 |
| Nested weekly/monthly | 0.1 | 0.00318245 | 0.00071891 |
| Nested yesterday control | 0.001 | 0.00280787 | 0.00064040 |
| Classical HAR RV | — | 0.00251658 | 0.00061033 |
| Training-mean constant | — | 0.00318375 | 0.00103401 |
| Yesterday RV persistence | — | 0.00387608 | 0.00057420 |

The longer-memory winner uses alpha .1 and only slightly improves over the paper;
comparison against the short-input control removes the apparent memory benefit.
The latter uses alpha .001. Classical HAR also beats the longer-memory quantum
candidate. These are valid unfavorable outcomes. Keep HAR and persistence as
strong reference models during D/A rather than comparing only quantum variants.

### Complete regularization comparison

Each row uses the best penalized-training restart among the five starts. Every
setting's five starts pass both convergence checks after tightening precision.
The short-memory unregularized and weakly regularized fits retain two different
local solutions; restart selection uses training objective throughout, even when
another local solution has a more attractive validation score.

| Alpha | Weekly/monthly train MSE | Weekly/monthly validation MSE | Yesterday train MSE | Yesterday validation MSE | Converged full / short |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 0.00307027 | 0.00084200 | 0.00278233 | 0.00064862 | 5/5 / 5/5 |
| 0.0001 | 0.00307044 | 0.00084254 | 0.00278298 | 0.00064672 | 5/5 / 5/5 |
| 0.001 | 0.00307892 | 0.00084549 | 0.00280787 | 0.00064040 | 5/5 / 5/5 |
| 0.01 | 0.00317124 | 0.00072182 | 0.00313000 | 0.00073998 | 5/5 / 5/5 |
| 0.1 | 0.00318245 | 0.00071891 | 0.00316553 | 0.00072290 | 5/5 / 5/5 |
| 1 | 0.00318459 | 0.00072020 | 0.00318243 | 0.00072061 | 5/5 / 5/5 |

The unregularized weekly/monthly model improves training MSE to .00307027 but
worsens validation MSE to .00084201. Regularization shrinks the additional weights
and brings validation behavior back toward the paper baseline. The conclusion
applies to this encoding, extension, standardized dataset and validation block.
Broader claims require independent data and a final test study.

### Validation handoff

`decision.json` selects `previous_day_only` for D. Keep the original paper as a
reference, use the short-input extension as the matched quantum control, and carry
HAR/persistence forward. Implement and validate the short-input policy in the D
runner before its next sweep: the existing main Born runner still uses its original
HAR feature map by default. Compare D on forecast likelihood/calibration, then test
A on generated-history realism separately. A D benefit and an A benefit each need
their own evidence; neither follows from completing this B investigation.

Do not restart B tuning to force a positive result, and do not launch the full
20-seed study from this checkpoint. This completes the focused B decision; the broader D/A gates remain open.

## What changed

The original encoded state is retained. Two rotations are inserted before its
readout, controlled by standardized weekly and monthly log-RV features. The four
optimized coordinates are the paper theta/lambda and two new weights. Phi is
fixed to zero because it cannot affect the readout. With both new weights zero,
the predicted probabilities equal the paper model for every input. Tests check
arbitrary baseline angles, both input modes and independent literal matrices.

The short-memory control has the identical four-parameter circuit, with yesterday's
standardized log RV in both extra gate slots. This tests longer information against
extra same-day flexibility. It does not assert identical effective capacity.

Fit the paper on training data using five uniform initializations. Choose its best
training fit and use it to initialize every extension: exact zero new weights for
seed 0, small seeded perturbations for seeds 1–4. Sweep penalties 0, .0001, .001,
.01, .1 and 1 on the two new weights only. Restart selection uses the penalized
training objective; regularization selection uses validation MSE. Include the
unextended paper as an explicit fallback for both input families.

The classical comparator is a separate raw-RV HAR point forecaster with an intercept
and past 1/7/30-day RV averages. It uses training-only OLS and nonnegative forecasts.
This differs from the existing log-HAR empirical-residual distribution model and
from the circuit's log-horizon feature map. Also score the training-mean constant
and yesterday-RV persistence. Parameter counts and different total search costs
remain explicit; one OLS solve is not the same computational effort as a circuit grid.

## Convergence and attempts

The first sweep used the existing 1e-5 COBYLA trust-region floor. All 65 fits reported
success, but the strongest-penalty winners had gradient norms just above 1e-5.
The decision was therefore recorded as inconclusive. The complete first run is
preserved in `results/nested-memory-2026-10-19/` at source commit `cd40d08`.

Repeat the same complete grid with floor 1e-7 for both extension families, while
keeping alpha values, starts, budgets, acceptance criteria and split unchanged.
The baseline remains at its established tolerance. The repeated source checkpoint
is `e1784e0`. This precision change was driven by the independent training gradient
check; it does not remove a difficult penalty or select a favorable subset of runs.
Both attempts' calls and elapsed fitting times must be included in search accounting.

## Verification and compute cost

The final run is `results/nested-memory-tight-2026-10-19/`, source checkpoint
`e1784e0`, Python 3.12.14, NumPy 2.5.4 and SciPy 1.18.1. Both observed-data files
retain their pinned SHA-256 hashes. The measured zero-weight prediction discrepancy
is exactly zero on all train/validation inputs; no paper-domain input guard activates.
The largest finite-difference gradient infinity norm is 2.08e-7, below the fixed
1e-5 threshold. All 65 fitted models pass both checks. Source checkpoint `cd40d08`
retains the first inconclusive attempt; audit it with that commit's package sources.

| Attempt | Fits | Optimizer objective calls including initial checks | Stationarity calls | Summed fit seconds |
| --- | ---: | ---: | ---: | ---: |
| Initial 1e-5 floor | 65 | 23,169 | 500 | 39.336 |
| Repeated 1e-7 floor | 65 | 58,389 | 500 | 99.389 |

Total: **82,558 training/diagnostic objective calls** across 130 fits and about **138.724 seconds** of summed optimization time on this machine. Each attempt additionally performs one HAR linear solve (roughly .005–.006 seconds), plus preparation, prediction, audit and plotting. These are local observational timings, not a fair hardware-speed benchmark. The original training-only engineering probe is outside this measured sweep accounting; it was not used to select validation settings.

Both attempts pass the literal-matrix artifact audit. For each run it recomputes
48,008 stored train/validation predictions (96,016 across the two attempts), with
maximum prediction discrepancy 2.78e-16, and independently checks the central
gradients, HAR solution, warm starts, penalty losses and selection. The zero-weight
identity discrepancy is zero. No test targets or scores appear in the saved arrays.
Both final plots were rendered and visually inspected. The current branch passes
47 tests (42 root pipeline tests and five legacy qvol tests), Ruff lint/format and
whitespace checks. The separate audited paper PR has additional tests.

## Commands and artifacts

From the repository root, with the locked environment and pinned author data:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 uv run python scripts/run_nested_memory.py \
  --author-data data/raw/author --output results/nested-memory-new-run
OPENBLAS_NUM_THREADS=1 uv run python scripts/verify_nested_memory.py \
  results/nested-memory-new-run --author-data data/raw/author
uv run python scripts/plot_nested_memory.py results/nested-memory-new-run
```

The verifier checks package and data hashes; independently multiplies the gates for
all saved predictions; reconstructs HAR by an unstandardized least-squares solve;
recomputes losses, penalties and central gradients; verifies warm starts, the
zero-weight identity and both selection stages. It checks that no test targets or
scores are saved. The tests additionally perturb all future test values and require
fits, scores and the policy decision to remain unchanged.

Each run folder is new and cannot be overwritten. `manifest.json` records the
configuration, source, versions, split, zero-weight checks and search cost.
`records.json` and compressed arrays retain every fit, initial and trained parameters,
objective histories, gradients and aligned train/validation predictions. `summary.json`
records the training-selected restart for every alpha. `decision.json` records the
validation-selected penalty and input policy for D. The two plots show the penalty
sweep and validation forecast curves. Generated experiment outputs remain ignored;
the measured findings, protocol, scripts and tests are versioned.

## Scope of the handoff

The 1% relative validation-gain rule is a practical threshold fixed before the
measured sweep, not a statistical significance test. All training-selected settings
must pass both optimizer and stationarity checks before deciding B. The five seeds
measure optimizer sensitivity, not uncertainty across independent market records.

The resulting input policy is for the next D probability-forecast comparison.
Retain the paper, short-memory and classical controls, evaluate D separately, and
only then test A realism training. No new categorical performance, recursive
realism benefit, independent test gain, quantum advantage or completed final study
is claimed by this point-forecast experiment. The project report remains paused.
