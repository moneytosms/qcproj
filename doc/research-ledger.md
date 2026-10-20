# Research and verification ledger

Snapshot prepared 20 October 2026. Detailed protocols and scorecards linked below are the
source of truth; this page gives a compact index and records what was checked where.

## Research findings

| Study | Main result | What it supports |
| --- | --- | --- |
| [Original-paper reproduction](paper-reproduction.md) | Rebuilt the one-qubit Bitcoin circuit and recovered broad qualitative patterns, including near-random returns and anti-persistent volatility increments. Some tails, scaling values, and normalization differ from the paper. | A documented reproduction, not exact numerical identity or a quantum speedup. |
| [Fresh-data B/D/A study](fresh-study.md) | Weekly/monthly memory lowered quantum test log loss by 0.051. Classical models also improved with memory and remained better; realism training made paths more realistic at some forecast cost. | Memory and realism tradeoffs on one Bitstamp holdout; no quantum advantage. |
| [Paper-model comparison](paper-comparison.md) | On the same Bitstamp days, the upgraded quantum range model scored 0.570 log loss vs 1.196 for the paper model. Same-input softmax scored 0.518 and remained better. | The upgrade beats the paper implementation on this task; classical controls still lead. |
| [Frozen 20-seed study](final-study.md) | HAR quantile and HAR residual scored 0.528910 and 0.529544 test NLL; quantum D scored 0.691983. | No quantum advantage in this fixed comparison. The historical holdout had prior exposure in smoke studies. |
| [Quantum v2/v3 study](v2-study.md) · [v3 results](v3-study.md) | V3 improved on v2 (0.5145 vs 0.5288), but remained behind softmax-v2 (0.4962) and network-v2 (0.5042); this was post-hoc. | Circuit/model iteration alone did not beat classical controls. |
| [ETH](eth-study.md) · [BTC](btc-study.md) replication | ETH quantum was 0.03% better than the network; BTC was 0.21% worse. Both paired intervals included zero. | No marked gain in the two-market replication. |
| [SOL/DOGE replication](sol-doge-study.md) | Quantum was 2.98% better than the best classical SOL model and 1.30% better on DOGE; both missed the 5% rule and intervals crossed zero. | The registered two-market gate failed. |
| [BTC market-signal study](btc-market-signal-study.md) | The added BTC volatility feature led the SOL network by 0.39%, far below the 5% gate. ETH was stopped after the SOL gate failed; DOGE and BTC self-control were not run. | The feature did not advance. |
| [First cross-market v3 panel](multimarket-v3-results.md) | Quantum was 2.79% worse on LTC, 6.89% worse on BNB, and 1.24% better on ADA with uncertainty crossing zero. | The three-market pass rule failed. |
| [Calibrated LINK/DOT/AVAX panel](calibrated-v3-results.md) | Quantum gained 2.45% on LINK, 0.66% on DOT, and 5.68% on AVAX. The three-market rule failed; QLIKE was worse than both classical controls on all three assets. | AVAX is a single-market primary-metric signal, not transferable or all-metric evidence. |
| [Calendar/readout development](calendar-development.md) · [controlled ensemble](ensemble-results.md) | Classical sine/tanh controls beat the tested quantum variants; the controlled ensemble assigned zero weight to quantum. | The tested calendar/readout and ensemble approaches did not close the forecast gap. |
| [BTC quantum upgrade](btc-quantum-upgrade-results.md) | Selected depth-3 RY quantum readout scored 0.6457 validation log loss vs 0.6614 for the network after a converged higher-budget check (2.39% lower). | An exploratory validation candidate only; the previously scored BTC test was kept closed. |

These studies use different datasets, targets, splits, and sometimes different score
definitions. Compare numbers only within each cited report. Across studies, none establishes
general quantum advantage or physical-hardware speedup.

## Verification and environments

Test counts below are snapshots from their named commits; they are not cumulative and
should not be compared as if the suites were identical.

| Snapshot | Checks recorded |
| --- | --- |
| Initial root pipeline | 32 tests passed; Ruff lint and format passed. |
| Paper reproduction | 13 Phase 1 tests; combined with held-out pipeline, 40 passed. Separately checked 150,000 recurrence steps and 1,623 rolling estimates. |
| Distribution / nested-memory milestones | Distribution report: 59 passed. Nested-memory report: 93 passed, 1 skipped. |
| Fresh/final study milestones | Fresh study: 94 passed, 1 skipped. Later final-study correction: 109 passed, 1 skipped. |
| SOL/DOGE and calendar development | SOL/DOGE: 105 passed, 1 skipped. Calendar/readout: 120 passed. |
| PR #13 snapshot | 146 passed, 3 skipped; Ruff checks passed. |
| PR #16 snapshot before v3 tests were integrated | 152 passed, 2 skipped; Ruff checks passed. |
| Current consolidation tree | `uv run pytest -q`: **154 passed, 2 skipped**; `uv run ruff check .` and `uv run ruff format --check .` passed; `git diff --check` was clean. |

The current checks ran locally on Linux x86_64 (Omarchy kernel 7.2.5, glibc 2.44), using
`uv` 0.12.5, Python 3.13.15, NumPy 2.5.4, SciPy 1.18.1, pytest 9.1.1, and Ruff 0.17.1.
Commands: `uv run pytest -q`, `uv run ruff check .`, and `uv run ruff format --check .`.
Historical studies report their own runtime details; for example, the audited Phase 1
reproduction used Python 3.12, while the fresh-data study ran on two CPU cores. No IBM
hardware run was performed in the fresh-data study. The simulation results are classical
statevector calculations.

## Branch and PR bookkeeping

As of 20 October 2026, research and implementation PRs #1–#16 and documentation PR #17 are
merged into `main`. PRs #13–#17 were merged during this consolidation. PR #14's downloaded
market datasets and generated fit/evaluation files were removed from its final branch update to
comply with the repository rule; its model code, tests, configs, frozen protocols, and aggregate
score reports are retained.

| PR | Topic branch | Status |
| --- | --- | --- |
| #1 | `codex/project-foundation` | Merged |
| #2 | `codex/paper-reproduction` | Merged |
| #3 | `codex/memory-fit-investigation` | Merged |
| #4 | `codex/nested-memory-followup` | Merged |
| #5 | `codex/distribution-realism-study` | Merged |
| #6 | `codex/classical-comparisons` | Merged |
| #7 | `codex/final-study` | Merged |
| #8 | `nidhi/memory-realism-fresh-data` | Merged |
| #9 | `codex/calendar-quantum-improvement` | Merged |
| #10 | `codex/quantum-complementarity` | Merged |
| #11 | `nidhi/quantum-v2` | Merged |
| #12 | `srimoneyshankar/eth-study` | Merged |
| #13 | `srimoneyshankar/eth-study` | Merged |
| #14 | `feat/multimarket-quantum-study` | Merged |
| #15 | `research/next-forecasting-approaches` | Merged |
| #16 | `feat/btc-quantum-upgrade` | Merged |
| #17 | `docs/repository-ledger` | Merged |
| #18 | `docs/repository-branch-audit` | Merged |

Remote refs for these topic branches are retained for traceability. The audit found no remote
branch head ahead of `origin/main`, and no open PRs. Branches were not deleted.
