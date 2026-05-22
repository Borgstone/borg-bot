from typing import List, Tuple
from .base import Strategy

class StrategyStack:
    def __init__(self, strategies: List[Tuple[Strategy, float]]):
        self.strategies = strategies  # (strategy, weight)

    class StrategyStack:
        def __init__(self, strategies):
            self.strategies = strategies

        def generate_signal(self, df, i):
            score = 0

            for strat, weight in self.strategies:
                s = strat.generate_signal(df, i)
                score += s * weight

            if score > 0:
                return 1
            elif score < 0:
                return -1
            return 0

        return weighted_sum / total_weight