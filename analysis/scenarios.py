"""Confluence scoring and up/down/unclear decision cards."""
from __future__ import annotations

from dataclasses import dataclass

DEFAULT_WEIGHTS = {"trend":0.25,"structure":0.30,"fibonacci":0.15,"momentum":0.20,"volume":0.10}
DISCLAIMER = "Не является финансовой консультацией — образовательный инструмент"

@dataclass(frozen=True)
class DecisionCard:
    direction: str
    condition: str
    entry_low: float | None
    entry_high: float | None
    invalidation: float | None
    targets: tuple[float, ...]
    risk_reward: float | None
    confidence: int
    label: str
    reasons_for: tuple[str, ...]
    reasons_against: tuple[str, ...]
    actionable: bool
    disclaimer: str = DISCLAIMER


def confidence_score(votes: dict[str,float], weights: dict[str,float] | None=None) -> int:
    weights=weights or DEFAULT_WEIGHTS
    unknown=set(votes)-set(weights)
    if unknown: raise ValueError(f"unknown vote families: {sorted(unknown)}")
    total=sum(weights[k] for k in votes)
    if total <= 0: return 0
    score=sum(max(0,min(1,float(votes[k])))*weights[k] for k in votes)/total*100
    return int(round(score))


def confidence_label(score:int)->str:
    if not 0 <= score <= 100: raise ValueError("score must be 0..100")
    if score < 45: return "нет преимущества, воздержаться"
    if score < 70: return "нейтральное наблюдение"
    return "план действий"


def risk_reward(entry: float, invalidation: float, target: float, direction: str) -> float:
    if direction not in {"up","down"}: raise ValueError("direction must be up or down")
    risk = (entry-invalidation) if direction=="up" else (invalidation-entry)
    reward = (target-entry) if direction=="up" else (entry-target)
    if risk <= 0 or reward <= 0: return 0.0
    return reward/risk


def make_card(direction:str, entry:tuple[float,float]|None, invalidation:float|None, targets:list[float], votes:dict[str,float], reasons_for:list[str], reasons_against:list[str], condition:str="") -> DecisionCard:
    if direction not in {"up","down","unclear"}: raise ValueError("invalid direction")
    score=confidence_score(votes)
    label=confidence_label(score)
    rr=None
    if direction != "unclear" and entry and invalidation is not None and targets:
        midpoint=sum(entry)/2
        rr=risk_reward(midpoint,invalidation,targets[0],direction)
    actionable=direction!="unclear" and score>=70 and rr is not None and rr>=1.5 and bool(reasons_against)
    if direction=="unclear": entry=None; invalidation=None; targets=[]
    return DecisionCard(direction,condition,entry[0] if entry else None,entry[1] if entry else None,invalidation,tuple(targets[:2]),rr,score,label,tuple(reasons_for),tuple(reasons_against) or ("данные неоднозначны",),actionable)


def three_scenarios(price:float, atr_value:float, votes:dict[str,float]) -> tuple[DecisionCard,DecisionCard,DecisionCard]:
    a=max(float(atr_value),price*0.005)
    up=make_card("up",(price-0.5*a,price+0.1*a),price-1.6*a,[price+2.0*a,price+3.2*a],votes,["структура допускает рост"],["сценарий отменяется при пробое инвалидации"],"удержание зоны поддержки")
    inv_votes={k:1-v for k,v in votes.items()}
    down=make_card("down",(price-0.1*a,price+0.5*a),price+1.6*a,[price-2.0*a,price-3.2*a],inv_votes,["структура допускает снижение"],["сценарий отменяется при пробое сопротивления"],"отбой от сопротивления")
    unclear=make_card("unclear",None,None,[],{k:0.5 for k in votes},["сигналы смешанные"],["нет достаточного преимущества"],"ждать подтверждения")
    return up,down,unclear
