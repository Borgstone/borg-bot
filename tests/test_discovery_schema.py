import sqlite3

import pandas as pd
import pytest

import borgbot.research.discovery_engine as discovery_engine
from borgbot.research.discovery_engine import (
    ensure_discovery_schema,
    run_holdout_validation,
    validate_context_coverage,
)


def test_discovery_schema_adds_regime_profile_and_is_idempotent():
    conn = sqlite3.connect(":memory:")
    try:
        conn.execute(
            "CREATE TABLE discovery_results (experiment_id TEXT, horizon_profile TEXT)"
        )

        ensure_discovery_schema(conn)
        first_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(discovery_results)")
        }
        assert "regime_profile" in first_columns

        ensure_discovery_schema(conn)
        second_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(discovery_results)")
        }
        assert second_columns == first_columns
    finally:
        conn.close()



def test_context_coverage_accepts_aligned_historical_ranges():
    base = pd.DataFrame({
        "timestamp": pd.date_range("2022-01-01", periods=48, freq="h"),
    })
    higher = pd.DataFrame({
        "timestamp": pd.date_range("2022-01-01", periods=2, freq="D"),
    })

    validate_context_coverage(base, higher, "1h", "1d")


def test_context_coverage_rejects_higher_timeframe_starting_too_late():
    base = pd.DataFrame({
        "timestamp": pd.date_range("2022-01-01", periods=48, freq="h"),
    })
    higher = pd.DataFrame({
        "timestamp": pd.date_range("2022-01-02", periods=2, freq="D"),
    })

    with pytest.raises(ValueError, match="starts after the base dataset"):
        validate_context_coverage(base, higher, "1h", "1d")


def test_context_coverage_rejects_higher_timeframe_ending_too_early():
    base = pd.DataFrame({
        "timestamp": pd.date_range("2022-01-01", periods=72, freq="h"),
    })
    higher = pd.DataFrame({
        "timestamp": pd.date_range("2022-01-01", periods=1, freq="D"),
    })

    with pytest.raises(ValueError, match="ends before the base dataset"):
        validate_context_coverage(base, higher, "1h", "1d")



def test_holdout_validation_rejects_overlap_with_discovery_folds():
    candles = pd.DataFrame({
        "timestamp": pd.date_range("2023-09-01", periods=100, freq="h"),
        "local_regime": ["UP"] * 100,
        "higher_regime": ["UP"] * 100,
    })
    with pytest.raises(ValueError, match="does not overlap"):
        run_holdout_validation(
            {"type": "rsi_trend_v2", "period": 11, "pullback_low": 40,
             "pullback_high": 70, "trend_period": 50},
            candles, "2023-09-01", "1h", "1d",
        )


def test_holdout_validation_runs_on_later_candles_without_reselecting(monkeypatch):
    candles = pd.DataFrame({
        "timestamp": pd.date_range("2023-09-30", periods=100, freq="h"),
        "local_regime": ["SIDEWAYS"] * 100,
        "higher_regime": ["UP"] * 100,
    })
    seen = {}

    def fake_run_backtest(config, data, backtest_config=None):
        seen["config"] = dict(config)
        seen["start"] = data["timestamp"].min()
        seen["rows"] = len(data)
        seen["backtest_config"] = dict(backtest_config or {})
        return {
            "equity_curve": [1.0, 1.05], "final_equity": 1.05, "roi": 5.0,
            "drawdown": 0.0, "gross_profit": 0.05, "gross_loss": 0.0,
            "winning_trades": 1, "losing_trades": 0, "trades": 1,
            "trade_log": [{"entry_bar": 0, "exit_bar": 1, "pnl_pct": 5.0}],
        }

    monkeypatch.setattr(discovery_engine, "run_backtest", fake_run_backtest)
    config = {"type": "rsi_trend_v2", "period": 11, "pullback_low": 40,
              "pullback_high": 70, "trend_period": 50}
    result = run_holdout_validation(
        config, candles, "2023-10-01", "1h", "1d",
        backtest_config={"fees_bps": 10.0, "slippage_pct": 0.0005},
        min_regime_trades=1,
    )

    assert seen["config"] == config
    assert seen["start"] == pd.Timestamp("2023-10-01 00:00:00")
    assert seen["backtest_config"]["fees_bps"] == 10.0
    assert seen["rows"] == int((candles["timestamp"] >= pd.Timestamp("2023-10-01")).sum())
    assert result["metrics"]["roi_pct"] == 5.0
    assert result["regime_profile"]["by_regime"][0]["higher_regime"] == "UP"
    assert result["regime_profile"]["by_regime"][0]["local_regime"] == "SIDEWAYS"
