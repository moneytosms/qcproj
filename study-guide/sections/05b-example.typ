#import "../template.typ": *

= Part 5B. One Day, End to End

Follow a single real day through the whole pipeline so every term above becomes concrete. Numbers are our recomputation from `data/bitstamp_daily.csv`, scaling with training days (to 2022-12-31).

*Target day: Wednesday 9 April 2025 (Bitcoin, Bitstamp).* The model must forecast this day using only earlier days.

#table(columns: (1.2fr, 1.4fr, 2fr),
  [Step], [Value], [Meaning],
  [Feature 1: yesterday's log RV], [−6.947], [Yesterday's RV was 0.00096 (a $sqrt("RV") approx 3.1%$ move): ordinary, a little below the training average of −6.79.],
  [Feature 2: 7-day mean], [−6.994], [The week was similar.],
  [Feature 3: 30-day mean], [−7.538], [The month was quiet (well below the training average).],
  [Feature 4: yesterday's return], [−0.037], [Yesterday the price fell about 3.7%.],
  [Standardise (training mean, std)], [−0.14, −0.23, −0.98, −0.92], [How unusual each feature is in units of standard deviations. (Training means: −6.79, −6.79, −6.78, 0.001; stds 1.11, 0.93, 0.77, 0.042.)],
  [What happened: log RV of the day], [−5.899], [$sqrt("RV") approx 5.2%$ move.],
  [Level (cut points −7.35, −6.29, −4.92)], [*wild*], [−5.899 lies between −6.29 and −4.92, so the true label is level 2 = $|10 chevron.r$.],
)

*What each model does with those four standardised numbers:*
- *HAR:* weighted sum of the first three numbers gives a point forecast of log RV, then converts to four level probabilities.
- *Softmax:* four scores, each a weighted sum of the four numbers plus a bias, passed through softmax.
- *Our circuit:* multiplies each number by a trainable weight, uses the results as the angles of $R_Y, R_Z$ gates on the two qubits (data gates), applies trainable rotations and a CNOT, repeats 3 times, then reads the probabilities of $|00 chevron.r, |01 chevron.r, |10 chevron.r, |11 chevron.r$.

*Scoring.* Suppose a model forecast (calm 25%, normal 40%, wild 30%, extreme 5%). The truth was *wild*, so the penalty is $-ln(0.30) = 1.204$. A sharper model giving wild 50% would earn $-ln(0.5) = 0.693$; one giving wild 5% would earn $3.0$. Average over 657 test days to get the log loss.

#idea(title: "What this day teaches")[
  The inputs pointed at a quiet-to-normal day (a quiet month, an ordinary yesterday), yet the day turned out wild (a sudden large move). No model can foresee news; a good model gives the wild level a modest probability rather than none, and log loss rewards exactly that hedging.
]

== Four mini-derivations you can reproduce

*1. Why $P(0) = (1+z)/2$.* State $cos(theta/2)|0 chevron.r + e^(i phi) sin(theta/2)|1 chevron.r$. $P(0) = cos^2(theta/2) = (1 + cos theta)/2$ and $z = cos theta$.

*2. Why $R_Y (pi/2)$ gives 50/50.* $R_Y (a)|0 chevron.r = cos(a/2)|0 chevron.r + sin(a/2)|1 chevron.r$. For $a = pi/2$ both coefficients are $1\/sqrt(2)$, so $P(0) = 1/2$.

*3. Why parameters = 8 per layer.* Per qubit per layer: 2 data weights + 2 free angles = 4; two qubits give 8; three layers give 24. For v2: each of the 2 qubits has 2 rotations, each an affine function of 6 inputs (6 weights + 1 bias = 7), so $2 times 2 times 7 = 28$ per layer and $times 3$ layers $= 84$.

*4. Why softmax-v2 has 28 parameters.* Four levels, each a linear score of 6 inputs plus a bias: $4 times (6 + 1) = 28$.
