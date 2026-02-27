import time
from borgbot.execution.base import ExecutionAdapter
from borgbot.state.store import get_position, set_position, add_trade


class PaperExecutionAdapter(ExecutionAdapter):
    def __init__(self, conn, logger, fees_bps: float, slippage_pct: float):
        self.conn = conn
        self.logger = logger
        self.fee_rate = fees_bps / 10_000.0
        self.slippage_pct = slippage_pct

    def _apply_slippage(self, price: float, side: str) -> float:
        if side == "buy":
            return price * (1.0 + self.slippage_pct)
        else:
            return price * (1.0 - self.slippage_pct)

    def execute_order(self, side: str, qty: float, price: float):
        if qty <= 0:
            self.logger.info("paper.skip_invalid_qty", qty=qty)
            return

        ts = int(time.time() * 1000)
        base_qty, cash, avg_price = get_position(self.conn)

        px = self._apply_slippage(price, side)
        notional = qty * px
        fee = notional * self.fee_rate

        if side == "buy":
            if cash < notional:
                self.logger.info("paper.skip_no_cash", cash=cash)
                return

            base_after = base_qty + qty
            cash_after = cash - notional - fee

            if base_after > 0:
                avg_price = ((base_qty * avg_price) + (qty * px)) / base_after

        elif side == "sell":
            if base_qty < qty:
                self.logger.info("paper.skip_no_position", base_qty=base_qty)
                return

            base_after = base_qty - qty
            cash_after = cash + notional - fee

            if base_after <= 1e-12:
                avg_price = 0.0
        else:
            return

        set_position(self.conn, base_after, cash_after, avg_price)
        add_trade(self.conn, ts, side, qty, px, fee, cash_after, base_after)

        self.logger.info(
            f"paper.{side}",
            qty=qty,
            price=px,
            fee=fee,
            cash_after=cash_after,
            base_after=base_after,
            avg_price=avg_price,
        )