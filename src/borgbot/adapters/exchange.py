from typing import List, Tuple, Optional
import ccxt
TIMEFRAME_MAP = {"1m":"1m","3m":"3m","5m":"5m","15m":"15m","30m":"30m","1h":"1h"}
class ExchangeAdapter:
    def __init__(self, name: str):
        name = name.lower()
        if name != "kucoin": raise ValueError("Only 'kucoin' supported in MVP")
        self.ex = ccxt.kucoin({
            "enableRateLimit": True,
            "options": {"adjustForTimeDifference": True},
            "timeout": 20000,
        })
        self.ex.load_markets()
    def ohlcv(self, symbol: str, timeframe: str, limit: int = 200, since: Optional[int] = None) -> List[List[float]]:
        tf = TIMEFRAME_MAP.get(timeframe, "1m")
        return self.ex.fetch_ohlcv(symbol, timeframe=tf, since=since, limit=limit)
    @staticmethod
    def closes_from_ohlcv(ohlcv: List[List[float]]) -> Tuple[List[int], List[float]]:
        ts = [int(r[0]) for r in ohlcv]; closes = [float(r[4]) for r in ohlcv]; return ts, closes
