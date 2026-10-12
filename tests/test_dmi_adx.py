import math

import numpy as np
import pandas as pd
import pytest

from borgbot.indicators.dmi_adx import dmi_adx


def candles_from_close(close, spread=1.0):
    close = np.asarray(close, dtype=float)
    return pd.Series(close + spread / 2), pd.Series(close - spread / 2), pd.Series(close)


def test_output_columns_index_and_warmup():
    high, low, close = candles_from_close(np.linspace(100.0, 130.0, 80))
    result = dmi_adx(high, low, close, period=14)
    assert list(result.columns) == ["plus_di", "minus_di", "dx", "adx"]
    assert result.index.equals(close.index)
    assert result["adx"].iloc[:27].isna().all()
    assert result["adx"].iloc[27:].notna().all()


def test_persistent_rise_has_positive_directional_dominance():
    high, low, close = candles_from_close(np.linspace(100.0, 180.0, 100))
    result = dmi_adx(high, low, close, period=14).dropna()
    assert not result.empty
    assert (result["plus_di"] > result["minus_di"]).all()
    assert result["adx"].between(0.0, 100.0).all()


def test_persistent_fall_has_negative_directional_dominance():
    high, low, close = candles_from_close(np.linspace(180.0, 100.0, 100))
    result = dmi_adx(high, low, close, period=14).dropna()
    assert not result.empty
    assert (result["minus_di"] > result["plus_di"]).all()


def test_adx_is_bounded_and_nonnegative():
    close = pd.Series(100.0 + np.sin(np.arange(160) / 3.0) * 4.0 + np.arange(160) * 0.03)
    result = dmi_adx(close + 0.8, close - 0.8, close, period=14).dropna()
    assert result["adx"].between(0.0, 100.0).all()
    assert result["dx"].between(0.0, 100.0).all()
    assert math.isfinite(float(result["adx"].iloc[-1]))


@pytest.mark.parametrize("period", [0, 1, -1, True, 14.0])
def test_invalid_period_rejected(period):
    high, low, close = candles_from_close(np.arange(30) + 100.0)
    with pytest.raises(ValueError, match="period"):
        dmi_adx(high, low, close, period=period)


def test_mismatched_lengths_rejected():
    with pytest.raises(ValueError, match="equal lengths"):
        dmi_adx([2, 3, 4], [1, 2], [1.5, 2.5, 3.5])


def test_mismatched_indexes_rejected():
    high = pd.Series([2.0, 3.0, 4.0], index=[0, 1, 2])
    low = pd.Series([1.0, 2.0, 3.0], index=[1, 2, 3])
    close = pd.Series([1.5, 2.5, 3.5], index=[0, 1, 2])
    with pytest.raises(ValueError, match="matching indexes"):
        dmi_adx(high, low, close)


def test_invalid_ohlc_rejected():
    with pytest.raises(ValueError, match="high must be"):
        dmi_adx([1.0, 2.0, 1.5], [0.5, 1.0, 2.0], [0.8, 1.5, 1.7])


def test_non_finite_ohlc_rejected():
    with pytest.raises(ValueError, match="finite values"):
        dmi_adx([2.0, np.nan, 4.0], [1.0, 2.0, 3.0], [1.5, 2.5, 3.5])


def test_input_series_are_not_modified():
    high, low, close = candles_from_close(np.linspace(100.0, 120.0, 40))
    before = (high.copy(), low.copy(), close.copy())
    dmi_adx(high, low, close, period=5)
    pd.testing.assert_series_equal(high, before[0])
    pd.testing.assert_series_equal(low, before[1])
    pd.testing.assert_series_equal(close, before[2])



def test_no_directional_movement_produces_zero_adx_not_missing():
    close = pd.Series(np.full(60, 100.0))
    high = pd.Series(np.full(60, 101.0))
    low = pd.Series(np.full(60, 99.0))
    result = dmi_adx(high, low, close, period=14)

    assert result["adx"].iloc[:27].isna().all()
    assert (result["adx"].iloc[27:] == 0.0).all()
