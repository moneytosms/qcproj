"""Build daily ETHUSDT realized variance from checksum-verified Binance 5m klines."""

import argparse
import csv
import hashlib
import io
import itertools
import json
import urllib.request
import zipfile
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np

BASE = "https://data.binance.vision/data/spot"
SYMBOL, INTERVAL = "ETHUSDT", "5m"
FIRST = date(2017, 8, 17)
LAST = date(2026, 10, 19)
FIVE_MIN_MS, DAY_MS = 300_000, 86_400_000
COLUMNS = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_asset_volume",
    "number_of_trades",
    "taker_buy_base_asset_volume",
    "taker_buy_quote_asset_volume",
    "ignore",
]


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def archive_url(day, monthly):
    kind = "monthly" if monthly else "daily"
    stamp = day.strftime("%Y-%m" if monthly else "%Y-%m-%d")
    name = f"{SYMBOL}-{INTERVAL}-{stamp}.zip"
    return f"{BASE}/{kind}/klines/{SYMBOL}/{INTERVAL}/{name}"


def timestamp_ms(value):
    """Normalize a Binance Spot archive timestamp to milliseconds."""
    value = int(value)
    return value // 1000 if value >= 10**15 else value


def download_checked(url, cache):
    cache.mkdir(parents=True, exist_ok=True)
    name = url.rsplit("/", 1)[-1]
    archive, checksum = cache / name, cache / f"{name}.CHECKSUM"
    for path, source in ((archive, url), (checksum, f"{url}.CHECKSUM")):
        if not path.is_file():
            with urllib.request.urlopen(source, timeout=60) as response, path.open("wb") as out:
                out.write(response.read())
    fields = checksum.read_text().strip().split()
    if len(fields) != 2 or fields[1] != name or sha256(archive) != fields[0]:
        archive.unlink(missing_ok=True)
        checksum.unlink(missing_ok=True)
        raise ValueError(f"Binance checksum mismatch: {name}")
    return archive


def source_archives(cache):
    archives = []
    month = date(FIRST.year, FIRST.month, 1)
    last_month = date(LAST.year, LAST.month, 1)
    while month <= last_month:
        if month.year == LAST.year and month.month == LAST.month:
            break
        archives.append(download_checked(archive_url(month, True), cache))
        month = date(month.year + (month.month == 12), month.month % 12 + 1, 1)
    day = max(FIRST, last_month)
    while day <= LAST:
        archives.append(download_checked(archive_url(day, False), cache))
        day += timedelta(days=1)
    return archives


def parse_archives(paths):
    bars = []
    hashes = {}
    for path in paths:
        hashes[Path(path).name] = sha256(path)
        with zipfile.ZipFile(path) as archive:
            members = [name for name in archive.namelist() if name.endswith(".csv")]
            if len(members) != 1:
                raise ValueError(f"Expected one CSV in {path}")
            with archive.open(members[0]) as raw:
                for row in csv.reader(io.TextIOWrapper(raw, encoding="utf-8")):
                    if not row or not row[0].isdigit():  # Binance added a header to newer files.
                        continue
                    if len(row) < 6:
                        raise ValueError(f"Malformed kline row in {path}")
                    timestamp = timestamp_ms(row[0])
                    # Binance Spot archives switched from milliseconds to microseconds in 2025.
                    close, volume = float(row[4]), float(row[5])
                    if not np.isfinite(close) or close <= 0 or not np.isfinite(volume):
                        raise ValueError(f"Invalid close or volume in {path}")
                    bars.append((timestamp, close, volume))
    bars.sort()
    if not bars or any(bars[i][0] == bars[i - 1][0] for i in range(1, len(bars))):
        raise ValueError("Binance archives are empty or contain duplicate timestamps")
    return bars, hashes


def build_daily(bars):
    first_day, last_day = bars[0][0] // DAY_MS, bars[-1][0] // DAY_MS
    by_day = defaultdict(list)
    gaps = []
    for previous, current in itertools.pairwise(bars):
        delta = current[0] - previous[0]
        if delta != FIVE_MIN_MS:
            gap = {
                "after_utc": datetime.fromtimestamp(previous[0] / 1000, UTC).isoformat(),
                "delta_ms": delta,
                "missing_bars": max(round(delta / FIVE_MIN_MS) - 1, 0),
                "offset_ms": delta % FIVE_MIN_MS,
            }
            gaps.append(gap)
    for timestamp, close, volume in bars:
        by_day[timestamp // DAY_MS].append((timestamp, close, volume))
    expected_days = range(first_day, last_day + 1)
    missing_dates = [
        datetime.fromtimestamp(d * DAY_MS / 1000, UTC).date().isoformat()
        for d in expected_days
        if d not in by_day
    ]
    if missing_dates:
        raise ValueError(f"Missing full UTC dates: {missing_dates[:10]}")

    rows, incomplete_days = [], []
    prior_close = None
    for ordinal in expected_days:
        day_bars = by_day[ordinal]
        day_bars.sort()
        returns = []
        intervals = 0
        for previous, current in itertools.pairwise(day_bars):
            returns.append(np.log(current[1] / previous[1]))
            if current[0] - previous[0] == FIVE_MIN_MS:
                intervals += 1
        # Include the one observed return across a day boundary, even if bars are missing.
        if prior_close is not None:
            returns.append(np.log(day_bars[0][1] / prior_close))
            if day_bars[0][0] - by_day[ordinal - 1][-1][0] == FIVE_MIN_MS:
                intervals += 1
        last_close = day_bars[-1][1]
        daily_return = 0.0 if prior_close is None else float(np.log(last_close / prior_close))
        row_date = datetime.fromtimestamp(ordinal * DAY_MS / 1000, UTC).date()
        rows.append(
            {
                "date": row_date.isoformat(),
                "return": daily_return,
                "rv": float(np.dot(returns, returns)),
                "intervals": intervals,
                "zero_volume_fraction": float(np.mean([bar[2] == 0 for bar in day_bars])),
            }
        )
        if len(day_bars) != 288 or (ordinal != first_day and intervals != 288):
            incomplete_days.append(
                {"date": row_date.isoformat(), "bars": len(day_bars), "returns": intervals}
            )
        prior_close = last_close
    if any(row["rv"] <= 0 for row in rows):
        raise ValueError("Daily RV must be positive for every retained UTC date")
    return rows, gaps, incomplete_days


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=Path(".cache/binance-eth-5m"))
    parser.add_argument("--output", type=Path, default=Path("data/ethusdt_daily.csv"))
    args = parser.parse_args()
    paths = source_archives(args.cache)
    bars, source_hashes = parse_archives(paths)
    rows, gaps, incomplete_days = build_daily(bars)
    if rows[0]["date"] != FIRST.isoformat() or rows[-1]["date"] != LAST.isoformat():
        raise ValueError(
            f"Expected daily coverage {FIRST} through {LAST}; got {rows[0]['date']} to {rows[-1]['date']}"
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=["date", "return", "rv", "intervals", "zero_volume_fraction"]
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    info = {
        "source": "Binance spot ETHUSDT 5m klines",
        "first_day": rows[0]["date"],
        "last_day": rows[-1]["date"],
        "days": len(rows),
        "bars": len(bars),
        "source_sha256": source_hashes,
        "gap_count": len(gaps),
        "missing_5m_bars": int(sum(gap["missing_bars"] for gap in gaps)),
        "gaps": gaps,
        "incomplete_day_count": len(incomplete_days),
        "incomplete_days": incomplete_days,
        "first_day_return_convention": "0; no prior Binance daily close is available",
        "output_sha256": sha256(args.output),
    }
    args.output.with_suffix(".json").write_text(json.dumps(info, indent=2) + "\n")
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
