import argparse
import os
from concurrent.futures import ProcessPoolExecutor
from borgbot.data.indicator_cache import build_indicator_cache
from borgbot.data.loader import load_data
from borgbot.backtest.engine import BacktestEngine
from borgbot.strategies.sma import SMAStrategy

from .grid import generate_sma_grid
from .store import (
    init_db,
    create_experiment,
    insert_result,
    complete_experiment,
)
from .ranking import compute_score


def resolve_workers(resource_mode, explicit_workers):

    if explicit_workers:
        return explicit_workers

    cpu = os.cpu_count()

    mapping = {
        "low": 1,
        "medium": min(2, cpu),
        "high": min(4, cpu),
        "max": max(1, cpu - 1),
    }

    return mapping.get(resource_mode, 1)


def run_single(combo, candles):

    strategy = SMAStrategy({
        "fast": combo["fast"],
        "slow": combo["slow"]
    })

    engine = BacktestEngine(strategy=strategy)

    result = engine.run(candles)

    roi = result["roi_pct"]
    trades = result["trades"]

    # drawdown placeholder (phase 5 will compute real one)
    drawdown = abs(roi) * 0.5

    score = compute_score(roi, drawdown)

    return {
        "fast": combo["fast"],
        "slow": combo["slow"],
        "roi": roi,
        "drawdown": drawdown,
        "trades": trades,
        "score": score,
    }


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("--symbol", required=True)
    parser.add_argument("--tf", required=True)

    parser.add_argument("--strategy", default="sma")
    parser.add_argument("--fast", default="5:20")
    parser.add_argument("--slow", default="20:100")

    parser.add_argument("--resources", default="low")
    parser.add_argument("--workers", type=int)

    args = parser.parse_args()

    init_db()

    candles = load_data(...)
    candles = build_indicator_cache(candles)

    combos = generate_sma_grid(args.fast, args.slow)

    workers = resolve_workers(args.resources, args.workers)

    print(f"Running {len(combos)} strategies with {workers} workers")

    exp_id = create_experiment(args.symbol, args.tf, args.strategy)

    results = []

    with ProcessPoolExecutor(max_workers=workers) as executor:

        futures = [
            executor.submit(run_single, combo, candles)
            for combo in combos
        ]

        for f in futures:
            r = f.result()

            insert_result(
                exp_id,
                r["fast"],
                r["slow"],
                r["roi"],
                r["drawdown"],
                r["trades"],
                r["score"],
            )

            results.append(r)

    complete_experiment(exp_id)

    top = sorted(results, key=lambda x: x["score"], reverse=True)[:10]

    print("\nTop strategies\n")

    for r in top:
        print(
            f"FAST {r['fast']}  SLOW {r['slow']} "
            f"ROI {r['roi']}%  DD {r['drawdown']}  Score {r['score']}"
        )


if __name__ == "__main__":
    main()