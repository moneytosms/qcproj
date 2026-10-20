# Calendar and direct-day readout: measured development results

Completed 20 October 2026 on Nidhi's unchanged Bitstamp dataset from PR #8, under
[the committed plan](improvement-plan.md). Training ends in 2022; validation is 2023–2024.
No new empirical test scores or final-seed fits were produced in this milestone. The
2025–2026 benchmark is already exposed by PR #8 and remains untouched by this sweep.

## Findings

The missing-weekend diagnosis is supported on validation. With otherwise identical
linear reference logits and uniform training weights, weekday indicators improve NLL
**.679985 → .633722**. Adding a validation-selected 730-day training half-life gives
**.630626**. Recency alone does not help without calendar information.

The new quantum readout improves further, but **the updated classical nonlinear models
still lead**. The second qubit's direct daily input is implemented and verified; it
does not improve validation in this grid. Information previously reached it indirectly
through entanglement, so absence of a direct gate input did not mean complete absence
of daily information from the joint measurement.

| Model | Chosen size | Feature ridge | Mean validation NLL ↓ |
| --- | --- | ---: | ---: |
| Sine control | 4 hidden units | .001 | **.608194** |
| Tanh control | 4 hidden units | .001 | .609031 |
| Quantum readout, original routing | 2 layers | .001 | .617749 |
| Quantum readout, direct day on qubit 1 | 2 layers | .001 | .620583 |
| Calendar linear | — | — | .630626 |

Nonlinear means use development seeds 910/911, each with three starts. Restart selection
uses training objective; size/penalty selection uses validation NLL. All models share
the selected calendar/recency policy. These are learned hybrid readouts with ordinary
linear skips, not the original direct-Born forecasters. Gains relative to older models
cannot be attributed solely to a quantum circuit.

## Controlled ablations

Best linear ridge for every listed setting was zero:

| Training weighting | Without calendar | With calendar |
| --- | ---: | ---: |
| Uniform | .679985 | .633722 |
| 365-day half-life | .685352 | .632194 |
| 730-day half-life | .682032 | .630626 |

At feature ridge .001, original-routing depth 2/3 scores .617749/.617815; direct-day
depth 2/3 scores .620583/.620902. At .01, all four quantum settings collapse back to
the linear score .630626. The added daily gate is therefore not a demonstrated fix
for the remaining forecast gap. The direct-day variant lowers the penalized training
objective but worsens validation, so extra expressivity is not automatically useful.

For seed 910 at selected settings, weighted training NLL before its penalty is .778486
(quantum), .781579 (direct-day), .767844 (tanh), .763211 (sine). Classical nonlinear
controls fit the training labels better too. Adequate local stationarity checks do not
prove a global optimum, but the results do not support claiming that an untrained
classical comparator caused the remaining gap.

## Post-hoc residual diagnostic and next hypothesis

Quantum and sine errors are not identical. After the planned sweep, a diagnostic on
the mean development probabilities tried mixing weights 0/.1/.25/.5/1. A mixture of
75% sine and 25% original-routing quantum scores **.606689**, versus sine alone .608194.
The same diagnostic's best sine/tanh mixture scores .607172. Direct-day quantum also
adds some complementary signal (.606971 at 25%). These are **exploratory validation
numbers**, not a preregistered ensemble result or a test advantage.

The next useful experiment is a properly controlled ensemble comparison: test whether
quantum predictions add value beyond an equally large, equally parameterized classical
ensemble. Freeze its member sets and weight-selection procedure before final fitting.
Keep a chronological validation diagnostic and report instability. A tiny development
gain can disappear on the reused benchmark; do not present this as a quantum win.

## Verification and cost

- 18 linear fits plus 96 nonlinear fits: **114/114** pass optimizer and independent
  central-gradient checks. All selected fits pass.
- **16,129 joint objective/gradient calls**, **12,600 diagnostic calls**; summed recorded
  fit time **982.174 seconds** with one-thread BLAS/OMP settings. Nonlinear training
  includes all starts. This is a cost record, not a hardware-speed claim.
- Independent dense-matrix replay checks all 114 saved objectives, **249,888 training
  probability rows**, validation scores and restart/setting choices. Maximum probability
  discrepancy **5.55e−16**. No final seeds are included in that verification.
- **120 tests pass**. Ruff lint/format and whitespace checks pass. Tests cover direct
  qubit-1 day sensitivity, finite-difference/dense gradients, future-data isolation,
  advancing weekdays, sealing, integration evaluation and corrupted uncertainty.
- The validation ablation figure was visually inspected. Raw output and the figure
  remain ignored under `results/calendar-study-2026-10-20`.

Package source was frozen in `ed3daea` before empirical fitting. The study's recorded
configuration and data/source hashes bind the run. The independent verifier and plotting
scripts were added without changing the training package. Original data/PDFs and Nidhi's
sealed results are unchanged. Report/slides remain paused.
