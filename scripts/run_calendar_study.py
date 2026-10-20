#!/usr/bin/env python3
"""Run the declared improvement study's training/validation stages; no test scoring."""

import argparse
import json
from pathlib import Path

from qcvol import calendar_study as cs
from qcvol.data import load_daily_csv
from qcvol.fresh_study import prepare_dates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["initialize", "develop", "train", "seal"])
    parser.add_argument("--data", type=Path, default=Path("data/bitstamp_daily.csv"))
    parser.add_argument("--config", type=Path, default=Path("configs/calendar-study.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = prepare_dates(load_daily_csv(args.data))
    if args.stage == "initialize":
        cs.initialize(data, cs.CalendarConfig(**json.loads(args.config.read_text())), args.output)
    else:
        result = getattr(cs, args.stage)(data, args.output)
        if args.stage == "develop":
            print(
                json.dumps({"linear": result["linear_key"], "choices": result["choices"]}, indent=2)
            )


if __name__ == "__main__":
    main()
