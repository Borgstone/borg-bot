import os
import pandas as pd
from .fetcher import fetch_ohlcv


def load_data(symbol: str, timeframe: str, start: str, end: str):

    symbol_clean = symbol.replace("/", "")
    path = f"/app/data/{symbol_clean}_{timeframe}.parquet"

    os.makedirs("/app/data", exist_ok=True)

    if not os.path.exists(path):
        print(f"Downloading {symbol} {timeframe} candles...")
        df = fetch_ohlcv(symbol, timeframe)
        df.to_parquet(path)
        print(f"Saved to {path}")

    else:
        df = pd.read_parquet(path)
        df["timestamp"] = pd.to_datetime(df["timestamp"])

    df["timestamp"] = pd.to_datetime(df["timestamp"])

    start = pd.to_datetime(start)
    end = pd.to_datetime(end)

    filtered = df[(df["timestamp"] >= start) & (df["timestamp"] <= end)]

    # fallback if range empty
    if filtered.empty:
        print("WARNING: Requested range has no candles. Using full dataset instead.")
        filtered = df

    return filtered.reset_index(drop=True)