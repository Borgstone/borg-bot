import numpy as np
from dateutil.relativedelta import relativedelta

from borgbot.backtest.engine import BacktestEngine
from borgbot.research.horizon import (
    DEFAULT_HORIZONS,
    aggregate_horizon_profiles,
    supported_horizons,
)
from borgbot.research.metrics import (
    aggregate_fold_metrics,
    calculate_max_drawdown,
    normalize_backtest_result,
)
from borgbot.strategies.registry import build_strategy


def generate_grid(config):

    configs = []

    if config["type"] == "sma":

        for fast in range(5, 16):

            for slow in range(20, 51):

                if fast < slow:

                    configs.append(
                        {
                            "type": "sma",
                            "fast": fast,
                            "slow": slow,
                        }
                    )

    elif config["type"] == "rsi":

        for period in range(10, 21):

            configs.append(
                {
                    "type": "rsi",
                    "period": period,
                }
            )

    elif config["type"] == "sma_rsi":

        for fast in range(5, 16):

            for slow in range(20, 51):

                for period in range(10, 21):

                    if fast < slow:

                        configs.append(
                            {
                                "type": "sma_rsi",
                                "fast": fast,
                                "slow": slow,
                                "period": period,
                            }
                        )

    elif config["type"] == "rsi_trend_v2":

        for period in [10, 11, 12]:

            for pullback_low in [30, 35, 40]:

                for pullback_high in [60, 65, 70]:

                    for trend_period in [50, 100]:

                        if (
                            pullback_low
                            < pullback_high
                        ):

                            configs.append(
                                {
                                    "type": "rsi_trend_v2",
                                    "period": period,
                                    "pullback_low": pullback_low,
                                    "pullback_high": pullback_high,
                                    "trend_period": trend_period,
                                }
                            )

    return configs


def run_backtest(
    config,
    candles,
):

    strategy = build_strategy(
        config
    )

    engine = BacktestEngine(
        strategy=strategy
    )

    result = engine.run(
        candles
    )

    raw_drawdown = result.get(
        "max_drawdown",
        0.0,
    )

    result = normalize_backtest_result(
        result
    )

    return {
        # -------------------------
        # Equity
        # -------------------------

        "equity_curve": result[
            "equity_curve"
        ],

        "final_equity": result[
            "final_equity"
        ],

        # -------------------------
        # Returns / risk
        # -------------------------

        "roi": result[
            "roi"
        ],

        "drawdown": float(
            raw_drawdown
        ),

        # -------------------------
        # Trade economics
        # -------------------------

        "gross_profit": result[
            "gross_profit"
        ],

        "gross_loss": result[
            "gross_loss"
        ],

        "winning_trades": result[
            "winning_trades"
        ],

        "losing_trades": result[
            "losing_trades"
        ],

        "trades": result[
            "trades"
        ],
    }


def optimize_on_train(
    config,
    train_data,
):

    grid = generate_grid(
        config
    )

    # Legacy research limit.
    # This will be redesigned separately.
    grid = grid[:10]

    best = None
    best_score = float("-inf")

    for cfg in grid:

        result = run_backtest(
            cfg,
            train_data,
        )

        score = (
            result["roi"]
            - (
                result["drawdown"]
                * 100
            )
        )

        if score > best_score:

            best_score = score
            best = cfg

    return best


def run_walkforward(
    config,
    candles,
    train_months,
    test_months,
    timeframe=None,
):

    start = candles[
        "timestamp"
    ].min()

    end = candles[
        "timestamp"
    ].max()

    print(
        candles[
            "timestamp"
        ].head()
    )

    current = start

    folds = []

    fold_count = 0

    while True:

        fold_count += 1

        # Keep the current VPS validation scope.
        if fold_count > 3:
            break

        train_end = (
            current
            + relativedelta(
                months=train_months
            )
        )

        test_end = (
            train_end
            + relativedelta(
                months=test_months
            )
        )

        if test_end > end:
            break

        train = candles[
            candles["timestamp"]
            < train_end
        ]

        test = candles[
            (
                candles["timestamp"]
                >= train_end
            )
            & (
                candles["timestamp"]
                < test_end
            )
        ]

        print(
            f"DEBUG SPLIT → Train: "
            f"{len(train)} | "
            f"Test: {len(test)} | "
            f"TrainEnd: {train_end} | "
            f"TestEnd: {test_end}"
        )

        if (
            len(train) < 100
            or len(test) < 50
        ):

            current += relativedelta(
                months=test_months
            )

            continue

        result = run_backtest(
            config,
            test,
        )

        result["timestamps"] = (
            test["timestamp"]
            .tolist()
        )

        folds.append(
            result
        )

        current += relativedelta(
            months=test_months
        )

    if not folds:
        return None

    metrics = aggregate_fold_metrics(
        folds
    )

    if timeframe is None:

        horizon_list = (
            DEFAULT_HORIZONS
        )

    else:

        horizon_list = supported_horizons(
            timeframe
        )

    horizon_profile = (
        aggregate_horizon_profiles(
            folds,
            horizons=horizon_list,
        )
    )

    return {
        "folds": folds,
        "metrics": metrics,
        "horizon_profile": horizon_profile,
    }
