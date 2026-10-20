#!/usr/bin/env python3
"""Run only the point-model training/validation investigation, preserving the test split."""

import argparse
import json
from pathlib import Path

from qcvol.data import load_author_data, prepare, sha256
from qcvol.memory_diagnostics import MemoryInvestigationConfig, run_investigation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--author-data", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("configs/memory-investigation.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = {
        "kind": "author-standardized",
        "sha256": {
            name: sha256(args.author_data / name) for name in ("data-rstand", "data-ystand")
        },
    }
    config = MemoryInvestigationConfig(**json.loads(args.config.read_text()))
    run_investigation(prepare(load_author_data(args.author_data)), config, args.output, source)
    print(f"Complete: {args.output.resolve()}")


if __name__ == "__main__":
    main()
