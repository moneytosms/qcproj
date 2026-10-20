#!/usr/bin/env python3
"""Run the Step 4 validation comparison; requires the completed Step 3 artifacts."""

import argparse
import json
from pathlib import Path

from qcvol.comparison_study import ComparisonConfig, run_comparison
from qcvol.data import load_author_data, prepare, sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--author-data", type=Path, required=True)
    parser.add_argument("--prior", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("configs/classical-comparison.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = {
        "sha256": {
            name: sha256(args.author_data / name) for name in ("data-rstand", "data-ystand")
        },
        "config_sha256": sha256(args.config),
    }
    result = run_comparison(
        prepare(load_author_data(args.author_data)),
        args.prior,
        args.output,
        ComparisonConfig(**json.loads(args.config.read_text())),
        source,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
