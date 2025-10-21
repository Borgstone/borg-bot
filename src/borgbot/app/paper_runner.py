import os, time, traceback, uuid
from datetime import datetime
import pytz
from pydantic import BaseModel
from borgbot.infra.logging import configure_logging
from borgbot.infra.config import load_config
from borgbot.infra.ids import run_id
from borgbot.adapters.exchange import ExchangeAdapter
from borgbot.core.strategy import SMAConfig, sma_cross_strategy
from borgbot.core.execution import paper_trade_once
from borgbot.core.risk import RiskState, is_in_window, daily_loss_breached
from borgbot.state.store import connect, get_last_candle_ts, set_last_candle_ts, get_position, set_position

TF_MS = {"1m":60000, "3m":180000, "5m":300000, "15m":900000, "30m":1800000, "1h":3600000}

def sleep_until_next_close(timeframe: str, grace_s: int = 2):
    tf_ms = TF_MS.get(timeframe, 60000)
    now = int(time.time() * 1000)
    next_close = ((now // tf_ms) + 1) * tf_ms + (grace_s * 1000)
    sleep_s = max(1, (next_close - now) / 1000.0); time.sleep(sleep_s)

def equity_from_state(conn, last_price: float) -> float:
    base_qty, cash, avg = get_position(conn)
    return cash + base_qty * last_price

def ensure_starting_cash(conn, starting_cash: float, logger):
    base_qty, cash, _ = get_position(conn)
    if base_qty == 0.0 and cash == 0.0:
        set_position(conn, 0.0, starting_cash, 0.0)
        logger.info("init.cash", starting_cash=starting_cash)

def main():
    rid = run_id()
    logger = configure_logging(run_id=rid)
    cfg = load_config()
    logger.info("app.start", settings=cfg.model_dump())

    conn = connect()
    ensure_starting_cash(conn, cfg.starting_cash, logger)
    ex = ExchangeAdapter(cfg.exchange)

    # risk day-open state (local time)
    tz = pytz.timezone(os.environ.get("TZ", "Europe/Dublin"))
    last_ts = get_last_candle_ts(conn)
    rs = None  # RiskState set after first price

    while True:
        try:
            ohlcv = ex.ohlcv(cfg.symbol, cfg.timeframe, limit=max(100, cfg.sma_slow + 10), since=None)
            ts = [int(r[0]) for r in ohlcv]; closes = [float(r[4]) for r in ohlcv]; latest_ts = ts[-1]

            if last_ts is None: last_ts = latest_ts - 1
            if latest_ts == last_ts:
                sleep_until_next_close(cfg.timeframe, grace_s=2)
                continue

            price = closes[-1]
            now_local = datetime.now(tz)

            # init risk state at first tick of the local day
            day_ymd = now_local.strftime("%Y-%m-%d")
            if rs is None or rs.day_ymd != day_ymd:
                eq = equity_from_state(conn, price)
                rs = RiskState(day_open_equity=eq, day_ymd=day_ymd)
                logger.info("risk.day_start", equity_open=eq, day=day_ymd)

            # checks: trading window + daily loss
            if not is_in_window(now_local, cfg.risk.trading_window):
                logger.info("risk.pause_outside_window", now=str(now_local), window=cfg.risk.trading_window)
                sleep_until_next_close(cfg.timeframe, grace_s=2)
                set_last_candle_ts(conn, latest_ts); last_ts = latest_ts
                continue

            eq = equity_from_state(conn, price)
            if daily_loss_breached(eq, rs, cfg.risk.daily_max_loss_pct):
                logger.error("risk.halt_daily_loss", equity=eq, day_open=rs.day_open_equity, max_loss_pct=cfg.risk.daily_max_loss_pct)
                time.sleep(60)  # park; we keep process alive but idle
                set_last_candle_ts(conn, latest_ts); last_ts = latest_ts
                continue

            # strategy decision on closed candles only
            signal = sma_cross_strategy(closes, SMAConfig(fast=cfg.sma_fast, slow=cfg.sma_slow))
            if signal in ("buy","sell"):
                paper_trade_once(conn, logger, side=signal, price=price,
                                 fees_bps=cfg.fees_bps, slippage_pct=cfg.slippage_pct, size_frac=1.0)
            else:
                logger.info("signal.hold", price=price)

            set_last_candle_ts(conn, latest_ts); last_ts = latest_ts
            sleep_until_next_close(cfg.timeframe, grace_s=2)

        except Exception as e:
            msg = str(e); backoff = 65 if "429" in msg else min(60, cfg.poll_seconds * 2)
            logger.error("loop.error", error=msg, backoff=backoff, tb=traceback.format_exc())
            time.sleep(backoff)

if __name__ == "__main__":
    main()
