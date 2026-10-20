# Step 4 classical-comparison protocol

Declared 20 October 2026 before the measured Step 4 run. Continue the Step 3 validation
study; no new test predictions or final 20-seed run. Preserve all earlier artifacts and
charge their training work when warm-starting from them. The project report stays paused.

## Shared evaluation and information limits

Use the pinned 913-row author data and the existing 529/177/177 split, training-only
scaler/bins/pools. Forecast validation targets with observations available before each
target. No parameter refitting on validation. Compute categorical NLL, normalized RPS,
extreme-bin Brier/calibration and log-RV quantile pinball, 90% coverage/width/interval score.
For old categorical models, quantiles invert their common empirical-bin predictive law.
HAR quantile regression additionally has a native quantile panel; do not conflate its
interpolated native law with the binned sampling approximation. Lower NLL does not
imply uniformly better quantile or calibration scores.

Retain prior quantum D and selected A, softmax D/A, and the original network D/A as
frozen references. Recompute their predictions from saved parameters; validate source
hashes for every previously present Python module and hashes of all imported artifacts.
Add frequency, short AR and full HAR residual-CDF references. HAR uses RV horizons
1/7/30; short learned models use previous-day log RV/return; GARCH uses return history
and a persistent filtered variance. They are different information/capacity panels.

## HAR quantile regression

Fit independent linear pinball regressions on standardized previous log-RV horizons
1/7/30 plus intercept, at quantiles
.01,.025,.05,.1,.2,.3,.4,.5,.6,.7,.8,.9,.95,.975,.99. Use SciPy HiGHS LP and certify primal
feasibility, dual feasibility, complementarity and mean primal/dual gap ≤1e−6. A short
control uses previous-day log RV and return plus intercept. This is 60/45 fitted
coefficients, not 4/3 parameters. No validation-selected quantile grid or penalty.

Sort predicted quantiles per row to repair crossings; save raw crossings too. For bin
probabilities, invert the interpolated sorted quantile curve, coalescing ties to the
rightmost quantile. Extrapolate exponential tails from endpoint spacing, with scale floor
.02 × training target standard deviation. Mix resulting bin probabilities with 1e−6 of
the training frequency law to prevent numeric zero probabilities. These tail/smoothing
choices are explicit observation assumptions; native .05/.5/.95 scores do not need them.
Shared recursive comparisons sample bins and training values with the same rule as D/A.

## Gaussian zero-mean GARCH(1,1)

Fit Gaussian return likelihood on exactly the 529 training target-row returns with
`arch`, rescaled by their training RMS to avoid numerical scale problems. The initial
backcast uses only the first 30 history returns. Use five valid starts
(alpha,beta)=(.05,.9),(.15,.7),(.3,.4),(.05,.5),(.2,.79), omega=1−alpha−beta,
5,000 SLSQP iterations and ftol=1e−10. Choose by training return likelihood; retain
optimizer status and compare the library variance to the independently coded recursion.
Check constrained stationarity with the analytic likelihood gradient and nonnegative
multipliers for active positivity/persistence constraints, tolerance 1e−4.

Return variance is not observed realized variance. Fit an affine observation law
log(RV_t)=a+b log(h_t in original return units)+training empirical residual, using training
rows only. This handles the unknown separate source scaling explicitly but does not
recover physical units. Count 3 GARCH plus 2 calibration coefficients and the residual
sample. Forecast bin probabilities via the same smoothed residual-CDF convention as HAR;
native log-RV quantiles use calibration plus empirical residual quantiles. No return VaR
claim is made for these author units.

For common-law paths, update filtered h using generated returns while sampling categorical
RV values from training pools and r=sqrt(RV)×Gaussian as for D/A. This is a calibrated
GARCH forecast under the common observation law, not native GARCH simulation. Separately
report a native reference: r=return_scale×sqrt(h)×Gaussian, RV from calibration plus a
sampled training residual, then update h. Do not put that native support/law into a
claim of matched generator performance. Seed both at the end of training history.

## Remaining network training and training-effort accounting

Continue **all five** old D network starts with exact analytic backpropagation of the
same clipped training NLL, up to 20,000 joint loss/gradient calls / 10,000 L-BFGS-B
iterations, ftol=1e−14, gtol=1e−7. Retain the best training point and independently check
central-difference gradient infinity norm ≤1e−4 plus optimizer success. Do not select
restarts by validation. If a continuation remains capped/nonstationary, report it.
If the training-selected continuation fails, leave its training conclusion inconclusive.

Reapply A to the new training-selected network D using the unchanged Step 3 lambda grid,
three warm starts, 600-call COBYLA allowance, four 128-day paths/60 burn-in, seed 10000.
Choose training restarts, then lambda using the unchanged validation NLL+.01×moment
distance criterion (eight 256-day paths, stream 20000). Preserve the old network A as a
reference; it is not a valid warm-start ablation of the revised D. Freeze selection before
fresh-stream evaluation. These previously used simulation streams are development data.

Record stored/removed/searched coordinates, classical empirical residual samples, LP
solves/iterations, optimizer/gradient/diagnostic calls and elapsed time. Distinguish new
work from inherited work; joint analytic calls are not equivalent FLOPs to a quantum
numerical-gradient evaluation. Compute local probability-Jacobian singular values and
rank at relative tolerance 1e−6 (absolute floor 1e−10) for fitted learned models; label
this tolerance/fit-dependent sensitivity, not a structural identifiability proof. Quantum
still has a four-depth historical search, so no compute-matched superiority claim.

## Fresh simulation audit and acceptance

After freezing revised network selection, use streams **50000 and 60000**, each
32 paths×512 days after 60 burn-in, for every primary candidate. Save complete generated
arrays, moment vectors, distances of mean moments, individual-path mean/SD and finite
counts. Add the separately labelled native GARCH reference on these streams. Do not
reselect on these outcomes. No new independent data uncertainty is created by more paths.

Verify saved forecasts, quantile/pinball and categorical scores, LP optimality certificates,
GARCH alignment/calibration/likelihood/constraints, warm-start history, selections and
recursive streams. Deliberately corrupt artifacts in tests. Preserve any failed/inconclusive
attempts; numerical repairs require a documented amendment and new output folder. Finish
with measured tables/plots, source/config/provenance, tests and a PR stacked on #5.

Primary implementation references:
[arch model fitting](https://arch.readthedocs.io/en/latest/univariate/generated/generated/arch.univariate.base.ARCHModel.fit.html),
[arch forecasting](https://arch.readthedocs.io/en/latest/univariate/forecasting.html),
[SciPy linprog](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linprog.html).
Installed arch source is also checked because its installed version is newer than the
published documentation landing page.
