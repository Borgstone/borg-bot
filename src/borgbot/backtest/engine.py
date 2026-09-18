import numpy as np


class BacktestEngine:
    """
    Backtest engine.

    Responsibilities:
    - Execute strategy signals against historical candles.
    - Manage the current position using the existing ATR-based
      stop, trailing stop, and max-holding rules.
    - Produce auditable trade and equity metrics.

    Risk and exit logic will eventually move into dedicated
    modular layers. For now, the engine remains the execution
    model used by research/backtesting.
    """

    def __init__(self, strategy, config=None):

        self.strategy = strategy
        self.config = config or {}

        # Current risk/exit configuration.
        self.atr_period = self.config.get(
            "atr_period",
            14,
        )

        self.atr_stop_mult = self.config.get(
            "atr_stop_mult",
            1.5,
        )

        self.atr_trail_mult = self.config.get(
            "atr_trail_mult",
            2.0,
        )

        self.max_holding = self.config.get(
            "max_holding",
            48,
        )

    def compute_atr(self, df):

        high = df["high"]
        low = df["low"]
        close = df["close"]

        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()

        tr = np.maximum(
            tr1,
            np.maximum(
                tr2,
                tr3,
            ),
        )

        return tr.rolling(
            self.atr_period
        ).mean()

    @staticmethod
    def mark_to_market_equity(
        realized_equity,
        position,
        entry_price,
        price,
    ):
        """
        Calculate total equity including the unrealized PnL
        of the currently open position.

        realized_equity contains only completed trades.
        """

        if position == 0:
            return realized_equity

        if entry_price <= 0 or price <= 0:
            return realized_equity

        if position == 1:
            return (
                realized_equity
                * (price / entry_price)
            )

        if position == -1:
            return (
                realized_equity
                * (entry_price / price)
            )

        return realized_equity

    @staticmethod
    def calculate_max_drawdown(equity_curve):

        if not equity_curve:
            return 0.0

        running_peak = equity_curve[0]
        max_drawdown = 0.0

        for value in equity_curve:

            running_peak = max(
                running_peak,
                value,
            )

            if running_peak <= 0:
                continue

            drawdown = (
                (running_peak - value)
                / running_peak
            )

            max_drawdown = max(
                max_drawdown,
                drawdown,
            )

        return max_drawdown

    def run(self, df):

        df = df.copy()

        if df.empty:
            return {
                "equity_curve": [],
                "final_equity": 1.0,
                "roi": 0.0,
                "roi_pct": 0.0,
                "trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "gross_profit": 0.0,
                "gross_loss": 0.0,
                "win_rate": 0.0,
                "avg_trade": 0.0,
                "profit_factor": 0.0,
                "max_drawdown": 0.0,
            }

        df["atr"] = self.compute_atr(df)

        # 1 = long
        # -1 = short
        # 0 = flat
        position = 0

        entry_price = 0.0
        stop_loss = 0.0
        trail_stop = 0.0
        holding = 0

        # Equity from completed trades only.
        realized_equity = 1.0

        equity_curve = []

        signal_count = 0

        trade_count = 0
        winning_trades = 0
        losing_trades = 0

        gross_profit = 0.0
        gross_loss = 0.0

        def close_position(exit_price):
            nonlocal position
            nonlocal entry_price
            nonlocal stop_loss
            nonlocal trail_stop
            nonlocal holding

            nonlocal realized_equity

            nonlocal trade_count
            nonlocal winning_trades
            nonlocal losing_trades

            nonlocal gross_profit
            nonlocal gross_loss

            if position == 0:
                return

            if exit_price <= 0 or entry_price <= 0:
                return

            if position == 1:

                pnl = (
                    exit_price / entry_price
                ) - 1.0

            else:

                pnl = (
                    entry_price / exit_price
                ) - 1.0

            trade_count += 1

            if pnl > 0:

                winning_trades += 1
                gross_profit += pnl

            else:

                losing_trades += 1
                gross_loss += abs(pnl)

            realized_equity *= (
                1.0 + pnl
            )

            position = 0
            entry_price = 0.0
            stop_loss = 0.0
            trail_stop = 0.0
            holding = 0

        for i in range(len(df)):

            row = df.iloc[i]

            signal = self.strategy.generate_signal(
                df,
                i,
            )

            if signal != 0:
                signal_count += 1

            try:
                price = float(row["close"])
            except (TypeError, ValueError):
                equity_curve.append(
                    realized_equity
                )
                continue

            if not np.isfinite(price) or price <= 0:

                equity_curve.append(
                    self.mark_to_market_equity(
                        realized_equity,
                        position,
                        entry_price,
                        price,
                    )
                    if np.isfinite(price)
                    else realized_equity
                )

                continue

            atr = row["atr"]

            atr_valid = (
                atr is not None
                and np.isfinite(float(atr))
                and float(atr) > 0
            )

            atr = (
                float(atr)
                if atr_valid
                else None
            )

            # ---------------------------
            # ENTRY
            # ---------------------------

            if position == 0 and atr_valid:

                if signal == 1:

                    position = 1
                    entry_price = price
                    holding = 0

                    stop_loss = (
                        entry_price
                        - atr * self.atr_stop_mult
                    )

                    trail_stop = (
                        entry_price
                        - atr * self.atr_trail_mult
                    )

                elif signal == -1:

                    position = -1
                    entry_price = price
                    holding = 0

                    stop_loss = (
                        entry_price
                        + atr * self.atr_stop_mult
                    )

                    trail_stop = (
                        entry_price
                        + atr * self.atr_trail_mult
                    )

            # ---------------------------
            # POSITION MANAGEMENT
            # ---------------------------

            elif position != 0:

                holding += 1

                # -----------------------
                # LONG
                # -----------------------

                if position == 1:

                    if atr_valid:

                        new_trail = (
                            price
                            - atr * self.atr_trail_mult
                        )

                        trail_stop = max(
                            trail_stop,
                            new_trail,
                        )

                    exit_position = False

                    # Hard stop.
                    if price <= stop_loss:

                        exit_position = True

                    # Trailing stop.
                    elif (
                        atr_valid
                        and price <= trail_stop
                    ):

                        exit_position = True

                    # Time-based exit.
                    elif holding >= self.max_holding:

                        exit_position = True

                    if exit_position:
                        close_position(price)

                # -----------------------
                # SHORT
                # -----------------------

                elif position == -1:

                    if atr_valid:

                        new_trail = (
                            price
                            + atr * self.atr_trail_mult
                        )

                        trail_stop = min(
                            trail_stop,
                            new_trail,
                        )

                    exit_position = False

                    # Hard stop.
                    if price >= stop_loss:

                        exit_position = True

                    # Trailing stop.
                    elif (
                        atr_valid
                        and price >= trail_stop
                    ):

                        exit_position = True

                    # Time-based exit.
                    elif holding >= self.max_holding:

                        exit_position = True

                    if exit_position:
                        close_position(price)

            # ---------------------------
            # MARK TO MARKET
            # ---------------------------

            marked_equity = (
                self.mark_to_market_equity(
                    realized_equity,
                    position,
                    entry_price,
                    price,
                )
            )

            equity_curve.append(
                marked_equity
            )

        # ---------------------------
        # END-OF-DATA EXIT
        # ---------------------------

        if position != 0:

            last_price = float(
                df["close"].iloc[-1]
            )

            if (
                np.isfinite(last_price)
                and last_price > 0
            ):

                close_position(last_price)

                # Replace the final marked value with the
                # now-realized equity.
                if equity_curve:
                    equity_curve[-1] = (
                        realized_equity
                    )

        # ---------------------------
        # METRICS
        # ---------------------------

        roi_pct = (
            (realized_equity - 1.0)
            * 100.0
        )

        max_drawdown = (
            self.calculate_max_drawdown(
                equity_curve
            )
        )

        if trade_count > 0:

            win_rate = (
                winning_trades
                / trade_count
            ) * 100.0

            avg_trade = (
                (
                    gross_profit
                    - gross_loss
                )
                / trade_count
            ) * 100.0

        else:

            win_rate = 0.0
            avg_trade = 0.0

        if gross_loss > 0:

            profit_factor = (
                gross_profit
                / gross_loss
            )

        elif gross_profit > 0:

            profit_factor = 999.0

        else:

            profit_factor = 0.0

        print(
            f"DEBUG: Signals = {signal_count}"
        )

        print(
            f"DEBUG: Trades = {trade_count}"
        )

        print(
            f"DEBUG: Win Rate = "
            f"{win_rate:.2f}%"
        )

        print(
            f"DEBUG: Profit Factor = "
            f"{profit_factor:.2f}"
        )

        return {
            "equity_curve": equity_curve,

            "final_equity": realized_equity,

            "roi": roi_pct,
            # Backward-compatible alias for older callers.
            "roi_pct": roi_pct,

            "trades": trade_count,

            "winning_trades": winning_trades,

            "losing_trades": losing_trades,

            "gross_profit": gross_profit,

            "gross_loss": gross_loss,

            "win_rate": win_rate,

            "avg_trade": avg_trade,

            "profit_factor": profit_factor,

            "max_drawdown": max_drawdown,
        }