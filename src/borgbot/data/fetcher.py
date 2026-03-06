import ccxt
import pandas as pd


def fetch_ohlcv(symbol: str, timeframe: str, since=None, limit=1000, exchange_name="kucoin"):
    exchange_class = getattr(ccxt, exchange_name)
    exchange = exchange_class()

    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=limit)

    df = pd.DataFrame(
        ohlcv,
        columns=["timestamp", "open", "high", "low", "close", "volume"],
    )

    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

    return df