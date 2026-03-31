import numpy as np
from dateutil.relativedelta import relativedelta
from borgbot.backtest.engine import BacktestEngine
from borgbot.strategies.sma import SMAStrategy
from borgbot.strategies.rsi import RSIStrategy
from borgbot.strategies.stack import StrategyStack


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

    return configs


def run_backtest(config, candles):
    strategy = build_strategy(config)
    engine = BacktestEngine(strategy=strategy)
    result = engine.run(candles)

    return {
        "roi": float(result["roi_pct"]),
        "drawdown": float(result.get("max_drawdown", 0.0)),
    }


def optimize_on_train(config, train_data):
    grid = generate_grid(config)

    best = None
    best_score = -1e9

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

    print("DEBUG TIMESTAMP TYPE:", candles["timestamp"].dtype)
    print("DEBUG TIMESTAMP SAMPLE:")
    print(candles["timestamp"].head())

    current = start

    folds = []

    while True:
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

        best_config = optimize_on_train(config, train)

        result = run_backtest(best_config, test)

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