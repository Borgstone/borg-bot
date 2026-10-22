import pandas as pd

from borgbot.indicators.sma import sma
from borgbot.indicators.rsi import rsi
from borgbot.indicators.atr import atr


def build_indicator_cache(df, sma_periods=None):
    """Build cached indicators, optionally limiting SMA periods to those needed."""
    cache = df.copy()

    periods = range(5, 201) if sma_periods is None else tuple(sorted(set(sma_periods)))
    if any(period < 1 for period in periods):
        raise ValueError("SMA periods must be positive integers")

    sma_cols = {
        f"sma_{period}": sma(cache["close"], period)
        for period in periods
    }

    rsi_cols = {
        f"rsi_{period}": rsi(cache["close"], period)
        for period in range(10, 21)
    }

    atr_col = {
        "atr_14": atr(
            cache["high"],
            cache["low"],
            cache["close"],
            14,
        )
    }

    indicators = pd.DataFrame(
        {
            **sma_cols,
            **rsi_cols,
            **atr_col,
        }
    )

    cache = pd.concat(
        [cache, indicators],
        axis=1,
    )

    return cache