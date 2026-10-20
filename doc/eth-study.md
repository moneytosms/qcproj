# ETH weekend-aware quantum forecast

The study did not establish a marked quantum improvement. Its pre-registered threshold
was at least 5% lower test log loss than the best classical comparator, with both paired
7- and 30-day 95% block-bootstrap intervals below zero.

## Data and protocol

Binance ETHUSDT spot 5-minute klines were checksum-verified and aggregated to UTC daily
realized variance. Data cover 2017-08-17 to 2026-10-19 (3,351 days). The archive has 33
timestamp gaps and 34 incomplete dates, all before the test period. Observed close changes
across gaps were included once; missing bars were not synthesized. The daily data and
checksums are in `data/ethusdt_daily.csv` and `data/ethusdt_daily.json`.

Training used 2017-09-16 to 2022-12-31 (1,933 targets), validation used 2023-2024 (731),
and the untouched test used 2025-01-01 to 2026-10-19 (657). Development selected a depth-1
RY quantum expert on the HAR baseline. A validation-only scalar temperature was fitted for
each final seed and applied unchanged to its test predictions. The final test was evaluated
once after hashing the data, config, code, selection, and all 20 training files. The full
protocol and amendments are in [eth-quantum-upgrade-protocol.md](eth-quantum-upgrade-protocol.md).

## Test results

Calibrated means average 20 final seeds. Lower is better.

| Model | Log loss | Normalized RPS | Extreme-bin Brier | QLIKE |
|---|---:|---:|---:|---:|
| RY quantum HAR hybrid | 0.648027 | 0.069749 | 0.003169 | 0.254218 |
| Weekend network | **0.648215** | 0.070073 | 0.003307 | 0.247706 |
| Weekend softmax-HAR hybrid | 0.652777 | **0.070023** | 0.003210 | 0.249178 |
| Weekend softmax | 0.654499 | 0.070196 | 0.003720 | 0.255746 |

The quantum hybrid's log-loss gain over the best classical model is 0.000188, or 0.03%.
Its paired mean differences (quantum minus classical) were:

| Comparator | Mean difference | 7-day 95% interval | 30-day 95% interval |
|---|---:|---:|---:|
| Weekend network | -0.000188 | [-0.014185, 0.010654] | [-0.014823, 0.011385] |
| Weekend softmax-HAR hybrid | -0.004749 | [-0.016394, 0.006452] | [-0.014837, 0.006315] |
| Weekend softmax | -0.006472 | [-0.026337, 0.011009] | [-0.027229, 0.011845] |

Every interval includes zero; the 5% threshold was missed. The study therefore does not
show a marked quantum benefit. Two of 20 softmax-HAR hybrid seed fits failed the registered
eligibility check. Their selected fits remain included in the summary.

The test is one market and one date window. Results are from exact classical simulation of
a small quantum circuit; they show neither hardware speedup nor general quantum advantage.
