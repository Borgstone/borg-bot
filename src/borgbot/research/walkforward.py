import argparse
import datetime
import sqlite3
import uuid
from dateutil.relativedelta import relativedelta
from borgbot.data.loader import load_data
from borgbot.data.indicator_cache import build_indicator_cache
from borgbot.backtest.engine import BacktestEngine
from borgbot.strategies.sma import SMAStrategy
from borgbot.strategies.rsi import RSIStrategy
from borgbot.strategies.stack import StrategyStack


DB_PATH = "/app/research/research.db"


def month_range(start, end, step):
    current = start
    while current < end:
        yield current
        current += relativedelta(months=step)


def run_backtest(strategy, candles):

    engine = BacktestEngine(strategy=strategy)
    result = engine.run(candles)

    return {
        "roi": float(result["roi_pct"]),
        "drawdown": float(result.get("max_drawdown", 0.0)),
    }


def save_results(rows):

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS walkforward_results (
            experiment_id TEXT,
            timestamp TEXT,
            symbol TEXT,
            timeframe TEXT,
            train_range TEXT,
            test_range TEXT,
            strategies TEXT,
            roi REAL,
            drawdown REAL
        )
    """
    )

    for r in rows:
        cur.execute(
            "INSERT INTO walkforward_results VALUES (?,?,?,?,?,?,?,?,?)",
            (
                r["experiment_id"],
                r["timestamp"],
                r["symbol"],
                r["timeframe"],
                r["train_range"],
                r["test_range"],
                r["strategies"],
                r["roi"],
                r["drawdown"],
            ),
        )

    conn.commit()
    conn.close()


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("--symbol", required=True)
    parser.add_argument("--tf", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--train_months", type=int, default=12)
    parser.add_argument("--test_months", type=int, default=3)

    args = parser.parse_args()

    start = datetime.datetime.fromisoformat(args.start)
    end = datetime.datetime.fromisoformat(args.end)

    experiment_id = str(uuid.uuid4())[:8]
    timestamp = datetime.datetime.utcnow().isoformat()

    strategies = StrategyStack([
        (SMAStrategy({"fast": 9, "slow": 21}), 1.0),
        (RSIStrategy({"period": 14, "overbought": 70, "oversold": 30}), 1.0)
    ])

    rows = []

    for train_start in month_range(start, end, args.test_months):

        train_end = train_start + relativedelta(months=args.train_months)
        test_end = train_end + relativedelta(months=args.test_months)

        if test_end > end:
            break

        candles = load_data(
            symbol=args.symbol,
            timeframe=args.tf,
            start=train_start.isoformat(),
            end=test_end.isoformat(),
        )

        candles = build_indicator_cache(candles)

        train_candles = candles[candles["timestamp"] < train_end]
        test_candles = candles[candles["timestamp"] >= train_end]
        test_result = run_backtest(strategies, test_candles)
        
        rows.append(
            {
                "experiment_id": experiment_id,
                "timestamp": timestamp,
                "symbol": args.symbol,
                "timeframe": args.tf,
                "train_range": f"{train_start}:{train_end}",
                "test_range": f"{train_end}:{test_end}",
                "strategies": "SMA+RSI",
                "roi": test_result["roi"],
                "drawdown": test_result["drawdown"],
            }
        )

        print(
            f"Train {train_start.date()} → {train_end.date()} | "
            f"Test ROI {test_result['roi']:.2f}%"
        )

    save_results(rows)


if __name__ == "__main__":
    main()