# Protocol: quantum v2 (better input encoding, weekend input)

Written and committed **before** any v2 model is trained on its final seeds or scored on
the test period.

## Why there is a v2

In the fresh study ([results](fresh-study.md)), the quantum model (0.570 test log loss) lost
to classical models with the same inputs (softmax 0.518). A validation-only design search on
2023-2024 (development seeds 900 and 901, 5 restarts each, test rows dropped on load) found
three causes:

1. **One qubit was blind to yesterday.** Qubit 1 (the low bit of the level) only received the
   monthly mean and the return; yesterday's and the weekly volatility reached it only through
   the CNOT.
2. **Calm-market extrapolation.** About 20% of validation days lie below the 5th percentile of
   training inputs. The circuit's output is a sum of sines and cosines of the inputs, which can
   bend back outside the training range. The quantum model fitted training data better than
   softmax (0.840 vs 0.854) but did worse on validation (0.713 vs 0.680).
3. **No calendar.** Mean log RV on weekends is lower than on weekdays by about 0.4 in training,
   1.2 in validation (and 1.4 in test, see the disclosure below).

## Disclosure

The weekend effect was first noticed in the **test** period of the fresh study, after it was
scored. The v2 design was then chosen using validation data only, but the idea is
test-informed. Therefore **every v2 score on the 2025-01-01 to 2026-10-19 test period is a
post-hoc result** and is labeled as such. The clean confirmation is a new market (Ethereum,
planned) or future data, with this design frozen.

## Frozen v2 design (chosen on validation)

Inputs (6): the four standardized HAR inputs (yesterday log RV, 7-day mean, 30-day mean,
yesterday's return), each squashed as 2·tanh(x/2), plus two calendar flags for the **target**
day: weekend (Saturday or Sunday) and Monday, each centered by its training mean.

Circuit (2 qubits, depth 3, 84 parameters): per layer, on each qubit, RY(a·x + b) then
RZ(c·x + d), where every angle is an affine function of **all six inputs**; then CNOT
(control qubit 0). Level = 2·q0 + q1, as before. Loss: training log loss + 0.001·‖θ‖²;
L-BFGS-B with exact gradients (JAX), 5 restarts from N(0, 0.3²), initialization seed
100000 + 100·seed + 10·depth + restart, best by training objective.

Validation evidence (mean of seeds 900 and 901; lower is better):

| Design | Params | Validation log loss |
| --- | ---: | ---: |
| Old quantum-har, depth 3 | 24 | 0.713 |
| Old circuit, squashed inputs, depth 4 | 32 | 0.683 |
| All inputs on both qubits, depth 3, + calendar | 84 | 0.665 |
| ... + squashed inputs | 84 | 0.640 |
| **... + ridge 0.001 (v2)** | 84 | **0.638** |
| ... with ridge 0.01 | 84 | 0.643 |
| Same, depth 2 | 56 | 0.651 |
| Softmax, + calendar, squashed (softmax-v2) | 28 | 0.623 |
| Small network (2 tanh units), + calendar, squashed (network-v2) | 26 | 0.626 |

Not adopted: Gray-code level readout (worse), a third rotation per qubit (worse at depth 2),
depth 1 (unstable).

## Models trained (final seeds 0-19)

* **quantum-v2**: the frozen design above.
* **quantum-v2-nocal**: same, without the two calendar flags (ablation: how much is the
  weekend input).
* **softmax-v2**: softmax on the same six inputs, no ridge (validation preferred none).
* **network-v2**: 6 → 2 tanh → 4 logits on the same inputs (26 parameters), no ridge.

References (already sealed, not refitted): quantum-har D and softmax-har D from the fresh
study; the paper's model from the [paper comparison](paper-comparison.md).

## Seal and evaluation

Training reads only training rows. After training, the v2 artifacts and the `qcvol_v2` source
are hashed into `results/v2-study/seal.json` and committed **before** evaluation; evaluation
verifies both this seal and the fresh-study seal before reading any test row, and runs once.

Measures on the 657 test days: log loss over the four levels (primary), Brier score, and
QLIKE of the implied point forecast (mean RV of each level's training days, weighted by the
probabilities). Paired circular block bootstrap over dates (7- and 30-day blocks, 2,000
replicates) on seed-averaged daily losses. Contrasts (negative favors the left model):

1. quantum-v2 − quantum-har D (does v2 improve our quantum model?)
2. quantum-v2 − softmax-v2 (quantum versus classical, same inputs)
3. quantum-v2 − network-v2
4. quantum-v2 − quantum-v2-nocal (weekend input contribution)

Every result is reported. Realism of generated paths is **not** evaluated for v2 (the
generator does not yet simulate calendar days); v2 is a forecasting improvement only.
