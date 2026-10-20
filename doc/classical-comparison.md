# Step 4: measured classical comparison

**Outcome:** HAR quantile regression leads this validation NLL/RPS comparison. A properly
regularized short-input network is competitive with softmax and beats quantum D on NLL.
Calibrated Gaussian GARCH is weaker on this dataset. Quantum has a small extreme-bin
Brier advantage; no model wins every metric and no quantum advantage is established.

Executed 20 October 2026 under the [protocol and amendment](classical-comparison-protocol.md).
This is a development comparison on reused validation, with no new test predictions.
The final 20-seed study and project report are not part of this milestone. Nidhi’s original
paper implementation remains preserved in `qvol/`; additional paper validation is PR #2.

## Dataset, models and scorecard

Pinned author commit `2fec7ee621006bcbe1b7860d05b9589a7276a8f6`; 913 input rows,
529 training /177 validation /177 test targets, train-only scaling, bin edges and pools.
All teacher-forced forecasts use observations strictly before their target; parameters
are fixed after training. Reported scores do not imply independent statistical significance.

| Model | Validation NLL ↓ | Normalized RPS ↓ | Extreme-bin Brier ↓ | Mean moment distance, common-law audit ↓ |
| --- | ---: | ---: | ---: | ---: |
| quantum-prior-D | 0.997917 | 0.114690 | 0.025746 | 13.9870 |
| quantum-prior-A | 1.007528 | 0.114061 | 0.025573 | 12.8106 |
| softmax-prior-D | 0.979151 | 0.114794 | 0.026002 | 11.3368 |
| softmax-prior-A | 0.988795 | 0.115839 | 0.028535 | 8.7441 |
| short-ar | 0.977830 | 0.115015 | 0.029527 | 10.3610 |
| har-residual | 0.930155 | 0.106127 | 0.033200 | 7.7808 |
| har-quantile | 0.917290 | 0.105597 | 0.031349 | 6.7645 |
| short-quantile | 0.983815 | 0.115389 | 0.028480 | 9.1579 |
| garch-calibrated | 1.050928 | 0.127214 | 0.034706 | 70.1753 |
| network-refined-D | 0.979798 | 0.115122 | 0.026593 | 14.8233 |
| network-refined-A | 1.011488 | 0.116684 | 0.033040 | 7.0698 |

Moment distance averages the distances of mean moment vectors on two 32×512-day
simulation streams after 60 burn-in days. Per-path distances/spread are retained in
`audit.json`; an aggregate distance can hide missing weekly/long-range structure.

HAR models use RV horizons 1/7/30. Quantum, softmax, network and short controls use
previous-day log RV and return. GARCH uses past returns plus persistent filtered variance.
These are different information sets and capacities, not a controlled causal comparison
of history alone. The full-HAR result does not overturn the earlier matched B point-model
finding, and that B finding never established that history is useless for distributions.

## Quantile regression and uncertainty forecasts

HAR QR minimizes pinball loss directly at 15 declared quantiles; it is not OLS plus a
residual CDF. Independent LP primal/dual certificates pass at every quantile in both
full and short models. Predicted crossing quantiles are sorted before scoring. Native
intervals/quantiles are evaluated separately from the shared binned observation law.

| Native model | Mean pinball over 15 quantiles ↓ | 90% coverage | Mean 90% width | 90% interval score ↓ | Crossing validation rows before sorting |
| --- | ---: | ---: | ---: | ---: | ---: |
| har-quantile | 0.128507 | 0.841808 | 1.916984 | 2.758240 | 36 |
| short-quantile | 0.135453 | 0.841808 | 1.971524 | 2.883142 | 8 |
| garch-calibrated | 0.154691 | 0.836158 | 2.263009 | 3.473849 | — |

The nominal 90% native intervals cover only **84.2%** of this validation block for
HAR QR and the short QR control. Coverage is imperfect despite the favorable pinball
score. The common-bin HAR QR interval covers 87.0%. These are measured calibration
shortfalls, not validated 90% guarantees. The extreme-bin Brier comparison also has
few positive examples (7 of 177 validation targets); small differences need uncertainty
assessment in the final study.

For native HAR QR bin probabilities, invert interpolated sorted quantiles with declared
exponential tails and a training-scale floor, then mix 1e−6 of the training frequency law.
NLL depends on that observation-law choice; native pinball does not depend on its tails.

| Model under the common empirical-bin law | Mean pinball ↓ | 90% coverage | 90% interval score ↓ |
| --- | ---: | ---: | ---: |
| quantum-prior-D | 0.137192 | 0.864407 | 2.801345 |
| quantum-prior-A | 0.136654 | 0.858757 | 2.771198 |
| softmax-prior-D | 0.136924 | 0.847458 | 2.765167 |
| softmax-prior-A | 0.137445 | 0.847458 | 2.748336 |
| short-ar | 0.137692 | 0.858757 | 2.800035 |
| har-residual | 0.131617 | 0.875706 | 2.736218 |
| har-quantile | 0.130839 | 0.870056 | 2.695971 |
| short-quantile | 0.137600 | 0.864407 | 2.767525 |
| garch-calibrated | 0.154686 | 0.847458 | 3.339146 |
| network-refined-D | 0.137634 | 0.864407 | 2.793652 |
| network-refined-A | 0.137837 | 0.847458 | 2.781969 |

## GARCH meaning, alignment and generation

Gaussian zero-mean GARCH(1,1) is fitted to 529 target-row returns after division by
a training-only RMS; its backcast uses the 30 history returns. Five valid starts are
selected by training return likelihood, not validation RV. Library conditional variances
agree with the independent recurrence, and the chosen constrained-gradient check passes.

- Standardized-return GARCH (omega, alpha, beta): `[0.02707691732722345, 0.027452279561916083, 0.947089323962132]`.
- Sum alpha+beta: 0.974542; chosen KKT residual 1.23e-06.
- Observation calibration (a,b): `[3.0626789531419765, 2.032623288120921]`; 529 empirical training residuals.

Return variance h is **not** observed realized variance. Training OLS fits
log(RV)=a+b log(h in original return units)+empirical residual. The source independently
standardized returns and RV; this calibration does not recover original physical units.
Physical-unit return VaR remains unavailable. A weak result here does not establish that
GARCH is generally inferior; its Gaussian law and RV calibration are specific choices.

The primary path comparison uses the same categorical/empirical-bin RV sampler and
Gaussian return innovations as D/A, updating h with generated returns. A separate native
GARCH reference draws returns from its own h and RV from the calibrated observation law.
Do not treat its different support/observation law as a matched generator comparison.

| GARCH generation law | Stream 50000 distance | Stream 60000 distance |
| --- | ---: | ---: |
| garch-calibrated | 75.3454 | 65.0052 |
| garch-native-reference | 74.7936 | 67.2646 |

## Network conditioning and the refinement

The first attempt continued all five old network starts with exact analytic derivatives.
The best old start reaches gradient norm 6.21e−8, but four alternatives still exhaust
10,000 iterations. They remain failed/capped records; their cost is retained. Additional
iterations alone did not resolve ill-conditioning. The original unregularized validation
NLL remains about 1.1472; it is not representative of the strongest small classical model.

The declared amendment adds L2 alpha×sum(p²) on all 24 coordinates, with four positive
alphas and five fresh starts each. Each restart is chosen on penalized training loss,
alpha on validation NLL, with the continued unregularized winner as the zero fallback.
**20/20 regularized fits pass status and independent stationarity checks.**

| Ridge alpha | Training-selected start | Penalized training objective | Validation NLL | Selected |
| ---: | ---: | ---: | ---: | --- |
| 0 | 0 | 0.928256 | 1.147179 |  |
| 0.0001 | 3 | 0.943547 | 0.994048 |  |
| 0.001 | 3 | 0.968928 | 0.979798 | yes |
| 0.01 | 3 | 1.065144 | 1.000383 |  |
| 0.1 | 4 | 1.249797 | 1.158717 |  |

Validation selects alpha=.001 (start 3), producing NLL .979798. A is retrained from this
new D model while keeping the ridge term in its loss; old network A stays a separate
reference. The selected new realism weight is .05. Network A trades worse NLL
(1.011488) for a smaller fresh-stream mean moment distance (7.0698 versus D 14.8233).
This is a forecast/realism preference, not an unconditional improvement.

## Parameter counts and local sensitivity

| Learned model | Original/stored coordinates | Structurally removed | Searched | Local probability-Jacobian rank |
| --- | ---: | ---: | ---: | ---: |
| quantum-prior-D | 16 | 2 | 14 | 14 |
| quantum-prior-A | 16 | 2 | 14 | 14 |
| softmax-prior-D | 9 | 0 | 9 | 9 |
| network-prior-D | 24 | 0 | 24 | 20 |
| network-continued-D | 24 | 0 | 24 | 20 |
| network-refined-D | 24 | 0 | 24 | 24 |
| network-refined-A | 24 | 0 | 24 | 24 |

The two terminal quantum RZ directions are absent from fitting. At the selected two
layers, 16 stored historical angles become 14 searched coordinates. Rank uses relative
cutoff 1e−6 and absolute floor 1e−10 at the fitted training inputs. Old/continued networks
have numerical rank 20, while regularized fits have rank 24; this is local numerical
sensitivity, not a global identifiability theorem. Softmax uses a fixed fourth logit.

Finance counts: HAR QR **60 coefficients**, short QR **45**, GARCH **3+2 calibration**
plus 529 residual samples; HAR OLS **4** plus 529 residuals; short AR **3** plus 529
residuals; frequency **3** free probabilities. Tail scales and bin preprocessing are
training-derived additional state. These are not parameter-matched models.

## Training-work ledger and preserved attempts

| Attempt | Continued NN joint objective/gradient calls | Ridge joint calls | New A objective calls | GARCH objective calls | LP solves / iterations | Total fit wall seconds |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| classical-comparison-2026-10-20 | 43,825 | 0 | 1,382 | 711 | 30 / 16,056 | 66.951 |
| classical-comparison-refined-2026-10-20 | 43,825 | 2,900 | 1,542 | 711 | 30 / 16,056 | 88.691 |

Step 4 across both attempts: **94,896 recorded iterative objective calls**, 60 LP solves, 155.642 summed fit seconds.
The first attempt and repeated work are charged, not discarded. Joint analytic calls
include a gradient; these differ from numerical-gradient probability calls and LP
iterations in FLOPs. Diagnostics (240 continuation calls each attempt plus 960 ridge
calls in the refinement and saved local-rank diagnostics) are separate.

Inherited Step 3: 388,860 objective calls +1,050 stationarity calls, 619.210 fit seconds.
Including Step 4: **483,756 iterative objective calls**, with LP and additional
diagnostics separately reported. The original quantum search covered four depths; the
network adds a four-alpha search. Do not compare only the cost of the winning fit.
Step 4 sets OPENBLAS_NUM_THREADS=1 and OMP_NUM_THREADS=1; Step 3 used library defaults.
These wall times are not a controlled performance/hardware benchmark.

## Verification, artifacts and next stage

- **68 tests pass**, including end-to-end independent verification and deliberate LP/selection tampering; Ruff lint/format and whitespace checks pass.
- First attempt: **14 records, 2,478 probability rows, 491,520 fresh-audit output days** verified.
- Refined attempt: **15 records, 2,655 probability rows, 524,288 audit output days** verified.
- Maximum independent dense-gate forecast error: **4.44e−16**.
- Verification recomputes LP primal/dual certificates, GARCH likelihood/calibration/constraints,
  native/common quantiles and scores, gradients, restart/ridge/lambda selections, sensitivity
  ranks and complete audit draws. Both figure exports were visually inspected.
- Source checkpoints: `5749764` first attempt; `c0ae60b` refined model code. Historical source
  hashes can be checked against committed Git blobs. Prior artifact hashes are retained.
- Both attempts reuse streams 50000/60000; those draws are separate from training/selection
  streams but are not a new independent replication across attempts. No choices use audit scores.
- Reused validation, one historical dataset, upstream scaling, finite horizons and explicit
  observation-law choices limit inference. Earlier smoke test scores exist; no claim of a
  pristine never-inspected test block is made. No new test scores were computed here.

Next freeze a final-study protocol and integrate the validated models before running
20+ seeds. The historical `configs/study.json` remains the old HAR-input smoke-era
pipeline; it must not silently stand in for this validated short-input comparison.
Keep failed unregularized starts as diagnostic evidence while using the stable regularized
network as the main neural comparator. The project report/slides remain paused.

```bash
uv sync --all-extras
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 uv run python scripts/run_classical_comparison.py \
  --author-data data/raw/author --prior results/distribution-study-2026-10-20 \
  --output results/classical-comparison-repeat
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 uv run python scripts/verify_classical_comparison.py \
  results/classical-comparison-refined-2026-10-20 --author-data data/raw/author
uv run python scripts/plot_classical_comparison.py results/classical-comparison-refined-2026-10-20
```

The complete protocol/config is tracked; raw data, arrays and PNGs remain ignored.
Use new output directories. To retain the earlier attempt linkage when rerunning, pass
`--previous-attempt results/classical-comparison-2026-10-20`.
