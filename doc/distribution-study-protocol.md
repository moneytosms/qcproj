# Sequential D → A development protocol

Frozen before measured execution, 20 October 2026. This extends the B decision in
[nested-memory-followup.md](nested-memory-followup.md). It is a validation study,
not the final 20-seed test comparison. B did not show a longer-memory benefit.
Nidhi's original paper implementation remains credited in `qvol/`.

## Information, targets and controls

Use the same pinned author data and 529/177/177 chronological target split. Train-only
standardization and four bins stay unchanged. Every learned distribution receives only
standardized previous-day log RV and return, including recursive simulation. The Born
circuit repeats yesterday's standardized log RV in its first three gate slots; the last
slot receives yesterday's return. This changes the information policy, not the gate order.
Remove the two terminal RZ angles: they cannot affect measurement probabilities through
the final CNOT permutation. Depth L has 8L stored original angles but only 8L−2 searched
coordinates; this is an upper bound on effective dimension, not a proof of identifiability.

Compare reference-logit softmax (9 identifiable coordinates), a short-input tanh network
(2→3→3 logits, fixed fourth logit, three log-RV skips; 24 coordinates), frequency, and
short AR plus empirical training residual CDF. Report full-input HAR residual CDF as a
separate information-rich reference. No point MSE is compared numerically with NLL.
GARCH and dedicated HAR quantile regression remain Step 4.

## D: fit probabilities first

Depths 1,2,3,4, five initialization seeds 0–4 for every depth and learned control. Fit
training categorical NLL with numerical-central-difference L-BFGS-B: 50,000 objective
calls requested, 2,000 iteration ceiling, gtol 1e−6, ftol 1e−13, up to 40 line-search
steps. SciPy may exceed `maxfun` to finish a numerical gradient; save actual calls.
Independent central differences with step 1e−5 must have infinity norm ≤1e−4 and the
optimizer must report success. Save every start, not only winners.

Choose the restart with lowest training NLL for each depth, then the depth with lowest
validation NLL. Apply the same training-only restart rule to softmax/network. All depth
winners must pass the training check for an adequate D comparison; otherwise label it
inconclusive and preserve the fits. Multiple starts describe optimization sensitivity,
not five independent data replications. There are 30 forecast fits.

## A: change the loss separately

Freeze each family's D-selected depth. At lambda .01,.05,.2, use three warm starts:
exact forecast winner, and independent seed-1/2 Gaussian jitters with standard deviation
.03 around it. Training loss is NLL plus lambda times squared moment distance, scaled
by training-window standard deviations with floor .02. Moments: log-RV ACF lags 1/7/30
and standard deviation of log-RV changes. Match the mean generated moment vector to
training moments, using four 128-day paths, 60 burn-in days, fixed common stream 10000.

COBYLA gets 600 evaluations plus an explicit initial check, radius .3, final radius
.002. Save status, all losses, time and parameters; a stopping-radius success on a
discrete loss does not establish smooth stationarity or global optimality. Choose the
best restart on penalized **training** loss at each lambda. This is 27 A fits, each
receiving the same allowance. A is an exploratory finite-budget search; expose budget
exhaustion rather than claim it disappeared. Keep the exact forecast fit at lambda zero
as a fallback. We select depth before A, not a joint depth/lambda Cartesian search.

Select lambda on validation NLL + .01 × distance of mean generated moments to validation
moments, with training-fitted scales. Selection uses eight 256-day paths and stream
20000, common across candidates. This fixed selection weight is distinct from the
training lambda. Save NLL, normalized RPS, extreme-bin Brier and calibration. Report
forecast deterioration alongside any realism gain; the combined score is a declared
preference, not proof of overall superiority.

## Fresh simulation audit and limits

After freezing selections, audit all training-selected lambda winners and controls with
two untouched common streams, 30000 and 40000, each 32 paths ×512 days plus 60 burn-in.
Save distances of mean moments **and** average individual-path distances and spread.
This checks Monte Carlo sensitivity on fresh draws; it is not a new held-out dataset
and cannot remove repeated validation selection bias. Do not reselect on these streams.
No test probabilities, scores or test-referenced generated statistics are calculated.
Previously published smoke test results exist, so avoid claiming a pristine unseen test.

Author inputs were independently standardized upstream, possibly using their full sample;
physical return units and independently rebuilt intraday RV remain unavailable. Generated
values come from empirical training-bin pools with Gaussian return innovations, so this
study cannot establish realistic extreme tails or the paper's full MFDFA behavior. No
quantum advantage is assumed. Record actual total training work and parameter counts;
the different architectures and four-depth quantum search are not compute-matched.

Configuration: `configs/distribution-study.json`. Preserve failed runs in new directories.
Package-source hashes freeze runnable code; raw artifacts remain ignored. Independent
verification must reconstruct quantum probabilities with literal full matrices, redo
selection, metrics and seeded rollouts, and fail on tampered artifacts.
