class StrategyStack:
    def __init__(self, strategies):
        """
        strategies: list of (strategy_instance, weight)
        """
        self.strategies = strategies

    def generate_signal(self, df, i):
        total_score = 0.0
        total_weight = 0.0

        for strat, weight in self.strategies:
            signal = strat.generate_signal(df, i)
            total_score += signal * weight
            total_weight += weight

        if total_weight == 0:
            return 0

        score = total_score / total_weight

        if score > 0:
            return 1
        elif score < 0:
            return -1
        return 0