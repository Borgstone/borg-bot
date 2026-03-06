import pandas as pd
from borgbot.trading.engine import TradingEngine

class BacktestEngine:

    def __init__(self, engine: TradingEngine, data: pd.DataFrame):
        self.engine = engine
        self.data = data
        self.equity_curve = []

    def run(self):

        for _, candle in self.data.iterrows():

            price = candle["close"]

            self.engine.on_price(price)

            equity = self.engine.get_equity(price)

            self.equity_curve.append(
                {
                    "timestamp": candle["timestamp"],
                    "equity": equity,
                }
            )

        return pd.DataFrame(self.equity_curve)