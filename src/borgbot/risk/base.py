from abc import ABC, abstractmethod

class RiskEngine(ABC):
    @abstractmethod
    def calculate_position_size(self, equity, price, context):
        pass