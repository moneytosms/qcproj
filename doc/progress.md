# Verified progress

Updated 20 October 2026. This records what was actually built and run. The long-term
research checklist is [implementation.md](implementation.md). Completed software does
not imply that the scientific gates have passed.

## Delivered in this implementation

- Installable `qcvol` Python package, locked environment, offline synthetic demo, CLI.
- Revision-pinned author-data acquisition with row alignment, hashes, source license
  and provenance; independent daily CSV validation.
- Chronological HAR pipeline, training-only standardization and four-level bins.
- Original circuit structure, exact Bloch twin, one-qubit memory point ablation,
  two-qubit Born simulator with 1–4 layers.
- Forecast-only fits and warm-started realism fits with fixed simulation streams;
  validation-only depth/lambda selection and separate final test evaluation.
- Frequency, softmax, 24-parameter tiny network and HAR residual-CDF comparators.
- Recursive generation, forecast/calibration scores, path statistics, Wasserstein,
  tail diagnostic, MFDFA with shuffled controls, and compatible-unit return VaR/Kupiec.
- Saved fit records, source/package hashes, config, optimizer statuses, arrays and
  aggregate scorecards; four figure exports and a CSV scorecard.
- Architecture decision records and a plain-language project guide with reading order.

## Checks actually run

| Check | Evidence |
| --- | --- |
| Unit and integration suite | **32 passed**: 27 new pipeline tests plus 5 existing `qvol/` tests; includes a full offline experiment |
| Lint | `uv run ruff check .` passed |
| Format | `uv run ruff format --check .` passed |
| Paper algebra | 256 random input pairs; phi error 0; twin maximum error 5.55e−16 |
| Born simulator | independent full-matrix comparison for 1, 2, 3, 4 layers |
| Temporal correctness | target-day exclusion; future-data perturbations cannot change training transforms or generated paths |
| Repeatability | repeated fits/rollouts with fixed seeds agree |
| MFDFA diagnostic | white noise and integrated noise produce appropriate scaling ranges |
| Risk calculation | Gaussian-mixture quantile matches a single Gaussian; coverage test handles 0/all violations |
| Synthetic CLI | completed `results/synthetic-smoke` |
| Author-data CLI | completed `results/author-smoke-verified` with 10 named model records and arrays |
| Plot export | 4 PNGs and scorecard CSV; layout inspected visually |

Commands are documented in the README and project guide. Generated `results/` and raw
`data/` stay local and ignored by Git. Completed major changes are published through pull requests to `moneytosms/qcproj`;
see the repository PR history for publication status.

## Author-data execution evidence

Source revision: `takaishi-physics/QCL-volatility` commit
`2fec7ee621006bcbe1b7860d05b9589a7276a8f6`.
Both input files have 913 aligned numbered rows. After 30 history days, 883 targets split
529 train / 177 validation / 177 test. Training level counts are 159 / 211 / 132 / 27.
These differ from the PDFs' pilot because our split includes a validation block.

Run: `configs/smoke.json`, seed 0, 40 COBYLA evaluations per optimization plus one
initial loss check, 3 circuit layers, lambdas 0 and .05. Training realism uses one 64-day
path; final scoring uses two 192-day paths after 10 burn-in days. There are six learned
distribution candidates, ten final named records, and ten compressed array files.
All fitted optimizers exhausted the small evaluation budget. **None of these smoke fits
should be described as converged.**

Distribution panel (test scores; lower is better):

| Model | Log loss | Normalized RPS | Mean per-path moment distance |
| --- | ---: | ---: | ---: |
| Frequency | 1.1969 | .1796 | 158.55 |
| HAR residual CDF | .5295 | .0589 | 7.32 |
| Quantum forecast | 1.1758 | .1672 | 34.63 |
| Quantum selected | 1.2591 | .1755 | 35.81 |
| Softmax forecast | .5616 | .0614 | 46.34 |
| Softmax selected | .5616 | .0614 | 46.34 |
| Tiny NN forecast | .5990 | .0607 | 75.16 |
| Tiny NN selected | .6842 | .0646 | 23.73 |

Validation selected lambda .05 for quantum and the tiny network, and zero for softmax.
The quantum test realism distance did not improve in this run despite its validation
selection. We retain that outcome. The author-data risk panel is disabled because
physical consistency of independently standardized return/RV units is unknown. Hill
estimates are unavailable at this path length (<200); the JSON records `null` and valid
path counts explicitly.

Point panel: paper RV MSE .0003044; B-only memory RV MSE .33159. B does not show a gain
at this tiny budget and chosen intermediate ansatz. This is a reason to investigate
training and controls, not to claim a successful upgrade. Point MSE is in standardized
RV units and cannot be compared numerically with categorical log loss.

These are software execution results. They do **not** establish improvement over the
paper, a successful realism objective, quantum advantage, or replication of the PDFs'
pilot. One seed provides no estimate of between-seed spread; that field is `null`.

## Research gate status

Upstream subsequently added a separate full-sample reproduction under `qvol/`, including
saved Phase 1 results. That work is preserved and linked in the guide. Its five tests were
run with this pipeline's tests after integration; its long experiment scripts were not
rerun here. The open gates below describe the evidence still needed for this held-out
pipeline and final combined study, not an assertion that the team has no Phase 1 work.

| Gate | Status | What is missing |
| --- | --- | --- |
| 1: reproduce paper | **Verified with numerical limits; PR #2 open** | Equation-level/core-statistic reproduction and comparison complete; exact table/series equality is not claimed |
| 2: establish B and D | **Open** | Adequate optimization, matched-capacity short-memory control, depth/level studies, comparable forecast/realism evidence |
| 3: complete fair scorecard | **Open** | GARCH(1,1), full required finance/quantile controls, stronger matched-compute comparison, uncertainty and convergence checks |
| 4: final study/report | **Not run** | 20+ seeds, full sweep, paper-matched diagnostics, final report/slides and literature recheck |

## Next implementation and research work

1. Review the audited full-sample reproduction in PR #2 and its explicit numerical
   gaps. Next investigate the B-only model's poor small-budget fit with additional
   optimizer budget/restarts and matched-capacity controls. Preserve the held-out test split.
2. Add a matched-capacity short-memory circuit and reduced-phase-parameter variants;
   report identifiable rather than only nominal parameter counts.
3. Add GARCH and a dedicated HAR quantile-regression baseline (the implemented HAR
   residual distribution already supplies empirical quantiles, but is a different method).
4. Validate MFDFA against an independent implementation and match the paper's scaling
   and rolling-window settings; quantify finite-sample uncertainty and tail sensitivity.
5. Budget and run the proposed 20-seed sweep only after those checks; include total
   hyperparameter-search work and uncertainty, not only per-fit optimizer counts.
6. Optional extensions: three-qubit/eight-level circuit, independently rebuilt five-minute
   RV data, Ethereum transfer, Qiskit cross-check and IBM hardware measurements.

No hardware demo, transfer run, long final sweep, final paper or slides have been produced.

## Audited reproduction milestone (PR #2)

[PR #2](https://github.com/moneytosms/qcproj/pull/2) independently adds the full-sample
reproduction to `qvol/`. It has ten converged COBYLA starts (MSE .0020477757088474932),
three 50,000-step generated histories, every complete 913-day window at step 365,
20 shuffles per window, full q-step .02 spectra, and 200 Gaussian controls.

Mean generated return h(2) is .49759 and log-RV-increment h(2) is .05249; shuffled
increments return near .503. Source hashes, 150,000 recurrence steps, and 1,623 original
rolling estimates were verified. Independent MFDFA fluctuation error is at most 2.22e-15.
The reproduction suite passes 13 tests; running it with this pipeline's 27 tests gives
40 passing tests. Seven measured comparison plots were visually inspected.

The [measured report on that branch](https://github.com/moneytosms/qcproj/blob/codex/paper-reproduction/doc/paper-reproduction.md)
explains differences in generated return tails, the empirical zero-return convention,
and the unpublished exact scale grid. This verifies the original-paper comparison
milestone while preserving uncertainty about exact numerical replication. It does not
change the earlier held-out smoke scores above. Source PDFs and historical results
remain unchanged. The PR is open for review; it has not been merged automatically.

## Memory point-fit investigation

The [measured investigation](memory-fit-investigation.md) completes the requested
training diagnosis without evaluating the held-out test split. It preserves all earlier
smoke scores. On the fixed author-data split, 102 point-model fits compare three starts,
one/three layers, full/short memory, legacy/training-informed initialization, budgets
40/500/3000 and phase-free 12000-evaluation attempts.

- Independent memory matrix and target-alignment checks pass; RV targets already fit
  the readout range. No gate-order or target-unit correction is indicated.
- Legacy three-layer initial predictions average .7766–.9577 versus training mean RV
  .035745. Training-informed starts average .0365–.0391 and greatly reduce small-budget
  failures. The new start is explicit; historical defaults remain reproducible.
- Phase-free one-layer prior fits converge for all three starts. Their training-selected
  validation MSE is .00053164 with full HAR and .00051614 with short-memory inputs.
  The paper training-only comparator gives .00072042. These are validation, not test scores.
- Deeper fits lower training error but can worsen validation; all six three-layer
  12000-evaluation attempts remain budget-limited. The short-memory control stays
  competitive, so the longer-memory benefit remains unproven and Gate 2 stays open.
- Total measured fitting work: 169383 objective calls and about 547.6 seconds on this
  CPU setup. The verifier reproduces 72012 predictions exactly and checks losses,
  provenance and selection. Both generated diagnostic plots were visually inspected.
- Current branch checks: 40 tests pass (35 root, five legacy qvol), plus Ruff lint/format
  and whitespace checks. These counts differ from the earlier combined reproduction
  milestone because the additional paper-audit tests live on the separate PR #2 branch.

Next use stable training-informed point fits and the short-memory control as references,
then investigate regularization or a nested ansatz before accepting the deeper B model.
The full B/D/A study, independent test comparison and 20-seed uncertainty analysis remain
pending. The project report remains paused at the user's request.

## Baseline preserving memory follow-up

The [measured follow-up](nested-memory-followup.md) completes the focused B decision
under the [fixed protocol and precision amendment](nested-memory-protocol.md). The
new four-coordinate circuit contains the paper exactly at zero added weights. Every
fit starts from the training-fitted paper; five starts and six penalties are compared
for full and short inputs. The paper is an explicit zero-weight fallback. A separate
raw-RV HAR OLS control uses the same 1/7/30 crypto horizons.

The first 65-fit attempt reported optimizer success but failed independent stationarity
checks at the strongest penalty, so its decision remains recorded as inconclusive.
Repeating the identical grid with a tighter trust-region floor gives 65/65 fits passing
both checks; no penalty, seed, split or validation acceptance rule was changed. Across
both attempts, 130 fits used 82558 objective/gradient-check calls and 138.724 summed
optimization seconds on this local setup. One HAR linear solve per attempt is reported
separately; these timings are not evidence of hardware advantage.

Training-selected, validation-tuned RV MSEs are .00071891 for the weekly/monthly
extension (alpha .1), .00064040 for its short-memory control (alpha .001), .00072042
for the paper, .00061033 for classical HAR and .00057420 for persistence. Longer
memory is 12.3% worse than its matched short-input control on this validation block.
**Retain previous-day inputs for D; this B extension has not demonstrated a benefit.**
Keep the paper, short-memory quantum, HAR and persistence references in later work.

Each attempt's verifier recomputes 48008 predictions using literal matrices, checks
penalties, central gradients, warm starts and both selection stages, and reconstructs
HAR independently. Maximum prediction discrepancy is 2.78e-16 and zero-weight identity
discrepancy is zero. No test scores were computed. The 47 current-branch tests pass
(42 root and five legacy qvol), along with lint/format and whitespace checks; two final
plots were visually inspected. Raw results remain local and ignored.

This conclusion is exploratory and limited to the current architecture and reused
validation block. Before D's next sweep, implement its selected short-input policy;
the existing main Born runner still defaults to HAR inputs. Then evaluate D's forecast
distribution, followed by A's realism effect. The full 20-seed study and independent
test comparison remain pending; the project report remains paused.

## Step 3 D → A development comparison

Completed the [frozen protocol](distribution-study-protocol.md) and
[measured comparison](distribution-study.md) on 20 October 2026. The new dedicated
runner uses previous-day log RV and return throughout training, validation and recursive
sampling; the historical HAR-input runner is preserved.

- 30 forecast fits, 27 realism fits, 3 controls; 60 saved candidate/control records.
- All 20 quantum D fits and all six training-selected D setting winners pass optimizer
  status and independent stationarity checks. Four other network starts hit the call
  ceiling; keep that training limitation visible.
- Validation selects quantum depth 2, then lambda .05. Fresh-stream mean moment distance
  improves 14.2774 → 13.0526 (8.6%); NLL worsens .997917 → 1.007528.
- Softmax scores .979151 before A and .988795 after selected A, with better fresh moment
  distances too. Full HAR reference NLL is .930155, with additional history information.
- Quantum weekly ACF remains about .012 against real validation .383. A does not repair
  the missing long-range structure. B's earlier point-model result is not a universal
  conclusion about memory in distribution forecasting.
- 388,860 objective calls plus 1,050 independent stationarity calls; 619.210 fit wall seconds.
  All 27 A optimizers stop by radius, not by budget; that is not a nonsmooth optimality proof.
- **59 tests pass**, Ruff checks pass. Independent artifact verification replays 42,360
  probability rows (max dense-gate error 7.77e−16), 628,224 recursive output days and all
  recorded choices/scores; both exported figures were inspected.

No new test scores were computed. Validation reuse and finite simulation horizons remain
limits. Step 4 comparisons and the 20-seed final study remain pending; report/slides stay
paused. Use `scripts/run_distribution_study.py`, not the old `configs/study.json`, for
this short-input D/A protocol. Raw measured arrays/plots stay ignored under
`results/distribution-study-2026-10-20`.
