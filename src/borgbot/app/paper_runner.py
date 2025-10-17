import os, time, traceback
from pydantic import BaseModel
from borgbot.infra.logging import configure_logging
from borgbot.adapters.exchange import ExchangeAdapter
from borgbot.core.strategy import SMAConfig, sma_cross_strategy
from borgbot.core.execution import paper_trade_once
from borgbot.state.store import connect, get_last_candle_ts, set_last_candle_ts, get_position, set_position
TF_MS = {"1m":60000, "3m":180000, "5m":300000, "15m":900000, "30m":1800000, "1h":3600000}
class Settings(BaseModel):
    exchange: str = os.environ.get("EXCHANGE", "kucoin")
    symbol: str = os.environ.get("SYMBOL", "BTC/USDT")
    timeframe: str = os.environ.get("TIMEFRAME", "1m")
    poll_seconds: int = int(os.environ.get("POLL_SECONDS", "15"))
    sma_fast: int = int(os.environ.get("SMA_FAST", "9"))
    sma_slow: int = int(os.environ.get("SMA_SLOW", "21"))
    fees_bps: float = float(os.environ.get("FEES_BPS", "10"))
    slippage_pct: float = float(os.environ.get("SLIPPAGE_PCT", "0.0005"))
    starting_cash: float = float(os.environ.get("STARTING_CASH", "1000"))
def ensure_starting_cash(conn, starting_cash: float, logger):
    base_qty, cash, _ = get_position(conn)
    if base_qty == 0.0 and cash == 0.0:
        set_position(conn, 0.0, starting_cash, 0.0); logger.info("init.cash", starting_cash=starting_cash)
def sleep_until_next_close(timeframe: str, grace_s: int = 2):
    tf_ms = TF_MS.get(timeframe, 60000)
    now = int(time.time() * 1000)
    next_close = ((now // tf_ms) + 1) * tf_ms + (grace_s * 1000)
    sleep_s = max(1, (next_close - now) / 1000.0); time.sleep(sleep_s)
def main():
    logger = configure_logging(); cfg = Settings()
    logger.info("app.start", settings=cfg.model_dump())
    conn = connect(); ensure_starting_cash(conn, cfg.starting_cash, logger)
    ex = ExchangeAdapter(cfg.exchange); last_ts = get_last_candle_ts(conn)
    while True:
        try:
            ohlcv = ex.ohlcv(cfg.symbol, cfg.timeframe, limit=max(100, cfg.sma_slow + 10), since=None)
            ts = [int(r[0]) for r in ohlcv]; closes = [float(r[4]) for r in ohlcv]; latest_ts = ts[-1]
            if last_ts is None: last_ts = latest_ts - 1
            if latest_ts == last_ts: sleep_until_next_close(cfg.timeframe, grace_s=2); continue
            signal = sma_cross_strategy(closes, SMAConfig(fast=cfg.sma_fast, slow=cfg.sma_slow)); price = closes[-1]
            if signal in ("buy","sell"):
                paper_trade_once(conn, logger, side=signal, price=price, fees_bps=cfg.fees_bps, slippage_pct=cfg.slippage_pct, size_frac=1.0)
            else: logger.info("signal.hold", price=price)
            set_last_candle_ts(conn, latest_ts); last_ts = latest_ts
            sleep_until_next_close(cfg.timeframe, grace_s=2)
        except Exception as e:
            msg = str(e); backoff = 65 if "429" in msg else min(60, cfg.poll_seconds * 2)
            logger.error("loop.error", error=msg, tb=traceback.format_exc(), backoff=backoff)
            time.sleep(backoff)
if __name__ == "__main__": main()
