# Controlled ensemble result: no added quantum value on validation

20 October 2026. Follow-up to [calendar development](calendar-development.md), using
the committed [ensemble protocol](ensemble-protocol.md). No new benchmark scores or
twenty-seed training runs were produced.

## Result

The apparent quantum/sine complementarity disappears when the calendar-linear model
is available as a competing member. All three ensembles converge to the same effective
mixture: **35.296% linear + 64.704% sine**. Tanh, both extra small classical models,
and both quantum models receive zero weight within numerical precision.

| Candidate | Pooled 2023–2024 NLL ↓ | 2024 NLL with weights fitted on 2023 ↓ |
| --- | ---: | ---: |
| Base classical ensemble | .604802036 | .696398021 |
| Five-member classical ensemble | .604802036 | .696398022 |
| Five-member quantum/classical ensemble | .604802036 | .696398023 |

The five-member alternatives each offer 277 model parameters and four free mixture
weights. The base has 163 model parameters and two free mixture weights. Counts
include offered members receiving zero weight. Inputs and weight fitting are matched.

The best individual model, sine, scored .608194396 on pooled validation. The earlier
75% sine / 25% quantum diagnostic scored .606689: an improvement over sine alone,
but an insufficient comparison. The stronger classical mixture scores .604802.

Chronological fitting chooses approximately 38.560% linear / 61.440% sine, again
without quantum weight. Member settings had already used both validation years, so
this diagnostic is not an independent holdout. These validation results do not
establish generalization or an economic benefit.

## Verification and decision

All member probabilities were independently rebuilt with explicit dense gate matrices;
maximum discrepancy is 4.996e-16. All six mixture optimizations pass simplex KKT checks,
with maximum residual 1.354e-8. The objective is convex in the mixture weights.
Numerical differences between ensemble scores are ties.

The declared progression gate fails. We do not launch a twenty-seed quantum ensemble
run or score the exposed 2025–2026 benchmark for this rejected candidate. This
follow-up provides no evidence that more seeds would establish an ensemble benefit.

Calendar information improves the project; direct-day encoding and the tested quantum
ensemble do not establish an advantage. This conclusion is limited to these inputs,
circuits, training choices and dataset. A useful next milestone is evaluation of the
frozen calendar-classical forecast on additional chronological windows or an independent
asset, retaining quantum models as comparisons. That requires a new generalization
protocol rather than continued tuning of the exposed benchmark.

## Reproduction

First reproduce calendar development as documented in the README. Then:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 uv run python scripts/ensemble_complementarity.py \
  --source results/calendar-study-repeat --output results/ensemble-repeat
```

Output records source artifact hashes, script/protocol hashes, all weights, KKT
residuals, model counts and the progression decision. Existing directories cannot
be overwritten. Source data and the frozen training package are unchanged.
The first execution and numerical-tie correction are preserved in ignored output
directories; the correction is explicitly disclosed in the protocol.

Repository verification passes: **124 tests**, Ruff lint/format, and whitespace checks.
New tests cover known interior/boundary mixture optima, member-order invariance,
invalid inputs and matched active-parameter counts.
