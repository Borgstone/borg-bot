import ccxt
import pandas as pd
import os
import time


DATA_DIR = "/app/data"


def sync(symbol, timeframe):

    exchange = ccxt.kucoin()

    pair = symbol.replace("/", "")

    path = f"{DATA_DIR}/{pair}_{timeframe}.parquet"

    df = pd.read_parquet(path)

    last_ts = int(df["timestamp"].max().timestamp() * 1000)

    candles = exchange.fetch_ohlcv(
        symbol,
        timeframe=timeframe,
        since=last_ts,
        limit=1000,
    )

    if not candles:
        return

    new = pd.DataFrame(
        candles,
        columns=["timestamp", "open", "high", "low", "close", "volume"],
    )

    new["timestamp"] = pd.to_datetime(new["timestamp"], unit="ms")

    df = pd.concat([df, new])

    df = df.drop_duplicates("timestamp")

    df = df.sort_values("timestamp")

    df.to_parquet(path)

    print("Dataset updated")


def main():

    while True:

        sync("BTC/USDT", "5m")

        time.sleep(3600)


if __name__ == "__main__":
    main()