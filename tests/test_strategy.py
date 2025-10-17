from borgbot.core.strategy import sma_cross_strategy, SMAConfig
def test_hold_on_short_history():
    assert sma_cross_strategy([1,2,3], SMAConfig(fast=2, slow=5)) == "hold"
