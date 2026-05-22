from borgbot.indicators.rsi import rsi
from borgbot.indicators.sma import sma
from .base import Strategy


class RSITrendV2Strategy(Strategy):

    def generate_signal(self, df, i) -> float:

        candles = context["candles"]
        closes = candles["close"]

        # === CONFIG
        period = self.config.get("period", 14)
        trend_period = self.config.get("trend_period", 50)

        pullback_low = self.config.get("pullback_low", 35)
        pullback_high = self.config.get("pullback_high", 65)

        # === INDICATORS
        rsi_series = rsi(closes, period)

        if len(rsi_series) < 2:
            return 0.0

        rsi_now = rsi_series.iloc[-1]
        rsi_prev = rsi_series.iloc[-2]

        sma_col = f"sma_{trend_period}"
        if sma_col not in candles:
            return 0.0

        sma_series = candles[sma_col]
        if len(sma_series) < trend_period:
            return 0.0

        trend_value = sma_series.iloc[-1]
        price = closes.iloc[-1]

        # === SAFETY
        if trend_value != trend_value:  # NaN
            return 0.0

        # =========================
        # 🟢 CONTEXT LAYER (TREND)
        # =========================
        if price > trend_value:
            trend = "up"
        elif price < trend_value:
            trend = "down"
        else:
            return 0.0

        # =========================
        # 🔵 SETUP LAYER (PULLBACK)
        # =========================
        setup_long = (
            trend == "up" and
            rsi_now < pullback_low
        )

        setup_short = (
            trend == "down" and
            rsi_now > pullback_high
        )

        # =========================
        # 🟡 TRIGGER LAYER (TURN)
        # =========================
        trigger_long = (
            setup_long and
            rsi_now > rsi_prev  # RSI turning up
        )

        trigger_short = (
            setup_short and
            rsi_now < rsi_prev  # RSI turning down
        )

        # =========================
        # 🎯 DECISION
        # =========================
        if trigger_long:
            return 1.0

        if trigger_short:
            return -1.0

        return 0.0