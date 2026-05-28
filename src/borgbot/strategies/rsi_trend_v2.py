class RSITrendV2Strategy:

    def __init__(self, config):

        self.period = config["period"]

        self.pullback_low = config["pullback_low"]
        self.pullback_high = config["pullback_high"]

        self.trend_period = config["trend_period"]

    def generate_signal(self, df, i):

        # Need enough candles
        if i < self.trend_period:
            return 0

        # -------------------------
        # VALUES
        # -------------------------

        price = df["close"].iloc[i]

        sma = df[f"sma_{self.trend_period}"].iloc[i]

        rsi = df[f"rsi_{self.period}"].iloc[i]
        prev_rsi = df[f"rsi_{self.period}"].iloc[i - 1]

        # DEBUG
        if i == 200:
            print("DEBUG STRATEGY")
            print("PRICE:", price)
            print("SMA:", sma)
            print("RSI:", rsi)

        # -------------------------
        # TREND
        # -------------------------

        trend_up = price > sma
        trend_down = price < sma

        # -------------------------
        # PULLBACK
        # -------------------------

        bullish_pullback = rsi < 50
        bearish_pullback = rsi > 50

        # -------------------------
        # TRIGGER
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