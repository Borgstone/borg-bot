from typing import List

def atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14):

    if len(closes) <= period:
        return 0.0

    trs = []

    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        )
        trs.append(tr)

    return sum(trs[-period:]) / period