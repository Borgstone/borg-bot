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
