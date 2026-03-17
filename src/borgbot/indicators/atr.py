import pandas as pd

def atr(high, low, close, period: int = 14):
    high = pd.Series(high)
    low = pd.Series(low)
    close = pd.Series(close)

    prev_close = close.shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    return tr.rolling(period).mean()