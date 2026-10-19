"""Phase 1 figure: how long volatility 'remembers' itself, real Bitcoin vs the paper's model."""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qvol import data, metrics
from qvol import paper_model as pm

EPS = 1e-6


def main():
    rv, ret = data.load_bitcoin()
    p = json.loads((ROOT / "results" / "01_reproduce.json").read_text())["params"]
    v, _ = pm.generate((p["theta"], p["phi"], p["lam"]), 50_000, ret[-1], rv[-1], seed=0)
    av, _ = data.load_author_generated()

    lags = np.arange(1, 61)
    series = [("Real Bitcoin", np.log(rv), "#1f2937"),
              ("Author's generated series", np.log(np.maximum(av, EPS)), "#9ca3af"),
              ("Our rebuild of the paper's model", np.log(v), "#2563eb")]
    fig, ax = plt.subplots(figsize=(8, 3.6))
    for name, x, c in series:
        ax.plot(lags, [metrics.acf(x, k) for k in lags], label=name, color=c, lw=2)
    ax.axhline(0, color="#e5e7eb", lw=1)
    ax.set_xlabel("days apart")
    ax.set_ylabel("correlation of log volatility")
    ax.set_title("The paper's model forgets after a day; real Bitcoin remembers for months", loc="left", fontsize=11, fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    out = ROOT / "results" / "fig_memory_gap.png"
    fig.savefig(out, dpi=200)
    print(f"Saved {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
