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
GLOBAL_TIMEFRAME = None


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
        return max(
            1,
            int(cpu * 0.7),
        )

    if mode == "max":
        return max(
            1,
            cpu - 1,
        )

    return 1


# ---------------------------
# INIT WORKER
# ---------------------------

def init_worker(
    candles,
    timeframe,
):

    global GLOBAL_CANDLES
    global GLOBAL_TIMEFRAME

    GLOBAL_CANDLES = candles
    GLOBAL_TIMEFRAME = timeframe


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
    global GLOBAL_TIMEFRAME

    wf = run_walkforward(
        config=config,
        candles=GLOBAL_CANDLES,
        train_months=12,
        test_months=3,
        timeframe=GLOBAL_TIMEFRAME,
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

        # Current selector compatibility.
        # "roi" remains the fold median.
        "roi": metrics["roi_median"],

        "drawdown": metrics["drawdown_max"],

        "roi_std": metrics["roi_std"],

        # Explicit return views.
        "roi_mean": metrics["roi_mean"],
        "roi_median": metrics["roi_median"],
        "roi_compounded": metrics["roi_compounded"],

        # Aggregate trade economics.
        "profit_factor": metrics["profit_factor"],
        "win_rate": metrics["win_rate"],
        "avg_trade": metrics["avg_trade"],

        "trades": metrics["trades"],
        "winning_trades": metrics["winning_trades"],
        "losing_trades": metrics["losing_trades"],

        "gross_profit": metrics["gross_profit"],
        "gross_loss": metrics["gross_loss"],

        # Consistency.
        "folds": metrics["folds"],
        "positive_folds": metrics["positive_folds"],
        "positive_fold_ratio": metrics[
            "positive_fold_ratio"
        ],

        # Horizon behavior.
        "horizon_profile": wf[
            "horizon_profile"
        ],

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
            trades INTEGER,
            roi_mean REAL,
            roi_median REAL,
            roi_compounded REAL,
            winning_trades INTEGER,
            losing_trades INTEGER,
            gross_profit REAL,
            gross_loss REAL,
            folds INTEGER,
            positive_folds INTEGER,
            positive_fold_ratio REAL,
            horizon_profile TEXT
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
        "roi_mean": "REAL",
        "roi_median": "REAL",
        "roi_compounded": "REAL",
        "winning_trades": "INTEGER",
        "losing_trades": "INTEGER",
        "gross_profit": "REAL",
        "gross_loss": "REAL",
        "folds": "INTEGER",
        "positive_folds": "INTEGER",
        "positive_fold_ratio": "REAL",
        "horizon_profile": "TEXT",
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
                    trades,
                    roi_mean,
                    roi_median,
                    roi_compounded,
                    winning_trades,
                    losing_trades,
                    gross_profit,
                    gross_loss,
                    folds,
                    positive_folds,
                    positive_fold_ratio,
                    horizon_profile
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?
                )
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
                    r["roi_mean"],
                    r["roi_median"],
                    r["roi_compounded"],
                    r["winning_trades"],
                    r["losing_trades"],
                    r["gross_profit"],
                    r["gross_loss"],
                    r["folds"],
                    r["positive_folds"],
                    r["positive_fold_ratio"],
                    json.dumps(
                        r["horizon_profile"],
                        separators=(
                            ",",
                            ":",
                        ),
                    ),
                ),
            )

        conn.commit()

    finally:

        conn.close()


# ---------------------------
# OUTPUT
# ---------------------------

def print_horizon_profile(
    profile,
):

    if not profile:
        return

    print(
        "
Deployment horizon profile:"
    )

    for horizon, metrics in profile.items():

        observations = metrics[
            "observations"
        ]

        if observations == 0:

            print(
                f"  {horizon}: "
                "no observations"
            )

            continue

        print(
            f"  {horizon}: "
            f"median {metrics['median_return_pct']:+.2f}% | "
            f"mean {metrics['mean_return_pct']:+.2f}% | "
            f"positive {metrics['positive_window_ratio'] * 100:.1f}% | "
            f"best {metrics['best_return_pct']:+.2f}% | "
            f"worst {metrics['worst_return_pct']:+.2f}% | "
            f"n={observations}"
        )


def print_strategy(
    r,
):

    print(
        f"{r['config']} "
        f"ROI median {r['roi_median']:.2f}% "
        f"ROI mean {r['roi_mean']:.2f}% "
        f"ROI compounded {r['roi_compounded']:.2f}% "
        f"DD {r['drawdown']:.2f} "
        f"STD {r['roi_std']:.2f} "
        f"PF {r['profit_factor']:.2f} "
        f"WR {r['win_rate']:.2f}% "
        f"AvgTrade {r['avg_trade']:.3f}% "
        f"Trades {r['trades']} "
        f"PositiveFolds "
        f"{r['positive_folds']}/{r['folds']} "
        f"Score {r['score']:.2f}"
    )


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

        init_worker(
            candles,
            args.tf,
        )

        results = [
            run_task(config)
            for config in configs
        ]

    else:

        with Pool(
            workers,
            initializer=init_worker,
            initargs=(
                candles,
                args.tf,
            ),
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

        print_strategy(r)

        print_horizon_profile(
            r["horizon_profile"]
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

        print_strategy(r)

    # -------------------------
    # SAVE
    # -------------------------

    save_results(
        results,
        args.symbol,
        args.tf,
    )


if __name__ == "__main__":
    main()
