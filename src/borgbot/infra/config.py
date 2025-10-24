# src/borgbot/infra/config.py
import os
import yaml
from typing import Any, Dict

def _to_int(v, default): 
    try: return int(v)
    except: return default

def _to_float(v, default):
    try: return float(v)
    except: return default

def _env_override(cfg: Dict[str, Any]) -> Dict[str, Any]:
    # base fields
    cfg['exchange']      = os.environ.get('EXCHANGE', cfg.get('exchange', 'kucoin'))
    cfg['symbol']        = os.environ.get('SYMBOL',   cfg.get('symbol', 'BTC/USDT'))
    cfg['timeframe']     = os.environ.get('TIMEFRAME',cfg.get('timeframe', '1m'))
    cfg['poll_seconds']  = _to_int(  os.environ.get('POLL_SECONDS'),  cfg.get('poll_seconds', 15))
    cfg['sma_fast']      = _to_int(  os.environ.get('SMA_FAST'),      cfg.get('sma_fast', 9))
    cfg['sma_slow']      = _to_int(  os.environ.get('SMA_SLOW'),      cfg.get('sma_slow', 21))
    cfg['fees_bps']      = _to_float(os.environ.get('FEES_BPS'),      cfg.get('fees_bps', 10.0))
    cfg['slippage_pct']  = _to_float(os.environ.get('SLIPPAGE_PCT'),  cfg.get('slippage_pct', 0.0005))
    cfg['starting_cash'] = _to_float(os.environ.get('STARTING_CASH'), cfg.get('starting_cash', 1000.0))

    # risk nested
    risk = cfg.get('risk', {}) or {}
    risk['daily_max_loss_pct'] = _to_float(os.environ.get('RISK_DAILY_MAX_LOSS_PCT'), risk.get('daily_max_loss_pct', 0.05))
    risk['trading_window']     = os.environ.get('RISK_TRADING_WINDOW', risk.get('trading_window', '00:00-23:59'))
    cfg['risk'] = risk

    return cfg

def load_config(path: str = "/app/config.yaml") -> Dict[str, Any]:
    with open(path, "r") as f:
        cfg = yaml.safe_load(f) or {}
    return _env_override(cfg)
