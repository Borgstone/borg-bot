from borgbot.strategies.base import Strategy
from borgbot.indicators.rsi import rsi


class RSIStrategy(Strategy):

    def __init__(self, period=14, overbought=70, oversold=30):
        self.period = period
        self.overbought = overbought
        self.oversold = oversold

    def generate_signal(self, candles):

        if len(candles) < self.period:
            return None

        closes = [c["close"] for c in candles]

        value = rsi(closes, self.period)

        if value < self.oversold:
            return "buy"

        if value > self.overbought:
            return "sell"

        return None