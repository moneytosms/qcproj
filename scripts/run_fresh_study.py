#!/usr/bin/env python3
"""Run one stage of the fresh-data study (see qcvol.fresh_runner for the stage order)."""

import argparse
import json
from pathlib import Path

import numpy as np

from qcvol import fresh_runner as fr
from qcvol.data import load_daily_csv, sha256, synthetic_data
from qcvol.fresh_study import prepare_dates


def load(args):
    if args.synthetic:
        daily = synthetic_data(days=900, seed=7)
        daily.index = np.datetime64("2020-01-01") + daily.index.astype("timedelta64[D]")
        return prepare_dates(daily, "2021-06-30", "2021-12-31"), {"synthetic": True}
    return prepare_dates(load_daily_csv(args.data)), {
        "data_sha256": sha256(args.data),
        "data_info": json.loads(args.data.with_suffix(".json").read_text()),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "stage",
        choices=[
            "manifest",
            "develop-d",
            "select-d",
            "develop-a",
            "select-a",
            "train",
            "seal",
            "evaluate",
        ],
    )
    parser.add_argument("--data", type=Path, default=Path("data/bitstamp_daily.csv"))
    parser.add_argument("--config", type=Path, default=Path("configs/fresh-study.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, action="append", default=[])
    parser.add_argument("--synthetic", action="store_true", help="offline integration check")
    args = parser.parse_args()
    config = fr.FreshConfig(**json.loads(args.config.read_text()))
    data, source = load(args)
    source["config_sha256"] = sha256(args.config)
    if args.stage == "manifest":
        fr.write_manifest(data, config, args.output, source)
    elif args.stage == "develop-d":
        for seed in args.seed:
            fr.develop_d(data, config, seed, args.output)
    elif args.stage == "select-d":
        print(json.dumps(fr.select_d(config, args.output), indent=2))
    elif args.stage == "develop-a":
        for seed in args.seed:
            fr.develop_a(data, config, seed, args.output)
    elif args.stage == "select-a":
        print(json.dumps(fr.select_a(config, args.output), indent=2))
    elif args.stage == "train":
        for seed in args.seed:
            fr.train_seed(data, config, seed, args.output)
    elif args.stage == "seal":
        fr.seal(config, args.output)
        print("Sealed; no test scores computed")
    else:
        result = fr.evaluate(data, config, args.output)
        print(
            json.dumps({k: v["log_loss"]["mean"] for k, v in result["summary"].items()}, indent=2)
        )


if __name__ == "__main__":
    main()
