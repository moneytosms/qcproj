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
    parser.add_argument("--previous-attempt", type=Path)
    args = parser.parse_args()
    source = {
        "sha256": {
            name: sha256(args.author_data / name) for name in ("data-rstand", "data-ystand")
        },
        "config_sha256": sha256(args.config),
    }
    if args.previous_attempt:
        previous = json.loads((args.previous_attempt / "manifest.json").read_text())
        if previous["status"] != "complete":
            raise ValueError("Previous attempt must be complete")
        source["previous_attempt"] = {
            "directory": str(args.previous_attempt.resolve()),
            "manifest_sha256": sha256(args.previous_attempt / "manifest.json"),
            "head": previous["code"]["head"],
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
