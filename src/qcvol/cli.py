"""Explicit, offline-by-default entry points; fetching upstream data is a separate script."""

import argparse
import json
from pathlib import Path

from .data import load_author_data, load_daily_csv, prepare, sha256, synthetic_data
from .experiment import ExperimentConfig, run_experiment
from .quantum import verify_paper


def main():
    parser = argparse.ArgumentParser(description="Quantum volatility course research runner")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("verify-paper", help="Check phi redundancy and exact Bloch twin")
    for name in ("demo", "run"):
        command = commands.add_parser(name)
        command.add_argument("--config", type=Path)
        command.add_argument(
            "--output", type=Path, required=True, help="New directory; never overwritten"
        )
        if name == "demo":
            command.add_argument("--days", type=int, default=360)
        else:
            source = command.add_mutually_exclusive_group(required=True)
            source.add_argument("--author-data", type=Path)
            source.add_argument("--csv", type=Path)
    args = parser.parse_args()
    if args.command == "verify-paper":
        report = verify_paper()
        print(json.dumps(report, indent=2))
        if max(report["phi_max_error"], report["twin_max_error"]) > 1e-12:
            raise SystemExit("Paper algebra check failed")
        return
    config = ExperimentConfig.load(args.config) if args.config else ExperimentConfig()
    if args.command == "demo":
        daily = synthetic_data(days=args.days)
        source = {"kind": "synthetic-demo", "seed": 42, "days": args.days}
    elif args.author_data:
        daily = load_author_data(args.author_data)
        source = {
            "kind": "author-standardized",
            "path": str(args.author_data.resolve()),
            "sha256": {
                name: sha256(args.author_data / name) for name in ("data-rstand", "data-ystand")
            },
        }
        provenance = args.author_data / "manifest.json"
        if provenance.exists():
            source["upstream_manifest"] = json.loads(provenance.read_text())
    else:
        daily = load_daily_csv(args.csv)
        source = {"kind": "daily-csv", "path": str(args.csv.resolve()), "sha256": sha256(args.csv)}
    summary = run_experiment(prepare(daily), config, args.output, source)
    print(json.dumps(summary, indent=2))
    print(f"Saved results to {args.output.resolve()}")


if __name__ == "__main__":
    main()
