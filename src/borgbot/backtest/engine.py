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
        signal_count = 0
        trade_count = 0
        winning_trades = 0
        losing_trades = 0
        gross_profit = 0.0
        gross_loss = 0.0
        trade_returns = []

        for i in range(len(df)):
            row = df.iloc[i]

            signal = self.strategy.generate_signal(df, i)
            if signal != 0:
                signal_count += 1

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

                        trade_count += 1
                        trade_returns.append(pnl)

                        if pnl > 0:
                            winning_trades += 1
                            gross_profit += pnl
                        else:
                            losing_trades += 1
                            gross_loss += abs(pnl)

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

                        trade_count += 1
                        trade_returns.append(pnl)

                        if pnl > 0:
                            winning_trades += 1
                            gross_profit += pnl
                        else:
                            losing_trades += 1
                            gross_loss += abs(pnl)

                        equity *= (1 + pnl)

                        position = 0

            equity_curve.append(equity)

        print(f"DEBUG: Signals = {signal_count}")
        print(f"DEBUG: Trades = {trade_count}")
        print(f"DEBUG: Win Rate = {win_rate:.2f}%")
        print(f"DEBUG: Profit Factor = {profit_factor:.2f}")

        roi_pct = (equity - 1.0) * 100

        # ---------------------------
        # METRICS
        # ---------------------------

        running_peak = -float("inf")
        max_drawdown = 0.0

        for value in equity_curve:

            running_peak = max(running_peak, value)

            drawdown = (running_peak - value) / running_peak

            max_drawdown = max(max_drawdown, drawdown)

        if trade_count > 0:
            win_rate = (winning_trades / trade_count) * 100
            avg_trade = (sum(trade_returns) / trade_count) * 100
        else:
            win_rate = 0.0
            avg_trade = 0.0

        if gross_loss > 0:
            profit_factor = gross_profit / gross_loss
        else:
            profit_factor = 999.0

        return {
            "equity_curve": equity_curve,
            "final_equity": equity,

            "roi_pct": roi_pct,

            "trades": trade_count,

            "win_rate": win_rate,
            "avg_trade": avg_trade,

            "profit_factor": profit_factor,

            "max_drawdown": max_drawdown,
        }