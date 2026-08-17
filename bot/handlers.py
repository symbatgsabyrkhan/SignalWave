"""Telegram UX definitions kept independent from analysis logic."""
from __future__ import annotations

MENU=("Загрузить CSV","Данные Binance","Полный технический анализ","Long / Short","Long-term","Backtest","Price alert")
INTENTS=("Scalp","Swing","Invest")
def start_text()->str:
    return "🌊 SignalWave Bot\n\nЗагрузите Koyfin CSV или выберите Binance. После /start остальные действия доступны кнопками.\n\nАнализ показывает воспроизводимые сценарии, а не гарантированный прогноз."
def csv_prompt()->str:
    return "📎 Отправьте CSV. Поддерживаются обычные Date/time, Open, High, Low, Close, Volume и Koyfin-колонки вида BTCUSD Open/High/Low/Close."
def validate_menu_choice(choice:str)->str:
    if choice not in MENU: raise ValueError("unknown menu choice")
    return choice
