# Improvement plan after Nidhi's fresh-data study

Declared 20 October 2026 before this follow-up's fits. Parent: Nidhi Rakesh's
[PR #8](https://github.com/moneytosms/qcproj/pull/8), inspected at commit
`341dc7ef5c106069e22a3407a07ec5b4f1222932`. Preserve her implementation/results and
the earlier negative study. Do not merge PRs or alter their sealed artifacts.

## Updated evidence and objective

Nidhi's larger Bitstamp experiment changes the earlier conclusion: HAR memory improves
the quantum forecast (.6204→.5695 test NLL), and same-length realism targets with memory
improve generated realism at an accuracy cost. Softmax HAR still leads (.5184); neither
quantum nor classical corrections to HAR quantile beat the underlying HAR on test.
The paper comparison also improves on the original one-qubit model. These are distinct
claims from beating strong classical controls.

Aim to beat the strongest properly trained classical forecasts, while allowing the
evidence to reject the proposed improvements. A quantum-containing hybrid beating an
older baseline does not establish a quantum-specific benefit. Both matched classical
nonlinear controls and the plain linear model must be reported.

The new test period (2025–2026) has now been scored and discussed in PR #8. It is an
exposed benchmark for this follow-up, not a newly unseen holdout. No claims of pristine
generalization, universal advantage, or physical hardware speedup are authorized by it.
The report/slides remain paused.

## Weak spots to target, in order

1. **Missing calendar information.** Train/validation both show lower weekend log RV;
   the validation effect is larger. Give every candidate the target UTC weekday, known
   in advance. Use six weekday indicators plus intercept; advance dates during recursion.
2. **Training-regime mismatch.** Compare uniform training weights with exponential
   half-lives 730/365 days. Weights depend only on completed training dates. Select with
   validation, retaining the uniform ablation. Do not change bins using validation/test.
3. **Restrictive Born readout.** Existing four Born probabilities directly constrain
   class odds. Test a learned reference-logit readout of three circuit probabilities,
   plus linear HAR/calendar skips. This contains the linear baseline exactly when the
   feature readout is zero. Bound quantum feature inputs with `atan` to test a less
   oscillatory response to standardized outliers. This is a hybrid, not a pure Born law.
4. **Attribution and optimization.** Compare same-input, approximately equal-parameter
   tanh and sine feature heads. Use analytic circuit sensitivities/backpropagation,
   independent finite-difference checks and complete restart/cost records. Remove the
   two inactive terminal RZ coordinates. Do not interpret failed optimization as advantage.

## Fixed first experiment

**User clarification before fitting:** the second qubit has no direct yesterday-volatility
input, and the weekend dip is large. Add a `quantum-shared` candidate that changes its
local RY angle from bias to bias + learned-weight × atan(yesterday's standardized log RV)
in every layer. Both qubits then receive yesterday directly. The original routing remains
an explicit ablation. Zero added weights recover the original circuit. This adds one
parameter per layer, so shared-readout extra counts are 25/34 versus original 23/31
and classical 24/32. Compare matched depth/penalty development rows as well as each
family's independently selected final model. This amendment precedes all empirical fits.

- Reuse PR #8's daily series unchanged: training through 2022, validation 2023/2024.
  Fit transformations/bins/pools using training only. No new data/output is committed.
- First select the linear reference-logit baseline over calendar off/on, half-life
  uniform/730/365, and ridge 0/.0001/.001 using validation NLL. Report 2023 and 2024
  separately as stability diagnostics; the equal-day pooled NLL selects the setting.
- Freeze its calendar/weighting policy for the nonlinear comparison. Retain linear
  coefficients as warm starts; fit nonlinear heads jointly with the skip coefficients.
- Quantum depths 2/3 correspond to tanh/sine hidden widths 3/4: 23/31 extra quantum
  coordinates versus 24/32 classical coordinates. Feature ridge .001/.01; base ridge
  stays at its selected value. Ridge applies to all feature coordinates. Development
  seeds 910/911, three starts per setting; choose starts on training objective, settings
  on mean validation NLL. Report each year's scores and all failures.
- Analytic L-BFGS-B up to 10,000 joint calls/5,000 iterations. Independent gradient
  infinity norm <=1e-4 plus solver success defines a passing fit. Every attempt is saved.
- If these candidates still trail classical models, diagnose training/validation
  residuals before declaring success or starting another study. Any amendment is
  recorded before additional fitting; do not expand the search against test results.
- After validation checks: twenty fresh seeds, three starts each, fixed selected
  settings. Seal source/config/data/training artifacts before benchmark scoring. Keep
  failed selected fits in scores and show passing-only sensitivity.
- Compare NLL/RPS/calibration, per-year errors, and paired 7/30-day date bootstrap;
  recursive paths use actual advancing weekdays, common random streams and same-length
  moment references. Separate forecast gains from realism. No A penalty is added until
  the forecast/calendar model has been evaluated; calendar alone may repair weekly ACF.
- Independent dense-gate prediction replay, seeded path replay, artifact tamper/leakage
  tests, and full Ruff/pytest checks precede the milestone PR targeting PR #8's branch.

## Deliverables and completion policy

Implement the runner/models, measured development note, architecture/progress updates,
comparison plots and a PR after the major change. Keep raw output ignored. Success
requires measured improvement over strong updated classical controls, with variability
and uncertainty shown; merely beating an obsolete baseline is insufficient. If the
first design fails, preserve it and continue from the diagnosed weakness without
claiming the objective achieved.
