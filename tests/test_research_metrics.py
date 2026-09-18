import math

import pytest

from borgbot.research.metrics import (
    aggregate_fold_metrics,
    calculate_max_drawdown,
    normalize_backtest_result,
)


def _valid_result(**overrides):

    result = {
        "roi": 5.0,
        "final_equity": 1.05,
        "equity_curve": [
            1.00,
            1.05,
        ],
        "gross_profit": 0.10,
        "gross_loss": 0.05,
        "winning_trades": 1,
        "losing_trades": 1,
        "trades": 2,
    }

    result.update(overrides)

    return result


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

    assert math.isclose(
        metrics["roi_compounded"],
        4.5,
    )

    assert math.isclose(
        metrics["profit_factor"],
        1.0,
    )

    assert math.isclose(
        metrics["win_rate"],
        50.0,
    )

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

    assert math.isclose(
        metrics["drawdown_max"],
        0.10,
    )


def test_empty_folds_are_rejected():

    with pytest.raises(
        ValueError,
        match="empty fold set",
    ):
        aggregate_fold_metrics([])


def test_missing_required_field_is_rejected():

    result = _valid_result()
    del result["gross_loss"]

    with pytest.raises(
        ValueError,
        match="missing required fields",
    ):
        normalize_backtest_result(result)


def test_non_finite_numeric_value_is_rejected():

    result = _valid_result(
        roi=float("nan"),
    )

    with pytest.raises(
        ValueError,
        match="Non-finite numeric value",
    ):
        normalize_backtest_result(result)


def test_non_integer_trade_count_is_rejected():

    result = _valid_result(
        winning_trades=1.5,
        losing_trades=1,
        trades=2,
    )

    with pytest.raises(
        ValueError,
        match="Non-integer value",
    ):
        normalize_backtest_result(result)


def test_boolean_trade_count_is_rejected():

    result = _valid_result(
        winning_trades=True,
        losing_trades=1,
        trades=2,
    )

    with pytest.raises(
        ValueError,
        match="Invalid integer value",
    ):
        normalize_backtest_result(result)


def test_roi_final_equity_mismatch_is_rejected():

    result = _valid_result(
        roi=10.0,
        final_equity=1.05,
    )

    with pytest.raises(
        ValueError,
        match="ROI/final_equity mismatch",
    ):
        normalize_backtest_result(result)


def test_equity_curve_must_be_positive():

    result = _valid_result(
        equity_curve=[
            1.00,
            0.0,
        ],
    )

    with pytest.raises(
        ValueError,
        match="equity_curve values must be > 0",
    ):
        normalize_backtest_result(result)


def test_gross_profit_requires_winning_trades():

    result = _valid_result(
        gross_profit=0.10,
        winning_trades=0,
        losing_trades=2,
        trades=2,
    )

    with pytest.raises(
        ValueError,
        match="Gross profit exists without winning trades",
    ):
        normalize_backtest_result(result)


def test_gross_loss_requires_losing_trades():

    result = _valid_result(
        gross_profit=0.10,
        gross_loss=0.05,
        winning_trades=2,
        losing_trades=0,
        trades=2,
    )

    with pytest.raises(
        ValueError,
        match="Gross loss exists without losing trades",
    ):
        normalize_backtest_result(result)


def test_zero_trade_result_is_valid():

    result = {
        "roi": 0.0,
        "final_equity": 1.0,
        "equity_curve": [],
        "gross_profit": 0.0,
        "gross_loss": 0.0,
        "winning_trades": 0,
        "losing_trades": 0,
        "trades": 0,
    }

    normalized = normalize_backtest_result(
        result
    )

    assert normalized["trades"] == 0
    assert normalized["gross_profit"] == 0.0
    assert normalized["gross_loss"] == 0.0


def test_drawdown_is_zero_for_monotonic_equity():

    assert math.isclose(
        calculate_max_drawdown(
            [1.0, 1.05, 1.10, 1.20]
        ),
        0.0,
    )


def test_drawdown_uses_peak_to_trough():

    assert math.isclose(
        calculate_max_drawdown(
            [1.0, 1.20, 1.08, 1.15]
        ),
        0.10,
    )
