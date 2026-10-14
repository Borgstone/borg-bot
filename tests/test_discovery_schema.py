import sqlite3

import pandas as pd
import pytest

from borgbot.research.discovery_engine import (
    ensure_discovery_schema,
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
