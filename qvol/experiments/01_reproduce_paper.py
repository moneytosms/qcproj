"""Phase 1: rebuild Takaishi's 1-qubit model, train it, generate a long history,
and compare it with real Bitcoin and with the author's own generated series."""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qvol import data, metrics
from qvol import paper_model as pm

N_GEN = 50_000
WINDOW = 913
EPS = 1e-6


def describe(v, r):
    logv = np.log(np.maximum(v, EPS))
    irv = np.diff(logv)
    segs = [slice(i, i + WINDOW) for i in range(0, len(v) - WINDOW + 1, WINDOW)][:20]
    return {
        "mean_vol": float(v.mean()),
        "std_vol": float(v.std()),
        "acf_logvol_lag1_7_30": [round(float(x), 3) for x in metrics.realism_moments(logv)[:3]],
        "spread_dlogvol": round(float(np.diff(logv).std()), 3),
        "h2_returns": round(float(np.mean([metrics.hurst2(r[s]) for s in segs])), 3),
        "h2_vol_increments": round(float(np.mean([metrics.hurst2(irv[s][:-1]) for s in segs])), 3),
        "mf_width_returns": round(float(np.mean([metrics.mf_width(r[s]) for s in segs])), 3),
        "tail_index_returns": round(float(metrics.hill_tail_index(r)), 2),
    }


def main():
    rv, ret = data.load_bitcoin()
    params, mse = pm.fit(ret, rv)
    theta, phi, lam = params
    print(f"Fitted theta={theta:.4f} phi={phi:.4f} lam={lam:.4f}  MSE={mse:.3e}")

    fitted = pm.predict(params, ret[:-1], rv[:-1])
    corr = float(np.corrcoef(fitted, rv[1:])[0, 1])
    print(f"Correlation of one-step forecast with actual RV: {corr:.3f}")

    av, ar = data.load_author_generated()
    scale_author = float((ar / np.sqrt(np.maximum(av, EPS))).std())

    rows = {"real_bitcoin": describe(rv, ret), "author_generated": describe(av, ar)}
    for name, sc in [("ours_scale_1", 1.0), ("ours_scale_matched", scale_author)]:
        v, r = pm.generate(params, N_GEN, ret[-1], rv[-1], ret_scale=sc, seed=0)
        rows[name] = describe(v, r)

    keys = list(rows["real_bitcoin"])
    print(f"\n{'':22s}" + "".join(f"{n:>22s}" for n in rows))
    for k in keys:
        print(f"{k:22s}" + "".join(f"{str(rows[n][k]):>22s}" for n in rows))

    out = {"params": {"theta": theta, "phi": phi, "lam": lam}, "train_mse": mse,
           "one_step_corr": corr, "author_return_scale": scale_author, "series": rows}
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "01_reproduce.json").write_text(json.dumps(out, indent=2))
    print("\nSaved results/01_reproduce.json")


if __name__ == "__main__":
    main()
