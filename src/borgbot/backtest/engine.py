import numpy as np


class BacktestEngine:
    def __init__(self, strategy, config=None):
        self.strategy = strategy
        self.config = config or {}

        # Risk config
        self.atr_period = self.config.get("atr_period", 14)
        self.atr_stop_mult = self.config.get("atr_stop_mult", 1.5)
        self.atr_trail_mult = self.config.get("atr_trail_mult", 2.0)
        self.max_holding = self.config.get("max_holding", 48)

    def compute_atr(self, df):
        high = df["high"]
        low = df["low"]
        close = df["close"]

        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()

        tr = np.maximum(tr1, np.maximum(tr2, tr3))
        atr = tr.rolling(self.atr_period).mean()

        return atr

    def run(self, df):
        df = df.copy()

        df["atr"] = self.compute_atr(df)

        position = 0  # 1 = long, -1 = short
        entry_price = 0
        stop_loss = 0
        trail_stop = 0
        holding = 0

        equity = 1.0
        equity_curve = []

        for i in range(len(df)):
            row = df.iloc[i]

            signal = self.strategy.generate_signal(df, i)

            price = row["close"]
            atr = row["atr"]

            if np.isnan(atr):
                equity_curve.append(equity)
                continue

            # ---------------------------
            # ENTRY
            # ---------------------------
            if position == 0:

                if signal == 1:
                    position = 1
                    entry_price = price
                    holding = 0

                    stop_loss = entry_price - atr * self.atr_stop_mult
                    trail_stop = entry_price - atr * self.atr_trail_mult

                elif signal == -1:
                    position = -1
                    entry_price = price
                    holding = 0

                    stop_loss = entry_price + atr * self.atr_stop_mult
                    trail_stop = entry_price + atr * self.atr_trail_mult

            # ---------------------------
            # POSITION MANAGEMENT
            # ---------------------------
            else:
                holding += 1

                # LONG
                if position == 1:

                    # update trailing
                    new_trail = price - atr * self.atr_trail_mult
                    trail_stop = max(trail_stop, new_trail)

                    exit_reason = False

                    # stop loss
                    if price <= stop_loss:
                        exit_reason = True

                    # trailing stop
                    elif price <= trail_stop:
                        exit_reason = True

                    # time exit
                    elif holding >= self.max_holding:
                        exit_reason = True

                    if exit_reason:
                        pnl = (price / entry_price) - 1
                        equity *= (1 + pnl)

                        position = 0

                # SHORT
                elif position == -1:

                    new_trail = price + atr * self.atr_trail_mult
                    trail_stop = min(trail_stop, new_trail)

                    exit_reason = False

                    if price >= stop_loss:
                        exit_reason = True

                    elif price >= trail_stop:
                        exit_reason = True

                    elif holding >= self.max_holding:
                        exit_reason = True

                    if exit_reason:
                        pnl = (entry_price / price) - 1
                        equity *= (1 + pnl)

                        position = 0

            equity_curve.append(equity)

        return {
            "equity_curve": equity_curve,
            "final_equity": equity
        }