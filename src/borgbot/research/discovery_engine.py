import argparse
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
from borgbot.research.walkforward_core import run_walkforward

SCORING_MODE = "balanced"

DB_PATH = "/app/research/research.db"

# Shared across workers
GLOBAL_CANDLES = None


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
# INIT WORKER (memory fix)
# ---------------------------
def init_worker(candles):
    global GLOBAL_CANDLES
    GLOBAL_CANDLES = candles


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
# SCORING FUNCTION
# ---------------------------
def score_result(roi, drawdown):
    return roi - (drawdown * 100)


# ---------------------------
# SINGLE RUN
# ---------------------------
def score_walkforward(metrics, mode="balanced"):
    roi = metrics["roi_median"]
    dd = metrics["drawdown_max"]
    std = metrics["roi_std"]

    # Normalize components
    dd_penalty = dd * 50        # was 100
    std_penalty = std * 2       # was 25 (WAY too aggressive)

    if mode == "conservative":
        return roi - (dd * 100) - (std * 5)

    elif mode == "balanced":
        return roi - dd_penalty - std_penalty

    elif mode == "aggressive":
        return roi - (dd * 25) - (std * 1)

    return roi - dd_penalty - std_penalty


def run_task(config):
    print(f"Running config: {config}")
    global GLOBAL_CANDLES

    wf = run_walkforward(
        config=config,
        candles=GLOBAL_CANDLES,
        train_months=12,
        test_months=3,
    )

    if wf is None:
        return None

    metrics = wf["metrics"]
    # 🚨 FILTER BAD STRATEGIES
    if metrics["roi_std"] > 10:
    return None

    score = score_walkforward(metrics, mode=SCORING_MODE)

    return {
        "config": config,
        "roi": metrics["roi_median"],
        "drawdown": metrics["drawdown_max"],
        "score": score,
        "roi_std": metrics["roi_std"],
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
            score REAL,
            roi_std REAL
        )
    """
    )

    experiment_id = str(uuid.uuid4())[:8]
    timestamp = datetime.datetime.utcnow().isoformat()

    for r in rows:
        cur.execute(
            "INSERT INTO discovery_results VALUES (?,?,?,?,?,?,?,?,?)",
            (
                experiment_id,
                timestamp,
                symbol,
                timeframe,
                str(r["config"]),
                r["roi"],
                r["drawdown"],
                r["roi_std"],
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
    parser.add_argument("--scoring", default="balanced")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--tf", required=True)
    parser.add_argument("--resources", default="low")

    args = parser.parse_args()

    global SCORING_MODE
    SCORING_MODE = args.scoring

    # LOAD DATA ONCE
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
    
    # LIMIT CONFIGS FOR TESTING
    configs = configs[:5]
    
    workers = resolve_workers(args.resources)

    print(f"\nRunning {len(configs)} strategies with {workers} workers\n")

    # SINGLE THREAD
    if workers == 1:
        init_worker(candles)
        results = [run_task(cfg) for cfg in configs]

    # MULTIPROCESS
    else:
        with Pool(workers, initializer=init_worker, initargs=(candles,)) as pool:
            results = pool.map(run_task, configs)

    results = [r for r in results if r is not None]

    # SORT RESULTS
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