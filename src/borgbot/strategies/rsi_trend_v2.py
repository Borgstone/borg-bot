from borgbot.indicators.rsi import rsi
from borgbot.indicators.sma import sma
from .base import Strategy


class RSITrendV2Strategy(Strategy):

    def generate_signal(self, df, i):

        if i < self.trend_period:
            return 0

        price = df["close"].iloc[i]

        if i == 200:
            print("DEBUG STRATEGY")
            print("PRICE:", price)

            print("SMA:", df[f"sma_{self.trend_period}"].iloc[i])

            print("RSI:", df[f"rsi_{self.period}"].iloc[i])

            print(df.columns.tolist())

        sma = df[f"sma_{self.trend_period}"].iloc[i]

        rsi = df[f"rsi_{self.period}"].iloc[i]
        prev_rsi = df[f"rsi_{self.period}"].iloc[i - 1]

        # -------------------------
        # CONTEXT LAYER
        # -------------------------

        trend_up = price > sma
        trend_down = price < sma

        # -------------------------
        # SETUP LAYER
        # -------------------------

        bullish_pullback = rsi < 50
        bearish_pullback = rsi > 50

        # -------------------------
        # TRIGGER LAYER
        # -------------------------

        rsi_turning_up = rsi > prev_rsi
        rsi_turning_down = rsi < prev_rsi

        # -------------------------
        # LONG
        # -------------------------

        if trend_up and bullish_pullback and rsi_turning_up:
            return 1

        # -------------------------
        # SHORT
        # -------------------------

        if trend_down and bearish_pullback and rsi_turning_down:
            return -1

    return 0