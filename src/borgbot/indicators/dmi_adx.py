"""Wilder's Directional Movement System (DMI/ADX).

This indicator calculates values only. Regime thresholds and higher-timeframe
alignment belong in the context layer.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def dmi_adx(high, low, close, period: int = 14) -> pd.DataFrame:
    """Return +DI, -DI, DX and ADX using Wilder smoothing.

    The returned DataFrame preserves the input index. Values remain NaN until
    enough history exists; no forward/back filling is performed.
    """
    if isinstance(period, bool) or not isinstance(period, int) or period < 2:
        raise ValueError("period must be an integer >= 2")

    high = pd.Series(high, copy=False, dtype="float64")
    low = pd.Series(low, copy=False, dtype="float64")
    close = pd.Series(close, copy=False, dtype="float64")

    if not (len(high) == len(low) == len(close)):
        raise ValueError("high, low and close must have equal lengths")
    if not (high.index.equals(low.index) and high.index.equals(close.index)):
        raise ValueError("high, low and close must have matching indexes")

    values = np.column_stack((high.to_numpy(), low.to_numpy(), close.to_numpy()))
    if not np.isfinite(values).all():
        raise ValueError("high, low and close must contain only finite values")
    if (high < low).any():
        raise ValueError("high must be >= low for every candle")

    size = len(high)
    tr = np.full(size, np.nan)
    plus_dm = np.full(size, np.nan)
    minus_dm = np.full(size, np.nan)
    h, l, c = high.to_numpy(), low.to_numpy(), close.to_numpy()

    if size > 1:
        up_move = h[1:] - h[:-1]
        down_move = l[:-1] - l[1:]
        plus_dm[1:] = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm[1:] = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
        tr[1:] = np.maximum.reduce((
            h[1:] - l[1:],
            np.abs(h[1:] - c[:-1]),
            np.abs(l[1:] - c[:-1]),
        ))

    smoothed_tr = np.full(size, np.nan)
    smoothed_plus = np.full(size, np.nan)
    smoothed_minus = np.full(size, np.nan)

    # Seed Wilder sums with the first period valid observations (bars 1..period).
    if size > period:
        smoothed_tr[period] = np.sum(tr[1 : period + 1])
        smoothed_plus[period] = np.sum(plus_dm[1 : period + 1])
        smoothed_minus[period] = np.sum(minus_dm[1 : period + 1])
        for i in range(period + 1, size):
            smoothed_tr[i] = smoothed_tr[i - 1] - smoothed_tr[i - 1] / period + tr[i]
            smoothed_plus[i] = smoothed_plus[i - 1] - smoothed_plus[i - 1] / period + plus_dm[i]
            smoothed_minus[i] = smoothed_minus[i - 1] - smoothed_minus[i - 1] / period + minus_dm[i]

    plus_di = np.full(size, np.nan)
    minus_di = np.full(size, np.nan)
    valid_tr = np.isfinite(smoothed_tr) & (smoothed_tr > 0)
    plus_di[valid_tr] = 100.0 * smoothed_plus[valid_tr] / smoothed_tr[valid_tr]
    minus_di[valid_tr] = 100.0 * smoothed_minus[valid_tr] / smoothed_tr[valid_tr]

    dx = np.full(size, np.nan)
    di_sum = plus_di + minus_di
    valid_dx = np.isfinite(di_sum) & (di_sum > 0)
    dx[valid_dx] = 100.0 * np.abs(plus_di[valid_dx] - minus_di[valid_dx]) / di_sum[valid_dx]
    # No directional movement is a valid zero-strength observation, not missing data.
    zero_direction = np.isfinite(smoothed_tr) & (smoothed_tr > 0) & np.isfinite(di_sum) & (di_sum == 0)
    dx[zero_direction] = 0.0

    adx = np.full(size, np.nan)
    first_adx = 2 * period - 1
    if size > first_adx:
        seed = dx[period : first_adx + 1]
        if np.isfinite(seed).all():
            adx[first_adx] = float(np.mean(seed))
            for i in range(first_adx + 1, size):
                if np.isfinite(dx[i]) and np.isfinite(adx[i - 1]):
                    adx[i] = ((adx[i - 1] * (period - 1)) + dx[i]) / period

    return pd.DataFrame(
        {"plus_di": plus_di, "minus_di": minus_di, "dx": dx, "adx": adx},
        index=high.index,
    )
