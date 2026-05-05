from borgbot.indicators.rsi import rsi
from borgbot.indicators.sma import sma
from .base import Strategy


class RSITrendStrategy(Strategy):

    def generate_signal(self, context) -> float:

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

        # === LONG (trend + pullback + momentum up)
        if (
            price > trend_value and                # Uptrend
            rsi_now > pullback_low and             # RSI recovering
            rsi_prev <= pullback_low and           # Was below → now rising
            rsi_now > rsi_prev                     # Momentum up
        ):
            return 1.0

        # === SHORT (trend + pullback + momentum down)
        if (
            price < trend_value and                # Downtrend
            rsi_now < pullback_high and            # RSI dropping
            rsi_prev >= pullback_high and          # Was above → now falling
            rsi_now < rsi_prev                     # Momentum down
        ):
            return -1.0

        return 0.0