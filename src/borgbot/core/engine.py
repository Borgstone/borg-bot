class TradingEngine:
    def __init__(self, strategy_stack, risk_engine, execution):
        self.strategy_stack = strategy_stack
        self.risk_engine = risk_engine
        self.execution = execution

    def on_new_candle(self, context, equity, price):
        signal = self.strategy_stack.generate_signal(context)

        if signal > 0:
            qty = self.risk_engine.calculate_position_size(equity, price, context)
            self.execution.execute_order("buy", qty, price)

        elif signal < 0:
            qty = self.risk_engine.calculate_position_size(equity, price, context)
            self.execution.execute_order("sell", qty, price)