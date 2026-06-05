import pandas as pd

from borgbot.indicators.sma import sma
from borgbot.indicators.rsi import rsi
from borgbot.indicators.atr import atr


def build_indicator_cache(df):

    cache = df.copy()

    # Precompute SMAs
    for period in range(5, 201):
        cache[f"sma_{period}"] = sma(cache["close"], period)

    # Precompute RSI
    for period in range(10, 21):
        cache[f"rsi_{period}"] = rsi(cache["close"], period)
        
    # Precompute ATR
    cache["atr_14"] = atr(
    cache["high"],
    cache["low"],
    cache["close"],
    14,
    )

    return cache