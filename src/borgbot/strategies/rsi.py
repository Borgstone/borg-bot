from borgbot.strategies.base import Strategy


class RSIStrategy(Strategy):

    def generate_signal(self, df, i):

        period = self.config.get("period", 14)
        overbought = self.config.get("overbought", 70)
        oversold = self.config.get("oversold", 30)

        rsi_col = f"rsi_{period}"

        if rsi_col not in df:
            return 0

        value = df[rsi_col].iloc[i]

        if value != value:
            return 0

        if value < oversold:
            return 1

        if value > overbought:
            return -1

        return 0