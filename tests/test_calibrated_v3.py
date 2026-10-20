import importlib.util
from pathlib import Path

import numpy as np

spec = importlib.util.spec_from_file_location(
    "evaluate_calibrated_v3", Path(__file__).parents[1] / "scripts/evaluate_calibrated_v3.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_temperature_fit_improves_already_correct_confident_predictions():
    probabilities = np.array([[0.95, 0.03, 0.01, 0.01], [0.02, 0.94, 0.02, 0.02]])
    labels = np.array([0, 1])

    temperature, calibrated = module.fit_temperature(probabilities, labels)

    assert 0.2 <= temperature <= 5
    assert np.allclose(calibrated.sum(axis=1), 1)
    assert module._scores(calibrated, labels, np.ones(2), np.ones(4))["log_loss"].mean() <= (
        module._scores(probabilities, labels, np.ones(2), np.ones(4))["log_loss"].mean()
    )
