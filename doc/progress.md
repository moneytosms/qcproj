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

## Step 4 classical comparison and conditioning follow-up

Completed the [protocol/amendment](classical-comparison-protocol.md) and
[measured comparison](classical-comparison.md), preserving both complete attempts.

- Full/short HAR quantile regression uses direct pinball LPs: all 30 quantile solves
  per attempt pass independent primal/dual checks. Full HAR QR validation NLL .917290,
  RPS .105597; short QR NLL .983815. Native/full-bin quantiles are scored separately.
- Gaussian zero-mean GARCH uses five starts and a training-only RV calibration. Chosen
  KKT residual 1.23e−6; variance alignment agrees with the library. Validation NLL
  1.050928 and weak realism remain negative results. Native paths are separately labelled.
- Analytic continuation resolves the best old network start but leaves four alternatives
  iteration-limited. Preserve those failures. A declared four-alpha ridge grid gives
  **20/20 eligible fits**; validation chooses alpha .001. Network D NLL .979798,
  competitive with softmax .979151 and better than quantum .997917.
- Repeating A with the fixed ridge penalty selects lambda .05; network NLL worsens to
  1.011488 while mean moment distance improves 14.8233 →7.0698 on the audit streams.
- Shared-law HAR QR audit moment distance 6.7645, compared with quantum A 12.8106.
  Quantum's extreme-bin Brier is slightly better; the metric ranking is not universal.
- Both attempts together use 94,896 new iterative objective calls plus 60 LP solves,
  155.642 summed fit seconds and separately reported diagnostics. Prior Step 3 costs
  remain charged. Parameter/information/search/thread differences prevent matched-cost claims.
- Independent verification passes: first attempt 2,478 probability rows /491,520 audit days;
  refined 2,655 rows /524,288 audit days, max dense-gate error 4.44e−16. Both figures inspected.

Native quantile assumptions, unknown source units, reused validation and reused audit
streams across the two documented attempts remain visible limits. No new test scores
or 20-seed study were produced. Next freeze/integrate the final-study runner rather than
launching the historical config unchanged. The project report and slides remain paused.

Current branch checks: **68 tests pass**, including finance gradient/certificate checks,
an end-to-end comparison with independent verification, deliberate LP-certificate and
selection tampering, and the original `qvol/` suite. Ruff lint/format and whitespace
checks pass. Raw measured output remains ignored.

## Final frozen study (20 October 2026)

Completed the [frozen protocol](final-study-protocol.md) and
[measured 20-seed comparison](final-study.md), after the Step 4 training repairs.
Source/config/data/training-artifact hashes were sealed before test scoring; no
hyperparameters or restarts were selected against test results.

- 20 fresh seeds, 240 forecast records, 260 path records and **8,519,680 output days**.
- All 300 D fits and 100 paper fits pass optimizer/independent-gradient checks; all
  180 A fits terminate by radius. Every selected seed passes. Finance checks pass.
- Test NLL: HAR quantile .528910; HAR residual .529544; network D .578365; softmax D
  .582168; quantum D .691983; quantum A .862279. No quantum advantage demonstrated.
- Quantum A worsens mean test moment distance 19.7151→31.8644 as well as NLL.
  Softmax/network A also worsen both mean scores. The earlier validation realism gains
  do not carry over; do not hide the negative outcomes or retune against this test.
- Calibrated GARCH has the smallest shared-law test moment distance (10.7134), despite
  weaker forecast NLL. Softmax D now leads extreme-bin Brier; only three extreme events
  limit calibration inference. Native HAR nominal 90% coverage is just 79.7%.
- Separate seed variability and paired 7/30-day date-bootstrap intervals are reported.
  Quantum A−D intervals are positive for both blocks; some D-vs-classical intervals
  include zero at 30 days. One reused period cannot establish universal superiority.
- 363,800 iterative objective calls, 9,800 independent diagnostic calls and 30 LP solves;
  1176.850 summed fit seconds, with development costs and method differences retained.
- Independent verification replays **42,480 probability rows**, max dense-gate error
  6.66e−16, every recursive output day, independent MFDFA and exact bootstrap results.
- **81 tests pass**, Ruff lint/format and whitespace checks pass; all six final figures
  inspected. Artifacts/plots/CSV stay ignored under `results/final-study-2026-10-20`.

The final study is complete for this protocol. Physical-unit risk, novelty review,
unseen-market replication and optional hardware/transfer are not thereby completed.
The project report and slides remain paused at the user's request.

## Fresh-data study: memory + realism, hybrids (20 Oct 2026, branch `nidhi/memory-realism-fresh-data`)

Completed the [pre-committed protocol](fresh-study-protocol.md) and the
[measured results](fresh-study.md) on Bitstamp daily RV, test 2025-01-01 to 2026-10-19
(657 days, unused by any earlier study). The paper's data was identified as Bitstamp
2020-08-30 to 2023-02-28.

- Memory helps: quantum-har D beats quantum-short D by 0.051 test log loss (interval
  −0.071 to −0.030); classical models gain similarly.
- With memory and same-length targets, realism training improves test-period realism for
  every family (15-20 of 20 seeds) but costs forecast log loss (quantum +0.035).
- No quantum advantage: softmax-har D 0.518 vs quantum-har D 0.570. HAR + quantum and
  HAR + softmax hybrids are both slightly worse than HAR quantile alone on test.
- Calm test regime (no extreme days by training cut-offs) and a strong weekend effect are
  recorded as limits; a weekday input is the clearest next step.
- 155/160 forecast fits and 120/120 realism fits pass checks; seal committed before scoring;
  independent recomputation matches. 93 tests pass (1 skipped).
- Follow-up ([protocol](paper-comparison-protocol.md), [results](paper-comparison.md)):
  the paper's exact 1-qubit model, refitted on the same training years (20 seeds, all fits
  pass), loses to our quantum-har D on log loss (1.196 vs 0.570), QLIKE (0.840 vs 0.504),
  squared error and realism (215 vs 34); all 95% date-bootstrap intervals exclude zero.
  Main cause: the paper's max-based input scaling squashes ordinary days after the 2020
  crash, plus one-day memory.

## ETH quantum upgrade (20 Oct 2026)

The user asked for a real forecast improvement over classical models, not just another
paper comparison. The [protocol](eth-quantum-upgrade-protocol.md) was committed before
ETH model scores. Binance ETHUSDT spot 5-minute archives are checksum-verified. The
derived daily file covers 2017-08-17 to 2026-10-19 (3,351 days; 963,337 bars). The archive
contains 33 timestamp gaps, 1,703 missing 5-minute intervals, and 34 affected days;
2025-01-01 to 2026-10-19 has complete 288 bars per day. Gaps are recorded, never filled;
observed close changes across gaps enter RV once. The builder and weekend circuit have
focused unit tests, including timestamp unit conversion, offset handling, and exact
statevector equivalence. Initial two-seed validation did not meet the goal: the weekend
network scored 0.5303 and softmax-HAR hybrid 0.5160, versus 0.6076 for the selected direct
quantum circuit and 0.5306 for the quantum-HAR hybrid. ETH test scores remain unopened.
Protocol amendment 2 adds RY weekend encoding and alternating entangler direction; these
variants were selected on validation before final training. RY depth 3 improved mean
validation loss to 0.5711, alternating CNOT depth 3 to 0.6523. A third amendment tests an
RY quantum expert on the HAR baseline because the existing RZ hybrid was close to the
network. Amendment 4 applies validation-fitted scalar temperature calibration uniformly
to all candidate families, selects by calibrated validation loss, and restricts final
training to the selected quantum model plus fixed quantum and classical controls. The
rescored winner is the depth-1 RY HAR hybrid (0.5195 calibrated validation log loss),
behind the softmax-HAR hybrid (0.5125) and just behind the weekend network (0.5171).
ETH final test (657 days, 20 seeds) is complete and documented in [eth-study.md](eth-study.md).
The calibrated RY HAR hybrid scored 0.6480 log loss versus 0.6482 for the weekend network,
a 0.03% difference. All paired 7/30-day intervals include zero, so the 5% marked-improvement
threshold was missed. Two classical hybrid seed fits were ineligible and remain included.
The user goal remains open; a fresh-market replication needs its own frozen protocol and
untouched test data.

BTCUSDT is the fixed-architecture replication target. Its protocol is committed in
[btc-replication-protocol.md](btc-replication-protocol.md) before data download or scoring.
BTC replication is complete and documented in [btc-study.md](btc-study.md). The RY HAR
hybrid scored 0.5320 log loss versus 0.5309 for the best classical network; 97.5% paired
intervals crossed zero. It did not meet the 5% improvement threshold. Across both tested
markets there is no marked quantum advantage; the user goal remains active.
An equal 20-seed probability ensemble was also checked on validation only. It remained
behind classical on ETH and was about 1.1% ahead of the best classical model on BTC, below
the 5% target. A validation-fitted blend of quantum plus weekend network assigned weight 0
to quantum on ETH and 0.928 on BTC, so the signal did not transfer consistently. No test
predictions were reused for these checks.
The depth-1 quantum outcome-readout candidate also failed ETH validation: both unregularized
25-parameter fits exhausted the 50,000-call budget, and calibrated loss (0.5236/0.5245)
trailed the network (0.5171). Its protocol amendment applies the existing 0.001 L2 penalty;
only ETH validation will be checked first, and BTC validation runs only if that gate passes.
The regularized readout converged but averaged 0.5221 calibrated log loss, 0.96% worse
than the same-seed network (0.5171). It failed the ETH gate; no BTC validation or test
scoring was done for this candidate.

The fixed SOL/DOGE replication data are built and pass coverage checks: SOL has 843 train,
731 validation, and 657 test targets; DOGE has 1,246/731/657. Both test windows have 288
5-minute bars every UTC day. The preregistered two-market panel has now been evaluated
once; results follow.

## SOL/DOGE fixed quantum replication (20 Oct 2026)

Completed the preregistered [two-market protocol](sol-doge-replication-protocol.md)
and results report ([sol-doge-study.md](sol-doge-study.md)). Both checksum-verified
Binance panels cover the full 2025-01-01 to 2026-10-19 test period; the common test
contains 657 targets per asset. Code, protocol, locked environment, datasets, fixed
selection and all 20-seed model artifacts were sealed before either test was opened.
Each test was evaluated once.

- SOL quantum RY hybrid calibrated log loss .404973; classical comparators .424834,
  .417410 and .424215. Its best classical comparison is a 2.98% gain, below the 5%
  threshold. Paired 97.5% intervals cross zero against softmax and network.
- DOGE quantum calibrated log loss .762719; comparators .763335, .772791 and .766459.
  Best gain is 1.30%; all paired 97.5% intervals cross zero.
- Every registered score, including RPS, extreme Brier and QLIKE, is reported. SOL has
  one and DOGE three ineligible softmax-HAR hybrid fits; these remain included. All
  quantum fits were eligible.
- The two-market success rule failed. No marked quantum advantage is established.
  The selected model version's preregistered replication panel is complete; do not add
  assets to this panel after seeing the outcomes.
- Final checks: 105 tests passed, 1 skipped; Ruff lint and format checks passed.


## Validation-only quantum/network blend check (20 Oct 2026)

A fixed 50/50 probability blend was checked on validation for the four existing markets,
using per-seed calibrated quantum RY HAR and weekend-network predictions. The blend was
0.87% lower loss than the network on BTC, 1.80% lower on SOL, 0.40% lower on DOGE, and
0.95% higher on ETH. No market reached the 5% target. This exploratory result used no test
labels and is documented in [validation-ensemble.md](validation-ensemble.md); it is not
confirmatory evidence and does not establish the goal.
## Calendar and quantum-readout improvement: development in progress

Inspected Nidhi's latest PR #8 at `341dc7e`, then branched from it. Her fresh-data study
supersedes the earlier limited memory conclusion: memory helps on the larger dataset,
and matched-horizon realism helps simulation at a forecast cost. Classical forecasts
still lead. The original branch passes 94 tests in this environment.

The [new plan](improvement-plan.md) was committed before empirical fitting. It targets
weekend inputs, training-regime weighting, direct yesterday-volatility encoding on the
second qubit, and a learned quantum readout with classical skips. Calendar/recency and
similar-capacity classical nonlinear controls are included. Source data and prior study
artifacts remain unchanged. The new model/gradient/calendar/leakage/seal tests pass;
no improved empirical score or quantum advantage has yet been established.

### Completed calendar/readout development

The [measured note](calendar-development.md) records the completed fixed sweep:
114/114 fits pass; independent replay verifies 249,888 probability rows and all saved
objectives/choices, max error 5.55e−16. Calendar improves linear validation NLL
.679985→.633722, then recency gives .630626. Quantum readout reaches .617749; the direct
day variant gives .620583. Classical sine/tanh controls still lead at .608194/.609031.
All 120 tests pass and the ablation plot was inspected. No new empirical test scoring
or final-seed training has occurred. The remaining forecast gap is real in this grid.

A post-hoc validation mixture suggests complementary quantum errors, motivating a
separate, capacity-controlled ensemble protocol. That small exploratory gain is not
an advantage claim. The overall improvement goal remains active.

### Completed controlled ensemble follow-up

The [protocol](ensemble-protocol.md) was committed before weight fitting. Matched
five-member ensembles each offer 277 model parameters plus four weight coordinates.
Both reduce to 35.296% calendar-linear and 64.704% sine, validation NLL .604802036.
Quantum weight is zero; 2023-fitted weights likewise give no quantum benefit in 2024.
The [measured result](ensemble-results.md) rejects the candidate before final-seed
training or benchmark scoring. Independent dense predictions agree within 4.996e-16,
and all mixture KKT residuals are below 1.354e-8. A numerical tie correction is disclosed.
