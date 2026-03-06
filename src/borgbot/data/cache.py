import os
import pandas as pd


DATA_DIR = "/app/data"


def _path(symbol: str, timeframe: str):
    sym = symbol.replace("/", "")
    path = os.path.join(DATA_DIR, sym)
    os.makedirs(path, exist_ok=True)
    return os.path.join(path, f"{timeframe}.parquet")


def load_cache(symbol: str, timeframe: str):
    path = _path(symbol, timeframe)
    if os.path.exists(path):
        return pd.read_parquet(path)
    return None


def save_cache(symbol: str, timeframe: str, df):
    path = _path(symbol, timeframe)
    df.to_parquet(path, index=False)


def append_cache(symbol: str, timeframe: str, df):
    existing = load_cache(symbol, timeframe)
    if existing is None:
        save_cache(symbol, timeframe, df)
        return

    combined = pd.concat([existing, df])
    combined = combined.drop_duplicates(subset=["timestamp"]).sort_values("timestamp")

    save_cache(symbol, timeframe, combined)