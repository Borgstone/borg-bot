from typing import List

def rsi(values: List[float], period: int = 14) -> float:

    if len(values) <= period:
        return 50.0

    gains = []
    losses = []

    for i in range(-period, 0):
        diff = values[i] - values[i-1]

        if diff > 0:
            gains.append(diff)
        else:
            losses.append(abs(diff))

    avg_gain = sum(gains) / period if gains else 0
    avg_loss = sum(losses) / period if losses else 0

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))