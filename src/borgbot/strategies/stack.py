from typing import List, Tuple
from .base import Strategy

class StrategyStack:
    def __init__(self, strategies: List[Tuple[Strategy, float]]):
        self.strategies = strategies  # (strategy, weight)

    def generate_signal(self, context) -> float:
        total_weight = 0.0
        weighted_sum = 0.0

        for strategy, weight in self.strategies:
            signal = strategy.generate_signal(context)
            weighted_sum += signal * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0

        return weighted_sum / total_weight