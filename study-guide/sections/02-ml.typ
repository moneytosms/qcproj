#import "../template.typ": *

= Part 2. Machine Learning and Fair Testing Basics

You need these ideas because the project is as much about *how to test honestly* as about quantum circuits.

== A model, in one paragraph

A *model* is a function with adjustable numbers (*parameters*, or *weights*) that turns inputs (*features*) into an output (*prediction*). *Training* means adjusting the parameters until predictions match known answers (the *labels* or *targets*). In our project: features = yesterday, week and month volatility plus yesterday's return; target = tomorrow's volatility level.

== Loss functions: measuring how wrong

A *loss* turns "how wrong" into one number that training pushes down.

- *Squared error* (the paper uses mean squared error, MSE): $"MSE" = 1/N sum (hat(v)_t - v_t)^2$. Fine when you predict one number.
- *Log loss* (also called cross-entropy or negative log-likelihood), used when the model outputs *probabilities for categories*:

$ "Log loss" = -1/N sum_(t=1)^(N) ln p_(t,"true") $

where $p_(t,"true")$ is the probability the model gave to the level that actually occurred on day $t$.

#fig("/fig/logloss_curve.png", [The penalty for the probability you gave to the true outcome. Give 90%: penalty 0.105. Give 50%: 0.693. Give 10%: 2.303. Give 1%: 4.605.], width: 70%)

#idea(title: "Weather-forecaster picture")[
  Say it will be calm with 90% and it is calm: tiny penalty. Hedge at 50%: medium penalty. Say 1% and it happens anyway: huge penalty. So log loss rewards forecasts that are *both confident and right*, and punishes confident mistakes hard. It is a "strictly proper" scoring rule: your best strategy is to report your honest probabilities.
]

*Worked example (verified).* The model forecasts (calm 60%, normal 30%, wild 8%, extreme 2%). If the day turns out calm, the penalty is $-ln(0.6) = 0.511$. If normal: $-ln(0.3) = 1.204$. If extreme: $-ln(0.02) = 3.912$. Averaging penalties over all test days gives the log loss.

*A useful anchor.* "Always predict the training-set mix" (30/40/25/5%) gives a log loss of about 1.22 on data with that same mix (the entropy $-sum p ln p$ of (0.30, 0.40, 0.25, 0.05) is 1.224). A score near 0.5 therefore means the model concentrates real probability on the right level most of the time. On our fresh test set the mix was unusual (75% calm) so the numbers are not comparable to 1.22; always compare models on the *same* test set.

*Other scores we report.* *Brier score* (mean squared error of the probabilities), *RPS* (ranked probability score: aware that "wild" is closer to "extreme" than "calm" is), *QLIKE* (volatility-specific error), and *calibration* (when the model says 30%, does it happen about 30% of the time?).

== Overfitting and the three-way split

A model with many knobs can memorise the training data, including its noise, and then fail on new days. This is *overfitting*. Defence: never judge on data you trained on.

#fig("/fig/split.png", [Time-ordered split used for the fresh Bitcoin study. The test period is opened exactly once.], width: 95%)

- *Training set* (oldest): fit the parameters.
- *Validation set* (middle): choose settings (how many layers, how strong a penalty) by looking at this score. You are allowed to look many times.
- *Test set* (newest): the final exam. Look *once*. If you tune on it you cheat yourself.
- *Time-ordered*, never shuffled. Shuffling would let a model learn from tomorrow to predict yesterday, which is impossible in real life ("look-ahead leakage").
- All scaling statistics and the percentile cut points for the four levels come from the *training period only*.

== Random seeds and why we ran everything 20 times

Training starts from random numbers and the final result depends on them. A *seed* fixes the random starting point. One lucky run proves nothing, so each model is trained from 20 different seeds and we report the average. Note: 20 seeds measure *training luck*, not "20 independent markets". We state this as a limitation.

== Optimisers: how parameters get tuned

Training = minimising the loss over the parameters. The project uses SciPy's:
- *L-BFGS-B*: uses gradients (slopes) to walk downhill quickly. Used when gradients are available (JAX computes them exactly).
- *COBYLA*: gradient-free; tries values and shrinks a trust region. Used in the paper rebuild, where the original paper also optimised without gradients.
- *Restarts*: because the loss landscape of quantum circuits has many valleys, we start from several random points and keep the best (by *training* loss, never test).
- *Regularisation (ridge)*: adds a penalty like $0.001 dot ||theta||^2$ to the loss to discourage extreme parameter values (reduces overfitting).

== The classical competitors ("twins")

A claim of "quantum is good" is meaningless unless a classical model with the *same inputs and output* is beaten. Ours:

#table(columns: (1.2fr, 3fr),
  [Model], [What it is],
  [Softmax regression], [The simplest probability model: each of the 4 levels gets a score that is a weighted sum of the inputs; softmax turns scores into probabilities that add to 100%. $p_k = e^(s_k) / sum_j e^(s_j)$. v2 version has 28 parameters (4 levels × (6 inputs + 1 bias)).],
  [Small neural network], [Same inputs, one hidden layer of "neurons" with a nonlinearity; slightly more flexible. 26 parameters in the v2 matching version.],
  [HAR quantile / HAR residual], [Classical HAR forecast of log RV, then converted to level probabilities either by quantile regression or by assuming a residual distribution.],
  [GARCH], [Textbook volatility model (Part 1), fitted with the `arch` library.],
  [Climatology ("usual mix")], [Always predict the training-set share of each level. The floor any model must beat.],
)

#idea(title: "Why 'same inputs' matters so much")[
  If the quantum model saw the week and month but the classical one saw only yesterday, any win would come from information, not from quantum physics. Matching inputs, outputs, training rows, seeds and effort isolates the one thing under test: *is a quantum circuit a better function approximator here?*
]

== Statistical confidence: the bootstrap

Suppose quantum scores 0.50 and classical 0.49 on 657 test days. Is that a real gap or luck? *Bootstrap*: re-draw the test days many times (with replacement) from the data, recompute the gap each time, and look at the spread of the results. Because volatility is autocorrelated we resample *blocks* of 7 or 30 consecutive days (the *block bootstrap*) instead of single days.
- The 95% (or 97.5%) *interval* is the range containing most resampled gaps.
- If the interval excludes zero, the difference is convincing. If it includes zero, it could be luck.
- Slide 33's "thousands of reshuffled test periods" is exactly this.

== Pre-registration and sealing

To avoid fooling ourselves (choosing the test that flatters us), for the multi-coin studies we:
+ wrote the protocol (models, data, metrics, pass/fail rule) in a document and committed it to git *before* training or scoring;
+ trained on training rows only, then *sealed* the trained parameters and data with SHA-256 fingerprints (hashes) so they could not be altered afterwards;
+ opened the test labels once.

*The 5% rule:* quantum must have at least 5% lower log loss than both classical controls on every coin in a group, with confidence intervals below zero.

#warn(title: "Honesty points you must volunteer")[
  The v2/v3 designs were partly informed by seeing the 2025-26 test period (e.g. the weekend effect). Their test scores are *post-hoc* and only indicative. The paper-vs-ours comparison was planned after the main test results were seen. We say so openly in the report.
]
