import sqlite3, os
from typing import Optional, Tuple

DB_PATH = os.environ.get("DB_PATH", "/app/state/borg.db")
DDL = [
    "CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT)",
    "CREATE TABLE IF NOT EXISTS position (id INTEGER PRIMARY KEY CHECK (id=1), base_qty REAL NOT NULL DEFAULT 0.0, cash REAL NOT NULL DEFAULT 0.0, avg_price REAL NOT NULL DEFAULT 0.0)",
    "CREATE TABLE IF NOT EXISTS trades (id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER NOT NULL, side TEXT NOT NULL, qty REAL NOT NULL, price REAL NOT NULL, fee REAL NOT NULL, cash_after REAL NOT NULL, base_after REAL NOT NULL)",
]

def connect():
    conn = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL;")
    for ddl in DDL:
        conn.execute(ddl)
    cur = conn.execute("SELECT COUNT(*) FROM position")
    (n,) = cur.fetchone()
    if n == 0:
        conn.execute("INSERT INTO position(id, base_qty, cash, avg_price) VALUES (1, 0.0, 0.0, 0.0)")
    return conn

def get_last_candle_ts(conn) -> Optional[int]:
    cur = conn.execute("SELECT v FROM kv WHERE k='last_candle_ts'")
    row = cur.fetchone()
    return int(row[0]) if row else None

def set_last_candle_ts(conn, ts: int):
    conn.execute(
        "INSERT INTO kv(k,v) VALUES('last_candle_ts', ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
        (str(ts),),
    )

def get_position(conn) -> Tuple[float, float, float]:
    cur = conn.execute("SELECT base_qty, cash, avg_price FROM position WHERE id=1")
    return cur.fetchone()

def set_position(conn, base_qty: float, cash: float, avg_price: float):
    conn.execute("UPDATE position SET base_qty=?, cash=?, avg_price=? WHERE id=1", (base_qty, cash, avg_price))

def add_trade(conn, ts:int, side:str, qty:float, price:float, fee:float, cash_after:float, base_after:float):
    conn.execute(
        "INSERT INTO trades(ts, side, qty, price, fee, cash_after, base_after) VALUES (?,?,?,?,?,?,?)",
        (ts, side, qty, price, fee, cash_after, base_after),
    )
