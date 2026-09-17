import numpy as np
from dateutil.relativedelta import relativedelta

from borgbot.backtest.engine import BacktestEngine
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


def run_backtest(config, candles):

    strategy = build_strategy(
        config
    )

    engine = BacktestEngine(
        strategy=strategy
    )

    result = engine.run(
        candles
    )

    return {
        # -------------------------
        # Equity
        # -------------------------

        "equity_curve": result.get(
            "equity_curve",
            [],
        ),

        "final_equity": float(
            result.get(
                "final_equity",
                1.0,
            )
        ),

        # -------------------------
        # Returns
        # -------------------------

        "roi": float(
            result.get(
                "roi_pct",
                result.get(
                    "roi",
                    0.0,
                ),
            )
        ),

        # -------------------------
        # Risk
        # -------------------------

        "drawdown": float(
            result.get(
                "max_drawdown",
                0.0,
            )
        ),

        # -------------------------
        # Trade economics
        # -------------------------

        "gross_profit": float(
            result.get(
                "gross_profit",
                0.0,
            )
        ),

        "gross_loss": float(
            result.get(
                "gross_loss",
                0.0,
            )
        ),

        "winning_trades": int(
            result.get(
                "winning_trades",
                0,
            )
        ),

        "losing_trades": int(
            result.get(
                "losing_trades",
                0,
            )
        ),

        "trades": int(
            result.get(
                "trades",
                0,
            )
        ),

        # -------------------------
        # Derived trade metrics
        # -------------------------

        "profit_factor": float(
            result.get(
                "profit_factor",
                0.0,
            )
        ),

        "win_rate": float(
            result.get(
                "win_rate",
                0.0,
            )
        ),

        "avg_trade": float(
            result.get(
                "avg_trade",
                0.0,
            )
        ),
    }


def optimize_on_train(config, train_data):

    grid = generate_grid(config)

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


def _calculate_max_drawdown(
    equity_curve
):

    if not equity_curve:
        return 0.0

    running_peak = equity_curve[0]
    max_drawdown = 0.0

    for value in equity_curve:

        running_peak = max(
            running_peak,
            value,
        )

        if running_peak <= 0:
            continue

        drawdown = (
            running_peak - value
        ) / running_peak

        max_drawdown = max(
            max_drawdown,
            drawdown,
        )

    return max_drawdown


def aggregate_fold_metrics(folds):
    """
    Aggregate walk-forward test folds using the actual
    underlying trade and equity data.

    Important:
    - ROI mean/median/std remain descriptive statistics.
    - ROI compounded represents sequential out-of-sample
      capital growth across the folds.
    - Profit factor is calculated from aggregate gross
      profit / aggregate gross loss.
    - Win rate is aggregate wins / aggregate trades.
    - Average trade is aggregate net trade return /
      aggregate trade count.
    - Drawdown is calculated from the combined OOS
      equity curve rather than averaging fold drawdowns.
    """

    if not folds:
        raise ValueError(
            "Cannot aggregate empty fold set"
        )

    rois = [
        fold["roi"]
        for fold in folds
    ]

    # -------------------------
    # Sequential OOS equity
    # -------------------------

    compounded_equity = 1.0

    combined_equity_curve = []

    for fold in folds:

        fold_curve = fold.get(
            "equity_curve",
            [],
        )

        for value in fold_curve:

            combined_equity_curve.append(
                compounded_equity
                * value
            )

        compounded_equity *= (
            fold["final_equity"]
        )

    # -------------------------
    # Trade-level aggregates
    # -------------------------

    gross_profit = sum(
        fold.get(
            "gross_profit",
            0.0,
        )
        for fold in folds
    )

    gross_loss = sum(
        fold.get(
            "gross_loss",
            0.0,
        )
        for fold in folds
    )

    winning_trades = sum(
        fold.get(
            "winning_trades",
            0,
        )
        for fold in folds
    )

    losing_trades = sum(
        fold.get(
            "losing_trades",
            0,
        )
        for fold in folds
    )

    trades = sum(
        fold.get(
            "trades",
            0,
        )
        for fold in folds
    )

    # -------------------------
    # Aggregate PF
    # -------------------------

    if gross_loss > 0:

        profit_factor = (
            gross_profit
            / gross_loss
        )

    elif gross_profit > 0:

        profit_factor = 999.0

    else:

        profit_factor = 0.0

    # -------------------------
    # Aggregate win rate
    # -------------------------

    if trades > 0:

        win_rate = (
            winning_trades
            / trades
        ) * 100.0

        avg_trade = (
            (
                gross_profit
                - gross_loss
            )
            / trades
        ) * 100.0

    else:

        win_rate = 0.0
        avg_trade = 0.0

    # -------------------------
    # Aggregate ROI
    # -------------------------

    roi_compounded = (
        (compounded_equity - 1.0)
        * 100.0
    )

    # -------------------------
    # Aggregate drawdown
    # -------------------------

    drawdown_max = (
        _calculate_max_drawdown(
            combined_equity_curve
        )
    )

    # -------------------------
    # Fold-level statistics
    # -------------------------

    roi_mean = float(
        np.mean(rois)
    )

    roi_median = float(
        np.median(rois)
    )

    roi_std = float(
        np.std(rois)
    )

    return {
        # Descriptive fold statistics.
        "roi_mean": roi_mean,
        "roi_median": roi_median,
        "roi_std": roi_std,

        # Sequential OOS performance.
        "roi_compounded": float(
            roi_compounded
        ),

        # Combined OOS risk.
        "drawdown_max": float(
            drawdown_max
        ),

        # Aggregate trade economics.
        "profit_factor": float(
            profit_factor
        ),

        "win_rate": float(
            win_rate
        ),

        "avg_trade": float(
            avg_trade
        ),

        "trades": int(
            trades
        ),

        "winning_trades": int(
            winning_trades
        ),

        "losing_trades": int(
            losing_trades
        ),

        "gross_profit": float(
            gross_profit
        ),

        "gross_loss": float(
            gross_loss
        ),

        "folds": int(
            len(folds)
        ),

        # -------------------------
        # Compatibility aliases
        # -------------------------
        #
        # Keep these names for the
        # current discovery layer.
        # Their values are now
        # correctly aggregated rather
        # than simple fold averages.

        "profit_factor_mean": float(
            profit_factor
        ),

        "win_rate_mean": float(
            win_rate
        ),

        "avg_trade_mean": float(
            avg_trade
        ),
    }


def run_walkforward(
    config,
    candles,
    train_months,
    test_months,
):

    start = candles["timestamp"].min()
    end = candles["timestamp"].max()

    print(
        candles["timestamp"].head()
    )

    current = start

    folds = []

    fold_count = 0

    while True:

        fold_count += 1

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

    return {
        "folds": folds,
        "metrics": metrics,
    }