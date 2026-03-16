import argparse
from borgbot.data.loader import load_data
from borgbot.backtest.engine import BacktestEngine
from borgbot.strategies.sma import SMAStrategy
from borgbot.data.indicator_cache import build_indicator_cache

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("--symbol", required=True)
    parser.add_argument("--tf", required=True)
    parser.add_argument("--from_date", required=True)
    parser.add_argument("--to_date", required=True)

    args = parser.parse_args()

    # load historical candles
    candles = load_data(
        symbol=args.symbol,
        timeframe=args.tf,
        start=args.from_date,
        end=args.to_date
    )

    # create strategy
    strategy = SMAStrategy({
        "fast": 9,
        "slow": 21
    })

    # run backtest
    engine = BacktestEngine(strategy=strategy)

    results = engine.run(candles)

    print("Backtest finished")
    print(results)


if __name__ == "__main__":
    main()