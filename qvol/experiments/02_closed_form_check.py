"""Phase 1: show that the paper's circuit has only 2 working parameters and an exact classical formula.

1. Changing phi leaves every prediction unchanged.
2. P0 = 1/2 + 1/2 n(theta, lam) . b(r, s), where b is the encoded qubit's Bloch vector.
3. The closed form reproduces the trained model on the real Bitcoin inputs.
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qvol import data
from qvol import paper_model as pm


def main():
    rv, ret = data.load_bitcoin()
    res_path = ROOT / "results" / "01_reproduce.json"
    if res_path.exists():
        p = json.loads(res_path.read_text())["params"]
        theta, phi, lam = p["theta"], p["phi"], p["lam"]
    else:
        (theta, phi, lam), _ = pm.fit(ret, rv)

    circuit = pm.predict((theta, phi, lam), ret, rv)
    phi_changed = [pm.predict((theta, ph, lam), ret, rv) for ph in (0.0, 1.0, -2.5, np.pi)]
    closed = np.array([pm.p0_closed_form(r, s, theta, lam) for r, s in zip(ret, rv)])

    max_phi_diff = float(max(np.abs(c - circuit).max() for c in phi_changed))
    max_closed_diff = float(np.abs(closed - circuit).max())
    print(f"Trained parameters: theta={theta:.4f} phi={phi:.4f} lam={lam:.4f}")
    print(f"Largest change in any prediction when phi is changed: {max_phi_diff:.2e}")
    print(f"Largest gap between closed form and circuit on all {len(rv)} days: {max_closed_diff:.2e}")
    n = [-np.sin(theta) * np.cos(lam), np.sin(theta) * np.sin(lam), np.cos(theta)]
    print(f"Readout direction n = ({n[0]:.4f}, {n[1]:.4f}, {n[2]:.4f}), |n| = {np.linalg.norm(n):.6f}")

    out = {"max_change_when_phi_varied": max_phi_diff, "max_closed_form_gap": max_closed_diff,
           "readout_direction": n, "working_parameters": 2}
    (ROOT / "results" / "02_closed_form.json").write_text(json.dumps(out, indent=2))
    print("Saved results/02_closed_form.json")


if __name__ == "__main__":
    main()
