# Quantum readout development protocol

## Purpose

The RY expert/HAR model has 11 trainable parameters and only one scalar correction over
HAR logits. Test whether a trainable classical readout of the circuit's four outcome
probabilities makes better use of the quantum representation while keeping the parameter
count close to the existing 27-parameter weekend network.

## Candidate

Use the same two-qubit, depth-1 weekend-aware RY circuit and the same five inputs. Feed its
four outcome probabilities into a trainable affine readout for three class logits; the
fourth logit is the reference. Add those logits to the fixed train-only HAR log
probabilities and normalize. This gives 10 circuit weights plus 15 readout coefficients,
25 trainable parameters total. No new features or data transformations are introduced.

## Development evaluation

- Use ETHUSDT and BTCUSDT training and validation splits already registered in their
  protocols. The validation periods are exploratory model-development data; neither test
  period may be read or used.
- Fit development seeds 900 and 901 with five restarts, the existing optimizer, train rows,
  and optimizer budget.
- Fit one scalar probability temperature on each seed's validation predictions. Report
  raw and calibrated loss by seed and the two-seed mean.
- Compare with the existing 11-parameter quantum HAR hybrid and the fixed weekend softmax,
  network, and softmax-HAR classical panel.
- Advance this candidate to a confirmatory test only if calibrated mean validation log
  loss is at least 5% below the best classical model on both markets. Otherwise record the
  negative result and do not score a new test set for this candidate.

Any confirmatory evaluation requires a new market with a committed protocol, a fixed
candidate and comparator panel, and an untouched test period. The prior ETH and BTC tests
remain closed to all new tuning and selection.

## Amendment 1: regularized readout after ETH development failure

The unregularized readout failed both seed eligibility checks at 50,000 objective calls.
Its trainable readout weights reached magnitudes above 3,000 and its calibrated ETH
validation losses were 0.5236 and 0.5245, versus 0.5171 for the same-seed network. Reject
that unregularized candidate. One amended candidate adds the same L2 penalty used by the
network (`network_ridge = 0.001`) over all circuit and readout parameters. Refit seeds 900
and 901 on ETH training data only, compare against the already fitted same-seed ETH
validation baselines, and advance to BTC validation only if it is eligible and clears the
same 5% margin over the best classical model on ETH. Both prior test periods remain
untouched by this development step.

The regularized readout converged on both ETH seeds (5,610 and 7,293 objective calls),
but calibrated losses were 0.522087 and 0.522088. The same-seed network mean was 0.517134;
the readout is about 0.96% worse. It fails the ETH gate, so BTC validation was not run for
this candidate and no test period was opened.
