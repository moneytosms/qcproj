#!/usr/bin/env python3
"""Run the baseline-preserving memory follow-up; test scoring is deliberately absent."""

import argparse
import json
from pathlib import Path

from qcvol.data import load_author_data, prepare, sha256
from qcvol.nested_study import NestedStudyConfig, run_followup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--author-data", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("configs/nested-memory.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = NestedStudyConfig(**json.loads(args.config.read_text()))
    source = {
        "kind": "author-standardized",
        "sha256": {
            name: sha256(args.author_data / name) for name in ("data-rstand", "data-ystand")
        },
        "config_sha256": sha256(args.config),
    }
    decision = run_followup(
        prepare(load_author_data(args.author_data)), config, args.output, source
    )
    print(json.dumps(decision, indent=2))


if __name__ == "__main__":
    main()
