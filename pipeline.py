"""End-to-end deterministic analysis pipeline independent of Telegram."""
from __future__ import annotations
import pandas as pd
from analysis.indicators import add_indicators
from analysis.structure import local_pivots,zigzag,support_resistance_zones,fit_trendline,strongest_zones
from analysis.fibonacci import levels_from_pivots,mark_confluence
from analysis.elliott import evaluate_impulse
from analysis.scenarios import three_scenarios


def analyze(df:pd.DataFrame)->dict:
    enriched=add_indicators(df)
    piv=zigzag(local_pivots(enriched,order=3),min_move_pct=1.0)
    zones=strongest_zones(support_resistance_zones(piv,tolerance_pct=1.0),6)
    fibs=[]
    if len(piv)>=2:
        try: fibs=mark_confluence(levels_from_pivots(piv),zones)
        except ValueError: pass
    ell=evaluate_impulse(piv)
    last=enriched.iloc[-1]; price=float(last["close"]); atr=float(last["atr_14"]) if pd.notna(last["atr_14"]) else price*0.02
    trend=0.5
    if pd.notna(last.get("sma_200",float("nan"))): trend=0.8 if price>last["sma_200"] else 0.2
    momentum=0.5
    if pd.notna(last.get("rsi_14",float("nan"))): momentum=max(0,min(1,(float(last["rsi_14"])-30)/40))
    votes={"trend":trend,"structure":0.65 if zones else 0.5,"fibonacci":0.7 if any(f.confluence for f in fibs) else 0.5,"momentum":momentum,"volume":0.65 if bool(last.get("volume_spike",False)) else 0.5}
    cards=three_scenarios(price,atr,votes)
    return {"data":enriched,"pivots":piv,"zones":zones,"fibs":fibs,"elliott":ell,"cards":cards,"votes":votes}
