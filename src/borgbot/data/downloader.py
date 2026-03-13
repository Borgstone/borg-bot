import argparse
import ccxt
import pandas as pd
import os
import time


DATA_DIR = "/app/data"


def download(symbol, timeframe, start, end):

    exchange = ccxt.kucoin()

    since = exchange.parse8601(start)
    end_ts = exchange.parse8601(end)

    all_candles = []

    while since < end_ts:

        candles = exchange.fetch_ohlcv(
            symbol,
            timeframe=timeframe,
            since=since,
            limit=1000,
        )

        if not candles:
            break

        all_candles.extend(candles)

        since = candles[-1][0] + 1

        time.sleep(exchange.rateLimit / 1000)

        print("Downloaded", len(all_candles), "candles")

    df = pd.DataFrame(
        all_candles,
        columns=["timestamp", "open", "high", "low", "close", "volume"],
    )

    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

    return df


def save(symbol, timeframe, df):

    os.makedirs(DATA_DIR, exist_ok=True)

    pair = symbol.replace("/", "")

    path = f"{DATA_DIR}/{pair}_{timeframe}.parquet"

    if os.path.exists(path):

        old = pd.read_parquet(path)

        df = pd.concat([old, df])

        df = df.drop_duplicates("timestamp")

        df = df.sort_values("timestamp")

    df.to_parquet(path)

    print("Saved dataset:", path)


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("--symbol", required=True)
    parser.add_argument("--tf", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)

    args = parser.parse_args()

    df = download(args.symbol, args.tf, args.start, args.end)

    save(args.symbol, args.tf, df)


if __name__ == "__main__":
    main()