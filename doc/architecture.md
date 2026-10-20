# Architecture decisions

These records explain choices made while implementing the project. The project PDFs
are the specification and explanatory references; their pilot claims are not execution
results. See [implementation.md](implementation.md) for the full research plan and
[progress.md](progress.md) for what has actually been verified.

## ADR 001 — A small Python package with separate mathematical layers

**Decision:** use `src/qcvol` with modules for data, quantum/classical models,
generation, training, metrics, and orchestration. Run through `qcvol` rather than notebooks.

**Reason:** the three research upgrades need controlled ablations. Shared preprocessing,
sampling, scores, and training prevent accidental differences between quantum and
classical experiments. Small functions let students read and test the mathematics.

**Trade-off:** notebooks may be added for exploration, but reusable logic belongs in the
package. There is no dashboard, cloud service, database, or deployment requirement.

## ADR 002 — NumPy statevectors first; quantum SDKs remain optional

**Decision:** simulate the one- and two-qubit circuits exactly with NumPy, batch independent
observations, and use SciPy COBYLA. Core runtime dependencies are NumPy and SciPy only.

**Reason:** a two-qubit pure state contains four complex amplitudes. Installing a large SDK
or requiring hardware adds no essential capability for the specified laptop experiment.
The batched simulator is checked against an independent Kronecker-matrix construction.

**Consequence:** these are noiseless classical simulations of quantum circuit probabilities.
Sampling on this laptop is pseudorandom, not a claim of physical quantum randomness.
An independent Qiskit/hardware comparison is still a separate research check.

## ADR 003 — Preserve circuit specification and state the parameter caveat

**Decision:** retain the planned 8-parameter layers, standard basis order `|q0 q1>` =
`00,01,10,11`, q0 controlling q1, and explicit `(theta, phi, lambda)` U3 argument order.

**Reason:** transparent reproduction is more useful than silently changing the ansatz.
The source paper lists its parameter vector in another order; named definitions avoid
mixing these conventions. `variance` means sigma squared, so the RZ argument sigma to
the fourth is `variance**2`, not `variance**4`.

**Finding:** the paper's phi angle is inactive. Independently, in the proposed two-qubit
circuit, the last two trainable RZ angles only change basis phases before a CNOT
permutation and Z measurement. They cannot change the probabilities. The 3-layer circuit
has **24 nominal parameters and at least two inactive directions** (at most 22 effective).
The B-only one-qubit model also has an inactive terminal RZ. Tests preserve these facts.
Softmax has 20 nominal parameters but 15 identifiable degrees of freedom, because a
common input-dependent shift of all four logits leaves probabilities unchanged. The
24-parameter tiny network uses reference logits to remove that softmax ambiguity.
Therefore “same size” is a nominal-budget comparison, not an established equal-capacity
comparison. A reduced-parameter circuit experiment is future work.

## ADR 004 — Keep upstream data and physical units distinct

**Decision:** explicitly download the author's two-column files at a fixed commit, save
SHA-256 hashes and license, keep raw downloads outside version control, and retain row
IDs. Accept independent consecutive-date CSVs separately.

**Reason:** `data-rstand` and `data-ystand` are files (the plan calls them folders).
The values are pre-scaled and contain no dates. The paper supplies an overall period,
but assigning dates to individual rows without checking alignment is unnecessary.
Upstream scaling may have used the whole sample; our train-only standardization cannot
undo that upstream look-ahead. New raw data will be needed for a strict forecasting study.

**Consequence:** author-data output is labeled standardized. Its return and RV scalings
need not preserve `Var(return) = RV`. Physical-unit VaR is disabled for this source.
For local CSV data the caller must supply compatible return/RV units and daily sampling.

## ADR 005 — Past-only HAR, chronological splits, training-only bins

**Decision:** target day t uses log RV at t−1, preceding seven-day mean, preceding
30-day mean, and return at t−1. Discard 30 warm-up rows, then split eligible targets
60%/20%/20%, without shuffling. Fit feature scaling and percentile bins on training only.

**Reason:** the detailed implementation plan requires validation. Its simplified 70/30 pilot
split cannot support honest hyperparameter selection. Crypto horizons are 7 and 30,
not the equity-market convention of 5 and 22.

**Consequence:** 913 daily observations give 883 eligible targets, split 529/177/177.
Test-day features can use earlier observed test days: this is rolling one-day-ahead
forecasting, not an unconditional forecast of the entire test block. Recursive simulation
uses only generated observations after its training-history initialization. Tied quantile
edges or empty pools fail rather than inventing four meaningful levels.

## ADR 006 — Give the B-only ablation an explicit design

**Decision:** use one qubit with weighted rotations `RY(day), RZ(week), RY(month),
RZ(return)` followed by trainable RY/RZ, repeated three times. Read P0 as a point RV.

**Reason:** the PDFs specify re-uploading for B but not a complete B-only circuit. This
choice makes a runnable intermediate model using the same four features.

**Trade-off:** B changes both memory and ansatz/parameter count, so the result does not
isolate memory alone. Add a matched-capacity short-memory control before making a
causal claim about B. Point-model MSE and distributional NLL are separate panels; a
point RV cannot be compared to a four-class NLL without an additional observation law.

## ADR 007 — Share the categorical observation model

**Decision:** bins use training log-RV quantiles .30/.70/.95. Generate a category using
Born (or classical) probabilities, choose uniformly from that bin's empirical training
log RV, and set return = exp(log RV/2) × independent standard Gaussian noise.

**Reason:** this implements the plan exactly and gives classical comparators the same
observation mechanism. Return shocks and within-bin values remain classical random draws.

**Trade-off:** the generator is bounded to observed training RV values. It cannot invent
more severe volatility than the training maximum, and its Gaussian return law is an
assumption. Test extreme events may reveal this limitation. HAR's categorical output uses
its residual CDF; the shared categorical generator is not a native HAR residual rollout.

## ADR 008 — Common random numbers, warm starts, and finite budgets

**Decision:** train NLL first, then warm-start each positive-lambda fit from it. Fix random
uniforms and Gaussian innovations during each objective. Draw a constant number of
random values regardless of which bins are selected. Train against mean simulated
moments, scaled by variability across overlapping training windows (floor .02).

**Reason:** common random numbers reduce objective noise and let quantum/classical
models receive the same streams. COBYLA needs no gradient through discrete sampling.
A fixed seed does **not** make this objective smooth. Window scales are descriptive
normalizers, not standard errors or confidence intervals.

**Budget:** `max_evaluations` maps to SciPy's COBYLA `maxiter`, which counts objective
evaluations. An extra initial-objective check is recorded as such in the methodology;
positive-lambda candidates also incur their shared forecast warm start. Optimizer status,
message, evaluations, initial/best loss, and elapsed seconds are saved. A budget-exhausted
fit is retained and labeled, never called convergence.

## ADR 009 — Validation selects; held-out test reports

**Decision:** select forecast-only circuit depth by validation NLL. Select the full model
across depths and lambdas using validation NLL + a prespecified validation realism weight
(default .01) × moment distance. That selection weight is distinct from training lambda.
The selected full model may choose lambda zero. Quantum, softmax, and tiny network use
the same candidate lambdas, budgets, splits, loss, and random streams.

**Trade-off:** depth search gives quantum more total candidate fits than classical; expose
this compute difference, rather than claim equal total search cost. Match total wall-clock
or evaluations in a stronger study. The runner saves test scores only for named final
selections; it does not use test scores to choose candidates.

## ADR 010 — Save evidence and distinguish undefined metrics

**Decision:** results contain a manifest, candidate fits/validation scores, per-model
records, compressed forecast/path arrays, and mean/std summaries. Refuse output-directory
reuse. Raw data and disposable runs are gitignored; measured smoke evidence is summarized
in the tracked progress document. Record source hashes, package versions, git revision
and dirty state, plus package source hashes. `uv.lock` pins the environment.

**Reason:** reproduce measurements and inspect failures. One seed gives unknown between-seed
spread (`null`), not evidence of zero variation. Undefined whole-path moment means are not silently averaged over only valid paths;
valid path counts are saved. Undefined ACF/MFDFA/tail estimates also
become JSON `null` or explicit unavailable diagnostics, never fabricated values.

**Metric conventions:** RPS averages over three ordered boundaries; a summed convention
is three times larger. Training/selection compares the mean simulated moment vector to
reference moments. Test realism averages individual path distances, exposing path spread.
MFDFA uses cubic trends, two-ended windows, q −5…5, and short diagnostic scaling ranges;
it is not yet the paper's 50,000-step/913-day rolling-window protocol. Its RV increments
are differences of **log** RV, as defined in the paper. Hill tails need at least 200 days.
A Kupiec test concerns violations of a return quantile under the explicit Gaussian/RV
mixture; “extreme volatility bin occurred” is not a VaR test.

## Integration with the existing Phase 1 package

Before publishing the first PR, upstream `main` gained the team's `qvol/` reproduction
package. Rebase onto it and preserve its code, datasets and results. Keep the new
`qcvol` namespace and root CLI separate because it implements a different held-out
protocol; do not silently substitute one package's scores for the other's. Root pytest
runs both suites. Root Ruff excludes `qvol/` to avoid an unrelated formatting rewrite.
The root guide links to both entry points. Consolidation can be a later reviewed change.

## Sources verified during implementation

- [Author data repository](https://github.com/takaishi-physics/QCL-volatility), pinned
  commit `2fec7ee621006bcbe1b7860d05b9589a7276a8f6`.
- [Original paper](https://arxiv.org/html/2609.04569v1), sections 3–6: gate definitions,
  full-sample fitting and upstream scaling. These differ from our held-out protocol.
- [SciPy COBYLA options](https://docs.scipy.org/doc/scipy/reference/optimize.minimize-cobyla.html):
  `maxiter` is the maximum number of function evaluations.
- [Matplotlib subplots](https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.subplots.html)
  and [savefig](https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.savefig.html)
  for optional local figures.

## ADR 011 — Investigate point training before claiming a memory improvement

**Decision:** keep the historical point-training defaults reproducible, and add explicit
`rv_prior` initialization, optional inactive-angle removal, and a separate training/validation
investigation runner. Do not change the Born distribution or realism loss in this milestone.

**Reason:** the legacy memory circuit starts near P0 = 1 whereas author RV targets are
mostly much smaller. At the training feature center, setting its last RY to
`2 arccos(sqrt(mean(training RV / rv_scale)))` gives the training mean readout. Small
seeded input weights allow learning around that prior. All other free rotations start at
zero. No validation or test targets enter the initialization. This changes optimization,
not the circuit family or target units. The legacy and prior starts are compared at the
same budgets; merely increasing a budget can overfit or converge to a poor local solution.

**Controls:** use the same 1- and 3-layer ansatz with yesterday's standardized log RV
repeated in the day/week/month slots. Keep the previous return input. This removes
multi-horizon information without changing nominal parameter counts. It does not prove
identical effective capacity. Independently compare the matrix circuit, confirm raw-RV
target alignment, and test terminal-phase invariance. Optional phase removal optimizes
2 paper angles or at most `6L-1` memory angles; saved parameters retain the full public
representation with the removed angle fixed to zero.

**Protocol:** each budget starts afresh. Choose the best restart by training MSE, then
compare those winners on validation MSE. Save all restarts, actual objective calls
(including the extra initial check), histories, convergence flags, parameters, predictions,
source hashes and elapsed fit times. Short-memory and full-memory candidates receive the
same grid. The investigation never scores test targets. Repeated use of validation is
exploratory model development, not evidence of out-of-sample superiority. Three starts
measure optimizer sensitivity, not uncertainty across independent datasets or a 20-seed study.

**Consequence:** a smaller training loss is not sufficient to accept B. Preserve the old
smoke results, use the new runner to diagnose them, and keep the final test comparison
and recursive-realism claims open. The measured findings and repeat instructions are in
[memory-fit-investigation.md](memory-fit-investigation.md).

## ADR 012 — Nest the paper inside a regularized two-weight memory extension

**Decision:** keep the original encoded state and readout, inserting weekly RY and
monthly RZ before U3. Set both added weights to zero to recover the paper exactly.
Warm-start from a training-fitted paper model, penalize only these two weights and
select their penalty on validation. A short-memory control repeats yesterday's
standardized log RV in both added gate slots. Keep the previous re-uploading model
and historical experiment unchanged.

**Reason:** the earlier B ansatz changed both inputs and circuit family. This small
extension gives an explicit zero-memory reference inside the same family, makes
initialization reproducible, and tests whether adding history helps beyond adding
flexibility. Fix the unobservable paper phi; optimize four meaningful coordinates
rather than carrying an inactive angle. No additional qubits are required.

**Controls and decision:** compare with a training-only paper fit and a raw-RV HAR
OLS forecaster on 1/7/30 horizons. Use five starts, explicit budgets, optimizer status
and finite-difference stationarity. A failed training-selected setting leaves the
memory decision inconclusive. The prespecified 1% validation improvement requirement
is a development rule, not a statistical test. Full details are frozen in
[nested-memory-protocol.md](nested-memory-protocol.md). Validation reuse, different
feature maps and total search work remain visible limitations. This milestone
selects a policy for D/A; it does not claim the final study has passed.

The initial nested sweep exposed a precision mismatch at alpha=1: COBYLA's 1e-5
trust-region floor did not satisfy the independent 1e-5 gradient threshold. Expose an
optional optimizer tolerance while preserving the historical default. Repeat the
full nested grid with floor 1e-7 for both controls, keeping the gradient check, alpha
grid, starts and decision unchanged. Preserve and cost the inconclusive first attempt.

## ADR 013 — Separate probability learning from realism selection

**Decision:** add a dedicated validation-only D/A runner. Apply the B-selected short
input policy inside every model, so it also controls recursively generated inputs.
Keep the historical HAR-based runner unchanged for reproducibility. Reduce terminal
quantum phases and the softmax shared-logit freedom. Give the small network the same
information with an explicit new 24-coordinate architecture. Full HAR remains a
separately labelled information-rich reference, alongside a short AR residual model.

**Reason:** extending the old smoke run would mix changes in memory, circuit depth,
loss and optimization. Fit NLL first with five starts and independent stationarity
checks, choose depth on validation, freeze it, then add the realism loss. Preserve
lambda zero as a fallback. There is no calibrated categorical observation law for the
paper's point output, so keep its MSE in the earlier B panel instead of comparing it
to probability NLL. This milestone tests D and A, without claiming B succeeded.

**Optimization:** use L-BFGS-B central numerical gradients for smooth forecast NLL;
count all numerical-gradient calls, including possible `maxfun` overshoot, and
independent central-difference diagnostics. Use COBYLA for the discrete fixed-stream
simulation loss. Its stopping-radius status is a finite-budget diagnostic, not a
stationarity proof. Record each restart, actual elapsed work and the larger quantum
depth search. Identical allowances do not imply identical total training effort.

**Simulation:** four training paths, eight selection paths, then two fresh 32-path audit
streams. Selection compares the mean moment vector; report individual-path distance
spread too, because averaging can conceal poor paths. Freeze lambda before the audit;
never promote a fresh-stream winner afterward. Reused validation is development data,
not independent evidence of quantum advantage. This is a sequential depth/lambda
selection, not a joint Cartesian sweep. The protocol is in
[distribution-study-protocol.md](distribution-study-protocol.md).

**Implementation detail:** fuse each local RY/RZ/RY/RZ block algebraically in the short
Born simulator to reduce rollout overhead. Test it against both the historical simulator
and independent dense Kronecker operators at all four depths. Artifact verification
uses dense operators and independently reconstructs the full random draw schedule,
recursive histories, scores and selection rules. Package hashes bind runs to source.

## ADR 014 — Add native finance forecasts and stabilize the classical network

**Decision:** fit HAR quantile regressions directly with HiGHS linear programming;
certify primal/dual optimality, repair predicted crossings by sorting, and document
CDF/tail construction when converting quantiles to bins. Keep native quantile scores
separate from the common categorical/empirical-bin quantiles. Count 60/45 coefficients
for full/short quantile models, with different information and capacity from D.

**Reason:** OLS plus residual quantiles is useful but is not quantile regression. Direct
pinball fitting allows conditional uncertainty to change with the inputs. Inverting
its finite quantile grid requires tail assumptions; native quantile scoring makes that
extra modeling step visible rather than conflating it with the fitted coefficients.

**GARCH:** use an optional `arch` Gaussian zero-mean GARCH(1,1), five starts on exactly
the training target-row returns, training-only return rescaling and prefix backcast.
Validate library recursion and constrained likelihood stationarity independently.
Author returns/RV have separate unknown scaling, and conditional return variance is
not realized variance. Fit an explicit training-only log-RV observation calibration
and empirical residual distribution. Count the two calibration coefficients and residual
sample. Shared-bin paths update h with generated returns; native GARCH paths are a
separately labelled observation-law reference. Do not infer physical-unit VaR.

**Network:** exact backpropagation avoids spending dozens of numerical-gradient calls
per step. The first comparison still caps four old unregularized starts, so preserve
it and add a declared L2 grid with five fresh starts per penalty. Choose restarts on
training and alpha on validation, then retain alpha when repeating A. Do not silently
reuse the earlier network A as an ablation of the new D. The stable regularized model
is a main comparator; failed unregularized starts remain evidence of conditioning.

**Fairness and evidence:** preserve both attempts, imported-source/artifact hashes,
all search costs and sensitivity-rank diagnostics. Local Jacobian rank is not a global
parameter-count theorem. Larger classical grids and richer historical inputs prevent
compute/capacity-matched superiority claims. The measured scorecard keeps negative
GARCH outcomes and quantum's small Brier advantage alongside classical NLL/RPS wins.
No new test scores or final 20-seed study are produced in this milestone. See
[classical-comparison-protocol.md](classical-comparison-protocol.md) and
[classical-comparison.md](classical-comparison.md).
