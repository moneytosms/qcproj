from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np

from qcvol_next.binance_data import (
    FIVE_MIN_MS,
    archive_url,
    build_daily,
    source_archives,
    timestamp_ms,
)


def two_days(missing=False, shifted=False):
    start = int(datetime(2020, 1, 1, tzinfo=UTC).timestamp() * 1000)
    bars = []
    for i in range(576):
        if missing and i == 300:
            continue
        offset = 94_800 if shifted and i >= 301 else 0
        bars.append((start + i * FIVE_MIN_MS + offset, float(np.exp(i / 100_000)), 1.0))
    return bars


def test_timestamp_ms_accepts_both_binance_spot_units():
    millis = int(datetime(2024, 12, 31, tzinfo=UTC).timestamp() * 1000)
    micros = int(datetime(2025, 1, 1, tzinfo=UTC).timestamp() * 1_000_000)
    assert timestamp_ms(millis) == millis
    assert timestamp_ms(micros) == micros // 1000


def test_archive_url_supports_a_second_spot_symbol():
    assert archive_url(datetime(2024, 1, 1).date(), True, "BTCUSDT").endswith(
        "/BTCUSDT/5m/BTCUSDT-5m-2024-01.zip"
    )


def test_source_archives_respects_symbol_and_date_window(tmp_path, monkeypatch):
    calls = []

    def download(url, cache):
        calls.append(url)
        return Path(url.rsplit("/", 1)[-1])

    monkeypatch.setattr("qcvol_next.binance_data.download_checked", download)
    paths = source_archives(
        tmp_path,
        "SOLUSDT",
        date(2020, 8, 1),
        date(2020, 9, 1),
    )
    assert len(paths) == 2
    assert any("SOLUSDT-5m-2020-08.zip" in url for url in calls)
    assert any("SOLUSDT-5m-2020-09-01.zip" in url for url in calls)


def test_build_daily_uses_utc_5m_returns_and_reports_gaps():
    rows, gaps, incomplete = build_daily(two_days())
    assert [r["date"] for r in rows] == ["2020-01-01", "2020-01-02"]
    assert rows[0]["return"] == 0
    assert rows[1]["intervals"] == 288
    assert rows[1]["rv"] > 0
    assert not gaps
    assert not incomplete

    _, gaps, incomplete = build_daily(two_days(missing=True))
    assert len(gaps) == 1 and gaps[0]["missing_bars"] == 1
    assert incomplete == [{"date": "2020-01-02", "bars": 287, "returns": 286}]

    _, gaps, _ = build_daily(two_days(missing=True, shifted=True))
    assert gaps[0]["missing_bars"] == 1
    assert gaps[0]["offset_ms"] == 94_800
