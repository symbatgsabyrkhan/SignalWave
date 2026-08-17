"""Plain-language report rendering for Telegram or text export."""
from __future__ import annotations

from analysis.scenarios import DISCLAIMER, DecisionCard


def render_short(symbol:str,timeframe:str,current_price:float,card:DecisionCard)->str:
    lines=[f"{symbol} — {timeframe} view",f"Текущая цена: {current_price:.2f}",f"Сценарий: {card.direction}",f"Уверенность: {card.confidence}/100 — {card.label}"]
    if card.entry_low is not None: lines.append(f"Зона входа: {card.entry_low:.2f}–{card.entry_high:.2f}")
    if card.invalidation is not None: lines.append(f"Инвалидация: {card.invalidation:.2f}")
    if card.targets: lines.append("Цели: "+", ".join(f"{x:.2f}" for x in card.targets))
    if card.risk_reward is not None: lines.append(f"R:R: {card.risk_reward:.2f}")
    lines.append("Это сценарий, а не обещание движения цены.")
    lines.append(DISCLAIMER)
    return "\n".join(lines)


def render_detailed(meta:dict,cards:list[DecisionCard],method_notes:dict[str,str],limitations:list[str],backtest:dict|None=None)->str:
    lines=["ПОДРОБНЫЙ ОТЧЁТ","","Данные:"]
    for k,v in meta.items(): lines.append(f"- {k}: {v}")
    lines += ["","Методы:"]+[f"- {k}: {v}" for k,v in method_notes.items()]
    lines += ["","Сценарии:"]
    for c in cards:
        lines.append(f"- {c.direction}: {c.confidence}/100, {c.label}; условие: {c.condition}; за: {'; '.join(c.reasons_for)}; против: {'; '.join(c.reasons_against)}")
    if backtest:
        lines += ["","Backtest:"]+[f"- {k}: {v}" for k,v in backtest.items()]
    lines += ["","Ограничения:"]+[f"- {x}" for x in limitations]
    lines += ["",DISCLAIMER]
    return "\n".join(lines)
