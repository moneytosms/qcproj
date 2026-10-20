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
