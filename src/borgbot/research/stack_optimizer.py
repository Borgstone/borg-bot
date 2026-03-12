import argparse
import itertools
import multiprocessing
import sqlite3
from pathlib import Path

from borgbot.backtest.engine import BacktestEngine
from borgbot.data.loader import load_data

from borgbot.strategies.sma import SMAStrategy
from borgbot.strategies.rsi import RSIStrategy
from borgbot.strategies.stack import StrategyStack


DB_PATH = "/app/research/research.db"


def score_strategy(roi, drawdown):
    """
    Stability-first scoring.
    Higher ROI good.
    Lower drawdown good.
    """
    return (roi * 100) - (drawdown * 50)


def run_backtest(args):
    strategies, candles = args

    stack = StrategyStack([(s, 1.0) for s in strategies])
    engine = BacktestEngine(strategy=stack)

    results = engine.run(candles)

    roi = float(results["roi_pct"])
    dd = float(results.get("max_drawdown", 0.0))

    return {
        "strategies": ",".join([s.__class__.__name__ for s in strategies]),
        "roi": roi,
        "drawdown": dd,
        "score": score_strategy(roi, dd),
    }


def resource_workers(level):
    cpu = multiprocessing.cpu_count()

    if level == "low":
        return 1
    if level == "medium":
        return max(1, cpu // 2)
    if level == "high":
        return max(1, int(cpu * 0.75))
    if level == "max":
        return max(1, cpu - 1)

    return 1


def save_results(results):

    Path("/app/research").mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS stack_results (
            strategies TEXT,
            roi REAL,
            drawdown REAL,
            score REAL
        )
        """
    )

    for r in results:
        cur.execute(
            "INSERT INTO stack_results VALUES (?,?,?,?)",
            (r["strategies"], r["roi"], r["drawdown"], r["score"]),
        )

    conn.commit()
    conn.close()


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("--symbol", required=True)
    parser.add_argument("--tf", required=True)
    parser.add_argument("--from_date", required=True)
    parser.add_argument("--to_date", required=True)
    parser.add_argument("--resources", default="low")

    args = parser.parse_args()

    candles = load_data(
    args.symbol,
    args.tf,
    args.from_date,
    args.to_date,
    )

    strategies = [
        SMAStrategy({"fast": 9, "slow": 21}),
        RSIStrategy({"period": 14, "overbought": 70, "oversold": 30}),
    ]

    combinations = []

    for r in range(1, len(strategies) + 1):
        combinations.extend(itertools.combinations(strategies, r))

    workers = resource_workers(args.resources)

    print(f"\nTesting {len(combinations)} strategy combinations")
    print(f"Workers: {workers}\n")

    pool = multiprocessing.Pool(workers)

    tasks = [(combo, candles) for combo in combinations]

    results = pool.map(run_backtest, tasks)

    results = sorted(results, key=lambda x: x["score"], reverse=True)

    save_results(results)

    print("Top strategies\n")

    for r in results[:10]:
        print(
            f"{r['strategies']} ROI {r['roi']:.2f}% DD {r['drawdown']:.2f} Score {r['score']:.2f}"
        )


if __name__ == "__main__":
    main()