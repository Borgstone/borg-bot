from borgbot.risk.base import RiskEngine


class FixedFractionSizing(RiskEngine):

    def __init__(self, config):
        self.max_position_frac = config.get("max_position_frac", 0.1)
        self.min_cash_buffer_frac = config.get("min_cash_buffer_frac", 0.1)

    def calculate_position_size(self, equity: float, price: float) -> float:
        """
        Returns quantity to buy/sell.
        """

        capital = equity * self.max_position_frac
        qty = capital / price

        return qty