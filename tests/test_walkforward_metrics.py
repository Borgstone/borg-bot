import math

import pytest

from borgbot.research.metrics import (
    aggregate_fold_metrics,
    normalize_backtest_result,
)


def test_aggregate_fold_metrics():

    folds = [
        {
            "roi": 10.0,
            "final_equity": 1.10,
            "equity_curve": [
                1.00,
                1.05,
                1.10,
            ],
            "gross_profit": 0.10,
            "gross_loss": 0.05,
            "winning_trades": 1,
            "losing_trades": 1,
            "trades": 2,
        },
        {
            "roi": -5.0,
            "final_equity": 0.95,
            "equity_curve": [
                1.00,
                0.90,
                0.95,
            ],
            "gross_profit": 0.08,
            "gross_loss": 0.13,
            "winning_trades": 1,
            "losing_trades": 1,
            "trades": 2,
        },
    ]

    metrics = aggregate_fold_metrics(
        folds
    )

    # Descriptive fold statistics.
    assert math.isclose(
        metrics["roi_mean"],
        2.5,
    )

    assert math.isclose(
        metrics["roi_median"],
        2.5,
    )

    assert math.isclose(
        metrics["roi_std"],
        7.5,
    )

    # Sequential compounding:
    # 1.10 * 0.95 = 1.045
    assert math.isclose(
        metrics["roi_compounded"],
        4.5,
    )

    # Combined gross profit/loss:
    # 0.18 / 0.18 = 1.0
    assert math.isclose(
        metrics["profit_factor"],
        1.0,
    )

    # 2 wins out of 4 trades.
    assert math.isclose(
        metrics["win_rate"],
        50.0,
    )

    # Net aggregate trade return is zero.
    assert math.isclose(
        metrics["avg_trade"],
        0.0,
    )

    assert metrics["trades"] == 4
    assert metrics["winning_trades"] == 2
    assert metrics["losing_trades"] == 2

    assert metrics["positive_folds"] == 1

    assert math.isclose(
        metrics["positive_fold_ratio"],
        0.5,
    )

    # Combined equity:
    #
    # Fold 1:
    # 1.00, 1.05, 1.10
    #
    # Fold 2 is scaled by 1.10:
    # 1.10, 0.99, 1.045
    #
    # Peak = 1.10
    # Trough = 0.99
    # DD = 0.10
    assert math.isclose(
        metrics["drawdown_max"],
        0.10,
    )


def test_trade_accounting_mismatch_is_rejected():

    invalid_fold = {
        "roi": 5.0,
        "final_equity": 1.05,
        "equity_curve": [
            1.00,
            1.05,
        ],
        "gross_profit": 0.10,
        "gross_loss": 0.05,
        "winning_trades": 3,
        "losing_trades": 1,
        "trades": 3,
    }

    with pytest.raises(
        ValueError,
        match="Trade accounting mismatch",
    ):
        normalize_backtest_result(
            invalid_fold
        )


def test_negative_gross_profit_is_rejected():

    invalid_fold = {
        "roi": 5.0,
        "final_equity": 1.05,
        "equity_curve": [
            1.00,
            1.05,
        ],
        "gross_profit": -0.10,
        "gross_loss": 0.05,
        "winning_trades": 1,
        "losing_trades": 1,
        "trades": 2,
    }

    with pytest.raises(
        ValueError,
        match="gross_profit cannot be negative",
    ):
        normalize_backtest_result(
            invalid_fold
        )
