import math
from typing import Any, Dict, Iterable, List


REQUIRED_BACKTEST_FIELDS = (
    "roi",
    "final_equity",
    "equity_curve",
    "gross_profit",
    "gross_loss",
    "winning_trades",
    "losing_trades",
    "trades",
)


def _to_float(
    value: Any,
    field: str,
) -> float:

    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Invalid numeric value for '{field}': {value!r}"
        ) from exc

    if not math.isfinite(result):
        raise ValueError(
            f"Non-finite numeric value for '{field}': {value!r}"
        )

    return result


def _to_int(
    value: Any,
    field: str,
) -> int:

    if isinstance(value, bool):
        raise ValueError(
            f"Invalid integer value for '{field}': {value!r}"
        )

    try:
        numeric_value = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Invalid integer value for '{field}': {value!r}"
        ) from exc

    if not math.isfinite(numeric_value):
        raise ValueError(
            f"Non-finite integer value for '{field}': {value!r}"
        )

    if not numeric_value.is_integer():
        raise ValueError(
            f"Non-integer value for '{field}': {value!r}"
        )

    return int(numeric_value)


def normalize_backtest_result(
    result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Normalize and validate the result returned by BacktestEngine.

    This is the boundary between the backtest engine and the
    research metrics layer.
    """

    if not isinstance(result, dict):
        raise TypeError(
            "Backtest result must be a dictionary"
        )

    missing = [
        field
        for field in REQUIRED_BACKTEST_FIELDS
        if field not in result
    ]

    if missing:
        raise ValueError(
            "Backtest result is missing required fields: "
            + ", ".join(missing)
        )

    equity_curve = result["equity_curve"]

    if equity_curve is None:
        equity_curve = []

    try:
        equity_curve = [
            _to_float(
                value,
                "equity_curve",
            )
            for value in equity_curve
        ]
    except TypeError as exc:
        raise ValueError(
            "equity_curve must be an iterable of numeric values"
        ) from exc

    for value in equity_curve:

        if value <= 0:
            raise ValueError(
                "equity_curve values must be > 0"
            )

    final_equity = _to_float(
        result["final_equity"],
        "final_equity",
    )

    if final_equity <= 0:
        raise ValueError(
            f"final_equity must be > 0, got {final_equity}"
        )

    roi = _to_float(
        result["roi"],
        "roi",
    )

    expected_roi = (
        final_equity - 1.0
    ) * 100.0

    if not math.isclose(
        roi,
        expected_roi,
        rel_tol=1e-9,
        abs_tol=1e-9,
    ):
        raise ValueError(
            "ROI/final_equity mismatch: "
            f"roi={roi}, "
            f"expected={expected_roi}"
        )

    gross_profit = _to_float(
        result["gross_profit"],
        "gross_profit",
    )

    gross_loss = _to_float(
        result["gross_loss"],
        "gross_loss",
    )

    if gross_profit < 0:
        raise ValueError(
            f"gross_profit cannot be negative: {gross_profit}"
        )

    if gross_loss < 0:
        raise ValueError(
            f"gross_loss cannot be negative: {gross_loss}"
        )

    winning_trades = _to_int(
        result["winning_trades"],
        "winning_trades",
    )

    losing_trades = _to_int(
        result["losing_trades"],
        "losing_trades",
    )

    trades = _to_int(
        result["trades"],
        "trades",
    )

    if winning_trades < 0:
        raise ValueError(
            "winning_trades cannot be negative"
        )

    if losing_trades < 0:
        raise ValueError(
            "losing_trades cannot be negative"
        )

    if trades < 0:
        raise ValueError(
            "trades cannot be negative"
        )

    if (
        winning_trades
        + losing_trades
        != trades
    ):
        raise ValueError(
            "Trade accounting mismatch: "
            f"winning_trades ({winning_trades}) + "
            f"losing_trades ({losing_trades}) != "
            f"trades ({trades})"
        )

    if (
        winning_trades == 0
        and gross_profit != 0
    ):
        raise ValueError(
            "Gross profit exists without winning trades"
        )

    if (
        losing_trades == 0
        and gross_loss != 0
    ):
        raise ValueError(
            "Gross loss exists without losing trades"
        )

    return {
        "equity_curve": equity_curve,
        "final_equity": final_equity,
        "roi": roi,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "trades": trades,
    }


def calculate_max_drawdown(
    equity_curve: Iterable[float],
) -> float:
    """
    Calculate maximum peak-to-trough drawdown.

    Returns a decimal fraction:
        0.10 = 10% drawdown
    """

    values = list(equity_curve)

    if not values:
        return 0.0

    running_peak = values[0]
    max_drawdown = 0.0

    for value in values:

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

    return float(max_drawdown)


def aggregate_fold_metrics(
    folds: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Aggregate out-of-sample walk-forward folds.

    The aggregation deliberately distinguishes between:

    1. Descriptive fold statistics
       - ROI mean
       - ROI median
       - ROI standard deviation

    2. Sequential OOS performance
       - compounded ROI

    3. Combined trade economics
       - profit factor
       - win rate
       - average trade

    4. Combined OOS risk
       - maximum drawdown

    5. Fold consistency
       - positive fold count
       - positive fold ratio

    Fold-level PF, win rate and average trade are NOT averaged.
    They are rebuilt from the underlying aggregate trade data.
    """

    if not folds:
        raise ValueError(
            "Cannot aggregate an empty fold set"
        )

    normalized_folds = [
        normalize_backtest_result(fold)
        for fold in folds
    ]

    # -------------------------
    # Fold ROI statistics
    # -------------------------

    rois = [
        fold["roi"]
        for fold in normalized_folds
    ]

    roi_mean = (
        sum(rois)
        / len(rois)
    )

    sorted_rois = sorted(rois)

    middle = len(sorted_rois) // 2

    if len(sorted_rois) % 2 == 0:

        roi_median = (
            sorted_rois[middle - 1]
            + sorted_rois[middle]
        ) / 2.0

    else:

        roi_median = sorted_rois[middle]

    roi_variance = (
        sum(
            (roi - roi_mean) ** 2
            for roi in rois
        )
        / len(rois)
    )

    roi_std = math.sqrt(
        roi_variance
    )

    # -------------------------
    # Sequential OOS equity
    # -------------------------

    compounded_equity = 1.0

    combined_equity_curve = []

    for fold in normalized_folds:

        fold_scale = (
            compounded_equity
        )

        for value in fold["equity_curve"]:

            combined_equity_curve.append(
                fold_scale * value
            )

        compounded_equity *= (
            fold["final_equity"]
        )

    roi_compounded = (
        (compounded_equity - 1.0)
        * 100.0
    )

    # -------------------------
    # Aggregate trade economics
    # -------------------------

    gross_profit = sum(
        fold["gross_profit"]
        for fold in normalized_folds
    )

    gross_loss = sum(
        fold["gross_loss"]
        for fold in normalized_folds
    )

    winning_trades = sum(
        fold["winning_trades"]
        for fold in normalized_folds
    )

    losing_trades = sum(
        fold["losing_trades"]
        for fold in normalized_folds
    )

    trades = sum(
        fold["trades"]
        for fold in normalized_folds
    )

    # -------------------------
    # Profit factor
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
    # Win rate / average trade
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
    # Drawdown
    # -------------------------

    drawdown_max = calculate_max_drawdown(
        combined_equity_curve
    )

    # -------------------------
    # Fold consistency
    # -------------------------

    positive_folds = sum(
        1
        for roi in rois
        if roi > 0
    )

    positive_fold_ratio = (
        positive_folds
        / len(rois)
    )

    return {
        "roi_mean": float(
            roi_mean
        ),

        "roi_median": float(
            roi_median
        ),

        "roi_std": float(
            roi_std
        ),

        "roi_compounded": float(
            roi_compounded
        ),

        "drawdown_max": float(
            drawdown_max
        ),

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
            len(normalized_folds)
        ),

        "positive_folds": int(
            positive_folds
        ),

        "positive_fold_ratio": float(
            positive_fold_ratio
        ),

        # Compatibility aliases.
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
