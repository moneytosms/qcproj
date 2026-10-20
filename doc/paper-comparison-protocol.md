# Follow-up protocol: our quantum model versus the paper's model on the same test

Written and committed **before** the paper model is fitted or scored on this data.

## Question

Is our quantum model (2 qubits, week and month memory, range output) better than the
paper's exact quantum model (Takaishi 2026, 1 qubit, yesterday only, one number) when both
are trained on the same data and judged on the same unseen test days?

## Disclosure

The main fresh study was already scored on the test period (2025-01-01 to 2026-10-19) before
this comparison was planned. This follow-up adds one model, the paper's, which has no
settings to tune. Our models are the sealed ones from the main study and are not changed,
refitted or reselected. The seal is checked before anything is computed.

## Paper model (as published, via the audited `qcvol.training` implementation)

* Circuit: RY(arcsin r) RZ(arccos r²) RY(arcsin(2v − 1)) RZ(arccos v²) U(θ, φ, λ); forecast
  RV = P0 × scale. Inputs: yesterday's return and RV, divided by 1.2 × their training
  maxima (the author's published data has maximum 0.833 = 1/1.2).
* Training: COBYLA on training mean squared error, as in the paper. φ has no effect (shown
  in Phase 1), so it is fixed at 0. 5 uniform restarts per seed, 10,000 evaluations each,
  best by training objective, 20 seeds (0-19) like our models.
* Generation: v[t+1] = P0(r[t], v[t]); r[t+1] = √v[t+1] × N(0, 1), as in the paper.

## Our models compared

quantum-har D (headline) and quantum-har A, both sealed. For context: quantum-short D,
softmax-har D, HAR residual and persistence (tomorrow's RV = today's RV).

## Measures on the 657 test days

1. **Point forecasts of RV** (what the paper's model is built for): squared error and QLIKE,
   the standard volatility forecast loss: QLIKE = RV/h − log(RV/h) − 1, with h the forecast.
   For range models, h = Σ p(level) × mean RV of that level's training days.
2. **Range forecasts:** log loss over the four levels. The paper model gets a range the
   same way the HAR residual baseline does: its forecast plus the empirical distribution of
   its training errors in log RV ("paper + residual").
3. **Realism of fake histories:** 32 paths of 657 days after 100 burn-in days; the same four
   moments, scales and distance as the main study, against the real test period.

## Uncertainty and contrasts

Paired circular block bootstrap over test dates (7- and 30-day blocks, 2,000 replicates) on
seed-averaged daily losses. Contrasts (negative favours our model): quantum-har D − paper
and quantum-har A − paper, for squared error, QLIKE and log loss. All results are reported.
