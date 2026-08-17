"""Fibonacci retracements/extensions derived from confirmed swing legs."""
from __future__ import annotations

from dataclasses import dataclass

from .structure import Pivot, Zone

RETRACE = (0.236, 0.382, 0.5, 0.618, 0.786)
EXT = (1.272, 1.618)

@dataclass(frozen=True)
class FibLevel:
    ratio: float
    price: float
    kind: str
    confluence: bool = False


def last_impulse(pivots: list[Pivot]) -> tuple[Pivot, Pivot]:
    if len(pivots) < 2:
        raise ValueError("at least two pivots required")
    ordered = sorted(pivots, key=lambda p: p.index)
    for i in range(len(ordered) - 1, 0, -1):
        a, b = ordered[i - 1], ordered[i]
        if a.kind != b.kind and a.price != b.price:
            return a, b
    raise ValueError("no alternating impulse found")


def fib_levels(start: float, end: float) -> list[FibLevel]:
    if start == end:
        raise ValueError("start and end must differ")
    move = end - start
    levels = [FibLevel(r, end - move * r, "retracement") for r in RETRACE]
    levels += [FibLevel(r, start + move * r, "extension") for r in EXT]
    return levels


def levels_from_pivots(pivots: list[Pivot]) -> list[FibLevel]:
    a, b = last_impulse(pivots)
    return fib_levels(a.price, b.price)


def mark_confluence(levels: list[FibLevel], zones: list[Zone], tolerance_pct: float = 0.5) -> list[FibLevel]:
    if tolerance_pct < 0:
        raise ValueError("tolerance_pct must be non-negative")
    out = []
    for l in levels:
        hit = any(abs(l.price - z.center) / max(abs(z.center), 1e-12) * 100 <= tolerance_pct for z in zones)
        out.append(FibLevel(l.ratio, l.price, l.kind, hit))
    return out
