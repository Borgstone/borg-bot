class RSITrendV2Strategy:

    def __init__(self, config):

        self.period = config["period"]

        self.pullback_low = config["pullback_low"]
        self.pullback_high = config["pullback_high"]

        self.trend_period = config["trend_period"]

        # -------------------------
        # DEBUG COUNTERS
        # -------------------------

        self.debug_trend_up = 0
        self.debug_trend_down = 0

        self.debug_pullback_long = 0
        self.debug_pullback_short = 0

        self.debug_trigger_long = 0
        self.debug_trigger_short = 0

        self.debug_final_long = 0
        self.debug_final_short = 0

    def generate_signal(self, df, i):

        if i == 200:
            print(df.columns.tolist())
            print(df[[f"rsi_{self.period}"]].tail())
            print(df[[f"sma_{self.trend_period}"]].tail())

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

        # -------------------------
        # TREND LAYER
        # -------------------------

        trend_up = price > sma
        trend_down = price < sma

        if trend_up:
            self.debug_trend_up += 1

        if trend_down:
            self.debug_trend_down += 1

        # -------------------------
        # PULLBACK LAYER
        # -------------------------

        bullish_pullback = (
            rsi >= self.pullback_low
            and rsi <= self.pullback_high
        )

        bearish_pullback = (
            rsi >= (100 - self.pullback_high)
            and rsi <= (100 - self.pullback_low)
        )

        if bullish_pullback:
            self.debug_pullback_long += 1

        if bearish_pullback:
            self.debug_pullback_short += 1

        # -------------------------
        # TRIGGER LAYER
        # -------------------------

        rsi_turning_up = rsi > prev_rsi
        rsi_turning_down = rsi < prev_rsi

        if rsi_turning_up:
            self.debug_trigger_long += 1

        if rsi_turning_down:
            self.debug_trigger_short += 1

        # -------------------------
        # FINAL LONG
        # -------------------------

        if trend_up and bullish_pullback and rsi_turning_up:

            self.debug_final_long += 1

            return 1

        # -------------------------
        # FINAL SHORT
        # -------------------------

        if trend_down and bearish_pullback and rsi_turning_down:

            self.debug_final_short += 1

            return -1

        # -------------------------
        # DEBUG OUTPUT
        # -------------------------

        if i == len(df) - 1:

            print("\nDEBUG STRATEGY COUNTS")
            print("----------------------")

            print("Trend Up:", self.debug_trend_up)
            print("Trend Down:", self.debug_trend_down)

            print("Bull Pullback:", self.debug_pullback_long)
            print("Bear Pullback:", self.debug_pullback_short)

            print("RSI Up:", self.debug_trigger_long)
            print("RSI Down:", self.debug_trigger_short)

            print("Final Long Signals:", self.debug_final_long)
            print("Final Short Signals:", self.debug_final_short)

        return 0