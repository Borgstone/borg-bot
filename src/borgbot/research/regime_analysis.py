"""Regime-conditional trade analysis for out-of-sample walk-forward folds.

Each completed trade is assigned to the local and higher-timeframe regime present
at its entry bar close. Returns for a regime bucket are compounded independently;
they are descriptive cohort statistics and are not additive components of overall
strategy ROI.
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

DEFAULT_MIN_REGIME_TRADES = 20


def annotate_entry_regimes(trade_log, candles, fold_number: int):
    """Copy trade records and add regime labels observed at their entry bar.

    The entry_bar is a positional index into the exact candles passed to the
    backtest. Missing context columns mean there is no regime analysis to attach.
    """
    required = {"local_regime", "higher_regime"}
    if not required.issubset(candles.columns):
        return []

    annotated = []
    context = candles.reset_index(drop=True)
    for trade in trade_log:
        bar = trade.get("entry_bar")
        if isinstance(bar, bool) or not isinstance(bar, int):
            raise ValueError(f"trade entry_bar must be an integer, got {bar!r}")
        if bar < 0 or bar >= len(context):
            raise ValueError(f"trade entry_bar is outside the candle window: {bar}")

        row = context.iloc[bar]
        record = dict(trade)
        record["fold"] = int(fold_number)
        record["higher_regime"] = str(row["higher_regime"])
        record["local_regime"] = str(row["local_regime"])
        annotated.append(record)
    return annotated


def _trade_stats(trades: list[dict[str, Any]]) -> dict[str, Any]:
    pnl_pct = []
    for trade in trades:
        try:
            value = float(trade["pnl_pct"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("each regime trade must contain numeric pnl_pct") from exc
        if not math.isfinite(value) or value <= -100.0:
            raise ValueError(f"invalid trade return percentage: {value!r}")
        pnl_pct.append(value)

    winners = sum(value > 0.0 for value in pnl_pct)
    losers = len(pnl_pct) - winners
    gross_profit_pct = sum(value for value in pnl_pct if value > 0.0)
    gross_loss_pct = sum(-value for value in pnl_pct if value < 0.0)

    if gross_loss_pct > 0.0:
        profit_factor = gross_profit_pct / gross_loss_pct
    elif gross_profit_pct > 0.0:
        profit_factor = 999.0
    else:
        profit_factor = 0.0

    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0
    for value in pnl_pct:
        equity *= 1.0 + value / 100.0
        peak = max(peak, equity)
        if peak > 0.0:
            max_drawdown = max(max_drawdown, (peak - equity) / peak)

    count = len(pnl_pct)
    return {
        "trades": count,
        "winning_trades": winners,
        "losing_trades": losers,
        "win_rate_pct": (winners / count * 100.0) if count else 0.0,
        "profit_factor": float(profit_factor),
        "avg_trade_pct": (sum(pnl_pct) / count) if count else 0.0,
        "compounded_return_pct": (equity - 1.0) * 100.0,
        "max_drawdown_pct": max_drawdown * 100.0,
        "gross_profit_pct": gross_profit_pct,
        "gross_loss_pct": gross_loss_pct,
    }


def aggregate_regime_profiles(
    folds,
    min_trades: int = DEFAULT_MIN_REGIME_TRADES,
) -> dict[str, Any]:
    """Aggregate higher × local regime trade outcomes across OOS folds."""
    if isinstance(min_trades, bool) or not isinstance(min_trades, int) or min_trades < 1:
        raise ValueError("min_trades must be an integer >= 1")

    trades_by_key = defaultdict(list)
    trades_by_fold = defaultdict(list)

    for fold_index, fold in enumerate(folds, start=1):
        for trade in fold.get("regime_trades", []):
            try:
                higher = str(trade["higher_regime"])
                local = str(trade["local_regime"])
                pnl_pct = float(trade["pnl_pct"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("regime trades require higher_regime, local_regime and pnl_pct") from exc
            if not math.isfinite(pnl_pct):
                raise ValueError("regime trade pnl_pct must be finite")
            key = (higher, local)
            normalized_trade = {**trade, "pnl_pct": pnl_pct}
            trades_by_key[key].append(normalized_trade)
            trades_by_fold[(key, fold_index)].append(normalized_trade)

    profile = []
    for higher, local in sorted(
        trades_by_key,
        key=lambda key: (-len(trades_by_key[key]), key[0], key[1]),
    ):
        group_trades = trades_by_key[(higher, local)]
        fold_results = []
        for fold_index in range(1, len(folds) + 1):
            fold_trades = trades_by_fold.get(((higher, local), fold_index), [])
            if not fold_trades:
                continue
            fold_results.append({
                "fold": fold_index,
                **_trade_stats(fold_trades),
            })

        positive_folds = sum(
            result["compounded_return_pct"] > 0.0
            for result in fold_results
        )
        folds_with_trades = len(fold_results)
        profile.append({
            "higher_regime": higher,
            "local_regime": local,
            **_trade_stats(group_trades),
            "sample_sufficient": len(group_trades) >= min_trades,
            "fold_consistency": {
                "positive_folds": int(positive_folds),
                "folds_with_trades": folds_with_trades,
                "total_folds": len(folds),
                "positive_fold_ratio": (
                    positive_folds / folds_with_trades
                    if folds_with_trades
                    else 0.0
                ),
            },
            "per_fold": fold_results,
        })

    return {
        "basis": "Trade outcome grouped by the local and higher-timeframe regimes at entry bar close.",
        "min_trades_for_interpretation": min_trades,
        "total_folds": len(folds),
        "return_note": (
            "Each regime bucket is compounded independently. Bucket returns are "
            "descriptive cohort statistics, not additive contributions to overall strategy ROI."
        ),
        "sample_note": (
            "Cells below min_trades_for_interpretation are exploratory only; the threshold "
            "is a reporting safeguard, not an optimized trading parameter."
        ),
        "by_regime": profile,
    }
