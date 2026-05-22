from borgbot.indicators.rsi import rsi
from borgbot.indicators.sma import sma
from .base import Strategy


class RSITrendStrategy(Strategy):

    def generate_signal(self, df, i) -> float:

        candles = context["candles"]
        closes = candles["close"]

        # -------------------------
        # CONFIG
        # -------------------------
        period = self.config.get("period", 14)

        # Pullback levels (NOT extreme RSI)
        pullback_low = self.config.get("pullback_low", 40)
        pullback_high = self.config.get("pullback_high", 60)

        trend_period = self.config.get("trend_period", 50)

        # -------------------------
        # INDICATORS
        # -------------------------
        rsi_series = rsi(closes, period)

        if len(rsi_series) < period + 2:
            return 0.0

        # RSI values
        rsi_now = rsi_series.iloc[-1]
        rsi_prev = rsi_series.iloc[-2]

        # SMA trend
        sma_series = sma(closes, trend_period)

        if len(sma_series) < trend_period:
            return 0.0

        trend_value = sma_series.iloc[-1]
        price = closes.iloc[-1]

        # Safety (NaN protection)
        if trend_value != trend_value:
            return 0.0

        # -------------------------
        # LOGIC
        # -------------------------

        # === LONG (trend + pullback zone)
        if (
            price > trend_value and
            rsi_now > pullback_low and
            rsi_now < pullback_high
        ):
            return 1.0

        # === SHORT (trend + pullback zone)
        if (
            price < trend_value and
            rsi_now < pullback_high and
            rsi_now > pullback_low
        ):
            return -1.0

        return 0.0