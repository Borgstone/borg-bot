def compute_score(roi, drawdown):
    """
    Drawdown-first ranking
    """
    return (roi * 0.3) + ((100 - abs(drawdown)) * 0.7)