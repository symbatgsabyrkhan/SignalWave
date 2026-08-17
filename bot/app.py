"""SignalWave Telegram bot: zero-friction inline UX + full analysis suite."""
from __future__ import annotations
import asyncio, os, tempfile
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
load_dotenv()

async def main():
    from aiogram import Bot, Dispatcher, F
    from aiogram.filters import CommandStart
    from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile
    from analysis.indicators import add_indicators
    from backtest.engine import simulate_signals, buy_and_hold
    from bot.handlers import start_text, csv_prompt
    from charts.plotter import render_analysis_suite, render_trade_plan_chart
    from data.loaders import fetch_binance, load_csv
    from pipeline import analyze
    from reports.render import render_short, render_detailed
    from storage.repository import Repository

    token=os.getenv("TELEGRAM_BOT_TOKEN")
    if not token: raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
    bot=Bot(token=token); dp=Dispatcher(); repo=Repository(os.getenv("SIGNALWAVE_DB","signalwave.db"))
    user_data:dict[int,pd.DataFrame]={}; user_meta:dict[int,dict]={}

    def kb(rows): return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t,callback_data=d) for t,d in row] for row in rows])
    main_kb=kb([[("📎 Загрузить CSV","csv"),("🌐 Binance","binance")],[("📊 Полный анализ","full")],[("⚖️ Long / Short","longshort"),("📅 Long-term","invest")],[("🧪 Backtest","backtest"),("🔔 Price alert","alert")]])
    symbol_kb=kb([[("BTCUSDT","sym:BTCUSDT"),("ETHUSDT","sym:ETHUSDT")],[("BNBUSDT","sym:BNBUSDT"),("SOLUSDT","sym:SOLUSDT")],[("⬅️ Меню","menu")]])
    tf_kb=lambda s: kb([[("1h",f"fetch:{s}:1h"),("4h",f"fetch:{s}:4h"),("1D",f"fetch:{s}:1d")],[("1W",f"fetch:{s}:1w"),("⬅️ Назад","binance")]])
    mode_kb=kb([[("⚡ Scalp","mode:scalp"),("📈 Swing","mode:swing")],[("⬅️ Меню","menu")]])

    def current(chat): return user_data.get(chat),user_meta.get(chat)
    async def require_data(target):
        df,meta=current(target.message.chat.id if isinstance(target,CallbackQuery) else target.chat.id)
        if df is None:
            await (target.message.answer("Сначала загрузите CSV или выберите Binance.",reply_markup=main_kb) if isinstance(target,CallbackQuery) else target.answer("Сначала загрузите CSV или выберите Binance.",reply_markup=main_kb))
            return None,None
        return df,meta

    async def full_report(message:Message):
        df,meta=await require_data(message)
        if df is None:return
        await message.answer("⏳ Строю 4 графика и отчёт…")
        try:
            result=await asyncio.to_thread(analyze,df); card=max(result["cards"],key=lambda c:c.confidence)
            detailed=render_detailed({"source":meta["source"],"symbol":meta["symbol"],"timeframe":meta["timeframe"],"rows":len(df)},list(result["cards"]),{"Indicators":"SMA/EMA, RSI, MACD, Bollinger, ATR","Structure":f"{len(result['pivots'])} pivots / {len(result['zones'])} zones","Fibonacci":f"{len(result['fibs'])} levels","Elliott":f"probabilistic {result['elliott'].confidence}/100"},["News/fundamentals are not included.","Elliott count can be ambiguous."])
            await message.answer(render_short(meta["symbol"],meta["timeframe"],float(result["data"]["close"].iloc[-1]),card)+"\n\n"+detailed)
            paths=await asyncio.to_thread(render_analysis_suite,result,"output",f"tg_{message.chat.id}")
            captions=["1/4 Trend + SMA/RSI","2/4 Support/Resistance + trendlines","3/4 Fibonacci + confluence","4/4 Elliott Wave primary count"]
            for p,c in zip(paths,captions): await message.answer_photo(FSInputFile(p),caption=c)
            await message.answer("Готово. Можно открыть торговый сценарий, backtest или alert.",reply_markup=main_kb)
        except Exception as e: await message.answer(f"❌ Анализ не выполнен: {type(e).__name__}: {e}")

    @dp.message(CommandStart())
    async def start(m:Message): await m.answer(start_text(),reply_markup=main_kb)
    @dp.callback_query(F.data=="menu")
    async def menu(c:CallbackQuery): await c.answer(); await c.message.answer("Выберите действие:",reply_markup=main_kb)
    @dp.callback_query(F.data=="csv")
    async def csv(c:CallbackQuery): await c.answer(); await c.message.answer(csv_prompt())
    @dp.message(F.document)
    async def doc(m:Message):
        if not m.document.file_name or not m.document.file_name.lower().endswith(".csv"): await m.answer("Нужен файл .csv"); return
        await m.answer("⏳ Проверяю CSV…"); tmp=None
        try:
            with tempfile.NamedTemporaryFile(suffix=".csv",delete=False) as f: tmp=Path(f.name)
            info=await bot.get_file(m.document.file_id); await bot.download_file(info.file_path,destination=tmp); vr=load_csv(tmp,source="koyfin")
            df=vr.data; symbol=str(df["symbol"].iloc[-1]) if "symbol" in df else "UNKNOWN"
            user_data[m.chat.id]=df; user_meta[m.chat.id]={"source":"Koyfin/CSV","symbol":symbol,"timeframe":str(df["timeframe"].iloc[-1]) if "timeframe" in df else "unknown"}
            warn="\n⚠️ Для SMA-200 желательно ≥200 свечей." if len(df)<200 else ""
            await m.answer(f"✅ CSV принят: {len(df)} свечей. {df['time'].iloc[0]} → {df['time'].iloc[-1]}.{warn}",reply_markup=main_kb)
        except Exception as e: await m.answer(f"❌ CSV не прошёл проверку: {e}")
        finally:
            if tmp and tmp.exists(): tmp.unlink(missing_ok=True)
    @dp.callback_query(F.data=="binance")
    async def binance(c:CallbackQuery): await c.answer(); await c.message.answer("Выберите инструмент:",reply_markup=symbol_kb)
    @dp.callback_query(F.data.startswith("sym:"))
    async def symbol(c:CallbackQuery): s=c.data.split(":",1)[1]; await c.answer(); await c.message.answer(f"{s}: выберите timeframe",reply_markup=tf_kb(s))
    @dp.callback_query(F.data.startswith("fetch:"))
    async def fetch(c:CallbackQuery):
        _,s,tf=c.data.split(":"); await c.answer(); await c.message.answer(f"⏳ Binance: {s} / {tf}, загружаю 1,000 свечей…")
        try:
            vr=await asyncio.to_thread(fetch_binance,s,tf,1000); user_data[c.message.chat.id]=vr.data; user_meta[c.message.chat.id]={"source":"Binance public API","symbol":s,"timeframe":tf}; await c.message.answer(f"✅ {s}/{tf}: {len(vr.data)} свечей загружено.",reply_markup=main_kb)
        except Exception as e: await c.message.answer(f"❌ Binance error: {e}")
    @dp.callback_query(F.data=="full")
    async def full(c:CallbackQuery): await c.answer(); await full_report(c.message)
    @dp.callback_query(F.data=="longshort")
    async def ls(c:CallbackQuery): await c.answer(); df,_=await require_data(c); (await c.message.answer("Выберите торговый горизонт:",reply_markup=mode_kb)) if df is not None else None
    @dp.callback_query(F.data.startswith("mode:"))
    async def mode(c:CallbackQuery):
        intent=c.data.split(":")[1]; await c.answer(); df,meta=await require_data(c)
        if df is None:return
        result=await asyncio.to_thread(analyze,df); cards=result["cards"][:2]; card=max(cards,key=lambda x:x.confidence)
        text=f"{'⚡ SCALP' if intent=='scalp' else '📈 SWING'}\n\n"+render_short(meta["symbol"],meta["timeframe"],float(result["data"]["close"].iloc[-1]),card)
        if card.entry_low is not None and card.invalidation is not None:
            risk=abs(((card.entry_low+card.entry_high)/2)-card.invalidation); text+=f"\nPosition-size hint: при риске 1% размер позиции = капитал×0.01 / {risk:.2f}."
        p=await asyncio.to_thread(render_trade_plan_chart,result["data"],Path("output")/f"trade_{c.message.chat.id}.png",card); await c.message.answer(text); await c.message.answer_photo(FSInputFile(p),caption="Entry / invalidation / TP1 / TP2")
    @dp.callback_query(F.data=="invest")
    async def invest(c:CallbackQuery):
        await c.answer(); df,meta=await require_data(c)
        if df is None:return
        r=await asyncio.to_thread(analyze,df); price=float(r["data"]["close"].iloc[-1]); sma=r["data"]["sma_200"].iloc[-1]; regime="bull" if pd.notna(sma) and price>sma else "bear/defensive"
        con=[f for f in r["fibs"] if f.confluence and f.ratio in (.618,.786)]; zones=", ".join(f"{x.price:,.2f}" for x in con) or "нет подтверждённой Fib 0.618/0.786 confluence — не форсировать вход"
        await c.message.answer(f"📅 LONG-TERM / INVEST\n\n{meta['symbol']} {meta['timeframe']}\nRegime vs SMA-200: {regime}\nDCA accumulation zones: {zones}\nRisk: распределяйте вход по частям; тезис пересматривается при сломе долгосрочной структуры.\n\nNot financial advice — educational tool.")
    @dp.callback_query(F.data=="backtest")
    async def backtest(c:CallbackQuery):
        await c.answer(); df,meta=await require_data(c)
        if df is None:return
        e=add_indicators(df); sig=pd.Series(0,index=e.index,dtype=int); ok=e.sma_20.notna()&e.sma_50.notna(); sig.loc[ok&(e.sma_20>e.sma_50)]=1; sig.loc[ok&(e.sma_20<e.sma_50)]=-1
        split=max(1,int(len(e)*.7)); oos=e.iloc[split:].reset_index(drop=True); osig=sig.iloc[split:].reset_index(drop=True); r=simulate_signals(oos,osig,fee_rate=.001,slippage_rate=.0005); pf="∞" if r.profit_factor==float("inf") else f"{r.profit_factor:.2f}"
        await c.message.answer(f"🧪 BACKTEST — 70/30 OOS\n{meta['symbol']} {meta['timeframe']}\nOOS bars: {len(oos)} | trades: {len(r.trades)}\nWin rate: {r.win_rate*100:.1f}%\nProfit factor: {pf}\nMax drawdown: {r.max_drawdown*100:.2f}%\nSortino: {r.sortino:.2f}\nExpectancy: {r.expectancy*100:.3f}%\nOOS return: {r.total_return*100:.2f}%\nBuy & Hold OOS: {buy_and_hold(oos)*100:.2f}%\nCosts: 0.1% fee + 0.05% slippage/side assumption. No same-bar execution.")
    @dp.callback_query(F.data=="alert")
    async def alert(c:CallbackQuery): await c.answer(); await c.message.answer("🔔 Отправьте: ALERT BTCUSDT 100000 above\nили ALERT BTCUSDT 90000 below")
    @dp.message(F.text.regexp(r"(?i)^ALERT\s+[A-Z0-9]{5,15}\s+\d+(\.\d+)?\s+(above|below)$"))
    async def save_alert(m:Message):
        _,s,l,d=m.text.split(); i=repo.add_alert(m.chat.id,s,float(l),d.lower()); await m.answer(f"✅ Alert #{i}: {s.upper()} {d.lower()} {float(l):g}. Фоновая проверка включена.")

    async def alert_worker():
        while True:
            try:
                rows=repo.conn.execute("SELECT DISTINCT symbol FROM alerts WHERE active=1").fetchall()
                for (s,) in rows:
                    try:
                        vr=await asyncio.to_thread(fetch_binance,s,"1m",2); price=float(vr.data.close.iloc[-1])
                        for a in repo.triggered_alerts(s,price):
                            await bot.send_message(a["chat_id"],f"🔔 PRICE ALERT\n{s}: {price:,.2f} crossed {a['direction']} {a['level']:,.2f}"); repo.deactivate_alert(a["id"])
                    except Exception: pass
            finally: await asyncio.sleep(60)
    worker=asyncio.create_task(alert_worker())
    try: await dp.start_polling(bot)
    finally: worker.cancel(); repo.close()

if __name__=="__main__": asyncio.run(main())
