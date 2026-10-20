import numpy as np
import pytest

from qcvol.data import DailyData, VolatilityBins, load_daily_csv, prepare, synthetic_data


def test_har_uses_only_completed_days():
    daily = synthetic_data(360)
    prepared = prepare(daily)
    y = np.log(daily.rv)
    np.testing.assert_allclose(
        prepared.raw_x[0], [y[29], y[23:30].mean(), y[:30].mean(), daily.returns[29]]
    )
    assert prepared.target_rows[0] == 30
    daily.rv[30] *= 3
    after = prepare(daily)
    np.testing.assert_equal(prepared.raw_x[0], after.raw_x[0])
    assert after.y[0] != prepared.y[0]


def test_future_values_cannot_change_training_scaler_bins_or_rows():
    original = synthetic_data(360)
    before = prepare(original)
    future_start = before.target_rows[before.validation.start]
    rv, returns = original.rv.copy(), original.returns.copy()
    rv[future_start:] *= 1e6
    returns[future_start:] *= -1e3
    after = prepare(DailyData(original.index, returns, rv, original.units))
    np.testing.assert_array_equal(before.x[before.train], after.x[after.train])
    np.testing.assert_array_equal(before.bins.edges, after.bins.edges)
    np.testing.assert_array_equal(before.scaler.mean, after.scaler.mean)
    np.testing.assert_array_equal(before.scaler.scale, after.scaler.scale)
    for pool_a, pool_b in zip(before.bins.pools, after.bins.pools):
        np.testing.assert_array_equal(pool_a, pool_b)


def test_bin_equality_goes_to_upper_bin_and_pools_are_correct():
    bins = VolatilityBins.fit(np.arange(100.0))
    np.testing.assert_array_equal(bins.label(bins.edges), [1, 2, 3])
    for k, pool in enumerate(bins.pools):
        assert np.all(bins.label(pool) == k)
    with pytest.raises(ValueError, match="coincide"):
        VolatilityBins.fit(np.ones(100))


def test_bad_csv_dates_are_not_silently_sorted(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("date,return,rv\n2026-01-02,0,.1\n2026-01-01,0,.2\n")
    with pytest.raises(ValueError, match="ascending"):
        load_daily_csv(path)


def test_nonpositive_rv_rejected():
    data = synthetic_data(360)
    data.rv[4] = 0
    with pytest.raises(ValueError, match="strictly positive"):
        DailyData(data.index, data.returns, data.rv, data.units)
