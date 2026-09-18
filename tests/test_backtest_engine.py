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
