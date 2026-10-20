# BTC market-signal validation study

This validation-only experiment tested the [registered protocol](btc-market-signal-protocol.md): add the preceding seven-day BTC log-RV mean to a weekend-aware quantum hybrid and to each classical comparator. ETH, SOL, BTC, and DOGE test rows were not used. The candidate failed the 5% validation gate on SOL, so the conjunctive advancement rule was impossible; ETH was stopped mid-panel and DOGE was not run.

## SOL: complete two-seed panel

Calibrated four-level validation log loss; lower is better.

| Model | Seed 900 | Seed 901 | Mean |
|---|---:|---:|---:|
| Quantum hybrid, depth 1 | 0.645546 | 0.645236 | 0.645391 |
| Quantum hybrid, depth 2 | 0.661093 | 0.672182 | 0.666638 |
| Quantum hybrid, depth 3 | 0.684591 | 0.700475 | 0.692533 |
| Six-input softmax | 0.659323 | 0.659323 | 0.659323 |
| Six-input network | 0.647917 | 0.647917 | 0.647917 |
| Six-input HAR residual | 0.657122 | 0.657122 | 0.657122 |

Depth 1 was best. Its 0.39% lead over the network missed the required 5% by a wide margin. No bootstrap intervals were computed after this gate failed. Every completed optimizer fit was eligible.

## ETH: partial panel at stop

| Model | Seed 900 | Seed 901 | Notes |
|---|---:|---:|---|
| Quantum hybrid, depth 1 | 0.539096 | 0.519148 | Complete |
| Quantum hybrid, depth 2 | 0.549822 | 0.524786 | Complete |
| Quantum hybrid, depth 3 | 0.535310 | not run | Partial |
| Six-input softmax | 0.540211 | not run | Partial |
| Six-input network | 0.520999 | not run | Partial |
| Six-input HAR residual | 0.527610 | 0.527610 | Complete |

All completed ETH fits were eligible. The missing ETH fits and the full DOGE panel were not run because SOL had already made advancement impossible. The BTC self-control was not run; its new feature duplicates its existing weekly HAR input.

## Decision

Reject this BTC-volatility input for the current quantum architecture as a marked-improvement candidate. The only complete two-seed market panel showed a 0.39% lead, while deeper circuits were worse. These validation scores are exploratory and do not support a claim of quantum advantage. This study did not read or rescore ETH or SOL test periods.
