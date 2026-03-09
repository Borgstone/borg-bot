import argparse

from borgbot.data.loader import load_data
from borgbot.backtest.engine import BacktestEngine
from borgbot.core.engine import TradingEngine
from borgbot.execution.paper import PaperExecutionAdapter
from borgbot.risk.fixed_fraction import FixedFractionSizing
from borgbot.strategies.sma import SMAStrategy
from borgbot.strategies.rsi import RSIStrategy


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("--symbol", required=True)
    parser.add_argument("--tf", required=True)
    parser.add_argument("--from_date", required=True)
    parser.add_argument("--to_date", required=True)

    args = parser.parse_args()

    data = load_data(
        args.symbol,
        args.tf,
        args.from_date,
        args.to_date,
    )

    strategy = SMAStrategy(9, 21)

    risk = FixedFractionSizing(
        max_position_frac=0.1,
        min_cash_buffer_frac=0.1,
    )

    execution = PaperExecutionAdapter()

    engine = TradingEngine(strategy, risk, execution)

    backtest = BacktestEngine(engine, data)

    equity = backtest.run()

    print(equity.tail())


if __name__ == "__main__":
    main()