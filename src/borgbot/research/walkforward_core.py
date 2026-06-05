import numpy as np
from dateutil.relativedelta import relativedelta
from borgbot.backtest.engine import BacktestEngine
from borgbot.strategies.rsi_trend_v2 import RSITrendV2Strategy 
# Legacy strategies (Session 2 archive)
# from borgbot.strategies.sma import SMAStrategy
# from borgbot.strategies.rsi import RSIStrategy
# from borgbot.strategies.stack import StrategyStack

def build_strategy(config):

    if config["type"] == "rsi_trend_v2":

        return RSITrendV2Strategy({
            "period": config["period"],
            "pullback_low": config["pullback_low"],
            "pullback_high": config["pullback_high"],
            "trend_period": config["trend_period"],
        })

    raise ValueError(
        f"Unsupported strategy type: {config['type']}"
    )

def generate_grid(config):
    configs = []

    if config["type"] == "sma":
        for fast in range(5, 16):
            for slow in range(20, 51):
                if fast < slow:
                    configs.append({
                        "type": "sma",
                        "fast": fast,
                        "slow": slow,
                    })

    elif config["type"] == "rsi":
        for period in range(10, 21):
            configs.append({
                "type": "rsi",
                "period": period,
            })

    elif config["type"] == "sma_rsi":
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


    elif config["type"] == "rsi_trend_v2":

        for period in [10, 11, 12]:
            for pullback_low in [30, 35, 40]:
                for pullback_high in [60, 65, 70]:
                    for trend_period in [50, 100]:

                        configs.append({
                            "type": "rsi_trend_v2",
                            "period": period,
                            "pullback_low": pullback_low,
                            "pullback_high": pullback_high,
                            "trend_period": trend_period,
                        })

    return configs


def run_backtest(config, candles):
    strategy = build_strategy(config)
    engine = BacktestEngine(strategy=strategy)
    result = engine.run(candles)

    return {
        "roi": float(result.get("roi_pct", result.get("roi", 0))),
        "drawdown": float(result.get("max_drawdown", 0.0)),
    }


def optimize_on_train(config, train_data):
    grid = generate_grid(config)
    grid = grid[:10]  # LIMIT FOR VPS

    best = None
    best_score = float("-inf")

    for cfg in grid:
        result = run_backtest(cfg, train_data)

        score = result["roi"] - (result["drawdown"] * 100)

        if score > best_score:
            best_score = score
            best = cfg
    
    return best


def run_walkforward(config, candles, train_months, test_months):

    start = candles["timestamp"].min()
    end = candles["timestamp"].max()

    print(candles["timestamp"].head())

    current = start

    folds = []

    fold_count = 0

    while True:
        fold_count += 1
        if fold_count > 3:
            break

        train_end = current + relativedelta(months=train_months)
        test_end = train_end + relativedelta(months=test_months)

        if test_end > end:
            break

        train = candles[candles["timestamp"] < train_end]
        test = candles[
            (candles["timestamp"] >= train_end) &
            (candles["timestamp"] < test_end)
        ]
        print(
            f"DEBUG SPLIT → Train: {len(train)} | Test: {len(test)} | "
            f"TrainEnd: {train_end} | TestEnd: {test_end}"
        )

        if len(train) < 100 or len(test) < 50:
            current += relativedelta(months=test_months)
            continue

        result = run_backtest(config, test)

        folds.append(result)

        current += relativedelta(months=test_months)

    if not folds:
        return None

    rois = [f["roi"] for f in folds]
    dds = [f["drawdown"] for f in folds]

    return {
        "folds": folds,
        "metrics": {
            "roi_mean": float(np.mean(rois)),
            "roi_median": float(np.median(rois)),
            "roi_std": float(np.std(rois)),
            "drawdown_max": float(np.max(dds)),
        }
    }