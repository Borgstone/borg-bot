import pandas as pd


class BacktestEngine:

    def __init__(
        self,
        strategy,
        starting_cash: float = 1000.0,
        fees_bps: float = 10.0,
        slippage_pct: float = 0.0005
    ):
        self.strategy = strategy
        self.cash = starting_cash
        self.position = 0.0
        self.fees_bps = fees_bps
        self.slippage_pct = slippage_pct
        self.trades = []

    def run(self, candles: pd.DataFrame):

        for i in range(50, len(candles)):

            window = candles.iloc[:i]
            price = candles.iloc[i]["close"]

            signal = self.strategy.generate_signal(window)

            # BUY
            if signal > 0 and self.position == 0:

                qty = self.cash / price
                cost = qty * price

                fee = cost * self.fees_bps / 10000

                self.cash -= cost + fee
                self.position = qty

                self.trades.append(("buy", price))

            # SELL
            elif signal < 0 and self.position > 0:

                value = self.position * price
                fee = value * self.fees_bps / 10000

                self.cash += value - fee
                self.position = 0

                self.trades.append(("sell", price))

        # final equity
        final_price = candles.iloc[-1]["close"]
        equity = self.cash + self.position * final_price

        roi = (equity - 1000) / 1000 * 100

        return {
            "trades": len(self.trades),
            "roi_pct": round(roi, 2),
            "final_equity": round(equity, 2)
        }