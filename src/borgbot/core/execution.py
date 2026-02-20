import time
from borgbot.state.store import get_position, set_position, add_trade
def apply_slippage(price: float, slippage_pct: float, side: str) -> float:
    return price * (1.0 + slippage_pct) if side == "buy" else price * (1.0 - slippage_pct)
def paper_trade_once(conn, logger, *, side: str, price: float, fees_bps: float, slippage_pct: float, size_frac: float = 1.0, min_cash_buffer_frac: float = 0.0):
    """Long-only paper engine."""
    ts = int(time.time() * 1000)
    base_qty, cash, avg_price = get_position(conn)
    fee_rate = fees_bps / 10_000.0
    if side == "buy":
        if cash <= 0.0: logger.info("paper.skip_no_cash", cash=cash); return
        deployable_cash = max(0.0, cash * (1.0 - min_cash_buffer_frac))
        notional = deployable_cash * size_frac
        if notional <= 0:
            logger.info("paper.skip_buffer_protection", cash=cash)
            return
        px = apply_slippage(price, slippage_pct, "buy")
        qty = (notional / px) * (1.0 - fee_rate)
        base_qty_after = base_qty + qty
        if base_qty_after > 0: avg_price = ((base_qty * avg_price) + (qty * px)) / (base_qty_after)
        cash_after = cash - notional
        fee = notional * fee_rate
        set_position(conn, base_qty_after, cash_after, avg_price)
        add_trade(conn, ts, "buy", qty, px, fee, cash_after, base_qty_after)
        logger.info("paper.buy", qty=qty, price=px, fee=fee, cash_after=cash_after, base_after=base_qty_after, avg_price=avg_price)
    elif side == "sell":
        if base_qty <= 0.0: logger.info("paper.skip_no_position", base_qty=base_qty); return
        qty = base_qty * size_frac
        px = apply_slippage(price, slippage_pct, "sell")
        notional = qty * px
        fee = notional * fee_rate
        cash_after = cash + (notional * (1.0 - fee_rate))
        base_qty_after = base_qty - qty
        avg_price_after = 0.0 if base_qty_after <= 1e-12 else avg_price
        set_position(conn, base_qty_after, cash_after, avg_price_after)
        add_trade(conn, ts, "sell", qty, px, fee, cash_after, base_qty_after)
        logger.info("paper.sell", qty=qty, price=px, fee=fee, cash_after=cash_after, base_after=base_qty_after)
    else:
        logger.info("paper.hold")
