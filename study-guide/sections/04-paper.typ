#import "../template.typ": *

= Part 4. The Base Paper and Our Rebuild of It

*Reference:* T. Takaishi, "Quantum Circuit Learning for Volatility Modeling: Multifractal Analysis of Realized Volatility Time Series", _Fractal and Fractional_ 10(7):442, 2026 (arXiv 2609.04569). Slides 10 to 19.

== What the paper does, step by step

+ *Data.* A Bitcoin series of 913 days (Aug 2020 to Feb 2023), supplied by the author already *rescaled*: returns $r_t$ into $[-1, 1]$ and volatility $sigma_t$ (a number derived from RV) into $[0, 1]$. Rescaling is needed because the values become *angles*.
+ *Encode yesterday.* Prepare one qubit starting at $|0 chevron.r$ and apply four data-dependent rotations (below).
+ *Learn.* Apply one trainable gate $U_3 (theta, phi, lambda)$.
+ *Read out.* $P(0)$ is the forecast of the next day's volatility $sigma_(t+1)$.
+ *Train* $(theta, phi, lambda)$ so forecasts match history (minimise mean squared error, 2000-step COBYLA optimiser, 10 restarts).
+ *Generate.* Feed the circuit's own forecast back in as the next day's input (together with a random return), repeating for 50,000 days to produce a synthetic price/volatility history.
+ *Judge realism* with multifractal analysis (MFDFA) comparing the generated data with real Bitcoin.

#fig("/fig/fig_paper_vs_ours.png", [Paper model vs our model (from our report).], width: 70%)

== The circuit in formulas

With $r$ = yesterday's (scaled) return and $s$ = yesterday's (scaled) volatility, the circuit applies, in order:

$ R_Y (arcsin r) quad R_Z (arccos r^2) quad R_Y (arcsin(2 s - 1)) quad R_Z (arccos s^2) quad U_3 (theta, phi, lambda) $

then measures. Forecast $= P(0)$.

#idea(title: "Plain meaning")[
  The first two gates 'write' yesterday's return into the arrow's orientation, the next two write yesterday's volatility, the last gate is the model's learned rotation. The measured chance of 0 is the output. Data goes in as *angles*; the answer comes out as a *probability*.
]

*Worked example (verified with our simulator).* Take $r = 0.3$, $s = 0.4$ and the fitted $theta = -4.557, phi = 0.360, lambda = 1.700$.
- Angles: $arcsin 0.3 = 0.3047$; $arccos 0.09 = 1.4806$; $arcsin(-0.2) = -0.2014$; $arccos 0.16 = 1.4101$.
- After the four data gates the arrow points at Bloch vector $bold(b) = (-0.3212, -0.1144, 0.9401)$ (mostly near the north pole).
- The learned gate corresponds to direction $bold(n) = (0.127, 0.980, -0.155)$.
- Forecast $P(0) = 1/2 + 1/2 (bold(n) dot bold(b)) = 1/2 + 1/2 (-0.2987) = 0.3507$.

Computing $P(0)$ by the full matrix product gives exactly the same 0.3507 (we verified to 3e-16 on all 913 real input pairs).

== The closed form and the "φ does nothing" discovery

Because the arrow's final measurement depends only on its height, the paper's whole model collapses to one dot product:

$ P(0) = 1/2 + 1/2 thin bold(n)(theta, lambda) dot bold(b)(r, s) $

where $bold(n) = (-sin theta cos lambda, sin theta sin lambda, cos theta)$ depends only on $theta$ and $lambda$, and $bold(b)$ is the Bloch vector produced by the data gates.

#math-box(title: "Why φ drops out (the proof in one line)")[
  $U_3 (theta, phi, lambda) = R_Z (phi) R_Y (theta) R_Z (lambda)$ up to a global phase that is invisible. $R_Z (phi)$ is the *last* rotation applied before we measure 0/1. A rotation around the vertical axis never changes height, hence never changes $P(0)$. So $phi$ is a dial connected to nothing.
]

#fig("/fig/phi_flat.png", [Numerical proof from our simulator: sweeping φ over a full circle leaves the forecast unchanged (spread 0.0); sweeping λ changes it (spread 0.34).], width: 80%)

*Consequences:* the paper's model really has *two* working parameters, not three. It uses only *one day* of history. It outputs *one number*. The optimiser can give very different-looking triples $(theta, phi, lambda)$ with identical forecasts (our report and a later audit found different angle values with the same fit quality).

*Our fit on the paper's data:* $theta = -4.557, phi = 0.360, lambda = 1.700$; training MSE 0.00205; correlation between forecast and real next-day value 0.449 (a modest but real predictive link).

== Generating synthetic histories

Rule: $sigma_(t+1) = P(0)(r_t, sigma_t)$ and $r_(t+1) = sigma_(t+1) epsilon_(t+1)$ with $epsilon tilde N(0,1)$. Start from the last real day, run 50,000 steps. The result is an invented price path whose statistical texture can be compared with the real series.

== Multifractal analysis (MFDFA) made simple

*The question:* does the invented series *behave* like the real one at every time scale?

*Hurst exponent $h$.* Measures memory in a series by seeing how its fluctuations grow with window size $s$: fluctuation $tilde s^h$.
- $h = 0.5$: pure random walk, no memory (like coin flips).
- $h > 0.5$: persistent, trends continue.
- $h < 0.5$: anti-persistent, jagged, "rough", reverses itself.

*DFA* (detrended fluctuation analysis) estimates $h$ robustly by removing local trends (we use cubic trends) in windows of many sizes. *MFDFA* (Kantelhardt et al. 2002) repeats this for many "moments" $q$; if $h(q)$ changes with $q$ the series is *multifractal* (different-size fluctuations scale differently).

#table(columns: (1.3fr, 1fr, 1fr),
  [Series (h at q = 2)], [Real Bitcoin], [Generated by model],
  [Returns], [about 0.5 (random-walk like)], [about 0.5 (matches)],
  [Increments of log RV (IRV)], [0.17 (very rough)], [0.05 to 0.08 (also very rough)],
  [Shuffled control], [0.5], [0.5],
)
(Numbers from our audit; the paper reports 0.504 / 0.155 / 0.030 for empirical returns / IRV / IAR. Scale-grid details are not public, so exact digits differ and we say 'not exactly replicated'.)

*Reading it:* the model's synthetic returns look random like real returns, and its volatility increments are as jagged as the real ones (far below 0.5). Shuffling destroys it (back to 0.5), proving the roughness is a real structure. That is the paper's claim that the circuit 'produces realistic data'.

#fig("/fig/fig_memory_gap.png", [Diagnostic figure from our rebuild: the single-day model's forecast memory versus real memory.], width: 80%)

== What we reproduced and what we did not

#table(columns: (1fr, 1fr),
  [Reproduced], [Not exactly reproduced],
  [The circuit and its fit (loss plateau about 0.002)], [Exact digits of every table entry; exact scale grid is unpublished],
  [Random-like generated returns], [Heavy tails: our generated returns have lighter tails than real returns],
  [Very rough generated volatility], [Zero-return handling changes one statistic (kurtosis 41.7 vs paper's 4.40 depending on convention)],
  [$phi$ has no effect (our new finding)], [],
)

#warn[Say "we reproduced the circuit, the fit and the central behaviour", not "we reproduced every number".]

== The four gaps that motivated our work (slide 15)

+ *Memory:* the circuit sees only yesterday, though volatility remembers weeks (Part 1 autocorrelation).
+ *Uncertainty:* one number, with no sense of how likely a storm is.
+ *Goal mismatch:* trained to predict next-day value, praised for looking realistic over 50,000 generated days.
+ *No fair test:* the model was never scored on unseen days or against a classical rival.
