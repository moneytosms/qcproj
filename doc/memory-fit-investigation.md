# Memory point model training investigation

19 October 2026. This milestone investigates the poor B-only point fit. It does not
run the B→D→A final study or claim quantum advantage. The project report remains paused.

## Question and evidence boundaries

The earlier smoke run used one initialization, three layers and 40 COBYLA evaluations.
Its test RV MSE was .33159 for B versus .0003044 for the paper model. Those historical
scores are retained in `progress.md`. This investigation uses the same chronological
529/177/177 split, but computes **training and validation scores only**. Its validation
numbers must not be compared directly with those historical test numbers.

## Checks and experimental design

- The target is the next day's raw RV, not log RV. Only the input features use log RV.
  Author RV is already within the probability readout domain; its point scale is one.
- Independently multiply the one-qubit matrices and compare with the batched simulator.
  Check the final RZ changes no probability. No circuit-order change is needed.
- Preserve the 30-day warm-up, training-only feature standardization and chronological
  split. A feature/target test and a perturbation of all future test values check isolation.
- Start each fit afresh at ceilings 40, 500 and 3,000 evaluations, with seeds 0, 1 and 2.
  Compare one and three layers, full HAR and short-memory inputs, and legacy/prior starts.
- Try 12,000-evaluation fits with the inactive phase removed and training-informed
  initialization; use broad uniform starts for the phase-free original paper model.
  A separate 500-evaluation control isolates phase removal at fixed initialization/budget.
- Choose each setting's restart by training MSE, then compare those winners on validation.
  Show all starts and convergence flags, including unfavorable outcomes. Validation is
  exploratory development data; this is not an independent statistical test.
- Track the extra initial objective check, all optimizer calls and elapsed fit time.
  Different layers have different forward costs even with equal evaluation ceilings.

The legacy initializer draws every angle from N(0,.3). `rv_prior` draws input weights
from N(0,.05), sets intermediate free rotations to zero and sets the final RY angle to
`2 arccos(sqrt(mean(training RV / rv_scale)))`. At the training feature center this gives
P0 equal to the normalized training target mean. The target scale and model family are
unchanged. No held-out target enters this formula.

The short-memory control repeats standardized yesterday log RV in the three RV gate
slots and retains yesterday return. Its nominal circuit and parameter counts match the
full HAR model. The input rank and effective capacity can still differ; it is an
information control, not proof of perfectly equal capacity.

## Measured findings

The target/circuit audit passes. The maximum literal-matrix discrepancy is 9.99e-16;
changing the terminal RZ changes predictions by at most 5.55e-16. Exponentiating the
stored training log targets recovers raw RV to 5.55e-17. All 529 training targets fit the
P0 domain: min .001815, mean **.035745**, median .021472, max .833333. No target scaling
or gate-order correction is justified by these checks.

### Initialization explains much of the smoke failure

For the original three-layer memory circuit, all three legacy starts predict much too
large an average RV. The training-informed starts begin near the observed scale. The
following are individual runs at the same 40-evaluation ceiling, not selected winners.
None of these six fits converged.

| Seed | Legacy initial mean prediction | Prior initial mean prediction | Legacy validation MSE | Prior validation MSE |
| --- | ---: | ---: | ---: | ---: |
| 0 | 0.858382 | 0.036520 | 0.25641006 | 0.00064678 |
| 1 | 0.957658 | 0.037104 | 0.04914744 | 0.00074962 |
| 2 | 0.776581 | 0.039132 | 0.00103909 | 0.00073484 |

This is an initialization and optimization failure, not evidence that RV should have been
used as a log target. The improved start is available explicitly; it is not a change to
the paper model or a post-hoc rescaling of validation/test targets.

### More training can worsen validation

For each row below, select the lowest-training-MSE restart among the three seeds. The
validation score belongs to that same restart. A convergence count refers to all three
starts, not just the winner. MSE is in author-standardized RV units (point scale one).
The 12,000-ceiling rows remove the inactive angle; they also have an explicit reduced
500-call control, so phase removal is not conflated with increasing the budget.

| Model | Layers | Start | Ceiling | Train MSE | Validation MSE | Converged starts |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| Full HAR | 3 | legacy | 40 | 0.00340169 | 0.00103909 | 0/3 |
| Full HAR | 3 | rv_prior | 40 | 0.00244973 | 0.00073484 | 0/3 |
| Paper | 1 | legacy | 500 | 0.00318485 | 0.00072042 | 3/3 |
| Full HAR | 3 | legacy | 500 | 0.00229260 | 0.00091854 | 0/3 |
| Full HAR | 3 | rv_prior | 500 | 0.00233376 | 0.00066852 | 0/3 |
| Full HAR | 3 | legacy | 3,000 | 0.00212761 | 0.00154859 | 0/3 |
| Full HAR | 3 | rv_prior | 3,000 | 0.00228195 | 0.00072492 | 0/3 |
| Paper | 1 | uniform reduced | 12,000 | 0.00318485 | 0.00072042 | 3/3 |
| Full HAR | 1 | rv_prior reduced | 12,000 | 0.00251367 | 0.00053164 | 3/3 |
| Short memory | 1 | rv_prior reduced | 12,000 | 0.00253691 | 0.00051614 | 3/3 |
| Full HAR | 3 | rv_prior reduced | 12,000 | 0.00219872 | 0.00121110 | 0/3 |
| Short memory | 3 | rv_prior reduced | 12,000 | 0.00235222 | 0.00052004 | 0/3 |
| Full HAR | 3 | rv_prior reduced | 500 | 0.00233017 | 0.00068030 | 0/3 |
| Short memory | 3 | rv_prior reduced | 500 | 0.00250739 | 0.00048667 | 0/3 |

At 3,000 evaluations, legacy full-HAR three-layer seed 0 reduces training MSE to .002128,
but its validation MSE rises to .001549. Seed 2 at the same budget instead gives validation
MSE .000556. Initialization sensitivity persists beyond a small smoke budget. The legacy
one-layer seed-0 fit even reports optimizer convergence at training MSE .120760, whereas
other starts reach about .002514. An optimizer success flag is a termination condition,
not proof of a good local or global solution.

The training-mean constant and persistence controls have validation MSE .00103401 and
.00057420 respectively. Their training MSEs are .00318375 and .00387608. The paper fit
here uses the training portion only, unlike the earlier full-sample reproduction; their
losses must not be compared as though they used the same target set.

### The long-memory benefit remains unproven

Compare the phase-free, training-informed one-layer fits: they converge reliably, but the
short-memory control is competitive with or better than full HAR on validation. The
larger three-layer circuit can lower training loss without providing a validation gain.
Across the whole exploratory grid, validation may favor a budget-limited candidate;
that is not a reason to call it converged or adopt it as the final study policy.

The three initialization seeds are not independent market samples. Their variability
measures optimizer sensitivity; it is not a confidence interval for predictive skill.
The same validation block has been used to develop initialization and depth choices, so
an independent final evaluation is still necessary. No test scores were computed here.

### Next action

Use the training-informed, phase-free one-layer fits as the stable point-training
reference for the next controlled study, retain multiple starts, and require convergence
checks rather than a fixed tiny budget. Keep the short-memory control. Do not declare B
a successful memory upgrade from this investigation. Investigate regularization or an
ansatz that contains the original baseline as a nested case before accepting deeper
memory circuits; the present design changes capacity as well as information. Distribution
forecasting and realism training still require their own controlled evaluations.

## Reproducing and reviewing the investigation

The checked-in configuration is `configs/memory-investigation.json`. From the repository
root, after installing the locked environment and obtaining the pinned author data:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 uv run python scripts/investigate_memory.py \
  --author-data data/raw/author --output results/memory-investigation-01
uv run python scripts/verify_memory_investigation.py results/memory-investigation-01 \
  --author-data data/raw/author
uv run python scripts/plot_memory_investigation.py results/memory-investigation-01
```

Run folders are new and never overwritten. `manifest.json` records source hashes, versions,
configuration, split metadata and mathematical checks. `records.json` retains every fit;
compressed arrays retain parameters, loss histories and aligned train/validation predictions.
`summary.json` identifies the training-selected restart within each setting. `selection.json`
records the exploratory validation selection and total search cost. The verifier recomputes
predictions/losses and selection from those arrays, and checks the source hashes. There are
no test scores or test target arrays in these artifacts. Metadata retains test row IDs/counts
so the split remains auditable.

The two plots show budget/initialization effects and validation forecast curves with
convergence histories. They live in the ignored run's `figures/` folder. Raw experiment
outputs stay local; this measured narrative and the deterministic runner are versioned.

## Verification and cost of the measured run

Local run: `results/memory-investigation-2026-10-19/`. Python 3.12.14, NumPy 2.5.4,
SciPy 1.18.1, qcvol 0.1.0; CPU execution with one BLAS/OpenMP thread. The 102 fits used
**169,383 actual objective calls**, including initial checks, and about **547.6 seconds**
of summed fitting time on this machine. This excludes acquisition, auditing, plotting and
other orchestration overhead; it is not a portable runtime prediction. Twenty-two of 102
fits reported optimizer success. All three phase-free one-layer prior starts converged
for each input set; none of the six three-layer 12,000-ceiling fits did.

The independent artifact verifier recomputed **72,012 train/validation predictions**
with maximum discrepancy **0**, checked all losses, source hashes, call counts, saved
parameters, training-only restart selection and validation selection. No test scores were
computed. Two figures were rendered and visually inspected. On this branch, the complete
suite passes **40 tests** (35 root pipeline tests, including eight new cases, plus five
legacy qvol tests); Ruff lint, formatting and diff whitespace checks pass. The separate
paper-audit PR has additional tests and remains independent of this branch.

The exploratory validation winner is a three-layer short-memory, legacy-initialized
500-evaluation setting: its training-selected restart has validation MSE .00047718 and
training MSE .00248002. None of its starts converged. We record that selection without
recommending it as a final converged model. Among the converged, phase-free one-layer
settings, full HAR gives validation MSE .00053164 and short memory .00051614. These
results do not establish an advantage from the longer memory inputs.

## Implemented behavior and remaining scope

`fit_point` now accepts `initialization="rv_prior"` and `reduce_inactive=True`, and supports
`memory_short`. Saved point parameters keep the full gate representation with a removed
phase fixed to zero; the fit separately records how many coordinates were optimized.
For three layers that is 18 stored and at most 17 optimized angles. A one-layer memory
fit has six stored and at most five optimized angles; the paper has three stored and two
optimized angles. Further degeneracies are not ruled out.

Historical default fitting remains unchanged so smoke runs can be replayed. The new
investigation explicitly exercises improved starts and phase-free fits. Adopting a final
training policy in the B/D/A study requires validation and fair search-budget accounting.
A low training loss does not establish long-memory skill, calibrated probabilities,
realistic recursive histories or quantum advantage. The 20-seed study remains pending.
