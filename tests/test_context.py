import numpy as np
import pandas as pd
import pytest

from borgbot.core.context import MarketContext
from borgbot.core.market_regime import MarketRegimeDetector


def frame(start, count, freq, step=0.2):
    close = 100.0 + np.arange(count) * step
    return pd.DataFrame({
        "timestamp": pd.date_range(start, periods=count, freq=freq),
        "high": close + 1.0,
        "low": close - 1.0,
        "close": close,
    })


def test_context_without_higher_timeframe_has_local_regime():
    candles = frame("2025-01-01", 60, "1h")
    result = MarketContext(candles).analyze()
    assert "local_adx" in result
    assert "local_regime" in result
    assert "higher_regime" not in result
    assert result["timestamp"].equals(candles["timestamp"])


def test_context_keeps_local_and_higher_regimes_separate():
    candles = frame("2025-01-20", 72, "1h")
    higher = frame("2025-01-01", 25, "1D", step=2.0)
    result = MarketContext(
        candles,
        higher_tf=higher,
        timeframe="1h",
        higher_timeframe="1d",
        detector=MarketRegimeDetector(period=2),
    ).analyze()
    assert "local_regime" in result
    assert "higher_regime" in result
    assert len(result) == len(candles)


def test_context_requires_timeframes_when_higher_data_is_provided():
    with pytest.raises(ValueError, match="timeframe and higher_timeframe"):
        MarketContext(frame("2025-01-01", 10, "1h"), higher_tf=frame("2024-12-01", 10, "1D")).analyze()
