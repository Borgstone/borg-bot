from borgbot.indicators.rsi import rsi
from .base import Strategy
from borgbot.indicators.sma import sma

class RSIStrategy(Strategy):

    def generate_signal(self, context) -> float:

        candles = context["candles"]
        closes = candles["close"]

        period = self.config.get("period", 14)
        overbought = self.config.get("overbought", 70)
        oversold = self.config.get("oversold", 30)

        rsi_series = rsi(closes, period)
        trend_period = self.config.get("trend_period", 50)
        sma_series = candles[f"sma_{trend_period}"]

        if len(sma_series) < trend_period:
            return 0.0

        trend_value = sma_series.iloc[-1]
        price = closes.iloc[-1]

        if len(rsi_series) < period:
            return 0.0

        value = rsi_series.iloc[-1]

        if value != value:  # NaN protection
            return 0.0

        # BUY only in uptrend
        if value < oversold and price > trend_value:
            return 1.0

        # SELL only in downtrend
        elif value > overbought and price < trend_value:
            return -1.0