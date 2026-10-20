#!/usr/bin/env python3
"""Run the trained 2-qubit forecaster on IBM quantum hardware (or a local sampler).

Run this only AFTER the fresh study is evaluated: it changes nothing in the study and only
measures how far hardware samples are from the exact probabilities used in the results.

    pip install qiskit qiskit-ibm-runtime
    python scripts/run_ibm_hardware.py --study results/fresh-study --local          # test
    IBM_TOKEN=... python scripts/run_ibm_hardware.py --study results/fresh-study    # QPU

IBM's free Open Plan gives up to 10 QPU minutes per 28 days. The defaults (40 test days,
1,000 shots each) are designed to stay well inside that.
"""

import argparse
import json
import os
from pathlib import Path

import numpy as np

from qcvol.data import load_daily_csv
from qcvol.fresh_models import FastBorn
from qcvol.fresh_study import prepare_dates


def build_circuit(x, parameters, layers):
    """Same gate sequence as FastBorn / BornCircuit, measured on both qubits."""
    from qiskit import QuantumCircuit

    w = np.asarray(parameters).reshape(layers, 8)
    qc = QuantumCircuit(2, 2)
    for layer in w:
        qc.ry(float(layer[0] * x[0]), 0)
        qc.rz(float(layer[1] * x[1]), 0)
        qc.ry(float(layer[4]), 0)
        qc.rz(float(layer[5]), 0)
        qc.ry(float(layer[2] * x[2]), 1)
        qc.rz(float(layer[3] * x[3]), 1)
        qc.ry(float(layer[6]), 1)
        qc.rz(float(layer[7]), 1)
        qc.cx(0, 1)
    qc.measure([0, 1], [0, 1])
    return qc


def counts_to_levels(counts, shots):
    """Qiskit bitstrings are 'c1c0'; our level index is 2*q0 + q1."""
    p = np.zeros(4)
    for bits, n in counts.items():
        q1, q0 = int(bits[0]), int(bits[1])
        p[2 * q0 + q1] += n / shots
    return p


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", type=Path, default=Path("results/fresh-study"))
    parser.add_argument("--data", type=Path, default=Path("data/bitstamp_daily.csv"))
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--days", type=int, default=40)
    parser.add_argument("--shots", type=int, default=1000)
    parser.add_argument("--local", action="store_true", help="local shot sampler, no account")
    parser.add_argument("--backend", default=None, help="IBM backend name (default least busy)")
    args = parser.parse_args()

    if not (args.study / "evaluation" / "results.json").is_file():
        raise SystemExit("Evaluate the study first; hardware runs come after the sealed results")
    entry = json.loads((args.study / f"train-seed{args.seed}.json").read_text())["models"][
        "quantum-har"
    ]
    layers, parameters = entry["depth"], np.array(entry["D"]["parameters"])
    data = prepare_dates(load_daily_csv(args.data))
    rows = np.linspace(data.test.start, data.test.stop - 1, args.days).astype(int)
    x, labels = data.x[rows], data.labels[rows]
    exact = FastBorn(layers).probabilities(x, parameters)
    circuits = [build_circuit(row, parameters, layers) for row in x]

    if args.local:
        from qiskit.primitives import StatevectorSampler

        sampler, backend_name, isa = StatevectorSampler(), "local StatevectorSampler", circuits
    else:
        from qiskit.transpiler import generate_preset_pass_manager
        from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

        service = QiskitRuntimeService(
            channel="ibm_quantum_platform", token=os.environ["IBM_TOKEN"]
        )
        backend = (
            service.backend(args.backend)
            if args.backend
            else service.least_busy(operational=True, simulator=False)
        )
        isa = generate_preset_pass_manager(optimization_level=1, backend=backend).run(circuits)
        sampler, backend_name = SamplerV2(mode=backend), backend.name
    result = sampler.run(isa, shots=args.shots).result()
    measured = np.array([counts_to_levels(r.data.c.get_counts(), args.shots) for r in result])

    def nll(p):
        return float(-np.mean(np.log(np.clip(p[np.arange(len(labels)), labels], 1e-12, 1))))

    tvd = 0.5 * np.abs(measured - exact).sum(axis=1)
    summary = {
        "backend": backend_name,
        "layers": layers,
        "seed": args.seed,
        "test_days": len(rows),
        "shots": args.shots,
        "mean_total_variation_distance": float(tvd.mean()),
        "max_total_variation_distance": float(tvd.max()),
        "log_loss_exact": nll(exact),
        "log_loss_measured": nll(np.clip(measured, 1 / args.shots, 1)),
        "shot_noise_reference_tvd": float(
            np.mean(
                0.5 * np.sqrt(exact * (1 - exact) / args.shots).sum(axis=1) * np.sqrt(2 / np.pi)
            )
        ),
    }
    out = args.study / ("hardware-local.json" if args.local else "hardware-ibm.json")
    out.write_text(
        json.dumps(
            {
                "summary": summary,
                "rows": rows.tolist(),
                "exact": exact.tolist(),
                "measured": measured.tolist(),
            },
            indent=2,
        )
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
