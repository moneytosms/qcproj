# BTCUSDT quantum forecast replication

The fixed ETH-selected RY HAR hybrid did not beat the best classical forecast on BTC.
This replication did not meet the 5% marked-improvement threshold.

## Data and protocol

The checksum-verified Binance BTCUSDT 5-minute archives cover 2017-08-17 to 2026-10-19
(3,351 UTC days). The builder records 33 timestamp gaps and 34 incomplete historical
dates; the 2025-01-01 to 2026-10-19 test interval is complete. Test-period returns were not
fabricated. See [data/README.md](../data/README.md) and the
[precommitted protocol](btc-replication-protocol.md).

The split matches ETH: train to 2022-12-31, validation 2023-2024, and 657 test days from
2025-01-01 to 2026-10-19. Architecture and depth were fixed from ETH validation. Final
models use 20 seeds, five restarts, and per-seed validation-only temperature calibration.
The 97.5% two-sided paired intervals account for the two market studies. Data, config,
protocol, selection, and code were frozen at commit `62d28f7` before test evaluation.

## Test results

Calibrated means average 20 final seeds. Lower is better.

| Model | Log loss | Normalized RPS | Extreme-bin Brier | QLIKE |
|---|---:|---:|---:|---:|
| RY quantum HAR hybrid | 0.531976 | **0.055172** | **0.001576** | 0.315640 |
| Weekend network | **0.530880** | 0.055560 | 0.001724 | 0.305485 |
| Weekend softmax | 0.534511 | 0.056081 | 0.001794 | **0.295503** |
| Weekend softmax-HAR hybrid | 0.537420 | 0.055604 | 0.001635 | 0.320761 |

Against the best classical log loss (weekend network), quantum is worse by 0.001096
(0.21%). The 97.5% intervals for quantum minus network were [-0.008732, 0.010571] for
7-day blocks and [-0.007817, 0.012366] for 30-day blocks. Both include zero. One of the
20 classical hybrid seed fits failed the eligibility check and remains included.

ETH had a negligible 0.03% log-loss edge with intervals crossing zero; BTC favors the
network by a negligible margin. The fixed RY HAR hybrid therefore has no demonstrated
marked advantage across these two markets. Both test windows overlap in time, and this
small simulation does not establish hardware speedup or general quantum advantage.
