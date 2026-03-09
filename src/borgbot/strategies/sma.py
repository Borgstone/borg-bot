from borgbot.strategies.base import Strategy
from borgbot.indicators.sma import sma


class SMAStrategy(Strategy):

    def __init__(self, fast=9, slow=21):
        self.fast = fast
        self.slow = slow

    def generate_signal(self, candles):
        if len(candles) < self.slow:
            return None

        closes = [c["close"] for c in candles]

        fast_sma = sma(closes, self.fast)
        slow_sma = sma(closes, self.slow)

        if fast_sma > slow_sma:
            return "buy"

        if fast_sma < slow_sma:
            return "sell"

        return None