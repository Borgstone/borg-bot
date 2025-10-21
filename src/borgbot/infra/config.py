import os, yaml
from pydantic import BaseModel

class RiskConfig(BaseModel):
    daily_max_loss_pct: float = 0.05   # halt if equity down ≥5% vs day-open
    trading_window: str = "00:00-23:59"  # local time window HH:MM-HH:MM

class AppConfig(BaseModel):
    exchange: str = os.environ.get("EXCHANGE", "kucoin")
    symbol: str = os.environ.get("SYMBOL", "BTC/USDT")
    timeframe: str = os.environ.get("TIMEFRAME", "1m")
    poll_seconds: int = int(os.environ.get("POLL_SECONDS", "15"))
    sma_fast: int = int(os.environ.get("SMA_FAST", "9"))
    sma_slow: int = int(os.environ.get("SMA_SLOW", "21"))
    fees_bps: float = float(os.environ.get("FEES_BPS", "10"))
    slippage_pct: float = float(os.environ.get("SLIPPAGE_PCT", "0.0005"))
    starting_cash: float = float(os.environ.get("STARTING_CASH", "1000"))
    risk: RiskConfig = RiskConfig()

def load_config(path: str = "/app/config.yaml") -> AppConfig:
    # YAML is optional; env always wins
    if os.path.exists(path):
        with open(path, "r") as f:
            data = yaml.safe_load(f) or {}
    else:
        data = {}
    # nested 'risk' dict if present
    rc = RiskConfig(**data.get("risk", {}))
    ac = AppConfig(**{k:v for k,v in data.items() if k != "risk"})
    ac.risk = rc
    return ac
