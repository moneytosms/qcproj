# Implementation plan

Source: **Quantum Stochastic Volatility SQC Project Plan**, especially pp. 8–11;
**Quantum_Volatility_Project_Guide** supplies the plain-language explanation.
Created 19 October 2026, before implementation. The PDFs describe intended research,
not verified experimental results in this repository. Their pilot numbers are not our results.

## Objective

Improve the paper's one-qubit point forecaster in the sequence **B (memory) → D
(distribution) → A (realism)**. Test improvements over the paper and compare honestly
with classical models. Do not assume quantum advantage. All essential work runs locally.

## Ordered work and acceptance gates

### 1. Foundation and reproduction (weeks 1–2)

- [x] Package Python code, dependencies, seeded CLI, tests, and reproducible artifacts.
- [x] Load the author's `data-rstand` and `data-ystand` with provenance and checksums;
      accept local daily CSVs with `date,return,rv` for independently rebuilt data.
- [x] Construct past-only log-RV features: lag 1, mean of preceding 7, mean of preceding
      30, previous return. Chronological train/validation/test; all fitted transforms
      and bin boundaries use training rows only.
- [x] Implement the stated RY/RZ encoding and U3 one-qubit circuit, MSE/COBYLA fit.
- [x] Verify phi redundancy and the exact Bloch-vector classical twin numerically.
- [x] Compare fitted curves and MFDFA h(2) with the paper's figures. Record scaling
      assumptions and discrepancies, rather than calling an algebra check reproduction.

**Gate 1:** numerical circuit checks pass and paper comparison is documented.
Author data are already standardized; their original units cannot be recovered just by
renaming the columns. Preserve this limitation in every result manifest.

### 2. Memory and range (weeks 3–4)

- [x] Add a one-qubit re-uploading point model on HAR inputs (B); document the chosen
      ansatz because the PDFs do not fully specify this intermediate model.
- [x] Implement two-qubit Born probabilities (B+D), 3 layers × 8 parameters = 24.
      Generalize to layers 1–4; compare against a 3-qubit/eight-level variant later.
- [x] Fit 30/70/95-percentile log-RV bins on training targets only. Forecast all four
      probabilities; sample a bin, then an empirical training value within that bin.
- [x] Generate paths recursively using generated returns and log RV after initialization.
- [x] Verify gate order, normalization, indexing, training-only bins, and seeded rollouts.

**Gate 2 remains open:** B and B+D need comparable held-out scores and adequate
training. The [memory-fit investigation](memory-fit-investigation.md) tests initialization,
budgets, depths and a short-memory control on training/validation only. Software
completion above does not establish a benefit from memory.

### 3. Realism and fair comparisons (weeks 5–6)

- [x] Add forecast NLL + lambda × standardized moment distance: ACF(log RV) at
      lags 1, 7, 30 and standard deviation of log-RV differences.
- [x] Estimate moment scales on training segments only; reuse fixed simulation streams
      during optimization and fresh seeds for evaluation. Fixed seeds reduce noise;
      discrete sampling still makes the objective nonsmooth.
- [x] Warm-start realism fits from forecast-only parameters. Sweep lambda in
      {0, .01, .05, .2}; select D depth first, then lambda at frozen depth on validation only.
- [ ] Add frequency and softmax baselines, an exactly 24-parameter tiny neural network,
      HAR residual/quantile baseline, and GARCH(1,1). Record effective as well as nominal
      parameter counts and compute budgets.
- [ ] Forecast scores: NLL, explicitly normalized ranked probability score, calibration.
      Implement predictive return-mixture VaR and Kupiec coverage testing separately
      from the probability of the extreme volatility bin.
- [ ] Realism: ACF, vol-of-vol, return tail index, Wasserstein, MFDFA h(2) and spectrum
      width, with shuffled controls. Label unavailable/unreliable estimates explicitly.

**Gate 3:** complete scorecard, same preprocessing and split, matched seeds/loss/budget
for learned quantum/classical distribution models. Point-model MSE is a separate panel;
point outputs must not be presented as calibrated categorical probabilities.

### 4. Final experiments and communication (weeks 7–8)

- [ ] Run 20+ seeds with sufficient budgets after gates pass; save raw per-seed records,
      fitted parameters, optimizer status, split metadata, config, and aggregate spread.
- [ ] Plot ablations, forecast/realism trade-off, extreme-bin calibration, scorecards.
- [ ] Report limitations, novelty literature check, and any failure to beat classical models.
- [ ] Write final report and slides from measured outputs.
- [ ] Optional: independent Qiskit/PennyLane circuit cross-check, IBM hardware shots,
      Ethereum transfer, Binance five-minute RV reconstruction, eight-level experiment.

## Implementation scope and status policy

Start with a working, testable local research pipeline, then evaluate each gate. Building
later-stage software does **not** mean an earlier scientific gate passed. Software
availability, smoke runs, and completed research are tracked separately below. Optional
hardware and transfer tasks do not block a laptop implementation. No pilot result is
copied into generated scorecards. Full experiments must be deliberately budgeted and
are not replaced with a quick demo.

## Intended repository structure

- `src/qcvol/data.py`: validation, HAR construction, splits, train-fitted transforms/bins.
- `src/qcvol/quantum.py`: gate algebra, paper circuit/twin, memory and Born circuits.
- `src/qcvol/classical.py`: comparable classical forecasters.
- `src/qcvol/generation.py`: recursive measurement/empirical-bin sampler.
- `src/qcvol/training.py`: forecast and simulation-aware optimization.
- `src/qcvol/metrics.py`: held-out forecast and path diagnostics.
- `src/qcvol/experiment.py`, `cli.py`: reproducible runs and saved artifacts.
- `tests/`: mathematical correctness, temporal leakage, sampling, integration.
- `scripts/`: explicit data acquisition; no implicit download on model import.
- `doc/architecture.md`: decision records with reasons and trade-offs.
- `doc/project-guide.md`: concepts, equations, commands, repository reading order.
- `doc/progress.md`: actual completion evidence and remaining scientific work.

## Open methodological choices to record

The detailed plan's three-way split takes precedence over the guide's simplified 70/30
pilot split (default 60/20/20 of eligible targets). The author's standardized series are
usable for comparison in their published units but not automatically for physical Bitcoin
VaR. Duplicate quantile edges/empty bins must fail clearly. NLL clipping is numerical
protection only. Independent test paths must not reuse training simulation seeds.

## Current checkpoint (19 October 2026)

The checked items above have working software and smoke-test evidence. Other checklist
items include scientific comparisons or mixed tasks that remain incomplete. Gate 1 now has verified equation-level/core-statistic reproduction and a documented
comparison in [PR #2](https://github.com/moneytosms/qcproj/pull/2), with explicit numerical
gaps. Exact equality to every source figure/table is not established. Gates 2–4 remain
open; no improvements over the paper are established. See
[progress.md](progress.md) for 32 passing tests (including the existing Phase 1 suite),
measured smoke scores, limitations and
remaining work. Source PDFs are preserved in the repository root.

## Reproduction milestone

[PR #2](https://github.com/moneytosms/qcproj/pull/2) adds the full audited reproduction
on an independent branch. It includes ten converged fits, three 50,000-step histories,
all 913-day/365-step rolling windows, 20 shuffles, q-step .02 spectra, 200 Gaussian controls,
and a measured report. Original data/source hashes and 150,000 recurrence steps were
verified. Use the PR's report for measured results and remaining normalization/zero-return
gaps. The code becomes available in the combined checkout when that PR is merged.

## Baseline preserving B decision

- [x] Add a two-weight extension containing the exact original paper at zero weights.
- [x] Warm-start from the training-fitted baseline, regularize only new weights and
      select the penalty using validation after training-only restart selection.
- [x] Compare with the paper, an identical-circuit short-memory control and raw-RV HAR.
- [x] Complete the focused comparison with convergence/stationarity checks and record
      the decision in [nested-memory-followup.md](nested-memory-followup.md).

The fixed follow-up retains previous-day inputs for D. B has not demonstrated a
longer-memory gain. This closes the focused B decision; Gate 2 overall remains open
until D is properly evaluated. Implement the short-input policy in the D runner, then
validate its probability forecasts before testing A. Keep the quantum/classical controls.
Do not mark the 20-seed final study complete or launch it before those gates pass.

## Step 3 development checkpoint (20 October 2026)

- [x] Enforce the B-selected previous-day policy for D training, validation and recursion.
- [x] Fit D at depths 1–4 with five starts, training-only restart selection and independent
      stationarity checks; select depth on validation NLL.
- [x] Fit A separately at the frozen D depth, three warm starts per positive lambda,
      train-only restart selection and a fixed validation trade-off rule including lambda zero.
- [x] Audit every lambda winner on two new 32×512-day streams; independently replay
      artifacts and inspect plots. Record training cost and capped restarts.

The [measured comparison](distribution-study.md) selects two layers / lambda .05 for
quantum. The aggregate realism improvement is modest and costs forecast accuracy;
weekly persistence remains poor, and classical controls still win on NLL. All D setting
winners pass their training checks; four alternative network starts remain budget-limited.
This is completed development evidence, not final 20-seed or independent test evidence.
Gate 3's complete classical/realism scorecard remains open. Next is Step 4: GARCH,
dedicated HAR quantile regression, training-effort controls and remaining comparator
optimization. Keep the project report paused.
