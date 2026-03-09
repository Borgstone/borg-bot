from typing import List

def sma(values: List[float], period: int) -> float:
    if len(values) < period:
        return 0.0

    return sum(values[-period:]) / period