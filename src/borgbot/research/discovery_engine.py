import argparse
import itertools
import sqlite3
import uuid
import datetime
import os
from multiprocessing import Pool

from borgbot.data.loader import load_data
from borgbot.data.indicator_cache import build_indicator_cache
from borgbot.backtest.engine import BacktestEngine
from borgbot.strategies.sma import SMAStrategy
from borgbot.strategies.rsi import RSIStrategy
from borgbot.strategies.stack import StrategyStack


DB_PATH = "/app/research/research.db"


# ---------------------------
# RESOURCE CONTROL
# ---------------------------
def resolve_workers(mode: str) -> int:
    cpu = os.cpu_count() or 1

    if mode == "low":
        return 1
    elif mode == "medium":
        return min(4, cpu)
    elif mode == "high":
        return max(1, int(cpu * 0.7))
    elif mode == "max":
        return max(1, cpu - 1)
    else:
        return 1


# ---------------------------
# STRATEGY FACTORY
# ---------------------------
def build_strategy(config):
    strategies = []

    if config["type"] == "sma":
        strategies.append(
            (SMAStrategy({"fast": config["fast"], "slow": config["slow"]}), 1.0)
        )

    elif config["type"] == "rsi":
        strategies.append(
            (RSIStrategy({"period": config["period"]}), 1.0)
        )

    elif config["type"] == "sma_rsi":
        strategies.append(
            (SMAStrategy({"fast": config["fast"], "slow": config["slow"]}), 0.5)
        )
        strategies.append(
            (RSIStrategy({"period": config["period"]}), 0.5)
        )

    return StrategyStack(strategies)


# ---------------------------
# SCORING FUNCTION (risk-first)
# ---------------------------
def score_result(roi, drawdown):
    return roi - (drawdown * 100)  # penalize drawdown heavily


# ---------------------------
# SINGLE RUN
# ---------------------------
def run_task(args):
    config, candles = args

    strategy = build_strategy(config)

    engine = BacktestEngine(strategy=strategy)
    result = engine.run(candles)

    roi = float(result["roi_pct"])
    dd = float(result.get("max_drawdown", 0.0))

    return {
        "config": config,
        "roi": roi,
        "drawdown": dd,
        "score": score_result(roi, dd),
    }


# ---------------------------
# SAVE RESULTS
# ---------------------------
def save_results(rows, symbol, timeframe):

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS discovery_results (
            experiment_id TEXT,
            timestamp TEXT,
            symbol TEXT,
            timeframe TEXT,
            config TEXT,
            roi REAL,
            drawdown REAL,
            score REAL
        )
    """
    )

    experiment_id = str(uuid.uuid4())[:8]
    timestamp = datetime.datetime.utcnow().isoformat()

    for r in rows:
        cur.execute(
            "INSERT INTO discovery_results VALUES (?,?,?,?,?,?,?,?)",
            (
                experiment_id,
                timestamp,
                symbol,
                timeframe,
                str(r["config"]),
                r["roi"],
                r["drawdown"],
                r["score"],
            ),
        )

    conn.commit()
    conn.close()


# ---------------------------
# MAIN
# ---------------------------
def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("--symbol", required=True)
    parser.add_argument("--tf", required=True)
    parser.add_argument("--resources", default="low")

    args = parser.parse_args()

    # LOAD DATA
    candles = load_data(
        symbol=args.symbol,
        timeframe=args.tf,
        start="2022-01-01",
        end="2026-01-01",
    )

    candles = build_indicator_cache(candles)

    # PARAMETER SPACE
    configs = []

    # SMA
    for fast in range(5, 16):
        for slow in range(20, 51):
            if fast < slow:
                configs.append({
                    "type": "sma",
                    "fast": fast,
                    "slow": slow,
                })

    # RSI
    for period in range(10, 21):
        configs.append({
            "type": "rsi",
            "period": period,
        })

    # SMA + RSI
    for fast in range(5, 16):
        for slow in range(20, 51):
            for period in range(10, 21):
                if fast < slow:
                    configs.append({
                        "type": "sma_rsi",
                        "fast": fast,
                        "slow": slow,
                        "period": period,
                    })

    workers = resolve_workers(args.resources)

    print(f"\nRunning {len(configs)} strategies with {workers} workers\n")

    tasks = [(cfg, candles) for cfg in configs]

    if workers == 1:
        results = [run_task(t) for t in tasks]
    else:
        with Pool(workers) as pool:
            results = pool.map(run_task, tasks)

    # SORT
    results.sort(key=lambda x: x["score"], reverse=True)

    print("\nTop strategies:\n")

    for r in results[:10]:
        print(
            f"{r['config']} ROI {r['roi']:.2f}% "
            f"DD {r['drawdown']:.2f} "
            f"Score {r['score']:.2f}"
        )

    save_results(results, args.symbol, args.tf)


if __name__ == "__main__":
    main()