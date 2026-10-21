# Quickstart

You will install the project, check the paper rebuild against its closed form, and run a smoke forecast on synthetic data. No network or API key is needed after `uv sync`.

Python 3.11 or newer; the locked setup uses 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/moneytosms/qcproj
cd qcproj
uv sync --locked --extra dev --extra plots --python 3.12
uv run qcvol verify-paper
uv run qcvol demo --config configs/smoke.json --output results/demo-01
```

`verify-paper` compares the simulator with the paper's closed-form one-qubit formula:

```text
{
  "samples": 256,
  "phi_max_error": 0.0,
  "twin_max_error": 5.551115123125783e-16
}
```

`demo` ends with `Saved results to results/demo-01`. Always choose a new output directory.

The smoke configuration uses one seed and a small budget. It proves the workflow runs; it does not measure model quality. See the [FAQ](faq).
