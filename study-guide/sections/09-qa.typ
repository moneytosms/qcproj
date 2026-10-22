#import "../template.typ": *

= Part 9. Questions You Might Be Asked

#let qa(q, a) = block(breakable: false, spacing: 0.9em)[
  #text(weight: "bold", fill: blue)[Q. #q] \
  #a
]

== About the idea

#qa[What is volatility, in one sentence?][How much a price swings in a period, measured here as the sum of squared 5-minute log returns over a day (realized volatility).]
#qa[Why forecast volatility and not price?][Direction is nearly unpredictable; the size of moves clusters and is predictable (autocorrelation 0.75 at one day). It is also what risk management and option pricing need.]
#qa[Why Bitcoin / crypto?][Highly volatile, trades 24/7, free data, and it is what the base paper used.]
#qa[What does 'the model has memory' mean?][It sees past days (yesterday, last week, last month) rather than only yesterday. Volatility is correlated across weeks, so more history means better forecasts.]
#qa[What is HAR and why is it your benchmark?][A linear regression of tomorrow's log RV on yesterday, 7-day and 30-day averages (Corsi 2009). Simple and notoriously hard to beat.]

== About the quantum part

#qa[What is a qubit and what does a measurement give?][A two-level quantum system with amplitudes $(alpha, beta)$. Measuring gives 0 with probability $|alpha|^2$ and 1 with probability $|beta|^2$.]
#qa[What is the Bloch sphere?][A picture of one qubit's state as an arrow in a ball. North pole is 0, south pole is 1; height sets the probabilities, longitude is a phase.]
#qa[What do R_Y and R_Z do?][Rotations of the arrow: $R_Y$ tilts it (changes the odds); $R_Z$ spins it around the vertical axis (changes phase only, unless followed by another rotation).]
#qa[How does data go into the circuit?][As rotation angles (angle encoding): $R_Y(arcsin r)$ and so on in the paper; in ours, input times a trainable weight.]
#qa[What does CNOT do and why use it?][Flips the second qubit if the first is 1. It entangles the qubits so the four outcome probabilities are not independent.]
#qa[Why two qubits?][Two qubits have four outcomes, matching our four volatility levels one to one.]
#qa[What is data re-uploading?][Feeding the same input into several layers with different trainable weights, making the circuit much more expressive.]
#qa[How is the circuit trained if it is quantum?][A classical optimiser (L-BFGS-B or COBYLA) adjusts the angles to reduce the loss; the circuit is simulated to evaluate it (hybrid quantum-classical training).]
#qa[Did you run on a real quantum computer?][No. Exact statevector simulator in NumPy/JAX. A script for IBM hardware exists but was not run.]
#qa[Is there any quantum speed-up possible here?][No: two qubits are trivially simulated by a laptop.]

== About the base paper and our rebuild

#qa[What did Takaishi's paper do?][A one-qubit circuit that takes yesterday's return and volatility, with one trainable $U_3$ gate; $P(0)$ is the next-day volatility; fed back to generate 50,000-day histories checked with multifractal analysis.]
#qa[What was your own discovery in the rebuild?][The $phi$ angle has no effect: $U_3 = R_Z(phi) R_Y(theta) R_Z(lambda)$ and the last $R_Z$ does not change the chance of reading 0. We proved it with the closed form $P(0) = 1/2 + 1/2 n dot b$ and numerically (spread 0.0).]
#qa[What is multifractal analysis / MFDFA?][A method that measures how fluctuations scale with window size via the Hurst exponent $h$. 0.5 means random walk; below 0.5 means rough, anti-persistent. Shuffled data returns to 0.5.]
#qa[Did you reproduce the paper exactly?][The circuit, fit and central behaviour yes (matrix vs closed form agree to 3e-16). Not every table digit: the exact scale grid is unpublished and our generated returns have lighter tails.]

== About our model and testing

#qa[What exactly changed versus the paper?][Memory (week and month), two qubits with a CNOT, four-level probability outputs, log loss training, time-ordered train/validation/test, classical same-input twins, fresh data plus ten coins, pre-written pass/fail rules.]
#qa[How do you define the four levels?][30th, 70th, 95th percentiles of *training* log RV (about −7.35, −6.29, −4.92 for Bitcoin).]
#qa[What is log loss and why that metric?][Mean of $-ln$ of the probability given to the true level. It is a proper scoring rule: rewards honest, confident, correct probabilities and punishes confident errors.]
#qa[What is QLIKE?][A standard volatility error that punishes under-forecasting more than over-forecasting.]
#qa[Why 20 seeds?][Training has random starts; averaging 20 evens out luck. It measures training variance only, not market diversity.]
#qa[What is the bootstrap interval?][Resample blocks of consecutive test days many times and recompute the gap; if the interval excludes zero the gap is unlikely to be luck.]
#qa[How do you stop yourself cheating?][Time-ordered splits, scaling and cut points from training only, written protocols committed before scoring, trained models hashed (sealed) before the test is opened, and rules like 'at least 5% on all coins in a group'.]
#qa[Why was the 5% rule chosen?][A margin large enough to matter beyond noise, fixed in advance so we could not pick a flattering threshold after seeing results.]

== About the results

#qa[So did quantum beat classical?][No. On fresh Bitcoin the classical softmax with same inputs got 0.5184 versus our v1 0.5695; with v2 inputs 0.4962 versus v3 0.5145. On ten coins no group met the 5% rule.]
#qa[Then what was the point?][(1) A verified rebuild with a new finding; (2) a design that halves the original model's error; (3) a rigorous negative result with a fair-testing recipe that others can reuse.]
#qa[Where did the halving come from?][Memory and probabilistic output, not quantum properties: classical models with the same changes do as well or better.]
#qa[Why did realism training hurt?][Optimising to make long generated histories look real competes with optimising next-day accuracy; the two goals pull in different directions.]
#qa[AVAX was 5.68% better. Is that a quantum win?][No. The rule requires every coin in the group to clear 5% (LINK and DOT did not); with ten coins one good result is expected by chance; and on QLIKE quantum was worse on all three.]
#qa[Are v2 and v3 results reliable?][They are post-hoc: designed after seeing a weekend effect in the test period, and scored on days already used. Treat as indicative.]
#qa[What would convince you of a quantum advantage?][A frozen design beating the best classical twin by the pre-set margin on a brand-new untouched test period, ideally on hardware and across many markets.]

== Traps: things NOT to say

#warn(title: "Avoid these claims")[
  - "We achieved quantum advantage" (no).
  - "We ran it on a quantum computer" (simulator only).
  - "We reproduced the paper exactly" (central behaviour and circuit, not every digit).
  - "Our model predicts price direction / makes money" (it forecasts volatility levels).
  - "The improvement is due to quantum" (due to memory and probability outputs).
  - "20 markets" for the 20 seeds (they are 20 training runs on one market).
]

= Part 10. Glossary

#table(columns: (1.1fr, 3fr),
  [Term], [Plain meaning],
  [Amplitude], [Complex number attached to a basis state; its squared size is the probability of that outcome.],
  [Autocorrelation], [Correlation of a series with itself $k$ steps earlier.],
  [Bell state / entanglement], [A two-qubit state like $(|00 chevron.r + |11 chevron.r)/sqrt(2)$ that cannot be split into two separate one-qubit states.],
  [Bitstamp / Binance], [Crypto exchanges providing our price data.],
  [Block bootstrap], [Resampling runs of consecutive days to estimate uncertainty when data are autocorrelated.],
  [Bloch sphere], [Ball picture of a single qubit state.],
  [Born rule], [Probability of an outcome equals squared size of its amplitude.],
  [Brier score], [Mean squared error of forecast probabilities.],
  [Calibration], [Whether forecasts of p% happen about p% of the time.],
  [CNOT], [Two-qubit gate: flip target if control is 1.],
  [COBYLA / L-BFGS-B], [Gradient-free / gradient-based optimisers from SciPy.],
  [Data re-uploading], [Feeding inputs into several circuit layers.],
  [Ensemble], [Averaging the predictions of several fitted models (here, 10 restarts).],
  [GARCH], [Classic model: variance depends on yesterday's shock and yesterday's variance.],
  [HAR], [Regression on yesterday, week and month averages of volatility.],
  [Hurst exponent h], [Memory measure: 0.5 random, above persistent, below rough.],
  [Kline / candle], [Open, high, low, close, volume for a time slice.],
  [Log loss], [$-1/N sum ln p_("true")$; lower is better.],
  [Log return], [$ln(P_1/P_0)$.],
  [MFDFA], [Multifractal detrended fluctuation analysis.],
  [Moment distance], [How far generated-path statistics are from real ones (realism score).],
  [Out-of-sample], [Data not used for training.],
  [Overfitting], [Memorising training noise; fails on new data.],
  [Pre-registration], [Writing the test plan before seeing results.],
  [QLIKE], [Volatility forecast loss favouring cautious forecasts.],
  [QCL], [Quantum circuit learning: trainable circuit as a model.],
  [Realized volatility (RV)], [Sum of squared intraday log returns.],
  [Ridge penalty], [Loss term discouraging large parameters.],
  [Rough volatility], [Very jagged volatility paths (small Hurst exponent).],
  [Seed], [Number fixing random initial conditions.],
  [Softmax], [Turns scores into probabilities that sum to 1.],
  [Statevector simulator], [Computes the exact amplitudes of a circuit on a classical computer.],
  [Temperature], [Dial that sharpens or flattens probabilities.],
  [USDT], [Stablecoin pegged near one US dollar.],
  [Volatility clustering], [Calm follows calm, wild follows wild.],
)

= Part 11. One-Page Cheat Sheet

*Formulas.* $"RV"_t = sum r^2$; $y_t = ln "RV"_t$; features $(y_(t-1), overline(y)_7, overline(y)_30, r_(t-1))$; $P(0) = |alpha|^2 = (1+z)/2$; paper: $P(0) = 1/2 + 1/2 n dot b$ with $phi$ absent; log loss $= -1/N sum ln p_"true"$.

*Numbers.* Paper log loss 1.196 vs our 0.5695 (52% lower); memory gain 0.051; v2 0.529, v3 0.5145, classical 0.4962; 20 seeds; 657 test days; 10 coins; rule: 5% on every coin in a group; no group passed; 109 tests.

*Three sentences.* We rebuilt a one-qubit volatility model and found one of its three dials is dead. We upgraded it with memory and four-level probability outputs, roughly halving its error, and tested it fairly. Classical models with the same inputs match or beat it, so we claim no quantum advantage.
