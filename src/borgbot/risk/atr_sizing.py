class ATRSizing(RiskEngine):
    def __init__(self, atr_period=14, risk_per_trade=0.01):
        self.atr_period = atr_period
        self.risk_per_trade = risk_per_trade

    def calculate_position_size(self, equity, price, context):
        atr = context.atr  # will inject later
        risk_amount = equity * self.risk_per_trade
        stop_distance = atr
        if stop_distance == 0:
            return 0.0
        qty = risk_amount / stop_distance
        return qty