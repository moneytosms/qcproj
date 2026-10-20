#!/usr/bin/env python3
"""Run frozen training, then score only sealed parameters; report task remains paused."""

import argparse
import json
from pathlib import Path

from qcvol.data import load_author_data, prepare, sha256
from qcvol.final_evaluation import evaluate_final
from qcvol.final_study import FinalConfig, train_final


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--author-data", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("configs/final-study.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stage", choices=["all", "train", "evaluate"], default="all")
    parser.add_argument("--evaluation-name", default="evaluation")
    args = parser.parse_args()
    data = prepare(load_author_data(args.author_data))
    if args.stage in ("all", "train"):
        source = {
            "sha256": {
                name: sha256(args.author_data / name) for name in ("data-rstand", "data-ystand")
            },
            "config_sha256": sha256(args.config),
        }
        train_final(data, FinalConfig(**json.loads(args.config.read_text())), args.output, source)
    if args.stage in ("all", "evaluate"):
        result = evaluate_final(data, args.output, args.evaluation_name)
        print(
            json.dumps(
                {
                    "seeds": len(
                        FinalConfig(
                            **json.loads((args.output / "manifest.json").read_text())["config"]
                        ).seeds
                    ),
                    "models": len(result["models"]),
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
