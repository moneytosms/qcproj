# Usage

Each task below is one command. Studies read author or exchange data, write a new run folder under `results/` (ignored by git), and have a matching `verify_*` script that audits the saved output.

## Run the tests and checks

```bash
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

## Fetch the paper author's Bitcoin data

```bash
uv run python scripts/fetch_author_data.py
uv run qcvol run --author-data data/raw/author --config configs/smoke.json --output results/btc-01
uv run python scripts/plot_results.py results/btc-01
```

## Forecast your own daily data

```bash
uv run qcvol run --csv data/my_daily.csv --config configs/smoke.json --output results/custom-01
```

The CSV format is in [Configuration](configuration).

## Run the frozen 20-seed study

```bash
uv sync --all-extras
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 uv run python scripts/run_final_study.py --help
```

Read the [frozen protocol](https://github.com/moneytosms/qcproj/blob/main/doc/final-study-protocol.md) first. Training is sealed before any test score is computed.

## Build the paper

```bash
typst compile paper/main.typ paper/quantum-volatility-paper.pdf
```
