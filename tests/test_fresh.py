import json

import numpy as np
import pytest

from qcvol import fresh_runner as fr
from qcvol.data import synthetic_data
from qcvol.fresh_models import FastBorn, Hybrid
from qcvol.fresh_study import prepare_dates, window_reference
from qcvol.metrics import moments
from qcvol.quantum import BornCircuit


def dated(days=900):
    daily = synthetic_data(days=days, seed=7)
    daily.index = np.datetime64("2020-01-01") + daily.index.astype("timedelta64[D]")
    return daily


@pytest.mark.parametrize("layers", [1, 2, 3, 4])
@pytest.mark.parametrize("rows", [3, 200])
def test_fast_born_matches_reference_circuit(layers, rows):
    rng = np.random.default_rng(layers)
    x, p = rng.normal(size=(rows, 4)), rng.normal(size=8 * layers)
    assert np.allclose(
        FastBorn(layers).probabilities(x, p), BornCircuit(layers).probabilities(x, p), atol=1e-12
    )


def test_short_circuit_ignores_week_and_month():
    rng = np.random.default_rng(0)
    x, p = rng.normal(size=(5, 4)), rng.normal(size=16)
    changed = x.copy()
    changed[:, 1:3] += 3.0
    model = FastBorn(2, short=True)
    assert np.allclose(model.probabilities(x, p), model.probabilities(changed, p))
    assert not np.allclose(FastBorn(2).probabilities(x, p), FastBorn(2).probabilities(changed, p))


def test_hybrid_with_zero_weight_is_the_base_model():
    rng = np.random.default_rng(1)
    base = rng.dirichlet(np.ones(4), size=6)
    x = rng.normal(size=(6, 4))
    hybrid = Hybrid(None, FastBorn(1))
    p = np.r_[0.0, rng.normal(size=8)]
    assert np.allclose(hybrid.pooled(base, x, p), base)
    p[0] = 0.7
    assert not np.allclose(hybrid.pooled(base, x, p), base)


def test_date_split_uses_training_only_for_preprocessing():
    daily = dated()
    data = prepare_dates(daily, "2021-06-30", "2021-12-31")
    dates = np.asarray(daily.index)[data.target_rows]
    assert dates[data.train][-1] == np.datetime64("2021-06-30")
    assert dates[data.validation][0] == np.datetime64("2021-07-01")
    assert dates[data.test][0] == np.datetime64("2022-01-01")
    changed = dated()
    changed.rv[-100:] *= 50
    other = prepare_dates(changed, "2021-06-30", "2021-12-31")
    assert np.allclose(data.scaler.mean, other.scaler.mean)
    assert np.allclose(data.bins.edges, other.bins.edges)


def test_window_reference_matches_window_length():
    y = dated().rv
    log_y = np.log(y)
    mean, scales = window_reference(log_y, len(log_y), count=1)
    assert np.allclose(mean, moments(log_y))
    assert np.all(scales >= 0.02)
    with pytest.raises(ValueError):
        window_reference(log_y, len(log_y) + 1)


def test_seal_detects_changed_training_artifact(tmp_path):
    data = prepare_dates(dated(), "2021-06-30", "2021-12-31")
    config = fr.FreshConfig(development_seeds=[900], final_seeds=[0])
    fr.write_manifest(data, config, tmp_path, {"synthetic": True})
    for name in (
        "select-d.json",
        "select-a.json",
        "develop-d-seed900.json",
        "develop-a-seed900.json",
        "train-seed0.json",
    ):
        (tmp_path / name).write_text(json.dumps({"placeholder": name}))
    fr.seal(config, tmp_path)
    fr.check_seal(data, tmp_path)
    (tmp_path / "train-seed0.json").write_text(json.dumps({"changed": True}))
    with pytest.raises(ValueError, match="Artifact changed"):
        fr.check_seal(data, tmp_path)
