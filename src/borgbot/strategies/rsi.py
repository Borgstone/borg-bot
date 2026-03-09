from borgbot.strategies.base import Strategy
from borgbot.indicators.rsi import rsi

class RSIStrategy(Strategy):

    def generate_signal(self, context) -> float:

        candles = context["candles"]

        period = self.config.get("period", 14)
        overbought = self.config.get("overbought", 70)
        oversold = self.config.get("oversold", 30)

        if len(candles) < period:
            return 0.0

        closes = [c["close"] for c in candles]

        value = rsi(closes, period)

        if value < oversold:
            return 1.0

        if value > overbought:
            return -1.0

        return 0.0