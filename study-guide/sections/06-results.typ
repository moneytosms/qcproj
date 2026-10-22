#import "../template.typ": *

= Part 6. Every Result, Explained

*How to read any result here:* lower log loss is better; compare only models scored on the *same* test set; ask "is the gap bigger than luck?" (bootstrap interval) and "was this planned before seeing the data?".

== Step 1: Rebuilding the paper (slides 16 to 19)

We rewrote the model from scratch in NumPy and trained it on the author's data. Outcomes: training MSE 0.00205; forecast/real correlation 0.449; synthetic returns random-like; synthetic volatility rough; matrix circuit equals the closed form to 3e-16; $phi$ has exactly zero effect. This is a *reproduction*: a trustworthy base, not an improvement.

== Step 2: Paper's own data, 20 seeds (slide 34)

#table(columns: (2fr, 1fr),
  [Model (paper's data, 177 test days)], [Test log loss],
  [HAR quantile (classical)], [*0.5289*],
  [HAR residual (classical)], [0.5295],
  [Small network (classical)], [0.5784],
  [Softmax (classical)], [0.5822],
  [Quantum, range forecast], [0.6920],
  [Quantum + realism training], [0.8623],
)
*Reading:* every classical model beats the quantum one. Realism training *hurt* forecasts (0.6920 to 0.8623) and, on the test data, made generated histories less realistic (moment distance 19.72 to 31.86).

== Step 3: Fresh Bitcoin and the head-to-head with the paper (slides 31 to 33, 35)

Fresh Bitstamp Bitcoin, 657 test days (Jan 2025 to Oct 2026), mean of 20 seeds.

#table(columns: (1.5fr, 1fr, 1fr),
  [Measure (lower = better)], [Original paper model], [Our quantum v1],
  [Log loss], [1.196], [*0.5695*],
  [QLIKE], [0.840], [*0.504*],
  [Realism distance], [215.3], [*33.5*],
)
All confidence intervals exclude zero. So: *our upgrade clearly beats the original model*, roughly halving log loss (1.196 to 0.5695; about 52% lower).

#fig("/fig/fresh.png", [Test log loss on fresh Bitcoin, 657 days, 20-seed mean (from our report).], width: 80%)

*Why did it improve?* Two reasons, neither exclusively quantum: *memory* (week and month): adding them improved log loss by 0.051 (interval −0.071 to −0.030); and *probabilistic output*: four probabilities carry more information than one number and are scored with a different, more demanding metric.

#fig("/fig/fig_memory.png", [Effect of memory on test log loss (fresh study).], width: 65%)

*But:* the classical softmax with the same inputs scored *0.5184*, better than our 0.5695. And slide 33: re-running the comparison on thousands of resampled test periods, the classical model stayed ahead in 95% of reshuffles, so it is not luck.

*Realism trade-off (slide 35).* Rewarding realistic paths: on fresh Bitcoin, forecasts worse but paths more realistic; on the paper's data, both got worse.

#warn[The paper-vs-ours comparison was planned after we had seen the main test results. Say this if asked.]

== Step 4: v2 and v3 (slide 36)

#fig("/fig/fresh_results.png", [Fresh Bitcoin test log loss across versions and the best classical twin.], width: 80%)

#table(columns: (2fr, 1fr),
  [Model], [Test log loss],
  [Quantum v1], [0.5695],
  [Quantum v2], [0.529],
  [Quantum v3], [0.5145],
  [Classical softmax-v2 (same inputs)], [*0.4962*],
)
Each version improved (v3 vs v2: −0.0144, interval −0.022 to −0.007) but the classical twin still wins by about 0.018. On QLIKE the gap is larger (v3 0.424 vs softmax 0.289). These scores are *post-hoc* (same test days as earlier studies), so they are hints.

#fig("/fig/fig_v2.png", [Quantum v2 comparison (from our report).], width: 65%)

== Step 5: Ten coins (slide 37)

#fig("/fig/multimarket.png", [Quantum gain over the best classical model per coin; the red line is the 5% target.], width: 85%)

#table(columns: (auto, auto, auto, auto, 1.2fr),
  [Coin], [Quantum], [Best classical], [Gain], [5% rule],
  [ETH], [0.6480], [0.6482], [+0.03%], [No],
  [BTC], [0.5320], [0.5309], [−0.21%], [No],
  [SOL], [0.4050], [0.4174], [+2.98%], [No],
  [DOGE], [0.7627], [0.7633], [+0.08%], [No],
  [LTC], [0.6132], [0.5966], [−2.79%], [No],
  [BNB], [0.3918], [0.3666], [−6.89%], [No],
  [ADA], [0.7602], [0.7698], [+1.24%], [No],
  [LINK], [0.5771], [0.5916], [+2.45%], [No],
  [DOT], [0.6387], [0.6430], [+0.66%], [No],
  [AVAX], [0.4485], [0.4755], [*+5.68%*], [Alone yes, group no],
)
*Gain* = how much lower the quantum log loss is than the best classical one (positive = quantum better). The groups were (LTC, BNB, ADA) and (LINK, DOT, AVAX); the rule needed *every* coin in a group to clear 5% with intervals excluding zero. AVAX alone cleared 5%, but LINK and DOT did not, and on QLIKE the quantum model was worse on all three. *No group passed.*

#idea(title: "How to say the AVAX result")[
  "One coin in ten looked clearly better, but we had set the rule in advance that a group must pass together, because with ten coins one winner is expected by chance alone."
]

== Putting the numbers together

- Original paper (1.196) to our v1 (0.5695): big, real gain from memory plus probabilistic output.
- v1 to v3 (0.5145): quantum design improvements, each statistically visible.
- Best classical twin (0.4962 / 0.5184): still ahead or equal.
- Across ten coins: quantum ties or loses in most cases; never meets the 5% bar jointly.

#table(columns: (1.6fr, 3fr),
  [Claim], [Supported?],
  [Our model beats the paper's model], [Yes (fresh Bitcoin, every metric)],
  [Memory helps], [Yes, interval excludes zero],
  [Quantum beats classical with same inputs], [No; classical equal or better in nearly all tests],
  [Realism training helps], [No; trade-off],
  [Works on hardware], [Not tested],
)
