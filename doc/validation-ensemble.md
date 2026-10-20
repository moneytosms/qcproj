# Exploratory validation-only quantum ensemble

This quick check used the already trained 20-seed quantum RY HAR hybrid and weekend
network. For each seed, both models were calibrated using that seed's validation-fitted
temperature, then their predicted probabilities were averaged at a fixed 50/50 weight.
The four-class log loss below uses validation labels only. No test rows or test scores were
read for this check. It is exploratory and does not replace a confirmatory protocol.

| Market | Quantum hybrid | Weekend network | Fixed 50/50 blend | Blend vs network |
|---|---:|---:|---:|---:|
| BTC | 0.654864 | 0.661434 | 0.655678 | 0.87% lower |
| ETH | 0.533549 | 0.517134 | 0.522049 | 0.95% higher |
| SOL | 0.645521 | 0.656222 | 0.644407 | 1.80% lower |
| DOGE | 0.761712 | 0.741301 | 0.738359 | 0.40% lower |

The fixed blend improves over the network on BTC, SOL and DOGE validation, but not ETH;
no market reaches the 5% target. This small check suggests the quantum probabilities may
add some signal to an ensemble, but it does not show a marked or generalizable benefit.
Do not use it to claim quantum advantage. A future confirmatory evaluation needs unseen
labels and a protocol committed before evaluation.
