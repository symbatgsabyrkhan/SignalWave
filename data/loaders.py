"""CSV/Koyfin and Binance public-data loaders."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pandas as pd
import requests

from .validation import ValidationResult, validate_candles


def file_sha256(path:str|Path)->str:
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(65536),b""): h.update(chunk)
    return h.hexdigest()


def _norm_num(s:pd.Series)->pd.Series:
    if pd.api.types.is_numeric_dtype(s): return pd.to_numeric(s,errors="coerce")
    t=s.astype(str).str.strip().str.replace(" ","",regex=False)
    both=t.str.contains(",") & t.str.contains(r"\.")
    t=t.where(~both,t.str.replace(",","",regex=False))
    comma_only=t.str.contains(",") & ~t.str.contains(r"\.")
    t=t.where(~comma_only,t.str.replace(",",".",regex=False))
    return pd.to_numeric(t,errors="coerce")


def normalize_csv_frame(raw:pd.DataFrame, symbol:str|None=None, timeframe:str="unknown", source:str="csv") -> ValidationResult:
    cols={str(c).strip():c for c in raw.columns}
    lower={k.lower():v for k,v in cols.items()}
    mapping={}
    for standard in ("time","date","open","high","low","close","volume"):
        if standard in lower: mapping[standard]=lower[standard]
    if "time" not in mapping and "date" in mapping: mapping["time"]=mapping["date"]
    # Koyfin columns, e.g. BTCUSD Open
    for standard in ("open","high","low","close","volume"):
        if standard not in mapping:
            matches=[c for c in raw.columns if re.search(rf"\b{standard}\b",str(c),re.IGNORECASE)]
            if matches: mapping[standard]=matches[0]
    if "time" not in mapping:
        matches=[c for c in raw.columns if re.search(r"date|time",str(c),re.IGNORECASE)]
        if matches: mapping["time"]=matches[0]
    missing=[x for x in ("time","open","high","low","close") if x not in mapping]
    if missing: raise ValueError(f"could not detect columns: {', '.join(missing)}")
    out=pd.DataFrame({k:raw[v] for k,v in mapping.items() if k!="date"})
    for c in ("open","high","low","close","volume"):
        if c in out: out[c]=_norm_num(out[c])
    vr=validate_candles(out,min_rows=1)
    data=vr.data.copy(); data["symbol"]=symbol or "UNKNOWN"; data["timeframe"]=timeframe; data["source"]=source
    return ValidationResult(data,vr.warnings)


def load_csv(path:str|Path, **kwargs)->ValidationResult:
    raw=pd.read_csv(path)
    return normalize_csv_frame(raw,**kwargs)


def parse_binance_klines(rows:list, symbol:str, timeframe:str)->ValidationResult:
    rec=[]
    for r in rows:
        if len(r)<6: raise ValueError("invalid Binance kline row")
        rec.append({"time":pd.to_datetime(int(r[0]),unit="ms",utc=True),"open":float(r[1]),"high":float(r[2]),"low":float(r[3]),"close":float(r[4]),"volume":float(r[5])})
    vr=validate_candles(pd.DataFrame(rec),min_rows=1)
    d=vr.data.copy(); d["symbol"]=symbol; d["timeframe"]=timeframe; d["source"]="binance"
    return ValidationResult(d,vr.warnings)


def fetch_binance(
    symbol: str,
    timeframe: str = "1d",
    limit: int = 1000,
    session=None,
    base_url: str | None = None,
) -> ValidationResult:

    if not (1 <= limit <= 1000):
        raise ValueError(
            "limit must be 1..1000"
        )

    s = session or requests

    endpoints = []

    if base_url:
        endpoints.append(base_url)

    endpoints.extend(
        [
            "https://data-api.binance.vision",
            "https://api.binance.com",
            "https://api-gcp.binance.com",
            "https://api1.binance.com",
            "https://api2.binance.com",
            "https://api3.binance.com",
            "https://api4.binance.com",
        ]
    )

    # Preserve order while removing duplicates.
    endpoints = list(
        dict.fromkeys(endpoints)
    )

    errors = []

    for endpoint in endpoints:
        try:
            resp = s.get(
                f"{endpoint}/api/v3/klines",
                params={
                    "symbol":
                        symbol.upper(),
                    "interval":
                        timeframe,
                    "limit":
                        limit,
                },
                timeout=15,
            )

            resp.raise_for_status()

            return parse_binance_klines(
                resp.json(),
                symbol.upper(),
                timeframe,
            )

        except Exception as exc:
            errors.append(
                f"{endpoint}: {exc}"
            )

    raise RuntimeError(
        "All Binance public endpoints failed. "
        + " | ".join(errors)
    )