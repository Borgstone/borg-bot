from borgbot.strategies.base import Strategy
from borgbot.indicators.sma import sma

class SMAStrategy(Strategy):

    def generate_signal(self, context) -> float:

        candles = context["candles"]

        fast = self.config.get("fast", 9)
        slow = self.config.get("slow", 21)

        if len(candles) < slow:
            return 0.0

        closes = [c["close"] for c in candles]

        fast_sma = sma(closes, fast)
        slow_sma = sma(closes, slow)

        if fast_sma > slow_sma:
            return 1.0

        if fast_sma < slow_sma:
            return -1.0

        return 0.0