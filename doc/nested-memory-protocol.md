# Baseline preserving memory follow-up protocol

This is the focused B follow-up requested after PR #3. It will decide whether the
next distribution experiment should retain longer history. It does not run the
20-seed final study, score test targets, resume the project report, or claim quantum advantage.

## Model and identity

Preserve the paper's encoded state E(r,v)|0>. Apply a weekly RY and monthly RZ,
then its trainable U3 readout. The four optimized coordinates are theta, lambda,
a and b; the unobservable final phi stays zero. In matrix order:

`U3(theta,0,lambda) @ RZ(b*x_month) @ RY(a*x_week) @ E(r,v) @ |0>`.

At a=b=0, this is exactly the original probability readout for every input and any
paper phi. Keep the same original return/RV scaling and domain handling. Weekly
and monthly features are standardized means of past log RV, using training-fitted
transforms. The short-memory control uses standardized yesterday log RV in both
new gate slots. Both extensions have four optimized coordinates and the same
regularizer, starts and budget. Their input ranks can differ, so identical nominal
counts do not establish equal effective capacity.

## Fixed training and selection rules

The checked-in `configs/nested-memory.json` declares the measured run:

- Keep 913 author observations, 30-day warm-up and 529/177/177 chronological split.
  Use only the first two splits for this investigation. Upstream rescaling may
  still contain full-sample information; this cannot be repaired by later transforms.
- Fit the paper on training targets with five broad uniform starts, seeds 0–4,
  two active angles, a 10,000-evaluation ceiling and the existing COBYLA settings
  rhobeg .3 and trust-region tolerance 1e-5. Choose the lowest training objective.
- Initialize both extensions from that fitted paper. Seed 0 uses exactly zero new
  weights; seeds 1–4 perturb only the two new weights with N(0,.05).
- For each family and each penalty in {0, .0001, .001, .01, .1, 1}, train all five
  starts afresh. Minimize normalized RV MSE + alpha*(a*a+b*b). Penalize only the
  new memory weights. The theta/lambda baseline is free to refit. Every setting
  includes the exact zero-weight baseline as an initial candidate.
- Select the restart by penalized **training** objective, then select alpha by
  **validation** RV MSE. Never choose a restart by its validation score. Include
  the unextended paper as a hard zero-weight fallback in each family's selection.
- Retain all runs. A setting is eligible only if its training-selected fit reports
  optimizer success and a central-difference gradient infinity norm <=1e-5
  (difference step 1e-5). If any setting fails this check, the B decision is
  inconclusive until convergence is resolved. A success flag is not a global-optimum proof.
- Accept longer memory provisionally for the next development stage only if its
  validation-selected setting improves at least 1% over the better of the paper
  and short-memory control. Otherwise retain previous-day inputs. The 1% rule
  is a practical development threshold, not a statistical significance test.
- Record all optimizer calls including the extra initial check, separately count
  four/eight stationarity objective calls, record times and all convergence flags.
  Quantum hyperparameter search is more work than a single classical linear solve.

A small engineering probe checked training-only convergence before this protocol;
no validation result was inspected in that probe. The declared grid and decision
rule are fixed before the measured sweep. Validation has already been used during
project development, so this remains exploratory even when every fit converges.

## Classical comparison

Fit a classical HAR point forecaster by OLS on raw RV horizons 1, 7 and 30 plus
an intercept, with training-only feature standardization. Forecasts are truncated
at zero for nonnegative RV. This is the crypto-calendar adaptation of HAR-RV;
the circuit uses log-horizon inputs, a bounded nonlinear map and a different loss
when regularized. Equal parameter counts do not make these families equivalent.
This point forecaster is separate from the existing log-HAR residual-CDF model.
Also report the training-mean constant and yesterday-RV persistence controls.
All scores are MSE in the same author-standardized RV units. No return-risk claim
is made from those independently rescaled source files.

HAR background: F. Corsi, A Simple Approximate Long-Memory Model of Realized
Volatility, Journal of Financial Econometrics 7(2), 174–196 (2009),
[doi:10.1093/jjfinec/nbp001](https://doi.org/10.1093/jjfinec/nbp001).
The 7/30 horizons are this project's adaptation for continuously traded crypto.

## Evidence and next action

Test the zero-weight identity at arbitrary paper parameters and both control
modes, compare nonzero weights with literal matrix multiplication, verify the
warm start and penalty, compare HAR with an independent least-squares construction,
and perturb all future test values to check that fits and selection cannot change.
Save every train/validation prediction and loss history. Independently recompute
predictions, penalties, stationarity and selection before documenting the decision.

If longer memory fails this controlled comparison, record the negative result,
retain the better simpler-input reference and move to D, then A, as separate
experiments. If it passes, retain B provisionally and carry its controls forward.
A final independent test study and variability analysis remain required either way.

## Convergence amendment before the repeated sweep

The first measured run used COBYLA trust-region tolerance 1e-5 for both extensions
(commit cd40d08, local `results/nested-memory-2026-10-19/`). All 65 fits reported
optimizer success, but the alpha=1 training-selected fits failed the fixed gradient
threshold: about 1.21e-5 and 1.53e-5. Its recorded decision is **inconclusive**.

Repeat the complete identical grid using nested-model trust-region tolerance 1e-7;
keep the baseline's established 1e-5 tolerance. Keep the 10,000 ceiling, all starts,
penalties, validation rule and gradient threshold unchanged. This is a training
precision correction for both input sets, prompted by the independent stationarity
check. First-run validation scores were visible in its logs; no alpha, feature, seed,
split or acceptance-threshold change is made in response to those scores. Preserve
the first run and report both attempts' compute costs. The repeated run uses
`configs/nested-memory.json` with its explicit `optimizer_tolerance`. The historical
root experiment keeps its original default tolerance and results.
