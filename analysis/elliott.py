"""Experimental Elliott Wave evaluator.

It enforces the three cardinal impulse rules and returns a probabilistic score.
"""
from __future__ import annotations

from dataclasses import dataclass

from .structure import Pivot


@dataclass(frozen=True)
class ElliottCount:
    valid: bool
    confidence: int
    labels: tuple[str, ...]
    reasons: tuple[str, ...]
    alternate: bool = False


def cardinal_rules(prices: list[float], bullish: bool = True) -> tuple[bool, list[str]]:
    if len(prices) != 6:
        raise ValueError("need six points: start, W1..W5")
    p0,p1,p2,p3,p4,p5 = map(float, prices)
    reasons=[]
    if bullish:
        w1 = p1-p0; w3=p3-p2; w5=p5-p4
        r1 = p2 > p0
        r2 = w3 > 0 and w3 >= min(w1,w5)
        r3 = p4 > p1
    else:
        w1 = p0-p1; w3=p2-p3; w5=p4-p5
        r1 = p2 < p0
        r2 = w3 > 0 and w3 >= min(w1,w5)
        r3 = p4 < p1
    if not r1: reasons.append("wave 2 retraces beyond wave 1 origin")
    if not r2: reasons.append("wave 3 is the shortest impulse wave")
    if not r3: reasons.append("wave 4 overlaps wave 1 territory")
    return r1 and r2 and r3, reasons


def ratio_score(prices: list[float]) -> int:
    p0,p1,p2,p3,p4,p5=map(float, prices)
    w1=abs(p1-p0); w2=abs(p2-p1); w3=abs(p3-p2); w4=abs(p4-p3); w5=abs(p5-p4)
    if min(w1,w3) == 0:
        return 0
    score=50
    def close(v,t,tol=0.25): return abs(v-t) <= tol*t
    if close(w2/w1,0.618): score += 15
    if close(w3/w1,1.618,0.35): score += 15
    if close(w4/w3,0.382,0.35): score += 10
    if 0.5 <= w5/w1 <= 1.8: score += 10
    return min(100,score)


def evaluate_impulse(pivots: list[Pivot], bullish: bool | None = None) -> ElliottCount:
    if len(pivots) < 6:
        return ElliottCount(False, 0, tuple(), ("not enough pivots",), False)
    seq = sorted(pivots, key=lambda p:p.index)[-6:]
    prices=[p.price for p in seq]
    if bullish is None:
        bullish = prices[1] > prices[0]
    valid,reasons=cardinal_rules(prices,bullish)
    if not valid:
        return ElliottCount(False, max(0,ratio_score(prices)-40), tuple(), tuple(reasons), True)
    conf=ratio_score(prices)
    return ElliottCount(True, conf, ("0","1","2","3","4","5"), ("cardinal rules satisfied",), conf < 75)
