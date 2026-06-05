from borgbot.strategies.base import Strategy


class SMAStrategy(Strategy):

    def generate_signal(self, df, i):

        fast_col = f"sma_{self.config['fast']}"
        slow_col = f"sma_{self.config['slow']}"

        if fast_col not in df:
            return 0

        if slow_col not in df:
            return 0

        fast = df[fast_col].iloc[i]
        slow = df[slow_col].iloc[i]

        if fast != fast or slow != slow:
            return 0

        if fast > slow:
            return 1

        if fast < slow:
            return -1

        return 0