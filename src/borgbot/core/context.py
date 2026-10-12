"""Research-facing market context assembly.

The context layer keeps local and higher-timeframe regimes separate. It does not
filter trades or modify strategy scores; those decisions require regime-conditional
out-of-sample evidence first.
"""
from __future__ import annotations

import pandas as pd

from borgbot.core.market_regime import MarketRegimeDetector
from borgbot.core.timeframe_alignment import align_higher_timeframe_regime


class MarketContext:
    def __init__(
        self,
        candles: pd.DataFrame,
        higher_tf: pd.DataFrame | None = None,
        timeframe: str | None = None,
        higher_timeframe: str | None = None,
        detector: MarketRegimeDetector | None = None,
    ):
        self.candles = candles
        self.higher_tf = higher_tf
        self.timeframe = timeframe
        self.higher_timeframe = higher_timeframe
        self.detector = detector or MarketRegimeDetector()

    def analyze(self) -> pd.DataFrame:
        """Return candle data plus local and, when supplied, aligned HTF regimes."""
        local = self.detector.analyze(self.candles)
        local = local.rename(
            columns={column: f"local_{column}" for column in local.columns}
        )
        result = pd.concat([self.candles.copy(), local], axis=1)

        if self.higher_tf is None:
            return result

        if self.timeframe is None or self.higher_timeframe is None:
            raise ValueError(
                "timeframe and higher_timeframe are required when higher_tf is supplied"
            )

        aligned = align_higher_timeframe_regime(
            self.candles,
            self.higher_tf,
            base_timeframe=self.timeframe,
            higher_timeframe=self.higher_timeframe,
            detector=self.detector,
            prefix="higher",
        )
        higher_columns = [
            column for column in aligned.columns
            if column.startswith("higher_")
        ]
        return pd.concat([result, aligned[higher_columns]], axis=1)
