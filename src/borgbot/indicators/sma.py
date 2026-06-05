import pandas as pd

def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period).mean()