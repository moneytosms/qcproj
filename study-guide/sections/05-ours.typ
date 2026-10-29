#import "../template.typ": *

= Part 5. What We Built

== The pipeline

#fig("/fig/pipeline.png", [From raw prices to a forecast and a score.], width: 95%)

+ *Raw prices* every 5 minutes (Binance) or 1 minute grouped to 5 (Bitstamp).
+ *Daily RV:* sum of squared 5-minute log returns inside each UTC day; take $y_t = ln("RV"_t)$.
+ *Features:* for each day, using only earlier days: $x_1$ = yesterday's $y$, $x_2$ = mean of last 7 days, $x_3$ = mean of last 30 days, $x_4$ = yesterday's return. First 30 days dropped.
+ *Standardise:* subtract the training mean, divide by the training standard deviation (training period only).
+ *Model:* quantum circuit or a classical twin outputs four probabilities.
+ *Score:* compare with what happened (log loss, etc.).

== Four volatility levels (the output)

Rather than predict a precise number, we predict a *category*. Cut points are the 30th, 70th and 95th percentiles of *training* log RV.

#fig("/fig/levels_real.png", [Real Bitcoin training days (through 2022) split into the four levels. Cut points computed by us: log RV of −7.35, −6.29 and −4.92.], width: 80%)

#table(columns: (auto, 1fr, 1fr, 1.5fr),
  [Level], [Share of training days], [Rough day-size move (sqrt RV)], [Two-qubit outcome],
  [calm], [30%], [below about 2.5%], [$|00 chevron.r$],
  [normal], [40%], [about 2.5% to 4.3%], [$|01 chevron.r$],
  [wild], [25%], [about 4.3% to 8.5%], [$|10 chevron.r$],
  [extreme], [5%], [above about 8.5%], [$|11 chevron.r$],
)
(Day-size moves are $sqrt("RV")$ at the cut points: e^(−3.67)=2.5%, e^(−3.14)=4.3%, e^(−2.46)=8.5%. Our own conversion for intuition.)

*Why four?* Two qubits have exactly four measurement outcomes, so the quantum output maps one-to-one onto the levels.

*Why percentiles from the past?* Defining the levels using the future would leak information. In the test period (2025 to 2026) Bitcoin was *calmer* than history: 75% of test days fell in 'calm', 22% normal, 4% wild and *none* extreme (our computation). That is why the report says "the test period had no extreme days", and why slide 7's '3 in 10, 4 in 10...' describes the training mix, not the test mix.

== Our two-qubit circuit (v1)

#fig("/fig/circuit.png", [One layer of the circuit: blue gates load data, green gates are trainable, a CNOT links the qubits; the layer repeats L times.], width: 95%)

Per layer and per qubit:
+ $R_Y (w_1 x_a)$ then $R_Z (w_2 x_b)$: *data gates*. The input is multiplied by a *trainable weight* $w$ and used as the angle. Qubit 0 takes $(x_1, x_2)$ = yesterday and the week; qubit 1 takes $(x_3, x_4)$ = the month and the return.
+ $R_Y (a)$ then $R_Z (b)$ with trainable $a, b$: *free rotations*.
+ *CNOT* (control qubit 0, target qubit 1) after both qubits are done.

Parameters per layer: 2 qubits × (2 data weights + 2 free angles) = 8. Three layers = *24 parameters* (we verified `n_params = 8 × layers`). Finally the four outcome probabilities are read off:

$ p_k = |chevron.l k | psi(bold(x); bold(theta)) chevron.r|^2, quad k in {00, 01, 10, 11} $

*Example output (verified):* a randomly initialised 3-layer circuit on one input gave (calm 83%, normal 2%, wild 9%, extreme 7%), summing to 100%. Training moves these numbers toward the real frequencies.

#fig("/fig/two_qubit_out.png", [Output of an untrained circuit; training reshapes these four bars to match reality.], width: 50%)

*Training objective:* minimise log loss on the training days, optionally plus a penalty (ridge) or a 'realism' term.

*Why re-upload?* Data is fed in again in every layer (with different weights), which makes the function richer (Part 3).

== The versions (v1, v2, v3) and what each fixed

A validation-only investigation after v1 lost to classical models found three causes (from our v2 protocol), each addressed:

#table(columns: (auto, 1.5fr, 1.5fr),
  [Version], [Problem found], [Change],
  [v1], [Baseline: 2 qubits, 4 inputs, 3 layers, 24 params.], [],
  [v2], [(1) One qubit never saw yesterday or the week directly (only via the CNOT). (2) About 20% of validation days lay below the 5th percentile of training inputs, and circuit outputs (sines and cosines) bend back outside the training range. (3) No calendar: weekend log RV is lower by about 0.4 (train) to 1.4 (test).], [Every angle is an affine function of *all six* inputs (the 4 features squashed by $2 tanh(x/2)$, plus weekend and Monday flags for the target day); 84 parameters; ridge 0.001 and L-BFGS-B with exact gradients; 5 restarts.],
  [v3], [v2 still trailed the classical softmax on validation (0.648 best-restart vs 0.623). Single training restarts are noisy.], [Ridge 0.01 and an *ensemble*: average the probabilities of 10 restarts (validation 0.631). Chosen on validation only, then run with 20 seeds. For the later cross-coin runs a *temperature* (a confidence dial) is also fitted per model on 2023 validation data.],
  [RY-HAR hybrid (multi-coin)], [Want any gain to be attributable to the circuit.], [Only $R_Y$ gates; the classical HAR forecast is added to the circuit's output, with a mixing dial. At dial = 0 it *is* the classical HAR model (slide 25), so any improvement is credited to the circuit.],
)

*Temperature (softmax temperature) in one line:* divide the model's raw scores by $T$ before turning them into probabilities; $T > 1$ flattens them (less confident), $T < 1$ sharpens them.

*Parameter-count context.* The matched classical models have similar size (softmax-v2: 28 parameters; network-v2: 26) so the race is also fair on capacity.

#warn[v2 and v3 were designed after seeing the test period had a weekend effect. They are 'post-hoc'. Present their scores as indicative.]

== Realism-aware training

The paper judged realism of generated histories, so we tried adding a penalty that makes *generated* histories match real statistics (autocorrelation at 1, 7, 30 days, and the spread of day-to-day changes in log RV), measured against real windows of the same length as the generated paths (a fix found in our fresh-study protocol: lag-30 autocorrelation is 0.302 on the full series but only 0.136 on 256-day windows). The *moment distance* is the scaled squared difference between the generated and the real values of these four statistics (lower = more realistic). Finding: it is a trade-off. On fresh data forecasts got slightly worse but paths more realistic; on the paper's data both got worse (Part 6).

== Experiment design

#fig("/fig/fair.png", [Every quantum model is paired with classical models given exactly the same information.], width: 85%)

*Studies in order:* (1) rebuild the paper; (2) paper's data, frozen 20-seed comparison, split 529/177/177; (3) fresh Bitcoin (Bitstamp) with a locked test set; (4) improved v2, v3; (5) ten coins with pre-registered 5% rule. (6) calendar, ensembles, calibration follow-ups documented in `doc/`.

== Code map

#table(columns: (1.2fr, 3fr),
  [Folder], [Contents],
  [`qvol/`], [Rebuild of the paper: `paper_model.py` (circuit, closed form, fit, generate), MFDFA, 5 experiment scripts],
  [`src/qcvol/`], [Main pipeline: `data.py` (features, levels), `quantum.py` (statevector simulator: gates, `BornCircuit`), `classical.py`, `training.py`, `metrics.py` (log loss, RPS, calibration, moment distance, MFDFA, bootstrap helpers)],
  [`src/qcvol_v2/`, `src/qcvol_v3/`], [Improved circuits],
  [`src/qcvol_next/`], [Binance data (checksum verified) and multi-coin models],
  [`scripts/`], [Data builders, study runners, checkers, plotting],
  [`doc/`], [A protocol (plan) and a results note per study; `progress.md`, `research-ledger.md`],
  [Tests], [109 pytest tests + Ruff lint (`uv run pytest -q`)],
)
