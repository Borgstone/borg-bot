from borgbot.indicators.rsi import rsi
from .base import Strategy

class RSIStrategy(Strategy):

    def generate_signal(self, context) -> float:

        candles = context["candles"]
        closes = candles["close"]

        period = self.config.get("period", 14)
        overbought = self.config.get("overbought", 70)
        oversold = self.config.get("oversold", 30)

        rsi_series = rsi(closes, period)

        if len(rsi_series) < period:
            return 0.0

        value = rsi_series.iloc[-1]

        if value != value:  # NaN protection
            return 0.0

        if value < oversold:
            return 1.0
        elif value > overbought:
            return -1.0
        else:
            return 0.0