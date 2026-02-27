from borgbot.risk.base import RiskEngine

class FixedFractionSizing(RiskEngine):
    def __init__(self, fraction: float):
        self.fraction = fraction

    def calculate_position_size(self, equity: float, price: float, context):
        if price <= 0:
            return 0.0
        return (equity * self.fraction) / price