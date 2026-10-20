# Decisions for the original-paper reproduction

These decisions accompany [the measured report](paper-reproduction.md). They explain
why the audited path is separate from both the legacy quick script and held-out training.

1. **Extend the existing `qvol/` package.** The team already has a literal paper circuit
   and historical reproduction outputs. Add an audited entry point and new modules;
   preserve those historical scripts/results so earlier measurements remain attributable.
   The PR is based on the original repo's main branch and does not require the separate
   held-out-pipeline PR.

2. **Keep full-sample reproduction distinct from forecasting.** Train on 912 next-day
   pairs from 913 published observations, without validation/test splitting. This answers
   the paper's descriptive generative question. It supplies no out-of-sample forecast claim.

3. **Optimize an exactly equivalent expression.** Precompute the encoded Bloch features
   and evaluate the same P0 function efficiently during COBYLA. Verify the result against
   the independent literal matrix circuit on every observed row. Keep all three stored
   angles for fidelity while reporting phi's inactivity; equivalent periodic angles need
   not equal the earlier fit's parameter text.

4. **Save every optimization attempt.** Record initial parameters, every objective value,
   status, message and evaluation count. Require the selected fit to converge. A loss
   plateau is measured evidence; a small fixed-budget smoke run cannot substitute for it.

5. **Correct MFDFA coverage.** Use the paper's stated lower fit cutoff, cubic two-ended
   detrending, full overlapping window grid, 20 shuffles, fine q spectra, and 200 Gaussian
   controls. QR projection onto the polynomial space gives batched speed without changing
   the trend subspace. Direct polynomial tests and the independent MFDFA package check
   numerical equivalence, including a separate q=0 test.

6. **Declare missing settings rather than infer convenient ones.** Choose an explicit
   geometric grid and record it; do not tune it to the published table. Keep preselected
   representative window 0. Record initial history and absence of burn-in. Sensitivity
   analyses are separately labeled; they do not overwrite the primary result.

7. **Keep time alignment exact.** Differencing 913 observations produces 912 increments.
   Analyze the complete shorter empirical record; generated records still support the
   full 913-day rolling window. Do not create an artificial endpoint or drop an increment
   from every generated window, as the earlier quick diagnostic did.

8. **Make domain handling observable.** Gaussian innovations remain unchanged in saved
   returns. Guard only the circuit input and positive-variance numerical domain; count
   events. A strict policy raises on return-domain escape. The measured full runs used
   neither guard, so these assumptions did not alter their paths.

9. **Expose the zero-return ambiguity.** One empirical return equals zero. Declare a
   log-absolute-return floor, report its sensitivity, and show defined-adjacent-pair
   kurtosis separately. Never replace the primary data with whichever convention
   happens to match a target statistic. This does not affect return or log-RV analyses.

10. **Report multiple sources on the same implementation.** Analyze real data, the
    published generated series and our three generated seeds with the same estimator.
    The published generated series is an independent reference, not a target used to fit
    the circuit or choose a return scaling factor.

11. **Verify raw arrays, not only green metadata.** The verifier checks source hashes,
    target alignment, innovation draws, every generation recurrence step, all original
    rolling estimates, and spectral identities. Its success establishes internal artifact
    integrity, not equality to all paper claims. Overlapping windows and scale-regression
    standard errors are not independent-process uncertainty estimates.

12. **Keep evidence reproducible and reviewable.** Pin direct dependency versions, log
    installed versions, retain source/data hashes, refuse output reuse, and mark a run
    complete only after figure export. Generated artifacts stay in ignored local folders;
    commit code, configuration, tests and a measured written report through a PR.

Primary references:

- [Original paper, equations and experimental protocol](https://arxiv.org/html/2609.04569v1)
- [Published source data](https://github.com/takaishi-physics/QCL-volatility)
- [Independent MFDFA implementation](https://mfdfa.readthedocs.io/en/latest/functions/index.html)
- [SciPy COBYLA options](https://docs.scipy.org/doc/scipy/reference/optimize.minimize-cobyla.html)
