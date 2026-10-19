# Verified progress

Updated 19 October 2026. This records what was actually built and run. The long-term
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
| 1: reproduce paper | **Open** | Compare fitted curves and long-run/rolling MFDFA against source figures; document deviations, rescaling and encoding-domain treatment |
| 2: establish B and D | **Open** | Adequate optimization, matched-capacity short-memory control, depth/level studies, comparable forecast/realism evidence |
| 3: complete fair scorecard | **Open** | GARCH(1,1), full required finance/quantile controls, stronger matched-compute comparison, uncertainty and convergence checks |
| 4: final study/report | **Not run** | 20+ seeds, full sweep, paper-matched diagnostics, final report/slides and literature recheck |

## Next implementation and research work

1. Audit upstream preprocessing and reproduce the original full-sample figure protocol
   separately from the held-out baseline. Check additional random starts and the B-only
   model's poor small-budget fit. Preserve the held-out test split.
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
