#!/usr/bin/env python3
"""Build daily realized variance from Bitstamp 1-minute BTC/USD closes.

RV(day) = sum of squared 5-minute log returns inside the UTC day, as in Takaishi (2026).
Return(day) = log(close at end of day / close at end of previous day).
Only complete UTC days from 2016-12-01 to 2026-10-19 are written, so the first target
day after the 30-day feature window is 2016-12-31 and every split date is covered.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

FIRST, LAST = "2016-12-01", "2026-10-19"
FILES = (
    "data/historical/btcusd_bitstamp_1min_2012-2025.csv.gz",
    "data/updates/btcusd_bitstamp_1min_latest.csv",
)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(source: Path) -> tuple[pd.DataFrame, dict]:
    parts = [pd.read_csv(source / f, usecols=["timestamp", "close", "volume"]) for f in FILES]
    minute = pd.concat(parts).drop_duplicates("timestamp").sort_values("timestamp")
    minute.index = pd.to_datetime(minute["timestamp"], unit="s", utc=True)
    close5 = minute["close"].resample("5min").last()
    volume5 = minute["volume"].resample("5min").sum()
    frame = pd.DataFrame({"r5": np.log(close5).diff(), "v5": volume5, "c5": close5})
    frame["day"] = frame.index.floor("D")
    groups = frame.groupby("day")
    daily = pd.DataFrame(
        {
            "rv": groups["r5"].apply(lambda x: float(np.nansum(x.to_numpy() ** 2))),
            "intervals": groups["r5"].count(),
            "zero_volume_fraction": groups["v5"].apply(lambda x: float((x.to_numpy() == 0).mean())),
            "close": groups["c5"].last(),
        }
    )
    daily["return"] = np.log(daily["close"]).diff()
    daily.index = daily.index.tz_localize(None).strftime("%Y-%m-%d")
    daily = daily.loc[FIRST:LAST]
    if len(daily) != (pd.Timestamp(LAST) - pd.Timestamp(FIRST)).days + 1:
        raise ValueError("Missing calendar days")
    if (daily["intervals"] < 287).any() or (daily["rv"] <= 0).any():
        raise ValueError("Incomplete day or nonpositive RV in the selected range")
    info = {
        "first_day": FIRST,
        "last_day": LAST,
        "days": len(daily),
        "source_sha256": {f: sha256(source / f) for f in FILES},
        "max_zero_volume_fraction": float(daily["zero_volume_fraction"].max()),
    }
    return daily, info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(".cache/bitstamp-minute"))
    parser.add_argument("--output", type=Path, default=Path("data/bitstamp_daily.csv"))
    args = parser.parse_args()
    daily, info = build(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    out = daily[["return", "rv", "intervals", "zero_volume_fraction"]].copy()
    out.index.name = "date"
    out.to_csv(args.output, float_format="%.10g")
    info["output_sha256"] = sha256(args.output)
    args.output.with_suffix(".json").write_text(json.dumps(info, indent=2) + "\n")
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
