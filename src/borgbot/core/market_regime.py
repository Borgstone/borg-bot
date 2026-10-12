"""ADX/DMI-based market regime classification."""
from __future__ import annotations

import pandas as pd

from borgbot.indicators.dmi_adx import dmi_adx


REGIME_UP = "UP"
REGIME_DOWN = "DOWN"
REGIME_SIDEWAYS = "SIDEWAYS"
REGIME_TRANSITION = "TRANSITION"
REGIME_UNKNOWN = "UNKNOWN"


class MarketRegimeDetector:
    """Classify directional regime from Wilder DMI/ADX.

    Defaults are conventional starting thresholds, not optimized parameters:
    ADX < 20 is weak/ranging, 20-25 is transitional, and ADX >= 25 is trending.
    This detector does not itself filter trades or change strategy scores.
    """

    def __init__(
        self,
        period: int = 14,
        sideways_adx: float = 20.0,
        trend_adx: float = 25.0,
    ):
        if isinstance(period, bool) or not isinstance(period, int) or period < 2:
            raise ValueError("period must be an integer >= 2")
        if not (0.0 <= sideways_adx < trend_adx <= 100.0):
            raise ValueError("thresholds must satisfy 0 <= sideways_adx < trend_adx <= 100")
        self.period = period
        self.sideways_adx = float(sideways_adx)
        self.trend_adx = float(trend_adx)

    def analyze(self, candles: pd.DataFrame) -> pd.DataFrame:
        """Return DMI/ADX values plus regime and ADX direction for each row."""
        required = {"high", "low", "close"}
        missing = required.difference(candles.columns)
        if missing:
            raise ValueError(f"candles missing required columns: {sorted(missing)}")

        result = dmi_adx(
            candles["high"],
            candles["low"],
            candles["close"],
            period=self.period,
        )
        result["adx_change"] = result["adx"].diff()
        # Preserve unknown during ADX warm-up instead of silently encoding it as False.
        result["adx_rising"] = pd.Series(pd.NA, index=result.index, dtype="boolean")
        valid_change = result["adx_change"].notna()
        result.loc[valid_change, "adx_rising"] = result.loc[valid_change, "adx_change"] > 0.0
        result["regime"] = [
            self._classify(adx, plus_di, minus_di)
            for adx, plus_di, minus_di in zip(
                result["adx"], result["plus_di"], result["minus_di"]
            )
        ]
        return result

    def _classify(self, adx, plus_di, minus_di) -> str:
        if pd.isna(adx) or pd.isna(plus_di) or pd.isna(minus_di):
            return REGIME_UNKNOWN
        if adx < self.sideways_adx:
            return REGIME_SIDEWAYS
        if adx < self.trend_adx:
            return REGIME_TRANSITION
        if plus_di > minus_di:
            return REGIME_UP
        if minus_di > plus_di:
            return REGIME_DOWN
        return REGIME_TRANSITION
