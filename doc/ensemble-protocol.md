# Quantum complementarity follow-up

Declared after the calendar development sweep and its exploratory mixture diagnostic,
before fitting the following ensemble weights or running final seeds. This is a
post-hoc follow-up, not an independent confirmatory experiment. The 2025–2026 benchmark
has already been exposed by PR #8.

## Fixed comparison

All members use calendar inputs and the selected 730-day training half-life. Preserve
the original development artifacts and source hashes. Reuse the selected linear,
four-unit tanh/sine, and two-layer quantum/direct-day models, with feature ridge .001.
Add three-unit tanh and sine controls at the same ridge from the existing development
grid. Count active circuit coordinates, excluding terminal RZ redundancies.

| Ensemble | Members | Member parameters |
| --- | --- | ---: |
| Base | Linear, tanh-4, sine-4 | 163 |
| Classical | Base plus tanh-3, sine-3 | 277 |
| Quantum | Base plus quantum-2, direct-day quantum-2 | 277 |

Both five-member ensembles have four additional simplex-weight degrees of freedom.
Equal nominal parameter counts do not imply equal computation or effective capacity;
report all restarts, optimizer calls, diagnostic calls and elapsed fit time.

## Weight fitting and decision rule

Average each member's probabilities over development seeds 910/911. Fit nonnegative
weights summing to one by minimizing validation NLL, using analytic gradients, SLSQP
and a simplex KKT residual check of 1e-5. Use the same optimizer for every ensemble.
Report weights, pooled scores and a chronological diagnostic: fit weights on 2023,
score 2024. Member settings already used both years, so this diagnostic is not a
clean holdout. Do not tune extra members, penalties or thresholds after these results.

Proceed to twenty fresh optimization seeds only if the quantum ensemble improves
pooled validation NLL over the matched classical ensemble and its 2023-trained weights
also improve 2024 NLL. Otherwise document the failed gate and retain the classical
ensemble without spending the larger final-training budget.

If the gate passes, freeze the pooled weights and member specifications before fitting
seeds 0–19 with the existing three-start training budgets. Select starts using training
objective only. Score the exposed benchmark once; report every seed, mean and
dispersion, paired 7/30-day block bootstrap intervals, and per-year results. The primary
contrast is quantum minus matched-classical ensemble NLL; negative favors quantum.
No superiority claim unless the measured effect and uncertainty support it.

This stage tests forecast complementarity. It does not establish improved generated
paths, hardware advantage, or transfer to another asset. Those require separate work.

## Numerical handling clarification after first execution

The first execution returned identical optima up to roundoff: pooled differences near
1e-15 and chronological differences near 1e-9. Its literal `<` comparison marked the
pooled difference as an improvement, but the chronological gate failed. We corrected
the comparison to treat absolute differences at or below 1e-7 as numerical ties.
This clarification was made after seeing those outputs; it is not a predeclared
scientific effect threshold. It cannot turn a failed gate into a successful one.
The first raw run remains preserved; the corrected output is in a separate directory.
