from borgbot.strategies.base import Strategy


class RSITrendV2Strategy(Strategy):

    def __init__(self, config):

        super().__init__(config)

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

        # -------------------------
        # REQUIRED INDICATORS
        # -------------------------

        rsi_col = f"rsi_{self.period}"
        sma_col = f"sma_{self.trend_period}"

        if rsi_col not in df or sma_col not in df:
            return 0

        # -------------------------
        # NEED ENOUGH DATA
        # -------------------------

        minimum_history = max(
            self.period + 1,
            self.trend_period,
        )

        if i < minimum_history:
            return 0

        # -------------------------
        # VALUES
        # -------------------------

        price = df["close"].iloc[i]

        sma_value = df[sma_col].iloc[i]

        rsi_value = df[rsi_col].iloc[i]
        prev_rsi = df[rsi_col].iloc[i - 1]

        # NaN protection
        if (
            price != price
            or sma_value != sma_value
            or rsi_value != rsi_value
            or prev_rsi != prev_rsi
        ):
            return 0

        # -------------------------
        # TREND LAYER
        # -------------------------

        trend_up = price > sma_value
        trend_down = price < sma_value

        if trend_up:
            self.debug_trend_up += 1

        if trend_down:
            self.debug_trend_down += 1

        # -------------------------
        # PULLBACK LAYER
        # -------------------------

        bullish_pullback = (
            rsi_value >= self.pullback_low
            and rsi_value <= self.pullback_high
        )

        bearish_pullback = (
            rsi_value >= (100 - self.pullback_high)
            and rsi_value <= (100 - self.pullback_low)
        )

        if bullish_pullback:
            self.debug_pullback_long += 1

        if bearish_pullback:
            self.debug_pullback_short += 1

        # -------------------------
        # TRIGGER LAYER
        # -------------------------

        rsi_turning_up = rsi_value > prev_rsi
        rsi_turning_down = rsi_value < prev_rsi

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