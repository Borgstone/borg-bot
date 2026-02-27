from abc import ABC, abstractmethod

class ExecutionAdapter(ABC):
    @abstractmethod
    def execute_order(self, side, qty, price):
        pass