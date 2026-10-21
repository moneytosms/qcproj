# Configuration

This page lists the run configs and the input data format.

| File | Purpose |
|---|---|
| `configs/smoke.json` | One seed, small budget. Verifies the workflow only. |
| `configs/study.json` | Original 20-seed sweep on HAR inputs. Historical. |
| `configs/final-study.json` | Frozen 20-seed protocol with short inputs. |
| `configs/distribution-study.json` | Step 3 D to A development comparison. |
| `configs/memory-investigation.json` | Grid for the memory-fit investigation. |

## CSV schema for your own data

Columns `date,return,rv`.

- Consecutive ascending daily ISO dates.
- Finite returns, strictly positive realized variance, in compatible units.
- At least 190 rows for the default split fractions: three chronological splits plus the 30-day warm-up.

## Environment

Set `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1` for the long studies so runs are reproducible and do not oversubscribe cores. No hardware keys or service credentials are used.
