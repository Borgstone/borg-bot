import pandas as pd
from .fetcher import fetch_ohlcv
from .cache import load_cache, append_cache


def load_data(symbol, timeframe, start=None, end=None, exchange="kucoin"):

    df = load_cache(symbol, timeframe)

    if df is None:
        df = fetch_ohlcv(symbol, timeframe, exchange_name=exchange)
        append_cache(symbol, timeframe, df)
        df = load_cache(symbol, timeframe)

    if start:
        df = df[df["timestamp"] >= pd.to_datetime(start)]

    if end:
        df = df[df["timestamp"] <= pd.to_datetime(end)]

    return df.reset_index(drop=True)