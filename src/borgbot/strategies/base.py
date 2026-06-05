from abc import ABC, abstractmethod

class Strategy(ABC):

    @abstractmethod
    def generate_signal(self, df, i):
        """
        Research/backtest interface.

        Returns:
            1 = long
            -1 = short
            0 = hold
        """
        pass