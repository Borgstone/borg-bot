from borgbot.research.walkforward_core import (
    aggregate_fold_metrics,
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
    assert metrics["roi_mean"] == 2.5
    assert metrics["roi_median"] == 2.5
    assert metrics["roi_std"] == 7.5

    # Sequential compounding:
    # 1.10 * 0.95 = 1.045
    assert metrics["roi_compounded"] == 4.5

    # Combined gross profit/loss:
    # 0.18 / 0.18 = 1.0
    assert metrics["profit_factor"] == 1.0

    # 2 wins out of 4 trades.
    assert metrics["win_rate"] == 50.0

    # Net aggregate trade return is zero.
    assert metrics["avg_trade"] == 0.0

    assert metrics["trades"] == 4

    # Combined equity:
    # fold 1 ends at 1.10.
    # fold 2 becomes:
    # 1.10, 0.99, 1.045
    # Maximum DD = 10%.
    assert metrics["drawdown_max"] == 0.10