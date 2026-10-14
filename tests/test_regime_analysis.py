import math

import pandas as pd
import pytest

from borgbot.research.regime_analysis import (
    aggregate_regime_profiles,
    annotate_entry_regimes,
)


def make_frame():
    return pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=3, freq="h"),
        "local_regime": ["UP", "SIDEWAYS", "UP"],
        "higher_regime": ["UP", "DOWN", "UP"],
    })


def test_entry_regime_annotation_uses_the_trade_entry_bar():
    candles = make_frame()
    trade_log = [
        {"entry_bar": 1, "exit_bar": 2, "pnl_pct": 4.0},
    ]

    result = annotate_entry_regimes(trade_log, candles, fold_number=2)

    assert result == [{
        "entry_bar": 1,
        "exit_bar": 2,
        "pnl_pct": 4.0,
        "fold": 2,
        "higher_regime": "DOWN",
        "local_regime": "SIDEWAYS",
    }]


def test_entry_regime_annotation_requires_valid_entry_position():
    candles = make_frame()
    with pytest.raises(ValueError, match="outside the candle window"):
        annotate_entry_regimes([{"entry_bar": 10}], candles, fold_number=1)


def test_regime_profiles_aggregate_trade_stats_and_fold_consistency():
    folds = [
        {
            "regime_trades": [
                {"higher_regime": "UP", "local_regime": "UP", "pnl_pct": 10.0},
                {"higher_regime": "UP", "local_regime": "UP", "pnl_pct": -5.0},
                {"higher_regime": "DOWN", "local_regime": "SIDEWAYS", "pnl_pct": -1.0},
            ]
        },
        {
            "regime_trades": [
                {"higher_regime": "UP", "local_regime": "UP", "pnl_pct": 5.0},
            ]
        },
        {
            "regime_trades": []
        },
    ]

    result = aggregate_regime_profiles(folds, min_trades=3)
    up_up = next(
        item for item in result["by_regime"]
        if item["higher_regime"] == "UP" and item["local_regime"] == "UP"
    )
    assert up_up["trades"] == 3
    assert up_up["winning_trades"] == 2
    assert up_up["losing_trades"] == 1
    assert math.isclose(up_up["win_rate_pct"], 200.0 / 3.0)
    assert math.isclose(up_up["profit_factor"], 3.0)
    assert math.isclose(up_up["avg_trade_pct"], 10.0 / 3.0)
    assert math.isclose(up_up["compounded_return_pct"], 9.725)
    assert up_up["sample_sufficient"] is True
    assert up_up["fold_consistency"]["positive_folds"] == 2
    assert up_up["fold_consistency"]["folds_with_trades"] == 2
    assert up_up["fold_consistency"]["total_folds"] == 3
    assert math.isclose(up_up["fold_consistency"]["positive_fold_ratio"], 1.0)

    sparse = next(
        item for item in result["by_regime"]
        if item["higher_regime"] == "DOWN" and item["local_regime"] == "SIDEWAYS"
    )
    assert sparse["trades"] == 1
    assert sparse["sample_sufficient"] is False


def test_regime_minimum_trade_threshold_must_be_positive_integer():
    with pytest.raises(ValueError, match="min_trades"):
        aggregate_regime_profiles([], min_trades=0)
