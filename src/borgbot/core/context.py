class MarketContext:
    def __init__(self, candles, higher_tf=None):
        self.candles = candles
        self.higher_tf = higher_tf