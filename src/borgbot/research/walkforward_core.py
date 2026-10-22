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
from borgbot.research.regime_analysis import (
    DEFAULT_MIN_REGIME_TRADES,
    aggregate_regime_profiles,
    annotate_entry_regimes,
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
    backtest_config=None,
):

    strategy = build_strategy(
        config
    )

    engine = BacktestEngine(
        strategy=strategy,
        config=backtest_config,
    )

    raw_result = engine.run(
        candles
    )

    raw_drawdown = raw_result.get(
        "max_drawdown",
        0.0,
    )
    trade_log = raw_result.get("trade_log", [])

    result = normalize_backtest_result(
        raw_result
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

        "trade_log": trade_log,
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
    context_timeframe=None,
    regime_min_trades=DEFAULT_MIN_REGIME_TRADES,
    backtest_config=None,
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

        # The training frame is not used by the current discovery process;
        # count its rows without materializing a wide copy of the cached candles.
        train_count = int((candles["timestamp"] < train_end).sum())

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
            f"{train_count} | "
            f"Test: {len(test)} | "
            f"TrainEnd: {train_end} | "
            f"TestEnd: {test_end}"
        )

        if (
            train_count < 100
            or len(test) < 50
        ):

            current += relativedelta(
                months=test_months
            )

            continue

        result = run_backtest(
            config,
            test,
            backtest_config=backtest_config,
        )

        result["timestamps"] = (
            test["timestamp"]
            .tolist()
        )

        result["regime_trades"] = annotate_entry_regimes(
            result.get("trade_log", []),
            test,
            fold_number=len(folds) + 1,
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

    regime_profile = None
    if {"local_regime", "higher_regime"}.issubset(candles.columns):
        regime_profile = aggregate_regime_profiles(
            folds,
            min_trades=regime_min_trades,
        )
        regime_profile["base_timeframe"] = timeframe
        regime_profile["higher_timeframe"] = context_timeframe

    return {
        "folds": folds,
        "metrics": metrics,
        "horizon_profile": horizon_profile,
        "regime_profile": regime_profile,
    }
