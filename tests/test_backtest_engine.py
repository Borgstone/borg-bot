import math

import pandas as pd

from borgbot.backtest.engine import BacktestEngine


class _HoldStrategy:
    def generate_signal(self, df, i):
        return 0


def test_backtest_engine_exposes_canonical_roi_field():
    candles = pd.DataFrame(
        {
            "timestamp": pd.date_range(
                "2022-01-01",
                periods=5,
                freq="h",
            ),
            "open": [100.0] * 5,
            "high": [101.0] * 5,
            "low": [99.0] * 5,
            "close": [100.0] * 5,
        }
    )

    result = BacktestEngine(
        strategy=_HoldStrategy()
    ).run(candles)

    assert "roi" in result
    assert "roi_pct" in result
    assert math.isclose(
        result["roi"],
        (result["final_equity"] - 1.0) * 100.0,
    )
    assert math.isclose(
        result["roi"],
        result["roi_pct"],
    )



class _EnterOnceStrategy:
    def generate_signal(self, df, i):
        return 1 if i == 14 else 0


def test_backtest_trade_log_records_entry_exit_and_realized_return():
    close = [100.0] * 15 + [98.0]
    candles = pd.DataFrame(
        {
            "timestamp": pd.date_range("2022-01-01", periods=len(close), freq="h"),
            "open": close,
            "high": [value + 1.0 for value in close],
            "low": [value - 1.0 for value in close],
            "close": close,
        }
    )

    result = BacktestEngine(
        strategy=_EnterOnceStrategy(),
        config={
            "atr_period": 2,
            "atr_stop_mult": 0.5,
            "atr_trail_mult": 10.0,
            "max_holding": 10,
        },
    ).run(candles)

    assert result["trades"] == 1
    assert len(result["trade_log"]) == 1
    trade = result["trade_log"][0]
    assert trade["entry_bar"] == 14
    assert trade["exit_bar"] == 15
    assert trade["side"] == "long"
    assert trade["entry_price"] == 100.0
    assert trade["exit_price"] == 98.0
    assert math.isclose(trade["pnl_pct"], -2.0)
    assert trade["entry_candle_timestamp"] == "2022-01-01T14:00:00"
    assert trade["exit_candle_timestamp"] == "2022-01-01T15:00:00"



class _EnterShortOnceStrategy:
    def generate_signal(self, df, i):
        return -1 if i == 14 else 0


def test_short_trade_return_uses_symmetric_percentage_price_move():
    close = [100.0] * 15 + [90.0]
    candles = pd.DataFrame({
        "timestamp": pd.date_range("2022-01-01", periods=len(close), freq="h"),
        "open": close,
        "high": [v + 1.0 for v in close],
        "low": [v - 1.0 for v in close],
        "close": close,
    })
    result = BacktestEngine(
        strategy=_EnterShortOnceStrategy(),
        config={"atr_period": 2, "atr_stop_mult": 0.5,
                "atr_trail_mult": 10.0, "max_holding": 10},
    ).run(candles)

    trade = result["trade_log"][0]
    assert trade["side"] == "short"
    assert math.isclose(trade["pnl_before_fees_pct"], 10.0)
    assert math.isclose(trade["pnl_pct"], 10.0)


def test_backtest_applies_entry_exit_slippage_and_per_side_fees():
    close = [100.0] * 16
    candles = pd.DataFrame({
        "timestamp": pd.date_range("2022-01-01", periods=len(close), freq="h"),
        "open": close,
        "high": [v + 1.0 for v in close],
        "low": [v - 1.0 for v in close],
        "close": close,
    })
    result = BacktestEngine(
        strategy=_EnterOnceStrategy(),
        config={"atr_period": 2, "atr_stop_mult": 0.5,
                "atr_trail_mult": 10.0, "max_holding": 1,
                "fees_bps": 10.0, "slippage_pct": 0.0005},
    ).run(candles)

    trade = result["trade_log"][0]
    entry_fill = 100.0 * 1.0005
    exit_fill = 100.0 * 0.9995
    price_return = exit_fill / entry_fill - 1.0
    expected_net = ((1.0 + price_return) * (1.0 - 0.001) ** 2 - 1.0) * 100.0

    assert math.isclose(trade["entry_price"], entry_fill)
    assert math.isclose(trade["exit_price"], exit_fill)
    assert math.isclose(trade["pnl_before_fees_pct"], price_return * 100.0)
    assert math.isclose(trade["pnl_pct"], expected_net)
    assert trade["fees_bps_per_side"] == 10.0
    assert trade["slippage_pct_per_side"] == 0.0005


def test_short_mark_to_market_uses_linear_short_return():
    assert math.isclose(
        BacktestEngine.mark_to_market_equity(1.0, -1, 100.0, 90.0),
        1.10,
    )


def test_invalid_execution_costs_are_rejected():
    import pytest

    with pytest.raises(ValueError, match="fees_bps"):
        BacktestEngine(_HoldStrategy(), config={"fees_bps": -1.0})
    with pytest.raises(ValueError, match="slippage_pct"):
        BacktestEngine(_HoldStrategy(), config={"slippage_pct": 1.0})
