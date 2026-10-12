"""Leakage-safe alignment of closed higher-timeframe regime values."""
from __future__ import annotations

import re

import pandas as pd

from borgbot.core.market_regime import MarketRegimeDetector, REGIME_UNKNOWN


_TIMEFRAME = re.compile(r"^(\d+)([mhdw])$")


def timeframe_duration(timeframe: str) -> pd.Timedelta:
    """Convert a CCXT-style minute/hour/day/week timeframe to a duration."""
    if not isinstance(timeframe, str):
        raise ValueError("timeframe must be a string such as '1h' or '1d'")
    match = _TIMEFRAME.fullmatch(timeframe.strip())
    if not match:
        raise ValueError(f"unsupported timeframe: {timeframe!r}")
    amount = int(match.group(1))
    unit = match.group(2)
    if amount <= 0:
        raise ValueError("timeframe duration must be positive")
    units = {"m": "minutes", "h": "hours", "d": "days", "w": "weeks"}
    return pd.Timedelta(**{units[unit]: amount})


def align_higher_timeframe_regime(
    base_candles: pd.DataFrame,
    higher_candles: pd.DataFrame,
    base_timeframe: str,
    higher_timeframe: str,
    detector: MarketRegimeDetector | None = None,
    prefix: str = "higher",
) -> pd.DataFrame:
    """Attach the latest fully closed higher-timeframe regime to each base bar.

    Candle timestamps are assumed to be candle-open timestamps, as in CCXT OHLCV.
    The base strategy is assumed to evaluate on the base candle close. A higher
    timeframe result becomes available only at higher timestamp + its duration.
    """
    base_duration = timeframe_duration(base_timeframe)
    higher_duration = timeframe_duration(higher_timeframe)
    if higher_duration <= base_duration:
        raise ValueError("higher_timeframe must be greater than base_timeframe")
    if not prefix or not prefix.replace("_", "").isalnum():
        raise ValueError("prefix must contain only letters, numbers or underscores")

    for name, frame in (("base_candles", base_candles), ("higher_candles", higher_candles)):
        required = {"timestamp", "high", "low", "close"}
        missing = required.difference(frame.columns)
        if missing:
            raise ValueError(f"{name} missing required columns: {sorted(missing)}")
        timestamps = pd.to_datetime(frame["timestamp"], errors="coerce")
        if timestamps.isna().any():
            raise ValueError(f"{name} timestamps must be valid")
        if timestamps.duplicated().any():
            raise ValueError(f"{name} timestamps must be unique")
        if not timestamps.is_monotonic_increasing:
            raise ValueError(f"{name} timestamps must be sorted ascending")

    detector = detector or MarketRegimeDetector()
    higher_values = detector.analyze(higher_candles)
    higher_values = higher_values.reset_index(drop=True)
    higher_values["available_at"] = (
        pd.to_datetime(higher_candles["timestamp"]).reset_index(drop=True)
        + higher_duration
    )
    higher_values = higher_values.rename(
        columns={column: f"{prefix}_{column}" for column in higher_values.columns if column != "available_at"}
    )

    original_index = base_candles.index
    left = base_candles.reset_index(drop=True).copy()
    left["__row_order"] = range(len(left))
    left["__signal_at"] = pd.to_datetime(left["timestamp"]) + base_duration
    left = left.sort_values("__signal_at")

    merged = pd.merge_asof(
        left,
        higher_values.sort_values("available_at"),
        left_on="__signal_at",
        right_on="available_at",
        direction="backward",
        allow_exact_matches=True,
    )
    merged = merged.sort_values("__row_order")
    regime_column = f"{prefix}_regime"
    merged[regime_column] = merged[regime_column].fillna(REGIME_UNKNOWN)
    merged = merged.drop(columns=["__row_order", "__signal_at", "available_at"])
    merged.index = original_index
    return merged
