# Next approaches: information, targets and credible evaluation

Research note, 2026-10-20. This is a proposal grounded in primary papers and a
bounded source audit; no new empirical model fits were run for this note.

The supplied seven-page *Schrödinger's Cat: Quantum Volatility Range Forecaster*
proposal establishes memory, four-category probabilities and realism training as
the project's three changes. It describes the original 913-day dataset and a
planned gradient-free optimizer. Later repository studies use larger rebuilt
datasets and exact-gradient fitting for v2/v3. The proposal is the starting
specification, rather than a record of every completed experiment. Its four
category probabilities also do not by themselves define a numerical prediction
interval with measured coverage.

## What appears genuinely new here

The source audit covered `doc/`, `src/qcvol*`, and tests at main `fc8d6c8`.
Existing work already includes daily/7/30 HAR inputs, calendar features, 1–4
circuit layers, Born and learned readouts, quantum/HAR hybrids, recency weights,
temperature calibration, classical quantile models, RPS evaluation and multiple
assets. Gray-code readout has also been tried. These are not new proposals.

The searches found no implemented signed realized semivariance, jump/continuous
decomposition, HARQ/quarticity feature, online adaptive conformal wrapper, or
Fourier-matched/no-entanglement experiment. The Binance builder currently reduces
five-minute returns to daily RV, daily return and audit fields
(`src/qcvol_next/binance_data.py`). That leaves potentially useful intraday
structure unused. “Untried” means absent in this inspected implementation, not a
claim of novelty in the literature or unpublished branches.

The priority below is expected practical value, with quantum attribution treated
as a separate scientific question. A better forecast may improve both quantum
and classical models.

## 1. Preserve the direction and composition of intraday variation

**Published finding.** Patton and Sheppard find that signed high-frequency
variation improves equity volatility forecasts; negative and positive variation
have different predictive effects. Corsi, Pirino and Renò show that jump effects
depend on separating continuous variation using a suitable estimator; naive
bipower estimates can suffer finite-sample bias. Neither finding establishes an
effect for these crypto assets. Sources: [Patton–Sheppard (2015)](https://public.econ.duke.edu/~ap172/Patton_Sheppard_REStat_2015.pdf),
[Corsi–Pirino–Renò (2010)](https://openaccess.city.ac.uk/id/eprint/4435/).

**Our hypothesis.** Two days can have identical total RV and very different
intraday downside variation or jump concentration. Daily return cannot recover
this information. The circuit currently receives a compressed description of
the day; increasing depth cannot reconstruct discarded observations.

**Small first experiment.** From complete five-minute close-return sequences,
compute `RS− = Σ r_i² 1(r_i < 0)` and `RS+ = Σ r_i² 1(r_i >= 0)`; verify their
sum equals existing RV. Add only downside share `RS−/RV` to the current calendar
HAR feature block. Compare base versus enriched inputs for softmax, a regularized
small network, HAR distribution control and the same quantum model. Give all
models identical information. Only if this helps on development folds, add a
separate continuous/jump experiment using an explicitly specified threshold
bipower estimator and a jump share. Keep feature ablations separate so a gain is
interpretable.

**Score and risk.** Use existing NLL and RPS, continuous QLIKE, and stratified
loss on high-downside/jump days defined from training thresholds. Discontinuities
from missing bars must not masquerade as jumps. Overnight boundary handling,
exchange outages, irregular intervals and thin trading need auditing. A higher
feature count can overfit the limited daily sample; one extra scalar first is a
stronger experiment than a large feature menu.

## 2. Tell the model how uncertain the RV estimate is: HARQ

**Published finding.** Bollerslev, Patton and Quaedvlieg use realized quarticity
to adjust volatility persistence for time-varying measurement error in RV.
Their HARQ models improve forecasts in their simulations and equity study;
the mechanism differs from simply adding a jump regressor. Under equally spaced
increments, their basic realized quarticity is `RQ = (M/3) Σ r_i⁴`. Source:
[Exploiting the Errors (2016), authors' working paper](https://pure.au.dk/ws/portalfiles/portal/85674324/rp15_14.pdf).

**Our hypothesis.** An RV value based on one huge increment should not receive
the same persistence weight as the same RV spread across the day. RQ supplies a
measurement-quality signal absent from current HAR inputs. It may be especially
useful when the distribution shifts between training and evaluation.

**Small first experiment.** Start with a canonical classical HARQ control in
its native scale and documented parameterization. Separately add one
training-standardized log-quarticity feature and a predeclared daily-log-RV
interaction to the existing probabilistic models; call this “quarticity-enriched”
rather than claiming it exactly reproduces HARQ. Compare base, semivariance-only,
quarticity-only, then the combined feature block. Reuse the same data dates,
optimizer budgets and seeds. Keep weekly/monthly quarticity adjustments out of
the first pass.

**Score and risk.** Evaluate categorical NLL/RPS and positive RV forecasts with
QLIKE. Fourth powers amplify bad ticks and jumps, and the theoretical measurement
error interpretation requires assumptions; it is not a universal noise meter.
Report sensitivity to 5-, 10- and 15-minute sampling as a fixed audit, with the
sampling frequency chosen using development data.

## 3. Forecast severity inside the bins, and use the categories' order

**Published foundation.** Ordered-response models exploit ordered categories
without assuming equal distances between them. Proper scoring rules support
training and assessing full distributions: RPS compares cumulative category
probabilities, while CRPS assesses a continuous CDF. Sources:
[McCullagh (1980)](https://www.stat.uchicago.edu/~pmcc/pubs/paper2.pdf),
[Gneiting–Raftery (2007)](https://sites.stat.washington.edu/people/raftery/Research/PDF/Gneiting2007jasa.pdf).

**Our hypothesis.** Correct bin probabilities leave the severity within a bin
unidentified. The current QLIKE forecast uses probabilities times fixed training
within-bin RV means. Thus lower category NLL need not imply better RV forecasts
or useful interval widths. This is a target limitation, not necessarily failed
quantum learning.

**Small first experiment.** First change only the training objective: current
Born/softmax/network heads with NLL versus normalized RPS training. RPS already
exists as a metric; its use as the fitting objective is the proposed change.
Do not select the winner after viewing test scores. Then test a small conditional
continuous distribution for log-RV, using shared HAR location plus a positive
input-dependent scale, with matched classical and quantum corrections. A Gaussian
log-RV head is a transparent initial control; verify its implied RV mean and tail
behavior. Compare against the existing direct HAR quantile regression, so
“continuous prediction” is not presented as entirely absent from the project.

**Score and risk.** Predeclare CRPS or mean quantile pinball as the continuous
primary score and report interval score/coverage, QLIKE and bin probabilities
obtained from the same distribution. NLL and RPS optimize different properties;
switching objectives does not promise better NLL. Parametric tail assumptions can
fail. Patton's proxy-robust loss results support care with noisy RV comparisons,
under their conditions, rather than treating any finite-sample QLIKE result as
conclusive ([Patton, 2011](https://public.econ.duke.edu/~ap172/Patton_vol_proxies_JoE_2011.pdf)).

## 4. Test a forecasting procedure that adapts through time

**Published finding.** Gibbs and Candès develop online conformal methods for
changing distributions, including an adaptive update and a later method that
adapts to shift scale/type; their applications include stock-volatility
prediction. Their guarantees concern coverage/regret properties under stated
conditions, not superiority of the underlying model's NLL or conditional
coverage for every market regime. Source:
[Conformal Inference for Online Prediction with Arbitrary Distribution Shifts](https://arxiv.org/abs/2208.08401).

**Our hypothesis.** Recency-weighted fitting of one static training sample and
post-hoc temperature calibration do not replace an online policy that learns
from newly realized outcomes. Calibration drift could be improved without a
larger circuit.

**Small first experiment.** Use historical development folds to compare fixed
parameters, monthly expanding-window refits and one fixed-length rolling-window
refit policy. Every prediction must be saved before observing its target. Hold
the report's class thresholds fixed within each evaluation fold; changing bins
changes the event being scored. Add an adaptive conformal wrapper to the chosen
continuous/quantile model with its update rate selected on past development
folds only. Give the same wrapper and retraining schedule to classical controls.

**Score and risk.** Track NLL/RPS for the underlying forecast and 90% interval
coverage, width and interval score for the wrapper. Plot rolling coverage and
loss by predeclared regimes. A wide interval can achieve coverage while being
unhelpful. Historical rolling tests are robustness evidence: they do not become
fresh confirmation when the global method was chosen after seeing those dates.

## 5. Make the quantum comparison identify a useful inductive bias

**Published foundation.** Data encoding determines accessible Fourier
frequencies, while circuit design constrains their coefficients. Quantum-kernel
geometry can help diagnose whether a chosen representation differs usefully
from classical alternatives; a large geometric difference alone does not prove
a forecasting advantage. Sources: [Schuld–Sweke–Meyer (2021)](https://arxiv.org/abs/2008.08605),
[Huang et al. (2021)](https://www.nature.com/articles/s41467-021-22539-9).
The [Bowles–Ahmed–Schuld benchmark (2024)](https://arxiv.org/abs/2403.07059)
also finds that removing entanglement can match or improve classification
performance on its small benchmark tasks. This motivates an ablation here;
it does not predict the result for volatility.

**Small first experiment.** Compare current entangled circuit, the identical
encoding with CNOTs removed, and a regularized classical trigonometric feature
model reflecting the encoding's frequency/interactions. With learned angle
weights, use both fixed-frequency controls and learned-frequency controls;
otherwise “matched spectrum” overstates the match. Audit probability Jacobian
rank and parameter sensitivity before increasing depth. Freeze all training
choices using development data.

Count effective observable parameters, gradient evaluations, restart count and
wall time; compare best-restart models and probability-averaged ensembles for
every family. Current v3 versus softmax is a same-input comparison, not an equal
capacity or ensemble-budget experiment. Removing unobservable terminal gates
can improve optimization without increasing expressive power. A no-CNOT model
may impose a restrictive joint-probability factorization, so report both the
native Born head and a matched learned readout.

This audit may explain a quantum result or rule out an expensive search. With
two classically simulated qubits, it cannot establish computational speedup.

### Verified observation in the current Born circuit

In `src/qcvol_v2/models.py` and `src/qcvol_v3/models.py`, each qubit's last
trainable block is `RZ(c*x+d) RY(a*x+b)`, followed by CNOT and computational-basis
measurement. The terminal RZ gates change phases only. CNOT then permutes basis
amplitudes; it cannot make these phases affect their squared magnitudes. All
`2 * (inputs + 1)` terminal RZ coefficients are therefore unobservable by the
Born probability output. For six inputs this is **14 of 84 nominal depth-three
parameters**. At most 70 remaining coordinates can affect predictions; this does
not establish that all 70 are independently identifiable. The Pauli-expectation
readout can observe phases and needs its own audit.

A read-only diagnostic used the independent 4x4 reference simulator, RNG seed
20261020, 128 random six-input rows and depths 1, 2, 3 and 4. Perturbing every
terminal RZ coefficient by independent `N(0, 4^2)` noise changed probabilities by
at most **8.88e-16** across these cases. The diagnostic did not fit models or
read held-out scores. The algebra, rather than this finite random sample,
establishes invariance. Removing these coefficients preserves the attainable
Born probabilities and removes unnecessary penalty/optimization coordinates;
it is not evidence of improved forecast accuracy. Future implementations should
add an invariance regression check and replay saved parameters before refitting.

V3's `fit_restarts` currently retains parameters and objectives but discards
optimizer termination, iterations and gradient diagnostics. Its runner averages
ten quantum restarts. The multi-market configuration in open PR #14 uses
five-restart classical controls that retain a best fit. The AVAX result is
therefore a same-input comparison with a budget/aggregation difference; an equal
ten-member classical probability ensemble is an unperformed control. Fixing
diagnostic recording and specifying both equal-restart and measured-cost
comparisons should precede another scientific run. Do not rewrite sealed runs.

## Recommended bounded experiment

Start with **one new input: lagged downside semivariance share**. First verify
the signed components sum to the existing RV using identical UTC boundaries and
intervals. Only complete five-minute intervals should enter this new experiment;
an outage-spanning return must not silently be treated as a regular increment.
Prespecify exclusion rules and apply them to every family, including the
30-day feature histories. This may require an explicitly separate clean dataset
from the historical builder that retains gap-spanning returns.

Use the current six-input block versus that same block plus downside share,
holding the output, class thresholds, calibration and model depth fixed. Include
softmax, a regularized network, HAR distribution control and the quantum model;
each family gets the identical feature ablation and comparable tuning and
aggregation budgets. Adding an affine circuit input changes parameter counts,
so report them and include a capacity control before attributing all benefit to
the new information. Fit scalers on past training rows only.

Use three expanding chronological development folds, with each later year
predicted from earlier data. Historical folds and all previously inspected
2025-2026 assets remain development evidence. Define the folds, eligible dates,
small ridge grid, refit schedule and common outcome rule in a separate committed
protocol before any fitting; this note is a recommendation, not a preregistration
or a scientific result. Select using pooled validation log loss. Report RPS,
calibration and high-volatility event counts as well, with time-block uncertainty
and synchronous dates across assets. Forecasting improvements must not
be described as improvements in recursive simulation without running that test.

Advance only if the feature helps more than one development period without
unacceptable calibration or tail degradation. Then freeze one candidate and its
controls for future data or an untouched, prespecified asset panel. Run quarticity
as a separate next ablation; do not immediately combine every proposed feature,
loss and adaptation rule into one search. A family-wide gain supports better
information; an additional robust quantum-versus-control gain is a different
claim and requires its own evidence.

## Evaluation rule before another search

Register the candidate list, primary metric, tuning budget, stopping rule and
practical improvement threshold before running. Treat already inspected assets
and dates as development. Reserve future dates or genuinely unexamined data for
confirmation; adding an asset with highly correlated market shocks does not
create independent evidence automatically.

Store paired daily losses and use time-block uncertainty, with dates resampled
synchronously across assets. Seeds quantify optimization variation; twenty
seeds do not multiply the number of observed market days by twenty. Pairwise
forecast tests should allow serially correlated loss differences
([Diebold–Mariano, 1995](https://doi.org/10.1080/07350015.1995.10524599)).
Correct for the declared model/asset comparisons or use a single predeclared
pooled endpoint. No correction can erase the earlier exploratory selection.
Report failed runs and optimizer diagnostics, all asset outcomes, tail-event
counts, and uncertainty beside any percentage improvement. The best immediate
research sequence is source/optimizer audit, one-scalar semivariance experiment,
quarticity experiment, then a frozen target/adaptation experiment; avoid testing
all combinations at once.
