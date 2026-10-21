# FAQ and limits

## Does the quantum model beat classical models?

No. The two-qubit model clearly beats the original one-qubit paper model on fresh Bitcoin data (log loss 0.5695 against 1.196), but a classical softmax model with the same inputs scores 0.5184. Across ten coins no group passed the 5% rule fixed in advance.

## Was a real quantum computer used?

No. Every circuit runs on an exact NumPy statevector simulator without noise. A script for IBM hardware exists and was not run.

## Why does `qcvol run` fail on my CSV?

The loader rejects non-consecutive dates, non-finite values and non-positive realized variance. Fix the file against the schema in [Configuration](configuration).

## Can I overwrite a results folder?

No. Choose a new output directory each run; saved manifests and hashes depend on it.

## Which numbers are final?

The frozen 20-seed study and the fresh-data comparison were evaluated once on a sealed test split. The v2 and v3 circuits and later panels reuse the same test period, so treat them as indicative. The [paper](https://github.com/moneytosms/qcproj/tree/main/paper) lists each limitation.

## Contributing

Work on a topic branch, run the three checks in [Usage](usage), and open a pull request to `moneytosms/qcproj`. See [AGENTS.md](https://github.com/moneytosms/qcproj/blob/main/AGENTS.md).
