# Frozen final-study protocol

Declared 20 October 2026 before this study's training or scoring. This is the final
20-seed distribution comparison after the B decision and Steps 3/4 development. The
project report remains paused. Do not revise this protocol after observing test results;
record any implementation repair explicitly and preserve prior artifacts.

## Questions, data and limits

Primary forecast metric: test categorical NLL. Also report normalized RPS, extreme-bin
Brier/calibration, empirical-bin quantile pinball, 90% interval coverage/width/score.
HAR quantile/GARCH native quantiles receive a separate panel. Primary realism summaries:
distance of mean generated moments and average individual-path distance; also ACF 1/7/30,
SD of log-RV changes, Wasserstein and return-tail diagnostics. No composite test ranking
or test-selected hyperparameters. Point-RV MSE is a separate baseline panel.

Use author source commit `2fec7ee621006bcbe1b7860d05b9589a7276a8f6`, all 913 aligned
rows, 30 history days, and unchanged eligible split 529 train /177 validation /177 test.
Keep training-only scaler, bins/pools and residual samples. Do not refit on train+validation.
Validation has already selected settings below; do not use it for further selection.
Earlier smoke work inspected this test block, so it is not a pristine unseen dataset.
Upstream independent standardization may use the full sample; physical-unit risk remains
unavailable. This is one period/dataset, not evidence of universal model superiority.

## Fixed models and optimization

For each of **20 seeds (0–19)** fit D models with **five fresh starts**:

- Quantum: ShortBorn, **two layers**, 16 stored historical coordinates, terminal two
  phases fixed to zero, **14 searched**. Input policy repeats previous-day standardized
  log RV in three slots and previous return in the fourth. Use existing central-gradient
  L-BFGS-B, 50,000 requested calls /2,000 iterations, gtol 1e−6, ftol 1e−13.
- Short softmax: reference-logit model, **9 coordinates**, same information and optimizer.
- Short network: existing **24-coordinate** model, **ridge alpha=.001 on all coordinates**,
  analytic L-BFGS-B, 20,000 joint calls /10,000 iterations, gtol 1e−7, ftol 1e−14.

D restart selection minimizes training objective (NLL plus ridge for network). Require
optimizer success and independent central-gradient infinity norm ≤1e−4 for a passing
training check. Do not hide failures or choose a higher-loss passing restart instead.
Evaluate every seed's preselected result, flag failures, and give a converged-only
sensitivity summary alongside all-seed primary summaries if failures occur.

From each selected D fit train A with fixed weights: **quantum .05, softmax .2,
network .05**. Keep network ridge in A. Three starts: exact D plus two Gaussian .03
jitters. Existing COBYLA radius .3→.002, 600 evaluations plus initial check; four
128-day training paths, 60 burn-in. Use training moments/scales only. Choose restart
on penalized training loss; no validation/test choice and no lambda-zero fallback
selection after results. D remains an explicit separate ablation. COBYLA success is
radius termination, not a certificate of nonsmooth global optimality.

Fit deterministic finance/control models **once**, not identically twenty times:
frequency, short AR residual CDF, full HAR residual CDF, full/short HAR quantile LPs
(15 quantiles, 60/45 coefficients), calibrated Gaussian GARCH (five starts, three variance
plus two RV-calibration coefficients). Preserve Step 4 LP certificates, GARCH recurrence/
KKT checks, observation laws and tail conventions unchanged. Deterministic forecast
scores repeat across seeds; zero across-seed SD is not zero market uncertainty.
Information and capacity differ, especially full HAR and return-history GARCH. No
compute/information/parameter-matched advantage claim. Report actual complete costs.

Paper reference: original one-qubit point circuit, five uniform starts per seed,
COBYLA 10,000 calls, two searched angles (stored phi zero), train MSE restart choice,
status and central-gradient ≤1e−5 check. Compare test raw-RV MSE separately with
persistence, training mean and raw-RV HAR OLS. Nidhi's original implementation remains
credited; this is a held-out reference, not an assertion of original authorship.
The previously rejected B point extension is not repeated as a new 20-seed memory claim.

## Randomness, staging and preservation

Seeds are run labels. D initialization RNG =100000+100×seed+restart; paper initialization
=200000+100×seed+restart; A jitter =300000+100×seed+restart. Common training draws use
400000+seed, evaluation draws 500000+seed. All models share the evaluation stream per
seed for paired Monte Carlo comparisons. Bootstrap RNG=600000; shuffle diagnostics
use 700000+1000×seed+model index. These streams differ from development streams.

Stage 1 fits and saves all restarts, training status/history, baselines and selected
parameters for all seeds. Seal hashes of config, source, data, baseline and per-seed
artifacts **before** the runner accesses test scores. Stage 2 only loads the seal;
changing any training artifact/config/source must fail scoring. Save predictions,
quantiles, daily losses and complete paths. A failed stage may be inspected; trained
sealed output can be evaluated without refitting. Never overwrite a completed evaluation.
Raw results remain ignored; tracked measured notes contain summaries and source checkpoints.

## Simulations and diagnostic scope

Each model/seed: **32 paths×1024 output days, 100 burn-in**, initialized from the last
30 training days. They are unconditional recursively generated histories, not paths
conditioned on test observations. Compare to test moments with training-fitted scales;
finite sample/horizon effects remain. Shared categorical/empirical-bin observation law
is primary. GARCH additionally gets a separately labelled native path-law reference.

Compute moments, Wasserstein and Hill estimates on all 32 paths. MFDFA and shuffled
controls use **path zero, fixed in advance**, per seed/model, to keep laptop cost
reasonable. Use existing cubic/two-ended/q−5…5 diagnostic defaults, on log-RV changes
and returns; no paper-grade scaling-range claim. Do not pool short paths into a false
long sequence. Test returns have only 177 days, so their Hill index is unavailable
under the ≥200 rule; preserve unavailable values. Author units prevent physical VaR.
Empirical bins bound simulated RV support; long histories cannot establish realistic
unseen extreme tails. Native GARCH is a different support/law reference.

## Summaries and uncertainty

Report mean, sample SD, min/max and valid counts across 20 seed scores; save all raw
seed values and passing-training counts. For A−D and quantum−classical NLL contrasts,
use daily loss differences averaged over training seeds, and **paired circular moving-
block bootstrap**, 2,000 replicates, fixed blocks **7 and 30** days. Same resampled
dates across all models/contrasts; show 2.5/97.5 percentiles, not multiple-test p-values.
These descriptive intervals concern one reused historical test period and do not turn
20 random initializations into 20 independent market samples. Report seed variability
and date-block uncertainty separately. Undefined diagnostics keep null/valid counts.

Final figures: forecast/quantile/calibration scorecards, A−D ablations and bootstrap
intervals, forecast curves, realism/moment gaps, path diagnostics and training effort.
Keep results where classical models win, GARCH fails, or A harms forecasting. Verify
all forecasts, scores, restart/gradient choices, seeded trajectories and seal/provenance;
independently recompute uncertainty and reject deliberate artifact tampering in tests.
This run is final for the declared protocol; negative results do not justify retuning
to the same test block. Hardware and transfer remain optional extensions.
