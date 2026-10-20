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

`ethusdt_daily.csv` is derived from Binance public ETHUSDT spot 5-minute klines, with
monthly ZIPs through 2026-09 and daily ZIPs for 2026-10-01 through 2026-10-19. Every ZIP
was checked against its `.CHECKSUM` sidecar. `ethusdt_daily.json` records source and output
hashes, gaps, and incomplete UTC days. Binance spot archive timestamps use milliseconds
before 2025-01-01 and microseconds from that date onward. The source has 33 gaps affecting
34 days and 1,703 missing 5-minute intervals; no missing bars were fabricated. RV includes
observed close-to-close returns across gaps once. The 2025-01-01 to 2026-10-19 test dates
are complete. Rebuild with:

```bash
uv run python scripts/build_binance_daily.py
```

The builder also accepts `--symbol BTCUSDT`; by default this writes
`data/btcusdt_daily.csv` and uses a symbol-specific ignored cache. The same checksum,
timestamp, gap, and daily RV rules apply.

For later-listed symbols, set `--archive-start YYYY-MM-01` to the first available monthly
archive and `--last-date YYYY-MM-DD` for the final daily archive date.

`btcusdt_daily.csv` was rebuilt from checksum-verified Binance BTCUSDT spot 5-minute
klines for 2017-08-17 to 2026-10-19 (3,351 UTC days). Its metadata records all archive
hashes, 33 timestamp gaps, 34 incomplete historical days, and output hash. The test dates
2025-01-01 to 2026-10-19 have full daily 5-minute coverage.

The fixed replication also includes `solusdt_daily.csv` (2020-08-11 onward, 2,261 days)
and `dogeusdt_daily.csv` (2019-07-05 onward, 2,664 days), both through 2026-10-19. Their
JSON metadata records each archive hash and every observed gap. Both have complete
5-minute coverage on test dates 2025-01-01 to 2026-10-19.
