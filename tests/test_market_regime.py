import numpy as np
import pandas as pd
import pytest

from borgbot.core.market_regime import (
    MarketRegimeDetector,
    REGIME_DOWN,
    REGIME_SIDEWAYS,
    REGIME_TRANSITION,
    REGIME_UNKNOWN,
    REGIME_UP,
)


def frame_from_close(close, spread=1.0):
    close = pd.Series(close, dtype=float)
    return pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=len(close), freq="1h"),
        "high": close + spread / 2,
        "low": close - spread / 2,
        "close": close,
    })


def test_regime_analysis_preserves_index_and_adds_expected_columns():
    candles = frame_from_close(np.linspace(100.0, 140.0, 80))
    candles.index = pd.Index(range(100, 180))
    result = MarketRegimeDetector().analyze(candles)

    assert result.index.equals(candles.index)
    assert {"plus_di", "minus_di", "dx", "adx", "adx_change", "adx_rising", "regime"} <= set(result.columns)
    assert (result["regime"].iloc[:27] == REGIME_UNKNOWN).all()
    assert result["regime"].iloc[-1] == REGIME_UP


def test_persistent_downtrend_is_classified_down():
    candles = frame_from_close(np.linspace(180.0, 100.0, 100))
    result = MarketRegimeDetector().analyze(candles)
    assert result["regime"].iloc[-1] == REGIME_DOWN


def test_classification_threshold_boundaries():
    detector = MarketRegimeDetector()
    assert detector._classify(19.999, 40.0, 20.0) == REGIME_SIDEWAYS
    assert detector._classify(20.0, 40.0, 20.0) == REGIME_TRANSITION
    assert detector._classify(24.999, 40.0, 20.0) == REGIME_TRANSITION
    assert detector._classify(25.0, 40.0, 20.0) == REGIME_UP
    assert detector._classify(25.0, 20.0, 40.0) == REGIME_DOWN
    assert detector._classify(25.0, 30.0, 30.0) == REGIME_TRANSITION
    assert detector._classify(np.nan, 30.0, 20.0) == REGIME_UNKNOWN


def test_missing_ohlc_columns_rejected():
    with pytest.raises(ValueError, match="missing required columns"):
        MarketRegimeDetector().analyze(pd.DataFrame({"close": [1, 2, 3]}))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"period": 1},
        {"sideways_adx": 25.0, "trend_adx": 20.0},
        {"sideways_adx": -1.0, "trend_adx": 25.0},
        {"sideways_adx": 20.0, "trend_adx": 101.0},
    ],
)
def test_invalid_detector_configuration_rejected(kwargs):
    with pytest.raises(ValueError):
        MarketRegimeDetector(**kwargs)


def test_adx_rising_is_defined_only_when_consecutive_adx_values_exist():
    candles = frame_from_close(np.linspace(100.0, 160.0, 70))
    result = MarketRegimeDetector().analyze(candles)
    assert result["adx_rising"].iloc[:28].isna().all()
    assert result["adx_rising"].iloc[28:].notna().all()
