# Frontier v4–v6 development protocol

Declared 22 October 2026 before executing the new candidates. This is a bounded
development experiment, not a confirmatory study or a computational-advantage claim.

## Goal

Measure whether inexpensive quantum-feature readouts and HAR corrections improve
forecasting against equally informed nonlinear classical controls. Produce all results,
including failed candidates, within the initial twenty-minute research sprint.

## Constraints

- Preserve all historical models, seals, source PDFs, and user work.
- Use existing Bitstamp BTC and Binance BTC, ETH, SOL, DOGE daily files. These five
  series are a convenience development panel, not five independent markets: the two
  BTC series overlap and all assets share market conditions.
- Train through 2022-12-31. Select ridge settings and mixtures using 2023 only.
  Score 2024 after selection. Exclude 2025 onward from feature/target construction.
  All these development periods were exposed in earlier research.
- Train-fitted scaling, class boundaries, residual distributions, and bin RV means.
  Inputs use strictly prior days; calendar flags describe the forecast target day.
- Start with seeds 42, 43, 44, reporting all completed and incomplete runs. Seeds
  describe random feature variability, never independent financial observations.
- No dataset downloads, hardware spending, external messages, or test-window retuning.

## Candidates and controls

| Track | Model | Required comparison |
|---|---|---|
| v4 | Trainable softmax head over original and frozen two-qubit probability features | Same-width sine/tanh features and linear softmax |
| v5 | Same quantum-feature head as a correction to HAR log probabilities | HAR alone and matched sine/tanh HAR corrections |
| v6 | 2023-selected convex mixture of quantum candidates and a classical candidate | Classical candidate selected on the same 2023 scores |

These names identify new experimental tracks, not successive proven improvements on
v3. Frozen circuit parameters make these quantum-inspired random-feature models;
they do not implement end-to-end trainable v3 or demonstrate a v3 improvement.
Feature counts match; effective capacity and feature-generation costs need not.
Report actual optimizer termination, gradient norms, elapsed time, coefficient counts,
all searched settings, and selected settings. Do not suppress failed fits.

## Acceptance criteria

1. Gradient checks, normalized probabilities, zero-correction fallback, chronological
   selection, and invariance to future targets pass automated tests.
2. Save complete per-date forecasts, fit records, preprocessing, source/data hashes,
   and software versions in a new ignored output directory. Refuse overwrite.
3. Primary development metric: four-class negative log likelihood (NLL). Also report
   Brier and QLIKE using training-only bin conditional RV means. No averaging these
   metrics into a favorable composite. QLIKE can disagree with NLL because a four-bin
   distribution poorly resolves continuous volatility within its extreme bin.
4. Compare each candidate with the best classical setting selected using 2023, never
   a comparator selected using 2024. Also show every classical audit score so the
   strength of the benchmark is inspectable.
5. A measured positive difference is not a significant improvement. Any exploratory
   paired date-block intervals use 7- and 30-day blocks; they cannot repair historical
   validation reuse or search over prior experiments. Three seeds are not a final study.
6. Publish the scorecard and a compilable manuscript draft, and run repository checks.
   Keep remaining confirmation work explicit in the research plan.

## Unresolved questions and stopping rules

- Does a gain survive matched nonlinear controls and a continuous-volatility metric?
- Does the quantum contribution remain nonzero in a selected mixture?
- Are random features competitive enough to justify more expensive circuit training?
- Stop this sprint at its time budget. Preserve partial/failing results and do not
  choose new features, assets, seeds, or regularization after reading 2024 outcomes.
- No positive result here licenses a claim to beat all classical computation: each
  two-qubit circuit has a cheap exact classical statevector implementation. A future
  claim must identify a finite benchmark, a frozen protocol, an untouched period,
  matched search effort, and a correction for the complete comparison family.

See [the research plan](frontier-research-plan.md) for subsequent work and
[the measured sprint](frontier-results.md) for what actually ran.
