"""Run the complete audited full-sample reproduction, then export the comparison figures."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qvol.reproduction import run  # noqa: E402 -- standalone experiment entry point


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=ROOT / "configs/reproduction.json"
    )
    parser.add_argument(
        "--output", type=Path, required=True, help="New directory; never overwritten"
    )
    parser.add_argument("--data", type=Path, default=ROOT / "data/takaishi")
    args = parser.parse_args()
    result = run(args.output, args.data, json.loads(args.config.read_text()))
    from qvol.reproduction_plots import export

    export(result)
    print(f"Complete: {args.output.resolve()}")


if __name__ == "__main__":
    main()
