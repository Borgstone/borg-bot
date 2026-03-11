import sqlite3
import os
from datetime import datetime


DB_PATH = "/app/research/research.db"


def get_conn():
    os.makedirs("/app/research", exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS experiments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        timeframe TEXT,
        strategy TEXT,
        started_at TEXT,
        completed_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS results (
        experiment_id INTEGER,
        fast INTEGER,
        slow INTEGER,
        roi REAL,
        drawdown REAL,
        trades INTEGER,
        score REAL
    )
    """)

    conn.commit()
    conn.close()


def create_experiment(symbol, timeframe, strategy):
    conn = get_conn()
    cur = conn.cursor()

    now = datetime.utcnow().isoformat()

    cur.execute(
        "INSERT INTO experiments(symbol,timeframe,strategy,started_at) VALUES (?,?,?,?)",
        (symbol, timeframe, strategy, now),
    )

    exp_id = cur.lastrowid
    conn.commit()
    conn.close()

    return exp_id


def complete_experiment(exp_id):
    conn = get_conn()
    cur = conn.cursor()

    now = datetime.utcnow().isoformat()

    cur.execute(
        "UPDATE experiments SET completed_at=? WHERE id=?",
        (now, exp_id),
    )

    conn.commit()
    conn.close()


def insert_result(exp_id, fast, slow, roi, drawdown, trades, score):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO results VALUES (?,?,?,?,?,?,?)",
        (exp_id, fast, slow, roi, drawdown, trades, score),
    )

    conn.commit()
    conn.close()