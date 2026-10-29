#import "../template.typ": *

= Part 7. What It All Means

== Why quantum did not win here

+ *Two qubits is tiny.* A laptop simulates the circuit instantly. There is nothing here a classical computer finds hard, so no speed-up is possible.
+ *Same information, same answers.* The circuit's output is a sum of sines and cosines of the inputs (a Fourier-type function). A small classical model with the same inputs can approximate nearly the same family of forecasts. Research agrees: Schreiber et al. (2022) show many small quantum models have classical "surrogates"; Bowles, Ahmed and Schuld (2024) show that with fair benchmarks, simple classical models usually outperform quantum ones.
+ *Advantage needs hard problems.* Quantum computers are expected to help on tasks that overwhelm classical machines (factoring, certain simulations). A four-input forecast is not one.

#say[
  "This is not a failure of the quantum idea. It is a clear picture of where it stands today: our careful design improvements raised accuracy, but they did not make the circuit better than a classical model with the same information."
]

== Limitations (volunteer these)

- *Simulator only.* No real quantum computer; no noise modelled. An IBM hardware script exists but was not run.
- *Reused test period.* v2, v3 and several later studies reuse the 2025 to 2026 test days; their scores are indicative, not confirmatory.
- *Seeds are not markets.* 20 seeds measure training randomness, not 20 independent experiments.
- *Optimiser budget.* Training stopped at a fixed budget; this does not prove the best settings were found.
- *Data limits.* The paper's data is pre-scaled (no real units); the fresh test period had no 'extreme' days.
- *Cross-asset replication* uses the same dates as earlier assets, so it is not a new chronological holdout.

== Future work

- Test the best Bitcoin setting (3-layer $R_Y$ circuit, 2.39% better than the network on validation) on truly new data.
- Run on IBM hardware and study noise.
- Formal forecast-comparison tests (Diebold-Mariano).
- Other quantum approaches: *quantum reservoir computing* (a fixed quantum system whose output is read by a simple trained layer) and *Born machines* (circuits that learn to sample data distributions).

== Team contributions (slide 42)

#table(columns: (1.1fr, 2.5fr),
  [Member], [Work],
  [Nidhi Rakesh], [`qvol` package (paper rebuild), v2 models, fresh Bitstamp memory and realism study, paper-vs-ours comparison, sealed results, IBM script],
  [Srimoneyshankar Ajith], [Coordination, Binance data pipeline with checksum verification, ETH/BTC/SOL/DOGE studies and pre-written rules, $R_Y$-HAR hybrid, research log],
  [Bharadwaj B Chand], [Paper-rebuild check and multifractal analysis, memory experiments, realism study, classical baselines (HAR, GARCH), verification scripts],
  [Vishnunath A Suresh], [Literature survey, metrics and statistical design, report and presentation],
  [Gopi Krish], [Code integration and PR review (#1 to #12), automated checks, LTC/BNB/ADA and LINK/DOT/AVAX studies, plots],
)
