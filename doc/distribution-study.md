# Step 3: measured D → A development comparison

**Measured outcome:** validation chooses two quantum layers. Adding A with lambda .05
reduces the fresh-stream mean moment distance from 14.2774 to 13.0526 (8.6%), but
worsens NLL from .997917 to 1.007528 (about 1%). Classical softmax still has lower
NLL and moment distance. This supports a modest forecast/realism trade-off in this
development run; it does not establish quantum advantage or final-study performance.

Executed 20 October 2026 using the [frozen protocol](distribution-study-protocol.md).
The earlier B comparison retained previous-day inputs. This study fits categorical
probability forecasts (D), then changes the loss with a realism penalty (A).
It is a development comparison on reused validation data. No new test scores were computed.
Original paper implementation credit remains with Nidhi in `qvol/`; the paper audit is PR #2.

## Execution and provenance

- Run folder (ignored): `results/distribution-study-2026-10-20`.
- Runnable package checkpoint: `6f5affdee3d3698826099b07c70b64504334876d` (package SHA-256 hashes recorded in manifest).
- Pinned author source: `takaishi-physics/QCL-volatility` commit `2fec7ee621006bcbe1b7860d05b9589a7276a8f6`.
- 913 aligned input rows; 529 training / 177 validation / 177 test eligible targets.
- Bin counts: 159 / 211 / 132 / 27, fitted on training log RV. All scaling/pools fit on training only.
- 30 forecast fits (5 starts × 4 quantum depths, 5 softmax, 5 network), 27 warm-started A fits, 3 controls.
- Every saved candidate has training/validation probabilities and selection paths.
- Fifteen training-selected lambda candidates/controls receive two fresh audit streams,
  each 32 paths ×512 days, after 60 burn-in days. Selection remains fixed before this audit.

## D: depth and forecast scorecard

Restarts are chosen by training NLL, then circuit depth by validation NLL.

| Quantum depth | Searched angles (upper bound) | Training winner start | Training NLL | Validation NLL | Stationarity check |
| ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 6 | 2 | 1.011815 | 1.021255 | pass |
| 2 | 14 | 0 | 0.950094 | 0.997917 | pass |
| 3 | 22 | 2 | 0.942990 | 1.000528 | pass |
| 4 | 30 | 2 | 0.930139 | 1.003897 | pass |

Validation selects **2 quantum layers**. Redundant terminal RZ angles are fixed to zero.
Deeper fits reduce training loss without a consistent validation gain.

| Forecast/control | Validation NLL ↓ | Normalized RPS ↓ | Extreme-bin Brier ↓ |
| --- | ---: | ---: | ---: |
| frequency | 1.194667 | 0.160067 | 0.038116 |
| short-ar | 0.977830 | 0.115015 | 0.029527 |
| har-reference | 0.930155 | 0.106127 | 0.033200 |
| quantum-d2-D-s0 | 0.997917 | 0.114690 | 0.025746 |
| softmax-d0-D-s2 | 0.979151 | 0.114794 | 0.026002 |
| network-d0-D-s0 | 1.147321 | 0.118281 | 0.027700 |

HAR has weekly/monthly information in addition to daily log RV; label it as an
information-rich reference. The other learned controls and short AR use yesterday’s
log RV and return only. Original point-model MSE is kept in the earlier B report;
it is not a categorical probability score.

## A: validation-selected trade-offs and untouched simulation draws

At each lambda, the restart minimizes the penalized training objective. Only those
winners enter validation lambda selection. Combined score = validation NLL + .01 ×
selection-stream moment distance. The two audit streams are not used to reselect.

| Family | Lambda | Start | Training NLL | Training distance | Validation NLL | Selection distance | Combined score | Fresh distance: stream 30000 / 40000 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| quantum | 0 | 0 | 0.950094 | 10.9492 | 0.997917 | 16.9385 | 1.167302 | 14.6561 / 13.8987 |
| quantum | 0.01 | 0 | 0.950167 | 10.4402 | 0.997798 | 16.5157 | 1.162955 | 14.0956 / 13.6306 |
| quantum **selected** | 0.05 | 0 | 0.950936 | 9.7136 | 1.007528 | 15.2304 | 1.159832 | 13.3740 / 12.7312 |
| quantum | 0.2 | 2 | 1.008492 | 9.3188 | 1.121600 | 13.0559 | 1.252159 | 10.7674 / 9.1030 |
| softmax | 0 | 2 | 0.957031 | 11.0885 | 0.979151 | 15.8062 | 1.137213 | 11.7122 / 10.9825 |
| softmax | 0.01 | 2 | 0.962279 | 9.6702 | 0.989298 | 12.6130 | 1.115429 | 9.8150 / 9.0482 |
| softmax | 0.05 | 1 | 0.962781 | 9.7668 | 0.989132 | 12.3487 | 1.112619 | 9.5761 / 8.7769 |
| softmax **selected** | 0.2 | 1 | 0.962839 | 9.7668 | 0.988795 | 12.3775 | 1.112570 | 9.6022 / 8.8259 |
| network | 0 | 0 | 0.928256 | 12.3694 | 1.147321 | 13.3603 | 1.280925 | 12.5660 / 12.0918 |
| network **selected** | 0.01 | 0 | 0.935129 | 8.8038 | 1.129391 | 10.8075 | 1.237466 | 9.1000 / 8.6479 |
| network | 0.05 | 0 | 0.936064 | 9.0228 | 1.142810 | 10.0863 | 1.243673 | 9.2662 / 8.8285 |
| network | 0.2 | 0 | 0.933338 | 9.0151 | 1.134451 | 11.3023 | 1.247474 | 8.9626 / 9.6231 |

The distance of mean moments can hide variation across histories. Save and report the
average individual-path distance too; each stream contains 32 paths. These standard
deviations describe path variation, not sampling confidence intervals on model superiority.

| Family / variant | Audit mean individual-path distance, stream 30000 | Stream 40000 |
| --- | --- | --- |
| quantum D | 16.0299 ± 6.8652 | 15.3153 ± 6.3002 |
| quantum selected D+A | 14.8489 ± 6.8553 | 14.0455 ± 5.4741 |
| softmax D | 13.1269 ± 5.5852 | 12.3434 ± 4.7720 |
| softmax selected D+A | 10.8337 ± 4.0778 | 10.1645 ± 4.5358 |
| network D | 13.8587 ± 5.6859 | 13.2621 ± 5.4056 |
| network selected D+A | 10.6690 ± 4.7833 | 10.0372 ± 4.0598 |

## What the aggregate improvement misses

The fresh-stream means below average the two 32-path streams; the real reference is
the validation block. The short-input quantum model still misses weekly persistence.
A improves the weighted aggregate, without restoring that missing structure.

| Series/model | ACF 1 | ACF 7 | ACF 30 | SD of log-RV changes |
| --- | ---: | ---: | ---: | ---: |
| Real validation | .613299 | .382667 | .078592 | .693399 |
| Quantum D | .550450 | .009958 | −.003286 | .804886 |
| Quantum D+A, λ=.05 | .560334 | .011979 | −.006487 | .797530 |
| Full HAR reference | .520090 | .257025 | .042493 | .796023 |

The B point-model result did not prove that weekly/monthly information is useless
for probability forecasting. Full HAR has better NLL (.930155) and fresh mean moment
distance (8.6187), with different information and a different model family. This
comparison cannot isolate the causal effect of longer history. Keep it in Step 4,
alongside GARCH and dedicated HAR quantile regression, and include a matched full-input
D control if revisiting memory. Do not silently switch the selected short-input design.

The softmax-selected lambdas .05 and .2 have almost equal validation composite scores
(1.112619 versus 1.112570). Treat that particular lambda choice as fragile. The fresh
streams do not justify changing the selection after seeing them.

## Training work and limits

| Family / stage | Fits | Optimizer success | Objective calls | Independent diagnostic calls | Fit wall seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| quantum / D | 20 | 20/20 | 135,436 | 720 | 350.943 |
| quantum / A | 9 | 9/9 | 686 | 0 | 44.778 |
| softmax / D | 5 | 5/5 | 2,375 | 90 | 1.300 |
| softmax / A | 9 | 9/9 | 484 | 0 | 10.740 |
| network / D | 5 | 1/5 | 248,332 | 240 | 178.750 |
| network / A | 9 | 9/9 | 1,547 | 0 | 32.699 |

Total: **388,860 objective calls + 1,050 stationarity calls**, 619.210 fit wall seconds.
Timing excludes saved-path evaluation/auditing and is specific to this machine and
its default numerical-library thread settings (no thread-limit environment variables).
Different models/search grids are not compute-matched: quantum has four depths,
softmax 9 identifiable coordinates, network 24 stored coordinates. The quantum count
8L−2 is only an upper bound on effective dimension. Short AR has 3 fitted coefficients
plus an empirical residual sample; HAR has 4 plus residuals; frequency has 3 free probabilities.

All training-selected D setting winners pass optimizer status plus the independent
1e−4 gradient threshold. This does not mean all restarts converged or global optima were found.
Four network starts hit the requested call ceiling (some numerical-gradient calls
overshoot it). Its training-selected start passes; its alternative starts remain
budget-limited. Do not portray the classical comparison as fully exhausted.

COBYLA radius termination on a discrete fixed-stream objective is not smooth
stationarity or a global certificate. A can fit the particular sampled training histories.
Fresh simulation audits measure this sensitivity; they do not undo validation reuse.
Path horizons differ from the 177-day validation reference, introducing finite-sample
moment effects. No 20-seed uncertainty study, GARCH, dedicated HAR quantile regression,
physical-unit risk validation, complete tail/MFDFA study or report/slides was completed here.

Author inputs were independently standardized upstream, potentially using the full sample.
Empirical within-bin sampling and Gaussian return innovations constrain generated
support/tails. These results cannot establish quantum advantage.

## Verification and repeat commands

- **59 tests passed**, including the original `qvol/` suite; Ruff lint and format passed.
- Independent artifact verification passed for **60 records, 42,360 probability rows**
  (maximum dense-gate error **7.77e−16**) and **628,224 recursive output days**.
- Validation scores, calibration, both selection stages, training objectives, fresh
  simulation statistics and data/package hashes were recomputed. No test scores exist
  in these artifacts.
- Both exported figures were inspected; the run, verifier and plots completed.


Independent dense 4×4 gate calculations, recursive random-draw replay, saved scores,
selection and source/data hashes are checked by the verifier. Unit/integration checks
cover future isolation, short inputs, phase removal and deliberate artifact tampering.

```bash
uv run python scripts/run_distribution_study.py \
  --author-data data/raw/author --output results/distribution-study-repeat
uv run python scripts/verify_distribution_study.py results/distribution-study-2026-10-20 \
  --author-data data/raw/author
uv run python scripts/plot_distribution_study.py results/distribution-study-2026-10-20
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
```

Use a new output directory. The package source hashes must match when verifying.
The plotter writes `distribution-study.png` and `distribution-scorecard.png` in the
ignored run directory. Measured tables are tracked here; raw arrays remain local.
