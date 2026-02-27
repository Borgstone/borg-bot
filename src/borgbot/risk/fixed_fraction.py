class FixedFractionSizing(RiskEngine):
    def __init__(self, fraction=0.1):
        self.fraction = fraction

    def calculate_position_size(self, equity, price, context):
        return (equity * self.fraction) / price