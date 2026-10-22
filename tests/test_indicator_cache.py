import pandas as pd

from borgbot.data.indicator_cache import build_indicator_cache


def sample_candles(rows=220):
    close = pd.Series(range(1, rows + 1), dtype=float)
    return pd.DataFrame(
        {
            "open": close,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 1.0,
        }
    )


def test_indicator_cache_can_build_only_requested_sma_periods():
    cached = build_indicator_cache(sample_candles(), sma_periods=(50, 100))

    assert "sma_50" in cached.columns
    assert "sma_100" in cached.columns
    assert "sma_5" not in cached.columns
    assert "sma_200" not in cached.columns
    assert "rsi_10" in cached.columns
    assert "rsi_20" in cached.columns
    assert "atr_14" in cached.columns


def test_indicator_cache_default_keeps_full_sma_range():
    cached = build_indicator_cache(sample_candles())

    assert "sma_5" in cached.columns
    assert "sma_50" in cached.columns
    assert "sma_100" in cached.columns
    assert "sma_200" in cached.columns
