#!/usr/bin/env python3
"""Explicit download of revision-pinned upstream data; raw files stay ignored by git."""

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

REVISION = "2fec7ee621006bcbe1b7860d05b9589a7276a8f6"
REPOSITORY = "https://github.com/takaishi-physics/QCL-volatility"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/raw/author"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = {
        "repository": REPOSITORY,
        "revision": REVISION,
        "units": "author-standardized",
        "calendar_dates": "not present in raw files",
        "license": "upstream GPL-3.0; preserve upstream license when redistributing",
        "files": {},
    }
    with tempfile.TemporaryDirectory(prefix="qcvol-upstream-") as temporary:
        repository = Path(temporary) / "upstream.git"
        subprocess.run(
            ["git", "clone", "--bare", "--quiet", REPOSITORY + ".git", str(repository)],
            check=True,
            timeout=60,
        )
        for name in ("data-rstand", "data-ystand", "Readme.txt", "LICENSE"):
            content = subprocess.run(
                ["git", "--git-dir", str(repository), "show", f"{REVISION}:{name}"],
                check=True,
                capture_output=True,
                timeout=10,
            ).stdout
            (args.output / name).write_bytes(content)
            manifest["files"][name] = {
                "url": f"{REPOSITORY}/blob/{REVISION}/{name}",
                "sha256": hashlib.sha256(content).hexdigest(),
            }
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Saved pinned upstream files and provenance to {args.output}")


if __name__ == "__main__":
    main()
