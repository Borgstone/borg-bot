import numpy as np
import pandas as pd
import pytest

from borgbot.core.timeframe_alignment import (
    align_higher_timeframe_regime,
    timeframe_duration,
)
from borgbot.core.market_regime import REGIME_UNKNOWN


def make_frame(start, count, freq, start_price=100.0, step=0.2):
    close = start_price + np.arange(count) * step
    return pd.DataFrame({
        "timestamp": pd.date_range(start, periods=count, freq=freq),
        "high": close + 1.0,
        "low": close - 1.0,
        "close": close,
    })


@pytest.mark.parametrize(
    ("value", "expected"),
    [("1m", pd.Timedelta(minutes=1)), ("4h", pd.Timedelta(hours=4)),
     ("1d", pd.Timedelta(days=1)), ("2w", pd.Timedelta(weeks=2))],
)
def test_timeframe_duration(value, expected):
    assert timeframe_duration(value) == expected


@pytest.mark.parametrize("value", ["", "hour", "0h", "-1d", "1M", "1.5h"])
def test_invalid_timeframe_rejected(value):
    with pytest.raises(ValueError):
        timeframe_duration(value)


def test_higher_candle_is_not_used_before_its_close():
    # Daily candle opens at midnight and is only available at next midnight.
    base = make_frame("2025-01-01 00:00:00", 50, "1h")
    higher = make_frame("2025-01-01 00:00:00", 4, "1D", step=10.0)

    result = align_higher_timeframe_regime(base, higher, "1h", "1d")

    # Hourly candle opened at 22:00 closes at 23:00: Jan 1 daily candle is not closed.
    assert result.loc[22, "higher_regime"] == REGIME_UNKNOWN
    # Hourly candle opened at 23:00 closes exactly at midnight, so Jan 1 daily candle is now usable.
    assert result.loc[23, "higher_regime"] != REGIME_UNKNOWN


def test_higher_timeframe_alignment_preserves_rows_and_index():
    base = make_frame("2025-01-01 00:00:00", 72, "1h")
    base.index = range(1000, 1072)
    higher = make_frame("2024-12-25 00:00:00", 10, "1D", step=10.0)

    result = align_higher_timeframe_regime(base, higher, "1h", "1d")

    assert len(result) == len(base)
    assert result.index.equals(base.index)
    assert "higher_adx" in result
    assert "higher_regime" in result
    assert result["timestamp"].equals(base["timestamp"])


def test_higher_timeframe_must_be_strictly_higher():
    base = make_frame("2025-01-01", 30, "1h")
    with pytest.raises(ValueError, match="greater than"):
        align_higher_timeframe_regime(base, base, "1h", "1h")


def test_unsorted_timestamps_rejected():
    base = make_frame("2025-01-01", 30, "1h")
    base = base.iloc[::-1].reset_index(drop=True)
    higher = make_frame("2024-12-20", 10, "1D")
    with pytest.raises(ValueError, match="sorted ascending"):
        align_higher_timeframe_regime(base, higher, "1h", "1d")
