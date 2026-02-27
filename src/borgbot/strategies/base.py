from abc import ABC, abstractmethod
from typing import Dict

class Strategy(ABC):
    def __init__(self, config: Dict):
        self.config = config

    @abstractmethod
    def generate_signal(self, context) -> float:
        """
        Returns:
            +1.0 = strong long
            -1.0 = strong short
             0.0 = hold
        """
        pass