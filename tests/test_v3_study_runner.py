import importlib.util
from pathlib import Path

import numpy as np

spec = importlib.util.spec_from_file_location(
    "v3_study_runner", Path(__file__).parents[1] / "scripts/run_v3_study.py"
)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def test_paired_intervals_identical_losses_are_zero():
    losses = np.linspace(0.2, 0.8, 90)
    result = runner.paired_intervals(
        losses,
        {"softmax": losses.copy()},
        (7, 30),
        np.random.default_rng(7),
        replicates=20,
    )

    assert [row["control"] for row in result] == ["softmax", "softmax"]
    assert all(row["mean_difference"] == row["lower"] == row["upper"] == 0 for row in result)
