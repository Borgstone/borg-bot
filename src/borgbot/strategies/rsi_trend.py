from borgbot.indicators.rsi import rsi
from borgbot.indicators.sma import sma
from .base import Strategy


class RSITrendStrategy(Strategy):

    def generate_signal(self, context) -> float:

        candles = context["candles"]
        closes = candles["close"]

        if len(closes) < 100:
            return 0.0

        # CONFIG
        period = self.config.get("period", 14)
        overbought = self.config.get("overbought", 70)
        oversold = self.config.get("oversold", 30)
        trend_period = self.config.get("trend_period", 50)

        # INDICATORS
        rsi_series = rsi(closes, period)
        sma_series = sma(closes, trend_period)

        if len(rsi_series) == 0 or len(sma_series) == 0:
            return 0.0

        value = rsi_series.iloc[-1]
        trend_value = sma_series.iloc[-1]
        price = closes.iloc[-1]

        # NaN safety
        if value != value or trend_value != trend_value:
            return 0.0

        # -------------------
        # CONTEXT + TRIGGER
        # -------------------

        # UPTREND → BUY THE DIP
        if price > trend_value:
            if value < oversold:
                return 1.0

        # DOWNTREND → SELL THE RALLY
        elif price < trend_value:
            if value > overbought:
                return -1.0

        return 0.0