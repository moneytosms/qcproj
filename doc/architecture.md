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
