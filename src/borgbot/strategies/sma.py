from borgbot.strategies.base import Strategy
from borgbot.indicators.sma import sma


class SMAStrategy(Strategy):

    def generate_signal(self, context):

        candles = context["candles"]

        closes = context["candles"]["close"]

        if len(closes) < 30:
            return 0.0

        fast = sma(closes, self.config["fast"])
        slow = sma(closes, self.config["slow"])

        if fast > slow:
            return 1.0

        if fast < slow:
            return -1.0

        return 0.0