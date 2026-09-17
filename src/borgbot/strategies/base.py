from abc import ABC, abstractmethod


class Strategy(ABC):
    """
    Canonical strategy interface for research, backtesting,
    paper trading, and eventually live trading.
    """

    def __init__(self, config=None):
        self.config = config or {}

    @abstractmethod
    def generate_signal(self, df, i):
        """
        Generate a trading signal for candle index i.

        Returns:
            1  = long
            -1 = short
            0  = hold
        """
        raise NotImplementedError