# Frozen 20-seed study: measured results

Executed 20 October 2026 under the [frozen protocol](final-study-protocol.md). This is
a fixed-method comparison after the B decision and Steps 3/4 development. The project
report/slides remain paused. Twenty seeds reuse one historical market period; they
measure training/simulation variability, not twenty independent datasets. Earlier
smoke experiments inspected the test block, so it is not a pristine unseen dataset.

## What the study establishes

**No quantum advantage is demonstrated.** HAR quantile regression has the lowest mean
test NLL (.528910), followed by HAR residual (.529544). The properly trained network D
(.578365) and softmax D (.582168) also beat quantum D (.691983) on this period.
Information and capacity differ across models, so these are observed comparisons.

**A's validation improvement does not carry over to the test comparison.** Quantum
NLL worsens .691983 → .862279, and mean test moment distance worsens 19.7151 →31.8644.
Both prescribed date-bootstrap intervals for its A−D NLL difference exclude zero.
Softmax/network A also worsen both mean metrics, but their A−D NLL intervals include
zero. Preserve these failures; do not select a new realism weight against this test.

The metric ranking varies: calibrated GARCH has the smallest shared-law test moment
distance (10.7134), despite weaker forecast NLL (.769469). Quantum's earlier validation
Brier edge also disappears: softmax D scores .010221 versus quantum D .015006. Only
three extreme-bin test events limit calibration conclusions. Native HAR's nominal 90%
interval covers just 79.7% of test observations; shared-bin coverage is lower still.

The 30-day bootstrap intervals for quantum D minus HAR quantile and softmax D include
zero, unlike the 7-day intervals. Do not claim universal statistical superiority from
one reused period. The separate point-MSE panel favors persistence over the paper circuit.

## Completion and provenance

- Kind: `final`; **20 seeds**; **240 forecast records** and **260 simulation records**.
- **8,519,680 simulated output days**, each model/seed 32×1024 days after 100 burn-in.
- Training package checkpoint: `a7951a8800dd5d9cbeaa64d686ac76454af4bc5c`; source/config/data/training-file hashes are sealed.
- All training was completed before sealing and test scoring. Seal: `cce04c8d38642b8545275fbcb192e8c639184b0a06e8be94d8a42135c6689b78`.
- Author source commit `2fec7ee621006bcbe1b7860d05b9589a7276a8f6`; 913 input rows, 529/177/177 train/validation/test targets.
- Transformations, bins/pools and residual samples use training rows only; no refit on validation.
- Fresh seed schedules, fixed depth/lambda/ridge; no test-selected restart or hyperparameters.
- Six deterministic models fitted once, then evaluated with independent simulation streams per seed.
- Original paper implementation credit: Nidhi in `qvol/`; the additional paper audit remains PR #2.

## Primary forecast scorecard

Numbers are **mean ± sample SD across training seeds**. Deterministic baseline losses
repeat by design; their zero seed SD is not zero uncertainty over market dates. The
primary NLL averages losses of separate trained models, not a probability ensemble.

| Model | Test NLL ↓ | Normalized RPS ↓ | Extreme-bin Brier ↓ | D / stage checks passed |
| --- | ---: | ---: | ---: | --- |
| har-quantile | 0.528910 ± 0.000000 | 0.057937 ± 0.000000 | 0.014739 ± 0.000000 | 20/20 · 20/20 |
| har-residual | 0.529544 ± 0.000000 | 0.058904 ± 0.000000 | 0.016086 ± 0.000000 | 20/20 · 20/20 |
| network-D | 0.578365 ± 0.000867 | 0.068898 ± 0.000263 | 0.010755 ± 0.000179 | 20/20 · 20/20 |
| softmax-D | 0.582168 ± 0.000000 | 0.067793 ± 0.000000 | 0.010221 ± 0.000000 | 20/20 · 20/20 |
| short-ar | 0.586611 ± 0.000000 | 0.068786 ± 0.000000 | 0.013311 ± 0.000000 | 20/20 · 20/20 |
| network-A | 0.611811 ± 0.047519 | 0.070642 ± 0.005104 | 0.012985 ± 0.001563 | 20/20 · 20/20 |
| softmax-A | 0.612298 ± 0.049036 | 0.069832 ± 0.006151 | 0.011890 ± 0.002406 | 20/20 · 20/20 |
| short-quantile | 0.618842 ± 0.000000 | 0.068331 ± 0.000000 | 0.012715 ± 0.000000 | 20/20 · 20/20 |
| quantum-D | 0.691983 ± 0.029139 | 0.085561 ± 0.001523 | 0.015006 ± 0.002277 | 20/20 · 20/20 |
| garch-calibrated | 0.769469 ± 0.000000 | 0.091622 ± 0.000000 | 0.016339 ± 0.000000 | 20/20 · 20/20 |
| quantum-A | 0.862279 ± 0.127900 | 0.110625 ± 0.021638 | 0.018621 ± 0.008851 | 20/20 · 20/20 |
| frequency | 1.196881 ± 0.000000 | 0.179594 ± 0.000000 | 0.017824 ± 0.000000 | 20/20 · 20/20 |

Full HAR has previous RV horizons 1/7/30; the learned models and short controls have
previous-day log RV/return. GARCH uses return history plus a persistent variance state.
Finance/native losses, capacities, information and training effort differ; this is not
a parameter/compute/information-matched advantage claim. Failed selected fits remain in
all-seed scores; passing-only NLL statistics are saved as a sensitivity summary.

## A versus D: keep both forecast and realism changes

| Family | D NLL | A NLL | Paired mean A−D NLL ↓ | D / A mean moment distance ↓ | A / D distance ratio |
| --- | ---: | ---: | ---: | --- | ---: |
| quantum | 0.691983 | 0.862279 | +0.170296 | 19.7151 / 31.8644 | 1.6162 |
| softmax | 0.582168 | 0.612298 | +0.030130 | 21.9047 / 37.1427 | 1.6956 |
| network | 0.578365 | 0.611811 | +0.033446 | 17.5718 / 36.2835 | 2.0649 |

A settings are fixed from validation: quantum .05, softmax .2, network .05; network
ridge remains .001. A is not selected again against D using test results. Its stopping
check is COBYLA radius termination, not a global/nonsmooth stationarity certificate.

### Why matching the training moments is insufficient

As a **post-hoc explanatory diagnostic**, measure the saved fresh-stream mean moments
against the training target instead of the test target, retaining the same training
scales. Distances improve D→A: quantum 18.0543→13.1667, softmax 15.7435→9.1571,
network 20.2287→9.7350. This is consistent with A moving toward its training-statistic
target while the test period has different dynamics; it is not a new primary success
metric or proof of a causal explanation. No settings were changed following this check.

For example, SD of log-RV changes is .6834 in training, .6934 in validation and .9293
in test. Quantum A generates .7518, versus D .7995. A therefore moves away from the
test-period target on this component. Weekly ACF remains .0250 versus test .4583;
the short-input circuit still misses persistent weekly structure.

## Separate date uncertainty: paired circular block bootstrap

Losses are averaged over training seeds at each test date, then the same date blocks
are resampled for paired model differences. 2,000 replicates per block length. Negative
differences favor the left model. Both prescribed block lengths are shown; no p-values
or universal-significance claim is made on this single, previously inspected period.

| Left − right | Mean NLL difference | 7-day 95% percentile interval | 30-day interval |
| --- | ---: | --- | --- |
| quantum-A − quantum-D | +0.170296 | [+0.109495, +0.237382] | [+0.080217, +0.276375] |
| softmax-A − softmax-D | +0.030130 | [-0.006046, +0.068513] | [-0.006219, +0.065204] |
| network-A − network-D | +0.033446 | [-0.006970, +0.076213] | [-0.007740, +0.071933] |
| quantum-D − softmax-D | +0.109815 | [+0.013909, +0.226324] | [-0.013978, +0.267887] |
| quantum-D − network-D | +0.113618 | [+0.027795, +0.221974] | [+0.003673, +0.264917] |
| quantum-D − har-quantile | +0.163073 | [+0.017979, +0.301074] | [-0.016212, +0.343167] |
| quantum-A − softmax-A | +0.249981 | [+0.103976, +0.421280] | [+0.054093, +0.511611] |
| quantum-A − network-A | +0.250468 | [+0.114967, +0.417515] | [+0.065511, +0.503622] |

## Quantiles and calibration

Test class counts (calm/normal/wild/extreme): **[142, 26, 6, 3]**.
Extreme-bin Brier/calibration differences have limited event counts. Coverage is an
observed fraction, not a guarantee. All calibration bins/quantile losses are retained.

| Common empirical-bin law | Mean pinball ↓ | 90% coverage | 90% interval score ↓ |
| --- | ---: | ---: | ---: |
| frequency | 0.441795 ± 0.000000 | 0.468927 ± 0.000000 | 12.950157 ± 0.000000 |
| garch-calibrated | 0.343959 ± 0.000000 | 0.531073 ± 0.000000 | 10.182911 ± 0.000000 |
| har-quantile | 0.292789 ± 0.000000 | 0.615819 ± 0.000000 | 8.078231 ± 0.000000 |
| har-residual | 0.294768 ± 0.000000 | 0.610169 ± 0.000000 | 8.238734 ± 0.000000 |
| network-A | 0.301747 ± 0.008324 | 0.585311 ± 0.012214 | 8.375380 ± 0.295896 |
| network-D | 0.303362 ± 0.000324 | 0.610169 ± 0.000000 | 8.457427 ± 0.004471 |
| quantum-A | 0.360844 ± 0.026865 | 0.577119 ± 0.018985 | 10.614309 ± 0.970958 |
| quantum-D | 0.331473 ± 0.002341 | 0.609322 ± 0.002070 | 9.566431 ± 0.120691 |
| short-ar | 0.304816 ± 0.000000 | 0.615819 ± 0.000000 | 8.503972 ± 0.000000 |
| short-quantile | 0.302665 ± 0.000000 | 0.604520 ± 0.000000 | 8.433583 ± 0.000000 |
| softmax-A | 0.300521 ± 0.008596 | 0.587853 ± 0.013151 | 8.336562 ± 0.275097 |
| softmax-D | 0.301892 ± 0.000000 | 0.598870 ± 0.000000 | 8.400715 ± 0.000000 |

| Native finance law | Mean pinball ↓ | 90% coverage | 90% interval score ↓ |
| --- | ---: | ---: | ---: |
| garch-calibrated | 0.329804 ± 0.000000 | 0.553672 ± 0.000000 | 9.648066 ± 0.000000 |
| har-quantile | 0.180538 ± 0.000000 | 0.796610 ± 0.000000 | 4.063432 ± 0.000000 |
| short-quantile | 0.214676 ± 0.000000 | 0.677966 ± 0.000000 | 5.746578 ± 0.000000 |

Native HAR QR intervals do not depend on the interpolated/exponential-tail bin
conversion used for its categorical scores. Common-bin quantiles invert the same RV
sampling law for every model. GARCH is calibrated from return variance to log RV using
only training rows; it does not recover original physical units.

## Recursive histories and remaining moment gaps

Generated histories start at the end of training and feed on their own outputs. They
are unconditional histories, not trajectories conditioned on the actual test sequence.
Compare 1024-day generated samples with a 177-day reference cautiously: sampling horizon
and market-period differences affect moment discrepancies. All 32 paths contribute.

| Model | Distance of mean moments ↓ | Mean individual-path distance ↓ | ACF 1 | ACF 7 | ACF 30 | SD of log-RV changes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Real test | — | — | 0.671287 | 0.458337 | -0.055153 | 0.929252 |
| frequency | 80.450206 ± 3.226634 | 81.578612 ± 3.143328 | -0.000213 | -0.002332 | -0.000315 | 1.209419 |
| garch-calibrated | 10.713356 ± 0.761406 | 16.266764 ± 0.852387 | 0.454767 | 0.429929 | 0.354495 | 0.985967 |
| har-quantile | 18.017690 ± 0.885677 | 18.705887 ± 0.877463 | 0.531830 | 0.267830 | 0.053241 | 0.782808 |
| har-residual | 15.776192 ± 0.768947 | 16.520815 ± 0.761996 | 0.524865 | 0.266609 | 0.045749 | 0.793854 |
| network-A | 36.283539 ± 9.184564 | 36.987513 ± 9.196719 | 0.576771 | 0.041624 | -0.008310 | 0.729775 |
| network-D | 17.571767 ± 0.814664 | 18.263822 ± 0.816535 | 0.550224 | 0.012764 | -0.006731 | 0.811483 |
| quantum-A | 31.864407 ± 12.220853 | 32.676968 ± 12.123028 | 0.538623 | 0.024982 | -0.005615 | 0.751801 |
| quantum-D | 19.715096 ± 0.830919 | 20.394901 ± 0.884407 | 0.554012 | 0.012603 | -0.005668 | 0.799469 |
| short-ar | 24.061493 ± 0.876194 | 24.618808 ± 0.867207 | 0.572312 | 0.016764 | -0.004783 | 0.776979 |
| short-quantile | 25.191579 ± 0.916897 | 25.724082 ± 0.902872 | 0.580890 | 0.019638 | -0.004864 | 0.771329 |
| softmax-A | 37.142746 ± 9.212964 | 37.762246 ± 9.215729 | 0.578004 | 0.050253 | -0.004659 | 0.725917 |
| softmax-D | 21.904729 ± 0.870825 | 22.525837 ± 0.902130 | 0.565630 | 0.019375 | -0.006360 | 0.786868 |

Native GARCH is separately labelled: mean distance 15.2111; different observation law/support prevents a matched-generator claim.
Empirical bins bound generated RV by the training pools. Long generated histories
cannot establish realistic unseen extremes or general tail extrapolation. Physical
VaR remains unavailable because the author standardized return/RV units separately.

## MFDFA and tails: diagnostic scope

Use path zero fixed in advance in each seed, cubic two-ended MFDFA and q−5…5; grey
crosses in the figure are shuffled controls. Finite-path estimates do not reproduce
or replace the audited paper’s 50,000-step scaling protocol.

| Model | Log-RV-change h(2) | Shuffled change h(2) | Return h(2) | Shuffled return h(2) |
| --- | ---: | ---: | ---: | ---: |
| quantum-D | 0.119426 ± 0.013106 | 0.505605 ± 0.046317 | 0.499409 ± 0.036830 | 0.502834 ± 0.048073 |
| quantum-A | 0.120152 ± 0.027016 | 0.505241 ± 0.052281 | 0.498130 ± 0.031503 | 0.508966 ± 0.047486 |
| softmax-A | 0.138433 ± 0.025072 | 0.487340 ± 0.039441 | 0.499219 ± 0.031198 | 0.509424 ± 0.055360 |
| network-A | 0.136884 ± 0.020085 | 0.520335 ± 0.044977 | 0.492696 ± 0.035893 | 0.504631 ± 0.045813 |
| har-quantile | 0.124736 ± 0.013527 | 0.496081 ± 0.046494 | 0.498243 ± 0.041038 | 0.502693 ± 0.048726 |
| garch-calibrated | 0.058874 ± 0.009412 | 0.490809 ± 0.043525 | 0.496572 ± 0.045753 | 0.500308 ± 0.036323 |

All-path generated return Hill indices and Wasserstein statistics are saved with
counts/SD. The real test has only 177 returns, so its Hill index is **unavailable**
under the ≥200 rule. No generated-vs-real tail superiority is inferred.

## Separate raw-RV point reference

| Model | Test RV MSE, mean ± seed SD |
| --- | ---: |
| paper | 0.000304 ± 0.000000 |
| persistence | 0.000267 ± 0.000000 |
| raw-har | 0.000320 ± 0.000000 |
| training-mean | 0.000941 ± 0.000000 |

The original paper fits two observable angles (stored phi fixed to zero). Point MSE
uses author RV units and is not compared numerically with categorical NLL. The B
extension’s earlier negative validation result is carried forward as a development
decision, not relabelled as a new 20-seed memory experiment.

## Complete training effort and status

All **300 D fits** and **100 paper fits** pass solver status and independent gradient
checks. All **180 A fits** terminate by the prescribed COBYLA radius. Every selected
seed passes its applicable check. Finance LP/recurrence/stationarity checks also pass;
passing-only summaries therefore agree with the complete selected-fit scorecard.

| Training group | Fits | Objective calls | Diagnostic calls | Fit wall seconds | LP solves |
| --- | ---: | ---: | ---: | ---: | ---: |
| quantum-D | 100 | 273,963 | 2,800 | 294.053 | 0 |
| quantum-A | 60 | 5,002 | 0 | 437.181 | 0 |
| softmax-D | 100 | 47,424 | 1,800 | 17.336 | 0 |
| softmax-A | 60 | 3,399 | 0 | 97.546 | 0 |
| network-D | 100 | 16,869 | 4,800 | 13.168 | 0 |
| network-A | 60 | 9,837 | 0 | 303.603 | 0 |
| paper-point | 100 | 6,595 | 400 | 12.688 | 0 |
| frequency | 1 | 0 | 0 | 0.000 | 0 |
| short-ar | 1 | 0 | 0 | 0.001 | 0 |
| har-residual | 1 | 0 | 0 | 0.000 | 0 |
| har-quantile | 1 | 0 | 0 | 0.598 | 15 |
| short-quantile | 1 | 0 | 0 | 0.460 | 15 |
| garch-calibrated | 5 | 711 | 0 | 0.218 | 0 |

Total recorded iterative objective calls: **363,800**, plus **9,800** independent diagnostics and **30 LP solves**.
Summed recorded fit seconds: **1176.850**. Raw-RV HAR adds one closed-form solve (not timed separately).
All restarts are charged, not only winners. Neural D calls include an analytic gradient;
quantum/softmax D use numerical gradients, A uses simulations, GARCH uses a different
likelihood, and LP iterations are different work. These are not equivalent FLOPs.
OPENBLAS_NUM_THREADS=1 and OMP_NUM_THREADS=1; timings are not a hardware-advantage claim.
Earlier development costs remain in the Step 3/4 notes and are not hidden as final-fit work.
At depth two, quantum has 16 historical stored /14 searched angles; softmax 9; neural 24;
HAR QR 60 /short QR45; GARCH3+2 plus residuals; OLS residual models also retain529 samples.

## Verification and repeat commands

Independent verifier passed **42,480 forecast probability rows**, max dense error **6.66e-16**, and **8,519,680 recursive output days**.
It reconstructs gates, training losses/gradients/restart selections, finance certificates,
all forecasts and quantiles, all simulated paths, independent polynomial MFDFA and the
exact paired bootstrap. Sealed training/source/data hashes are checked first. Unit tests
reject changed training artifacts, future-data leakage and corrupted uncertainty results.
The complete suite passes **81 tests**; Ruff lint/format and whitespace checks pass.

Raw artifacts/plots/CSV remain local and ignored under
`results/final-study-2026-10-20/evaluation`. The six figures were visually inspected.

```bash
uv sync --all-extras
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 uv run python scripts/run_final_study.py \
  --author-data data/raw/author --output results/final-study-repeat
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 uv run python scripts/verify_final_study.py \
  results/final-study-2026-10-20 --author-data data/raw/author
uv run python scripts/plot_final_study.py results/final-study-2026-10-20 --author-data data/raw/author
```

Use a new output directory. Frozen training can be evaluated separately with `--stage evaluate`
and a new `--evaluation-name`; this does not authorize retuning after observing the test.
Unavailability/failed-fit counts and all original seed values remain part of the evidence.
The final study is complete for this protocol; the project report/slides remain paused.
