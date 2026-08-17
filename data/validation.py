"""Canonical candle validation and friendly warnings."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

REQUIRED=("time","open","high","low","close")
@dataclass(frozen=True)
class ValidationResult:
    data: pd.DataFrame
    warnings: tuple[str,...]


def validate_candles(df:pd.DataFrame, min_rows:int=1)->ValidationResult:
    missing=[c for c in REQUIRED if c not in df.columns]
    if missing: raise ValueError(f"missing required columns: {', '.join(missing)}")
    out=df.copy()
    out["time"]=pd.to_datetime(out["time"],utc=True,errors="raise")
    for c in ("open","high","low","close"):
        out[c]=pd.to_numeric(out[c],errors="raise")
    if "volume" in out:
        out["volume"]=pd.to_numeric(out["volume"],errors="coerce")
    else:
        out["volume"]=float("nan")
    warnings=[]
    dup=int(out["time"].duplicated().sum())
    if dup:
        warnings.append(f"removed {dup} duplicate timestamps")
        out=out.drop_duplicates("time",keep="last")
    if not out["time"].is_monotonic_increasing:
        warnings.append("timestamps were sorted")
        out=out.sort_values("time")
    if (out[["open","high","low","close"]] <= 0).any().any(): raise ValueError("prices must be positive")
    if (out["high"] < out[["open","close"]].max(axis=1)).any(): raise ValueError("high below open/close")
    if (out["low"] > out[["open","close"]].min(axis=1)).any(): raise ValueError("low above open/close")
    if len(out) < min_rows: warnings.append(f"only {len(out)} rows; {min_rows} recommended")
    if out["volume"].isna().all(): warnings.append("volume is missing")
    if len(out)>=3:
        diffs=out["time"].sort_values().diff().dropna()
        if len(diffs) and (diffs > diffs.median()*1.5).any(): warnings.append("possible missing periods detected")
    return ValidationResult(out.reset_index(drop=True),tuple(warnings))
