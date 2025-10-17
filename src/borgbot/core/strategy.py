from pydantic import BaseModel, Field
from typing import List, Literal
class SMAConfig(BaseModel):
    fast: int = Field(9, gt=0)
    slow: int = Field(21, gt=0)
    def validate_(self): assert self.fast < self.slow, "fast must be < slow"
Signal = Literal["hold", "buy", "sell"]
def sma(values: List[float], window: int) -> List[float]:
    out, s = [], 0.0
    for i, v in enumerate(values):
        s += v
        if i >= window: s -= values[i-window]
        out.append(s / window if i+1 >= window else float('nan'))
    return out
def sma_cross_strategy(closes: List[float], cfg: SMAConfig) -> Signal:
    cfg.validate_()
    if len(closes) < cfg.slow + 2: return "hold"
    fast, slow = sma(closes, cfg.fast), sma(closes, cfg.slow)
    a1, b1 = fast[-2], slow[-2]; a2, b2 = fast[-1], slow[-1]
    if a1 <= b1 and a2 > b2: return "buy"
    if a1 >= b1 and a2 < b2: return "sell"
    return "hold"
