# Data

`bitstamp_daily.csv` is derived from Bitstamp BTC/USD 1-minute candles published at
https://github.com/ff137/bitstamp-btcusd-minute-data (commit
`c711b69cdcffd1356247126b1e0f53455efb70ba`). The bulk history is licensed CC BY-SA 4.0
(attribution: Zielak (mczielinski), Bitcoin Historical Data, Kaggle) and daily updates CC BY
4.0. This derived daily file is shared under CC BY-SA 4.0.

Columns: `date` (UTC day), `return` (log close-to-close), `rv` (sum of squared 5-minute log
returns), `intervals` (5-minute returns in the day), `zero_volume_fraction`.

Rebuild it with:

```bash
bash scripts/fetch_bitstamp.sh            # about 250 MB into .cache/bitstamp-minute
uv run python scripts/build_bitstamp_daily.py
```

`bitstamp_daily.json` records the input and output SHA-256 hashes.
