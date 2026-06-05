import pandas as pd

from borgbot.indicators.sma import sma
from borgbot.indicators.rsi import rsi
from borgbot.indicators.atr import atr


def build_indicator_cache(df):

    cache = df.copy()

    sma_cols = {
        f"sma_{period}": sma(cache["close"], period)
        for period in range(5, 201)
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