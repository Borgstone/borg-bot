import math
from typing import Dict, Iterable, List

import numpy as np
import pandas as pd


DEFAULT_HORIZONS = (
    "1h",
    "4h",
    "1d",
    "3d",
    "7d",
    "14d",
    "30d",
    "60d",
    "90d",
)


def horizon_to_timedelta(
    horizon: str,
) -> pd.Timedelta:
    """
    Convert a supported horizon label to a pandas Timedelta.

    Calendar months are deliberately represented as fixed-day
    research horizons:
        30d ~= one month
        60d ~= two months
        90d ~= three months

    This keeps the measurement unambiguous and independent of
    calendar month length.
    """

    try:
        delta = pd.Timedelta(horizon)
    except ValueError as exc:
        raise ValueError(
            f"Unsupported horizon: {horizon!r}"
        ) from exc

    if delta <= pd.Timedelta(0):
        raise ValueError(
            f"Horizon must be positive: {horizon!r}"
        )

    return delta


def timeframe_to_timedelta(
    timeframe: str,
) -> pd.Timedelta:
    """
    Convert an exchange timeframe label such as 1m, 5m, 1h
    into a Timedelta.
    """

    aliases = {
        "1m": "1min",
        "3m": "3min",
        "5m": "5min",
        "15m": "15min",
        "30m": "30min",
        "1h": "1h",
        "2h": "2h",
        "4h": "4h",
        "6h": "6h",
        "8h": "8h",
        "12h": "12h",
        "1d": "1d",
        "3d": "3d",
        "1w": "7d",
    }

    normalized = aliases.get(
        timeframe,
        timeframe,
    )

    try:
        delta = pd.Timedelta(
            normalized
        )
    except ValueError as exc:
        raise ValueError(
            f"Unsupported timeframe: {timeframe!r}"
        ) from exc

    if delta <= pd.Timedelta(0):
        raise ValueError(
            f"Timeframe must be positive: {timeframe!r}"
        )

    return delta


def supported_horizons(
    timeframe: str,
    horizons: Iterable[str] = DEFAULT_HORIZONS,
) -> List[str]:
    """
    Return horizons that are at least as long as the source
    candle timeframe.

    This prevents meaningless measurements such as a 1h horizon
    against a 4h candle series.
    """

    candle_delta = timeframe_to_timedelta(
        timeframe
    )

    supported = []

    for horizon in horizons:

        horizon_delta = horizon_to_timedelta(
            horizon
        )

        if horizon_delta >= candle_delta:
            supported.append(horizon)

    return supported


def _validate_series(
    timestamps: Iterable,
    equity_curve: Iterable[float],
):
    timestamps = pd.to_datetime(
        list(timestamps),
        errors="raise",
    )

    equity = np.asarray(
        list(equity_curve),
        dtype=float,
    )

    if len(timestamps) != len(equity):
        raise ValueError(
            "timestamps and equity_curve must have the same length"
        )

    if len(timestamps) == 0:
        return (
            np.array(
                [],
                dtype="datetime64[ns]",
            ),
            equity,
        )

    if not timestamps.is_monotonic_increasing:
        raise ValueError(
            "timestamps must be sorted ascending"
        )

    if timestamps.has_duplicates:
        raise ValueError(
            "timestamps must be unique"
        )

    if not np.all(np.isfinite(equity)):
        raise ValueError(
            "equity_curve contains non-finite values"
        )

    if np.any(equity <= 0):
        raise ValueError(
            "equity_curve values must be > 0"
        )

    return (
        timestamps.to_numpy(
            dtype="datetime64[ns]"
        ),
        equity,
    )


def analyze_horizon(
    timestamps: Iterable,
    equity_curve: Iterable[float],
    horizon: str,
) -> Dict[str, float]:
    """
    Measure rolling out-of-sample returns over a deployment horizon.

    For every possible starting timestamp with a matching future
    observation, measure:

        equity[t + horizon] / equity[t] - 1

    This describes how the strategy behaves when continuously
    deployed over that elapsed horizon.
    """

    timestamps, equity = _validate_series(
        timestamps,
        equity_curve,
    )

    delta = horizon_to_timedelta(
        horizon
    )

    if len(timestamps) == 0:

        return {
            "horizon": horizon,
            "observations": 0,
            "mean_return_pct": 0.0,
            "median_return_pct": 0.0,
            "std_return_pct": 0.0,
            "positive_window_ratio": 0.0,
            "best_return_pct": 0.0,
            "worst_return_pct": 0.0,
        }

    returns = []

    for i, timestamp in enumerate(timestamps):

        target = (
            timestamp
            + np.timedelta64(
                delta.value,
                "ns",
            )
        )

        j = np.searchsorted(
            timestamps,
            target,
            side="left",
        )

        if j >= len(timestamps):
            break

        start_equity = equity[i]
        end_equity = equity[j]

        if start_equity <= 0:
            continue

        window_return = (
            end_equity
            / start_equity
        ) - 1.0

        if math.isfinite(
            float(window_return)
        ):
            returns.append(
                float(window_return)
            )

    if not returns:

        return {
            "horizon": horizon,
            "observations": 0,
            "mean_return_pct": 0.0,
            "median_return_pct": 0.0,
            "std_return_pct": 0.0,
            "positive_window_ratio": 0.0,
            "best_return_pct": 0.0,
            "worst_return_pct": 0.0,
        }

    values = np.asarray(
        returns,
        dtype=float,
    )

    return {
        "horizon": horizon,
        "observations": int(len(values)),
        "mean_return_pct": float(
            np.mean(values) * 100.0
        ),
        "median_return_pct": float(
            np.median(values) * 100.0
        ),
        "std_return_pct": float(
            np.std(values) * 100.0
        ),
        "positive_window_ratio": float(
            np.mean(values > 0.0)
        ),
        "best_return_pct": float(
            np.max(values) * 100.0
        ),
        "worst_return_pct": float(
            np.min(values) * 100.0
        ),
    }


def analyze_horizon_profile(
    timestamps: Iterable,
    equity_curve: Iterable[float],
    horizons: Iterable[str] = DEFAULT_HORIZONS,
) -> Dict[str, Dict[str, float]]:
    """
    Analyze multiple deployment horizons for one OOS period.
    """

    return {
        horizon: analyze_horizon(
            timestamps,
            equity_curve,
            horizon,
        )
        for horizon in horizons
    }


def aggregate_horizon_profiles(
    folds: List[Dict],
    horizons: Iterable[str] = DEFAULT_HORIZONS,
) -> Dict[str, Dict]:
    """
    Aggregate horizon observations across OOS folds.

    Window returns are concatenated across folds rather than
    averaging fold-level percentages. Each fold remains separately
    inspectable through fold_profiles.

    Horizon windows never cross fold boundaries.
    """

    if not folds:
        raise ValueError(
            "Cannot aggregate horizon profiles from empty folds"
        )

    result = {}

    for horizon in horizons:

        fold_profiles = []
        all_returns = []

        for fold_index, fold in enumerate(
            folds,
            start=1,
        ):

            profile = analyze_horizon(
                fold["timestamps"],
                fold["equity_curve"],
                horizon,
            )

            profile["fold"] = fold_index

            fold_profiles.append(
                profile
            )

            # Reconstruct the rolling returns for
            # aggregate statistics.
            timestamps, equity = _validate_series(
                fold["timestamps"],
                fold["equity_curve"],
            )

            delta = horizon_to_timedelta(
                horizon
            )

            for i, timestamp in enumerate(
                timestamps
            ):

                target = (
                    timestamp
                    + np.timedelta64(
                        delta.value,
                        "ns",
                    )
                )

                j = np.searchsorted(
                    timestamps,
                    target,
                    side="left",
                )

                if j >= len(timestamps):
                    break

                start_equity = equity[i]
                end_equity = equity[j]

                if start_equity <= 0:
                    continue

                window_return = (
                    end_equity
                    / start_equity
                ) - 1.0

                if math.isfinite(
                    float(window_return)
                ):
                    all_returns.append(
                        float(window_return)
                    )

        values = np.asarray(
            all_returns,
            dtype=float,
        )

        if len(values) == 0:

            aggregate = {
                "horizon": horizon,
                "observations": 0,
                "mean_return_pct": 0.0,
                "median_return_pct": 0.0,
                "std_return_pct": 0.0,
                "positive_window_ratio": 0.0,
                "best_return_pct": 0.0,
                "worst_return_pct": 0.0,
            }

        else:

            aggregate = {
                "horizon": horizon,
                "observations": int(
                    len(values)
                ),
                "mean_return_pct": float(
                    np.mean(values) * 100.0
                ),
                "median_return_pct": float(
                    np.median(values) * 100.0
                ),
                "std_return_pct": float(
                    np.std(values) * 100.0
                ),
                "positive_window_ratio": float(
                    np.mean(values > 0.0)
                ),
                "best_return_pct": float(
                    np.max(values) * 100.0
                ),
                "worst_return_pct": float(
                    np.min(values) * 100.0
                ),
            }

        aggregate["folds"] = len(folds)
        aggregate["fold_profiles"] = fold_profiles

        result[horizon] = aggregate

    return result
