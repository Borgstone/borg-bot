import sqlite3

from borgbot.research.discovery_engine import ensure_discovery_schema


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
