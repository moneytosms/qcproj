# BTC market-signal quantum development protocol

## Purpose

Test whether adding a causal, market-wide volatility feature helps the weekend-aware
quantum HAR hybrid relative to classical models with exactly the same information. This
is validation-only development. ETH, BTC, SOL and DOGE test periods have already been
used and will not be read or rescored.

## Feature

For each target day, compute the mean of BTC log realized variance over the preceding
seven completed UTC days. Align by target date, then standardize using only the receiving
asset's training targets. Append this as one input after the four HAR inputs and the
target-day weekend flag. For the BTC self-control, this feature duplicates the existing
7-day HAR coordinate; report that limitation.

## Fixed model panel

- Quantum candidate: two-qubit weekend RY circuit, with one additional learned RZ
  rotation per qubit per layer conditioned on the BTC feature, wrapped as an additive
  correction to a train-only HAR residual forecast. Test depths 1, 2, and 3.
- Classical comparators: multinomial softmax, a two-hidden-unit tanh network, and the
  train-only HAR residual forecast. Give every model the same six standardized inputs.
- Same training years, validation years, four train-fitted outcome bins, log loss,
  optimizer, five restarts, and development seeds 900 and 901. Fit temperature on each
  seed's validation predictions for every learned model.

## Decision rule

Report all per-asset validation scores and optimizer failures. This experiment may only
select a candidate for a later confirmatory study. Advance only if the quantum model's
mean calibrated validation log loss is at least 5% below every classical comparator on
ETH, SOL, and DOGE, with paired 7- and 30-day validation intervals below zero. No existing
test set can satisfy confirmation. A future study requires a newly registered asset and
an untouched test period before that test is opened.

This protocol does not claim quantum advantage. Validation reuse makes any positive
result exploratory until independently confirmed.

## Amendment 1: network correction and checkpointing (20 Oct 2026)

The first execution exposed a shape error in the classical network's direct skip path
after the quantum depth sweep and softmax fit. No score file was written. Partial console
scores are retained in session notes but excluded from selection; the registered panel
will be rerun from scratch. The network now adds its two skip logits to the first two
learned class logits, leaving the fourth class as reference. Each completed fit is saved
to an ignored partial results file so interruption cannot discard earlier fits. No model,
data split, seed, restart, budget or metric was changed.

## Amendment 2: stop after SOL fails advancement gate (20 Oct 2026)

The complete two-seed SOL validation panel failed the registered 5% advancement margin:
the best quantum depth averaged 0.645391 versus 0.647917 for the six-input network, a
0.39% reduction. Since the cross-market gate is conjunctive, no result on another market
can make this candidate eligible. The ETH run was stopped after seed 900's full panel and
seed 901's quantum depths 1 and 2; depth 3, the second seed's classical fits, and DOGE
were not run. Report these partial results explicitly and do not advance the candidate.
No test data or scores were read.
