"""Transparent technical-indicator calculations.

Every value is derived from input candles; there are no hard-coded market claims.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def sma(s: pd.Series, period: int) -> pd.Series:
    if period <= 0:
        raise ValueError("period must be positive")
    return s.astype(float).rolling(period, min_periods=period).mean()


def ema(s: pd.Series, period: int) -> pd.Series:
    if period <= 0:
        raise ValueError("period must be positive")
    return s.astype(float).ewm(span=period, adjust=False, min_periods=period).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    if period <= 0:
        raise ValueError("period must be positive")
    c = close.astype(float)
    delta = c.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    out = out.mask((avg_loss == 0) & (avg_gain > 0), 100.0)
    out = out.mask((avg_gain == 0) & (avg_loss > 0), 0.0)
    return out


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    if not (0 < fast < slow and signal > 0):
        raise ValueError("require 0 < fast < slow and signal > 0")
    fast_e = ema(close, fast)
    slow_e = ema(close, slow)
    line = fast_e - slow_e
    sig = line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    return pd.DataFrame({"macd": line, "signal": sig, "histogram": line - sig})


def bollinger(close: pd.Series, period: int = 20, std_mult: float = 2.0) -> pd.DataFrame:
    if period <= 1 or std_mult <= 0:
        raise ValueError("invalid Bollinger parameters")
    mid = sma(close, period)
    sd = close.astype(float).rolling(period, min_periods=period).std(ddof=0)
    return pd.DataFrame({"middle": mid, "upper": mid + std_mult * sd, "lower": mid - std_mult * sd})


def true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    parts = pd.concat(
        [
            (df["high"] - df["low"]).abs(),
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    )
    return parts.max(axis=1)


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    if period <= 0:
        raise ValueError("period must be positive")
    tr = true_range(df)
    return tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def volume_features(volume: pd.Series | None, period: int = 20) -> pd.DataFrame:
    if period <= 1:
        raise ValueError("period must be > 1")
    if volume is None:
        return pd.DataFrame(columns=["volume_ma", "volume_ratio", "volume_spike"])
    v = volume.astype(float)
    ma = v.rolling(period, min_periods=period).mean()
    ratio = v / ma.replace(0, np.nan)
    return pd.DataFrame({"volume_ma": ma, "volume_ratio": ratio, "volume_spike": ratio >= 1.5})


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for p in (20, 50, 100, 200):
        out[f"sma_{p}"] = sma(out["close"], p)
        out[f"ema_{p}"] = ema(out["close"], p)
    out["rsi_14"] = rsi(out["close"], 14)
    m = macd(out["close"])
    out[["macd", "macd_signal", "macd_hist"]] = m[["macd", "signal", "histogram"]]
    b = bollinger(out["close"])
    out[["bb_mid", "bb_upper", "bb_lower"]] = b[["middle", "upper", "lower"]]
    out["atr_14"] = atr(out, 14)
    if "volume" in out:
        vf = volume_features(out["volume"])
        for col in vf:
            out[col] = vf[col]
    else:
        out["volume_ma"] = np.nan
        out["volume_ratio"] = np.nan
        out["volume_spike"] = False
    return out
