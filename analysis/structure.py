"""Market-structure primitives: pivots, ZigZag filtering, S/R zones and trend lines."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd
from scipy.signal import argrelextrema

@dataclass(frozen=True)
class Pivot:
    index: int
    price: float
    kind: str  # high | low

@dataclass(frozen=True)
class Zone:
    low: float
    high: float
    center: float
    touches: int
    strength: float
    kind: str

@dataclass(frozen=True)
class TrendLine:
    kind: str
    slope: float
    intercept: float
    touches: int
    score: float


def local_pivots(df: pd.DataFrame, order: int = 3) -> list[Pivot]:
    if order < 1:
        raise ValueError("order must be >= 1")
    if len(df) < 2 * order + 1:
        return []
    highs = df["high"].to_numpy(float)
    lows = df["low"].to_numpy(float)
    hi_idx = argrelextrema(highs, np.greater_equal, order=order)[0]
    lo_idx = argrelextrema(lows, np.less_equal, order=order)[0]
    pivots = [Pivot(int(i), float(highs[i]), "high") for i in hi_idx]
    pivots += [Pivot(int(i), float(lows[i]), "low") for i in lo_idx]
    return sorted(pivots, key=lambda p: (p.index, 0 if p.kind == "low" else 1))


def zigzag(pivots: list[Pivot], min_move_pct: float = 2.0) -> list[Pivot]:
    if min_move_pct < 0:
        raise ValueError("min_move_pct must be non-negative")
    if not pivots:
        return []
    ordered = sorted(pivots, key=lambda p: p.index)
    out = [ordered[0]]
    for p in ordered[1:]:
        last = out[-1]
        if p.kind == last.kind:
            better = (p.kind == "high" and p.price >= last.price) or (p.kind == "low" and p.price <= last.price)
            if better:
                out[-1] = p
            continue
        move = abs(p.price - last.price) / max(abs(last.price), 1e-12) * 100
        if move >= min_move_pct:
            out.append(p)
    return out


def support_resistance_zones(pivots: list[Pivot], tolerance_pct: float = 1.0) -> list[Zone]:
    if tolerance_pct <= 0:
        raise ValueError("tolerance_pct must be positive")
    if not pivots:
        return []
    prices = sorted(pivots, key=lambda p: p.price)
    clusters: list[list[Pivot]] = []
    for p in prices:
        if not clusters:
            clusters.append([p]); continue
        center = float(np.mean([x.price for x in clusters[-1]]))
        if abs(p.price - center) / max(abs(center), 1e-12) * 100 <= tolerance_pct:
            clusters[-1].append(p)
        else:
            clusters.append([p])
    max_touches = max(len(c) for c in clusters)
    zones = []
    for c in clusters:
        vals = [p.price for p in c]
        kinds = [p.kind for p in c]
        center = float(np.mean(vals))
        kind = "support" if kinds.count("low") >= kinds.count("high") else "resistance"
        strength = min(1.0, len(c) / max_touches)
        zones.append(Zone(min(vals), max(vals), center, len(c), strength, kind))
    return sorted(zones, key=lambda z: (-z.strength, z.center))


def fit_trendline(pivots: list[Pivot], kind: str, tolerance: float = 0.01) -> TrendLine | None:
    pts = [p for p in pivots if p.kind == kind]
    if kind not in {"high", "low"}:
        raise ValueError("kind must be high or low")
    if len(pts) < 2:
        return None
    x = np.array([p.index for p in pts], dtype=float)
    y = np.array([p.price for p in pts], dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    pred = slope * x + intercept
    rel = np.abs(y - pred) / np.maximum(np.abs(y), 1e-12)
    touches = int((rel <= tolerance).sum())
    score = touches / len(pts)
    return TrendLine(kind, float(slope), float(intercept), touches, float(score))


def strongest_zones(zones: list[Zone], limit: int = 6) -> list[Zone]:
    if limit < 0:
        raise ValueError("limit must be non-negative")
    return sorted(zones, key=lambda z: (-z.strength, -z.touches))[:limit]
