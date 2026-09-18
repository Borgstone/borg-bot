import math

import pandas as pd
import pytest

from borgbot.research.horizon import (
    aggregate_horizon_profiles,
    analyze_horizon,
    supported_horizons,
)


def make_series(values):
    timestamps = pd.date_range(
        "2026-01-01",
        periods=len(values),
        freq="1h",
    )

    return timestamps, values


def test_analyze_one_hour_horizon():

    timestamps, equity = make_series(
        [
            1.0,
            1.1,
            1.2,
            1.1,
        ]
    )

    result = analyze_horizon(
        timestamps,
        equity,
        "1h",
    )

    assert result["observations"] == 3

    assert math.isclose(
        result["mean_return_pct"],
        (
            10.0
            + (1.2 / 1.1 - 1.0) * 100.0
            + (1.1 / 1.2 - 1.0) * 100.0
        ) / 3.0,
    )

    assert math.isclose(
        result["positive_window_ratio"],
        2.0 / 3.0,
    )

    assert math.isclose(
        result["best_return_pct"],
        10.0,
    )


def test_longer_horizon_uses_elapsed_time():

    timestamps, equity = make_series(
        [
            1.0,
            1.1,
            1.21,
            1.331,
            1.4641,
        ]
    )

    result = analyze_horizon(
        timestamps,
        equity,
        "2h",
    )

    assert result["observations"] == 3

    # Every two-hour window compounds to 21%.
    assert math.isclose(
        result["median_return_pct"],
        21.0,
        rel_tol=1e-9,
        abs_tol=1e-9,
    )


def test_horizon_requires_matching_future_observation():

    timestamps, equity = make_series(
        [1.0, 1.1, 1.2],
    )

    result = analyze_horizon(
        timestamps,
        equity,
        "1d",
    )

    assert result["observations"] == 0


def test_supported_horizons_filter_by_timeframe():

    result = supported_horizons(
        "4h",
        [
            "1h",
            "4h",
            "1d",
        ],
    )

    assert result == [
        "4h",
        "1d",
    ]


def test_horizon_validation_rejects_unsorted_timestamps():

    timestamps = pd.to_datetime(
        [
            "2026-01-01 01:00:00",
            "2026-01-01 00:00:00",
        ]
    )

    with pytest.raises(
        ValueError,
        match="sorted ascending",
    ):
        analyze_horizon(
            timestamps,
            [1.0, 1.1],
            "1h",
        )


def test_horizon_validation_rejects_duplicate_timestamps():

    timestamps = pd.to_datetime(
        [
            "2026-01-01 00:00:00",
            "2026-01-01 00:00:00",
        ]
    )

    with pytest.raises(
        ValueError,
        match="unique",
    ):
        analyze_horizon(
            timestamps,
            [1.0, 1.1],
            "1h",
        )


def test_aggregate_horizon_profiles_do_not_cross_folds():

    fold_one_timestamps, fold_one_equity = (
        make_series(
            [
                1.0,
                1.1,
                1.21,
            ]
        )
    )

    fold_two_timestamps, fold_two_equity = (
        make_series(
            [
                1.0,
                0.9,
                0.81,
            ]
        )
    )

    profiles = aggregate_horizon_profiles(
        [
            {
                "timestamps": fold_one_timestamps,
                "equity_curve": fold_one_equity,
            },
            {
                "timestamps": fold_two_timestamps,
                "equity_curve": fold_two_equity,
            },
        ],
        horizons=["1h"],
    )

    result = profiles["1h"]

    assert result["observations"] == 4
    assert result["folds"] == 2
    assert len(result["fold_profiles"]) == 2

    # First fold: two +10% windows.
    # Second fold: two -10% windows.
    assert math.isclose(
        result["positive_window_ratio"],
        0.5,
    )


def test_empty_horizon_folds_are_rejected():

    with pytest.raises(
        ValueError,
        match="empty folds",
    ):
        aggregate_horizon_profiles(
            [],
            horizons=["1h"],
        )
