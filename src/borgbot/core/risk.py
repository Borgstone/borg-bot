from dataclasses import dataclass
from datetime import datetime, time as dtime
from typing import Tuple
import pytz

def parse_window(win: str) -> Tuple[dtime, dtime]:
    a,b = win.split("-")
    h1,m1 = map(int, a.split(":"))
    h2,m2 = map(int, b.split(":"))
    return dtime(h1,m1), dtime(h2,m2)

@dataclass
class RiskState:
    day_open_equity: float
    day_ymd: str     # e.g. "2025-10-15"

def is_in_window(now_local: datetime, window: str) -> bool:
    start, end = parse_window(window)
    t = now_local.time()
    return start <= t <= end if start <= end else (t >= start or t <= end)

def daily_loss_breached(equity: float, rs: RiskState, max_loss_pct: float) -> bool:
    if rs.day_open_equity <= 0: return False
    dd = (equity - rs.day_open_equity) / rs.day_open_equity
    return dd <= -abs(max_loss_pct)
