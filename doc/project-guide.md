# Quantum volatility project: from idea to running code

Read this first if you are joining the course project. It connects the simple PDF guide
to the code, explains the experiment, and gives a reading order. The PDFs stay in the
repository as reference material. The implementation plan is [implementation.md](implementation.md);
reasons behind engineering choices are in [architecture.md](architecture.md). Actual
completion and measured checks are in [progress.md](progress.md).

The repository also includes the team's existing [`qvol/`](../qvol/README.md) Phase 1
reproduction, added upstream while this pipeline was being developed. Its experiments
use full-sample fitting and live under `qvol/experiments/`; this guide's `qcvol` commands
run the new held-out comparison pipeline from the repository root. Their outputs are
separate. Read the Phase 1 README and experiment 01 when studying paper reproduction;
its claims are not automatically evidence that our held-out models have passed a gate.

## 1. What question are we trying to answer?

A quiet Bitcoin day is often followed by another quiet day; turbulent days also cluster.
We want to forecast **tomorrow's volatility level and its probability**, and generate
long artificial histories that preserve this clustering.

For example, a useful forecast could be `[.10, .50, .30, .10]`: 10% calm, 50% normal,
30% wild, 10% extreme. These numbers are an illustration, not a measured repo result.
They do not predict whether Bitcoin's price goes up or down. They describe the size of
price movement, not a trading recommendation.

Our central research question is whether three changes improve a published one-qubit
volatility model. A second question is whether a classical model performs as well or
better. An honest classical win is a valid result. There is no expected quantum speedup
from simulating two qubits.

## 2. Start with the financial quantities

A return measures a price change. A five-minute log return is
`log(price_now / price_five_minutes_ago)`. Daily **realized variance**, conventionally
called RV in these documents, is the sum of squared intraday returns. Squaring prevents
positive and negative changes from cancelling. If the intraday returns were .01, −.02,
.01, RV would be .0006 in decimal-return units. Standard deviation is the square root
of a variance; the terms are sometimes loosely mixed in finance writing.

RV is positive and highly skewed. We work mainly with `y = log(RV)` to reduce the scale
of large spikes. ACF at lag 7 measures the linear relationship between today's log RV
and log RV seven days earlier. A positive ACF over many lags is evidence of persistence.
Vol-of-vol here means the standard deviation of daily changes in log RV.

Our first dataset is the author's published standardized returns and RV. It has 913
numbered observations. It is not five-minute prices, and we cannot rebuild RV or recover
original financial units from these files alone. The acquisition manifest preserves its
source commit, hashes and license. A strict raw-data forecasting study remains future work.

## 3. The quantum ideas used here

A qubit's pure state has two complex amplitudes, `a|0> + b|1>`. Its probabilities are
`|a|²` and `|b|²`, which sum to one. A quantum gate changes amplitudes through a unitary
matrix. RY mixes amplitudes; RZ changes their phases. Phases can affect later gates even
when they do not immediately change probabilities.

Two qubits have four amplitudes for `00, 01, 10, 11`. Our CNOT flips the second bit
when the first bit is one. Together with the rotations it can produce correlations and
entangled states. The Born rule converts each final amplitude to its squared magnitude.
That gives four probabilities.

The laptop computes these probabilities exactly with a statevector. Sampling from those
probabilities simulates measurement using a pseudorandom number generator. On hardware,
actual circuit measurements would supply outcomes; finite shots and device noise would
also introduce estimation error. No hardware account or token is needed for the code here.

## 4. The paper's starting model

The reference is Tetsuya Takaishi's [Quantum Circuit Learning for Volatility Modeling](https://arxiv.org/abs/2609.04569).
It encodes yesterday's standardized return and RV into one qubit using RY/RZ gates,
applies U3, and uses `P0` as tomorrow's RV point forecast. It minimizes RV mean squared
error with COBYLA. It then recursively generates a history using
`return = sqrt(predicted_RV) * Gaussian_noise`.

The paper reads a probability as a **number** representing variance. It does not output a
four-level distribution. Its scalar probability is not a confidence score that the RV is
correct. Its parameter phi affects only a final phase and cannot affect P0. There is an
exact equivalent classical formula:

`P0 = 1/2 + 1/2 * dot(n, b)`

Here `b` is the encoded state's three-dimensional Bloch vector and `n` is a unit vector
controlled by theta and lambda. Read `paper_probability`, `bloch_vector`, and `paper_twin`
in `quantum.py` together. `qcvol verify-paper` numerically checks equality and phi
invariance. That is an algebra check, not a full reproduction of the paper's figures.

The paper fits the entire sample to study generated statistics. We use a held-out protocol
for comparisons. Our `paper` model is thus a baseline using the stated circuit, not an
assertion that the original full-sample experiment has already been reproduced.

## 5. The three upgrades, in order

### B — Remember multiple horizons

For target day t construct four features using only completed earlier days:

| Feature | Meaning | Source days |
| --- | --- | --- |
| day | yesterday's log RV | t−1 |
| week | average log RV over the previous week | t−7 through t−1 |
| month | average over the previous month | t−30 through t−1 |
| return | yesterday's return | t−1 |

Crypto runs every day, so a week has 7 observations and a month has 30. Standardize each
feature using its training mean and training standard deviation. A standardized value of
+2 means two training standard deviations above the training mean.

`memory_b` is a one-qubit re-uploading point model using these inputs. Its exact gate
sequence is our documented intermediate design because the PDFs leave it unspecified.
It also increases capacity, so an extra capacity-matched control will be needed to isolate
the benefit of memory alone.

### D — Forecast a distribution from measurements

The main model has two qubits and three layers. In each layer:

1. q0 receives RY(weight × day), then RZ(weight × week).
2. q1 receives RY(weight × month), then RZ(weight × return).
3. Each receives a learned RY and RZ rotation.
4. CNOT links q0 to q1.

Repeating these steps is **data re-uploading**. Each layer stores eight angles/weights;
three layers store 24. The two terminal RZ angles do not affect observed probabilities,
so these are 24 nominal parameters, with at least two inactive directions. This matters
when discussing fairness and expressive capacity.

| Basis state | Volatility level | Training log-RV interval |
| --- | --- | --- |
| 00 | calm | below percentile 30 |
| 01 | normal | percentile 30 to below 70 |
| 10 | wild | percentile 70 to below 95 |
| 11 | extreme | percentile 95 and above |

The cut points come from training targets only. Ties are assigned to the upper interval.
A test day can be larger than the training maximum and still be labeled extreme.

The forecast is the four Born probabilities. A model can confidently make a wrong forecast;
we must check calibration across many days, not just show a convincing example.

### A — Train generated histories to look realistic

Forecast-only training minimizes negative log likelihood: take the probability assigned
to the true level, take minus its logarithm, then average over training days. Predicting
1% for the observed event incurs a much larger penalty than predicting 80%.

Realism training adds a second term:

`loss = forecast_NLL + lambda * sum(((generated_moments - real_moments)/scales)**2)`

The moments are log-RV ACF at 1, 7 and 30 days and vol-of-vol. Training reference moments
and their normalization scales use training data only. A positive lambda fit starts from
the forecast-only solution. Lambda controls the **training** trade-off. We compare several
lambdas on validation data; the test split does not choose one.

Generation is a feedback loop: construct today's features → predict four probabilities →
sample a level → sample a training log-RV value within it → draw a Gaussian return → append
that generated day → repeat. There is no access to real future days in this loop.

Sampling makes the loss nonsmooth. Fixed streams make candidate evaluations reproducible
and less noisy, not differentiable. COBYLA searches without gradients. We reserve different
streams for training, validation, and final test paths.

## 6. How the data split prevents accidental answers

We discard the first 30 days as feature history. Of the remaining eligible targets, the
first 60% train, next 20% validate, and last 20% test. With 913 rows that means
529 / 177 / 177 targets. These differ from the PDFs' pilot counts by design.

Training learns angles, scaling, bins, empirical pools and reference moments. Validation
chooses architecture depth and lambda. Test measures the final named selections. The
validation selection criterion is NLL plus a prespecified realism weight (.01 by default),
which is distinct from the candidate training lambdas.

Test forecasts are rolling one-day-ahead: yesterday's **observed** test RV may be an input
to today's forecast, because it would already be known. Synthetic path generation uses
its own previous predictions after initialization. These are different tasks.

The published standardized source may already contain full-sample rescaling. Our own
train-only operations cannot remove that upstream issue. We record it and do not claim
a completely untouched raw-data holdout experiment.

## 7. What the comparisons tell us

| Code name | Purpose | Forecast panel |
| --- | --- | --- |
| paper | original one-qubit structure | RV MSE |
| memory_b | one-qubit HAR re-uploading | RV MSE |
| quantum_forecast | B+D; depth chosen by validation NLL | four-level probabilities |
| quantum_selected | B+D+A candidate selection, may select lambda zero | four-level probabilities |
| frequency | always predict training level frequencies | four-level probabilities |
| softmax_forecast / selected | classical linear probability model, same loss/streams | four-level probabilities |
| tiny_nn_forecast / selected | 24-parameter nonlinear classical comparator | four-level probabilities |
| har_residual | standard log-HAR with training residual CDF | four-level probabilities |

Softmax stores 20 coefficients, but common-logit shifts leave 15 identifiable degrees
of freedom. The tiny network uses two tanh hidden units, three reference logits, and
five skip connections for 24 stored parameters. Neither comparator establishes equal
functional capacity. All use the same categorical generation mechanism for comparable
path tests; HAR is not yet being tested with its native continuous residual generator.
GARCH(1,1) is planned and is not currently included in these results.

Quantum/classical learned distributions share optimizer budgets, seeds, loss, and
preprocessing per fit. Sweeping several quantum depths creates more total search work;
that should be reported and controlled in a final comparison.

## 8. Read both report cards

**Forecast:** log loss (smaller is better), normalized RPS (smaller; nearby level errors
cost less), extreme-bin Brier score (squared probability error), and calibration counts.
Our RPS averages three cut-point errors. A paper that sums those errors reports a value
three times larger. RV MSE is reported separately for point forecasters.

**Realism:** lagged ACF, vol-of-vol, normalized moment distance, Wasserstein distance
between log-RV distributions, a Hill return-tail estimate, and MFDFA diagnostics on returns
and log-RV increments. Shuffling removes time ordering while retaining the marginal values;
comparing original and shuffled statistics helps distinguish distribution shape from memory.
MFDFA estimates h(q), tau(q), alpha and f(alpha); h(2) summarizes scaling, and the spectrum
width is a multifractality diagnostic. Short samples can give misleading patterns.

The current MFDFA routine is a diagnostic implementation checked on simulated white noise
and integrated noise. It has not reproduced the paper's rolling-window protocol. For
insufficient data a metric is unavailable rather than invented. Hill estimation requires
200 days; MFDFA requires 160 finite nonconstant observations and enough scales.

VaR is a return quantile, not the probability of the extreme volatility category. The code
can invert the explicit Gaussian/empirical-RV mixture and apply a Kupiec violation test.
This is disabled for the author's independently standardized series, whose scales cannot
be assumed physically consistent. For compatible local CSVs it is an assumption-based
input-unit risk diagnostic; short samples provide weak evidence.

## 9. Install and run

From the repository root, with Python 3.11+ and [uv](https://docs.astral.sh/uv/) available:

```bash
uv sync --extra dev --extra plots --python 3.12
uv run qcvol verify-paper
uv run pytest -q
```

Use an output directory that does not already exist. Runs refuse overwrite.

Offline synthetic example (clearly labeled synthetic):

```bash
uv run qcvol demo --config configs/smoke.json --output results/demo-01
```

Author data (requires internet and Git for the explicit fetch step):

```bash
uv run python scripts/fetch_author_data.py
uv run qcvol run --author-data data/raw/author --config configs/smoke.json --output results/btc-01
uv run python scripts/plot_results.py results/btc-01
```

Independent daily data must have columns `date,return,rv`, strictly ascending consecutive
ISO dates, finite returns, and positive RV. The caller is responsible for compatible
units. For example, columns can begin `2025-01-01,0.012,0.0004`; a usable file needs many
more rows. Missing days are rejected, not silently filled.

```bash
uv run qcvol run --csv data/my_daily.csv --config configs/smoke.json --output results/custom-01
```

The smoke configuration uses one seed and 40 optimizer evaluations. It tests the software
and is too small to support a scientific conclusion. Budget exhaustion is expected and
recorded. The study configuration proposes 20 seeds, four depths and four lambdas:

```bash
uv run qcvol run --author-data data/raw/author --config configs/study.json --output results/study-01
```

That can take substantially longer. Passing this command does not complete paper
replication, the missing controls, or the remaining finance baselines. Inspect one run
and its convergence before spending the full compute budget. `uv.lock` pins dependencies;
use `uv sync --locked --extra dev --extra plots` to reproduce the saved environment.

## 10. Understand the saved files

| File | Read it to learn |
| --- | --- |
| manifest.json | config, source hash, split, transforms, units, package versions, limitations |
| candidates.json | every tried depth/lambda, learned parameters, optimizer status, validation scores |
| records.json | final named model/seed scores, calibration, per-path diagnostics |
| summary.json | mean and between-seed standard deviation; one-seed spread is null |
| model-seedN.npz | test probabilities or point predictions, targets/rows, parameters, generated paths |
| figures/ | optional plots from `scripts/plot_results.py` |

Example inspection in Python:

```python
import numpy as np

run = np.load("results/btc-01/quantum_selected-seed0.npz")
print(run["probabilities"][0])  # calm, normal, wild, extreme
print(run["log_rv_paths"].shape)
```

If a run fails, its manifest remains `running`. Use a new output path when rerunning.
Do not mistake an incomplete folder for a complete experiment. Do not replace measured
values with the PDFs' pilot table. Optimizer `success: false` can simply mean the configured
function-evaluation budget was reached; inspect its message and improve the budget.

## 11. The order to read the repository

1. **README.md** — installation and where things live.
2. **This guide** — understand the objective, terminology and execution path.
3. **doc/implementation.md**, then **doc/progress.md** — intended stages versus actual evidence.
4. **doc/architecture.md** — assumptions, parameter caveats, reproducibility choices.
5. **qvol/README.md**, then **qvol/experiments/01_reproduce_paper.py** — the existing
   full-sample reproduction and its saved results. Then **src/qcvol/data.py** — trace
   one held-out target day and confirm its inputs are in the past.
6. **src/qcvol/quantum.py** — RY/RZ/U3 → paper encoding → classical twin → BornCircuit.
   Read **tests/test_quantum.py** alongside it for the independent matrix comparison.
7. **src/qcvol/classical.py** — frequency, softmax, tiny NN and HAR comparators.
8. **src/qcvol/generation.py** — how probabilities become a recursive artificial history.
9. **src/qcvol/metrics.py** — precise definitions of what training and evaluation measure.
10. **src/qcvol/training.py** — forecast loss, realism loss, common random numbers,
    initialization and optimizer budget. Notice the separate point-model path.
11. **configs/smoke.json**, then **src/qcvol/experiment.py** — follow preparation →
    candidate fits → validation choice → final scores/artifacts.
12. **src/qcvol/cli.py** and **scripts/** — entry points, data acquisition and figures.
13. **tests/test_data.py**, **test_generation_training.py**, **test_metrics.py**,
    **test_experiment.py** — leakage, repeatability, scoring and serialization checks.
14. Run the smoke command and compare its files with section 10; then return to the
    PDFs for the broader study and final research claims.

For a first code walkthrough, follow `cli.main → prepare → run_experiment →
fit_distribution → model.probabilities → generate → forecast_scores`.

## 12. How to contribute without invalidating the study

Choose a task from the unchecked plan. Record any new assumption in the architecture
document. Add correctness checks for mathematical or temporal behavior, run tests and
lint, and save a fresh run. Keep evaluation seeds separate from training. Select choices
on validation; reserve test for reporting. Update progress with actual evidence.

Before claiming success, complete the paper-figure gate, matched-capacity ablations,
GARCH and any required quantile baseline, adequate optimization, 20+ seeds, uncertainty
analysis, and a fresh literature review. Hardware and Ethereum transfer are optional.
The PDFs' pilot numbers and novelty assertions are context, not proof from this repository.

## 13. Quick vocabulary

| Term | Meaning here |
| --- | --- |
| RV / log RV | daily realized variance / its natural logarithm |
| HAR | model/features combining daily, weekly and monthly volatility history |
| ansatz | chosen trainable circuit structure |
| re-uploading | encoding the same features again in several layers |
| Born probabilities | squared magnitudes of state amplitudes |
| shot | one measurement outcome from one prepared circuit |
| NLL / log loss | penalty for assigning low probability to the observed class |
| realism moment | summary of an artificial history's temporal behavior |
| lambda | weight of the realism penalty during training |
| ablation | staged comparison to examine the effect of a change |
| classical twin | non-quantum model used to test what the circuit contributes |
| calibration | agreement between predicted probabilities and event frequencies |
| seed | starting value making pseudorandom draws reproducible |
| held-out | observations kept out of parameter fitting |
| MFDFA | multiscale detrended fluctuation analysis for scaling diagnostics |
| Kupiec | unconditional coverage test of return-quantile violations |

## Reading the baseline preserving memory follow-up

Start with [the measured decision](nested-memory-followup.md), then the
[protocol and convergence amendment](nested-memory-protocol.md) and ADR 012 in
[architecture.md](architecture.md). The follow-up retains previous-day inputs for D;
its validation results do not establish longer-memory skill.

For the code, read `src/qcvol/nested_memory.py` for the exact zero-weight paper
identity, warm start and raw-RV HAR comparator. Then read `src/qcvol/nested_study.py`
for regularization/restart selection, convergence gates and the policy decision.
`tests/test_nested_memory.py` checks independent matrices and future-data isolation.
Run, audit and plot using the three `scripts/*nested_memory.py` entry points described
in the measured note. Raw run folders stay ignored. The existing main Born runner
still needs the selected short-input policy before the next D comparison.
