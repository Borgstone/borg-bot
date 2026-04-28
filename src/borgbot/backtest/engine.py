import pandas as pd


class BacktestEngine:

    def __init__(
        self,
        strategy,
        starting_cash: float = 1000.0,
        fees_bps: float = 10.0,
        slippage_pct: float = 0.0005,
        trailing_pct: float = 0.05,  # 5% trailing stop
    ):
        self.strategy = strategy
        self.cash = starting_cash
        self.position = 0.0
        self.fees_bps = fees_bps
        self.slippage_pct = slippage_pct
        self.trailing_pct = trailing_pct

        self.trades = []

        # Position state
        self.entry_price = None
        self.peak_price = None

    def run(self, candles):
        if len(candles) == 0:
            raise ValueError("No candles loaded for the requested time range")

        for i in range(50, len(candles)):
            window = candles.iloc[:i]
            price = candles.iloc[i]["close"]

            context = {
                "candles": window
            }

            signal = self.strategy.generate_signal(context)

            # -------------------
            # BUY
            # -------------------
            if signal > 0 and self.position == 0:

                qty = self.cash / price
                cost = qty * price

                fee = cost * self.fees_bps / 10000

                self.cash -= cost + fee
                self.position = qty

                self.trades.append(("buy", price))

                # initialize trailing state
                self.entry_price = price
                self.peak_price = price

            # -------------------
            # SELL (signal-based)
            # -------------------
            elif signal < 0 and self.position > 0:

                value = self.position * price
                fee = value * self.fees_bps / 10000

                self.cash += value - fee
                self.position = 0

                self.trades.append(("sell", price))

                # reset state
                self.entry_price = None
                self.peak_price = None

            # -------------------
            # TRAILING STOP
            # -------------------
            if self.position > 0:

                # update peak price
                if self.peak_price is None or price > self.peak_price:
                    self.peak_price = price

                stop_price = self.peak_price * (1 - self.trailing_pct)

                if price < stop_price:

                    value = self.position * price
                    fee = value * self.fees_bps / 10000

                    self.cash += value - fee
                    self.position = 0

                    self.trades.append(("trailing_stop", price))

                    # reset state
                    self.entry_price = None
                    self.peak_price = None

        # -------------------
        # FINAL EQUITY
        # -------------------
        final_price = candles.iloc[-1]["close"]
        equity = self.cash + self.position * final_price

        roi = (equity - 1000) / 1000 * 100

        return {
            "trades": int(len(self.trades)),
            "roi_pct": float(round(roi, 2)),
            "final_equity": float(round(equity, 2))
        }