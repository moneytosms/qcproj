#!/usr/bin/env python3
"""Run the sequential D/A validation study with the short-input policy."""

import argparse
import json
from pathlib import Path

from qcvol.data import load_author_data, prepare, sha256
from qcvol.distribution_study import DistributionConfig, run_distribution_study


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--author-data", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("configs/distribution-study.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = DistributionConfig(**json.loads(args.config.read_text()))
    source = {
        "sha256": {
            name: sha256(args.author_data / name) for name in ("data-rstand", "data-ystand")
        },
        "config_sha256": sha256(args.config),
    }
    print(
        json.dumps(
            run_distribution_study(
                prepare(load_author_data(args.author_data)), config, args.output, source
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
