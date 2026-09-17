import argparse
import datetime
import json
import os
import sqlite3
import uuid
from multiprocessing import Pool

from borgbot.data.loader import load_data
from borgbot.data.indicator_cache import build_indicator_cache
from borgbot.research.walkforward_core import run_walkforward
from borgbot.research.selector import select_strategies


SCORING_MODE = "balanced"

DB_PATH = "/app/research/research.db"

GLOBAL_CANDLES = None


# ---------------------------
# RESOURCE CONTROL
# ---------------------------

def resolve_workers(mode: str) -> int:

    cpu = os.cpu_count() or 1

    if mode == "low":
        return 1

    if mode == "medium":
        return min(4, cpu)

    if mode == "high":
        return max(1, int(cpu * 0.7))

    if mode == "max":
        return max(1, cpu - 1)

    return 1


# ---------------------------
# INIT WORKER
# ---------------------------

def init_worker(candles):

    global GLOBAL_CANDLES

    GLOBAL_CANDLES = candles


# ---------------------------
# SCORING
# ---------------------------

def score_walkforward(
    metrics,
    mode="balanced",
):

    roi = metrics["roi_median"]
    dd = metrics["drawdown_max"]
    std = metrics["roi_std"]

    if mode == "conservative":

        return (
            roi
            - (dd * 40)
            - (std * 0.5)
        )

    if mode == "balanced":

        return (
            roi
            - (dd * 25)
            - (std * 0.25)
        )

    if mode == "aggressive":

        return (
            roi
            - (dd * 10)
            - (std * 0.10)
        )

    return (
        roi
        - (dd * 25)
        - (std * 0.25)
    )


# ---------------------------
# SINGLE RUN
# ---------------------------

def run_task(config):

    print(
        f"Running config: {config}"
    )

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

    # Very broad research-stage filter.
    # Tight deployment criteria belong in selector.py.
    if metrics["roi_std"] > 50:
        return None

    score = score_walkforward(
        metrics,
        mode=SCORING_MODE,
    )

    return {
        "config": config,

        "roi": metrics["roi_median"],

        "drawdown": metrics["drawdown_max"],

        "roi_std": metrics["roi_std"],

        "profit_factor": metrics.get(
            "profit_factor_mean",
            0.0,
        ),

        "win_rate": metrics.get(
            "win_rate_mean",
            0.0,
        ),

        "avg_trade": metrics.get(
            "avg_trade_mean",
            0.0,
        ),

        "trades": metrics.get(
            "trades",
            0,
        ),

        "score": score,
    }


# ---------------------------
# DATABASE SCHEMA
# ---------------------------

def ensure_discovery_schema(conn):
    """
    Ensure discovery_results has the current schema.

    Existing databases are migrated in-place by adding any
    missing columns. Existing research data is preserved.
    """

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
            roi_std REAL,
            profit_factor REAL,
            win_rate REAL,
            avg_trade REAL,
            trades INTEGER
        )
        """
    )

    existing_columns = {
        row[1]
        for row in cur.execute(
            "PRAGMA table_info(discovery_results)"
        )
    }

    required_columns = {
        "experiment_id": "TEXT",
        "timestamp": "TEXT",
        "symbol": "TEXT",
        "timeframe": "TEXT",
        "config": "TEXT",
        "roi": "REAL",
        "drawdown": "REAL",
        "score": "REAL",
        "roi_std": "REAL",
        "profit_factor": "REAL",
        "win_rate": "REAL",
        "avg_trade": "REAL",
        "trades": "INTEGER",
    }

    for column, column_type in required_columns.items():

        if column not in existing_columns:

            print(
                f"DB MIGRATION → adding column: {column}"
            )

            cur.execute(
                f"ALTER TABLE discovery_results "
                f"ADD COLUMN {column} {column_type}"
            )

    conn.commit()


# ---------------------------
# SAVE RESULTS
# ---------------------------

def save_results(
    rows,
    symbol,
    timeframe,
):

    os.makedirs(
        "/app/research",
        exist_ok=True,
    )

    conn = sqlite3.connect(
        DB_PATH
    )

    try:

        ensure_discovery_schema(conn)

        cur = conn.cursor()

        experiment_id = str(
            uuid.uuid4()
        )[:8]

        timestamp = (
            datetime.datetime.utcnow()
            .isoformat()
        )

        for r in rows:

            cur.execute(
                """
                INSERT INTO discovery_results (
                    experiment_id,
                    timestamp,
                    symbol,
                    timeframe,
                    config,
                    roi,
                    drawdown,
                    score,
                    roi_std,
                    profit_factor,
                    win_rate,
                    avg_trade,
                    trades
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    experiment_id,
                    timestamp,
                    symbol,
                    timeframe,
                    str(r["config"]),
                    r["roi"],
                    r["drawdown"],
                    r["score"],
                    r["roi_std"],
                    r["profit_factor"],
                    r["win_rate"],
                    r["avg_trade"],
                    r["trades"],
                ),
            )

        conn.commit()

    finally:

        conn.close()


# ---------------------------
# MAIN
# ---------------------------

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--scoring",
        default="balanced",
    )

    parser.add_argument(
        "--symbol",
        required=True,
    )

    parser.add_argument(
        "--tf",
        required=True,
    )

    parser.add_argument(
        "--resources",
        default="low",
    )

    args = parser.parse_args()

    global SCORING_MODE

    SCORING_MODE = args.scoring

    # -------------------------
    # LOAD DATA
    # -------------------------

    candles = load_data(
        symbol=args.symbol,
        timeframe=args.tf,
        start="2022-01-01",
        end="2026-01-01",
    )

    candles = build_indicator_cache(
        candles
    )

    # -------------------------
    # PARAMETER SPACE
    # -------------------------

    configs = []

    for period in range(10, 21):

        for low in [30, 35, 40]:

            for high in [60, 65, 70]:

                for trend in [50, 100]:

                    if low < high:

                        configs.append(
                            {
                                "type": "rsi_trend_v2",
                                "period": period,
                                "pullback_low": low,
                                "pullback_high": high,
                                "trend_period": trend,
                            }
                        )

    # Keep current VPS test limit.
    configs = configs[:50]

    workers = resolve_workers(
        args.resources
    )

    print(
        f"\nRunning {len(configs)} "
        f"strategies with {workers} workers\n"
    )

    # -------------------------
    # EXECUTION
    # -------------------------

    if workers == 1:

        init_worker(candles)

        results = [
            run_task(config)
            for config in configs
        ]

    else:

        with Pool(
            workers,
            initializer=init_worker,
            initargs=(candles,),
        ) as pool:

            results = pool.map(
                run_task,
                configs,
            )

    results = [
        result
        for result in results
        if result is not None
    ]

    # -------------------------
    # SORT
    # -------------------------

    results.sort(
        key=lambda x: x["score"],
        reverse=True,
    )

    # -------------------------
    # SELECT
    # -------------------------

    selected = select_strategies(
        results
    )

    print(
        "\nDeployable strategies:\n"
    )

    for r in selected:

        print(
            f"{r['config']} "
            f"ROI {r['roi']:.2f}% "
            f"DD {r['drawdown']:.2f} "
            f"STD {r['roi_std']:.2f} "
            f"PF {r['profit_factor']:.2f} "
            f"WR {r['win_rate']:.2f}% "
            f"Trades {r['trades']} "
            f"Score {r['score']:.2f}"
        )

    # -------------------------
    # DEPLOYABLE FILE
    # -------------------------

    with open(
        "/app/research/deployable.json",
        "w",
    ) as f:

        json.dump(
            selected,
            f,
            indent=2,
        )

    # -------------------------
    # TOP RESULTS
    # -------------------------

    print(
        "\nTop strategies:\n"
    )

    for r in results[:10]:

        print(
            f"{r['config']} "
            f"ROI {r['roi']:.2f}% "
            f"DD {r['drawdown']:.2f} "
            f"STD {r['roi_std']:.2f} "
            f"PF {r['profit_factor']:.2f} "
            f"WR {r['win_rate']:.2f}% "
            f"Trades {r['trades']} "
            f"Score {r['score']:.2f}"
        )

    save_results(
        results,
        args.symbol,
        args.tf,
    )


if __name__ == "__main__":
    main()