from borgbot.indicators.rsi import rsi
from .base import Strategy

class RSIStrategy(Strategy):

    def generate_signal(self, context) -> float:

        candles = context["candles"]
        closes = candles["close"]

        period = self.config.get("period", 14)
        overbought = self.config.get("overbought", 70)
        oversold = self.config.get("oversold", 30)
        trend_period = self.config.get("trend_period", 50)

        # --- RSI ---
        rsi_series = rsi(closes, period)

        if len(rsi_series) < period:
            return 0.0

        value = rsi_series.iloc[-1]

        if value != value:  # NaN
            return 0.0

        # --- TREND (from cache) ---
        col = f"sma_{trend_period}"

        if col not in candles:
            return 0.0

        sma_series = candles[col]

        if len(sma_series) < trend_period:
            return 0.0

        trend_value = sma_series.iloc[-1]
        price = closes.iloc[-1]

        if trend_value != trend_value:  # NaN
            return 0.0

        # --- SIGNAL LOGIC ---

        # BUY
        if value < oversold:
            if price > trend_value:
                return 1.0
            return 1.0

        # SELL
        elif value > overbought:
            if price < trend_value:
                return -1.0
            return -1.0

        return 0.0