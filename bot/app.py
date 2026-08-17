"""SignalWave Telegram bot runtime.

Supports:
- local long polling: python -m bot.app
- production webhook mode through web/app.py
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

load_dotenv()


_bot = None
_dp = None
_repo = None
_alert_worker_task = None
_initialized = False


def create_runtime():
    """
    Create and configure the Telegram Bot + Dispatcher once.

    The same runtime is used by:
    - local polling
    - FastAPI webhook deployment
    """
    global _bot, _dp, _repo, _initialized

    if _initialized:
        return _bot, _dp, _repo

    from aiogram import Bot, Dispatcher, F
    from aiogram.filters import CommandStart
    from aiogram.types import (
        CallbackQuery,
        FSInputFile,
        InlineKeyboardButton,
        InlineKeyboardMarkup,
        Message,
    )

    from analysis.indicators import add_indicators
    from backtest.engine import buy_and_hold, simulate_signals
    from bot.handlers import csv_prompt, start_text
    from charts.plotter import (
        render_analysis_suite,
        render_trade_plan_chart,
    )
    from data.loaders import fetch_binance, load_csv
    from pipeline import analyze
    from reports.render import render_detailed, render_short
    from storage.repository import Repository

    token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not set"
        )

    bot = Bot(token=token)
    dp = Dispatcher()

    repo = Repository(
        os.getenv(
            "SIGNALWAVE_DB",
            "signalwave.db",
        )
    )

    user_data: dict[int, pd.DataFrame] = {}
    user_meta: dict[int, dict] = {}

    def kb(rows):
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=text,
                        callback_data=data,
                    )
                    for text, data in row
                ]
                for row in rows
            ]
        )

    main_kb = kb(
        [
            [
                (
                    "📎 Загрузить CSV",
                    "csv",
                ),
                (
                    "🌐 Binance",
                    "binance",
                ),
            ],
            [
                (
                    "📊 Полный анализ",
                    "full",
                )
            ],
            [
                (
                    "⚖️ Long / Short",
                    "longshort",
                ),
                (
                    "📅 Long-term",
                    "invest",
                ),
            ],
            [
                (
                    "🧪 Backtest",
                    "backtest",
                ),
                (
                    "🔔 Price alert",
                    "alert",
                ),
            ],
        ]
    )

    symbol_kb = kb(
        [
            [
                (
                    "BTCUSDT",
                    "sym:BTCUSDT",
                ),
                (
                    "ETHUSDT",
                    "sym:ETHUSDT",
                ),
            ],
            [
                (
                    "BNBUSDT",
                    "sym:BNBUSDT",
                ),
                (
                    "SOLUSDT",
                    "sym:SOLUSDT",
                ),
            ],
            [
                (
                    "⬅️ Меню",
                    "menu",
                )
            ],
        ]
    )

    def tf_kb(symbol):
        return kb(
            [
                [
                    (
                        "1h",
                        f"fetch:{symbol}:1h",
                    ),
                    (
                        "4h",
                        f"fetch:{symbol}:4h",
                    ),
                    (
                        "1D",
                        f"fetch:{symbol}:1d",
                    ),
                ],
                [
                    (
                        "1W",
                        f"fetch:{symbol}:1w",
                    ),
                    (
                        "⬅️ Назад",
                        "binance",
                    ),
                ],
            ]
        )

    mode_kb = kb(
        [
            [
                (
                    "⚡ Scalp",
                    "mode:scalp",
                ),
                (
                    "📈 Swing",
                    "mode:swing",
                ),
            ],
            [
                (
                    "⬅️ Меню",
                    "menu",
                )
            ],
        ]
    )

    def current(chat_id):
        return (
            user_data.get(chat_id),
            user_meta.get(chat_id),
        )

    async def require_data(target):
        if isinstance(
            target,
            CallbackQuery,
        ):
            chat_id = (
                target.message.chat.id
            )
        else:
            chat_id = target.chat.id

        df, meta = current(chat_id)

        if df is None:
            message = (
                "Сначала загрузите CSV "
                "или выберите Binance."
            )

            if isinstance(
                target,
                CallbackQuery,
            ):
                await target.message.answer(
                    message,
                    reply_markup=main_kb,
                )
            else:
                await target.answer(
                    message,
                    reply_markup=main_kb,
                )

            return None, None

        return df, meta

    async def full_report(
        message: Message,
    ):
        df, meta = await require_data(
            message
        )

        if df is None:
            return

        await message.answer(
            "⏳ Строю 4 графика и отчёт…"
        )

        try:
            result = await asyncio.to_thread(
                analyze,
                df,
            )

            card = max(
                result["cards"],
                key=lambda c: c.confidence,
            )

            detailed = render_detailed(
                {
                    "source":
                        meta["source"],
                    "symbol":
                        meta["symbol"],
                    "timeframe":
                        meta["timeframe"],
                    "rows":
                        len(df),
                },
                list(
                    result["cards"]
                ),
                {
                    "Indicators":
                        (
                            "SMA/EMA, RSI, MACD, "
                            "Bollinger, ATR"
                        ),
                    "Structure":
                        (
                            f"{len(result['pivots'])} "
                            "pivots / "
                            f"{len(result['zones'])} "
                            "zones"
                        ),
                    "Fibonacci":
                        (
                            f"{len(result['fibs'])} "
                            "levels"
                        ),
                    "Elliott":
                        (
                            "probabilistic "
                            f"{result['elliott'].confidence}"
                            "/100"
                        ),
                },
                [
                    (
                        "News/fundamentals "
                        "are not included."
                    ),
                    (
                        "Elliott count "
                        "can be ambiguous."
                    ),
                ],
            )

            short = render_short(
                meta["symbol"],
                meta["timeframe"],
                float(
                    result["data"][
                        "close"
                    ].iloc[-1]
                ),
                card,
            )

            await message.answer(
                short
                + "\n\n"
                + detailed
            )

            paths = (
                await asyncio.to_thread(
                    render_analysis_suite,
                    result,
                    "output",
                    (
                        "tg_"
                        f"{message.chat.id}"
                    ),
                )
            )

            captions = [
                "1/4 Trend + SMA/RSI",
                (
                    "2/4 Support/Resistance "
                    "+ trendlines"
                ),
                (
                    "3/4 Fibonacci "
                    "+ confluence"
                ),
                (
                    "4/4 Elliott Wave "
                    "primary count"
                ),
            ]

            for path, caption in zip(
                paths,
                captions,
            ):
                await message.answer_photo(
                    FSInputFile(path),
                    caption=caption,
                )

            await message.answer(
                (
                    "Готово. Можно открыть "
                    "торговый сценарий, "
                    "backtest или alert."
                ),
                reply_markup=main_kb,
            )

        except Exception as exc:
            await message.answer(
                (
                    "❌ Анализ не выполнен: "
                    f"{type(exc).__name__}: "
                    f"{exc}"
                )
            )

    @dp.message(CommandStart())
    async def start(
        message: Message,
    ):
        await message.answer(
            start_text(),
            reply_markup=main_kb,
        )

    @dp.callback_query(
        F.data == "menu"
    )
    async def menu(
        callback: CallbackQuery,
    ):
        await callback.answer()

        await callback.message.answer(
            "Выберите действие:",
            reply_markup=main_kb,
        )

    @dp.callback_query(
        F.data == "csv"
    )
    async def csv(
        callback: CallbackQuery,
    ):
        await callback.answer()

        await callback.message.answer(
            csv_prompt()
        )

    @dp.message(F.document)
    async def document(
        message: Message,
    ):
        filename = (
            message.document.file_name
            or ""
        )

        if not filename.lower().endswith(
            ".csv"
        ):
            await message.answer(
                "Нужен файл .csv"
            )
            return

        await message.answer(
            "⏳ Проверяю CSV…"
        )

        tmp = None

        try:
            with tempfile.NamedTemporaryFile(
                suffix=".csv",
                delete=False,
            ) as file:
                tmp = Path(
                    file.name
                )

            info = await bot.get_file(
                message.document.file_id
            )

            await bot.download_file(
                info.file_path,
                destination=tmp,
            )

            validated = load_csv(
                tmp,
                source="koyfin",
            )

            df = validated.data

            if "symbol" in df:
                symbol = str(
                    df["symbol"].iloc[-1]
                )
            else:
                symbol = "UNKNOWN"

            if "timeframe" in df:
                timeframe = str(
                    df[
                        "timeframe"
                    ].iloc[-1]
                )
            else:
                timeframe = "unknown"

            user_data[
                message.chat.id
            ] = df

            user_meta[
                message.chat.id
            ] = {
                "source": "Koyfin/CSV",
                "symbol": symbol,
                "timeframe": timeframe,
            }

            warning = (
                "\n⚠️ Для SMA-200 "
                "желательно ≥200 свечей."
                if len(df) < 200
                else ""
            )

            await message.answer(
                (
                    f"✅ CSV принят: "
                    f"{len(df)} свечей. "
                    f"{df['time'].iloc[0]} "
                    "→ "
                    f"{df['time'].iloc[-1]}."
                    f"{warning}"
                ),
                reply_markup=main_kb,
            )

        except Exception as exc:
            await message.answer(
                (
                    "❌ CSV не прошёл "
                    f"проверку: {exc}"
                )
            )

        finally:
            if (
                tmp
                and tmp.exists()
            ):
                tmp.unlink(
                    missing_ok=True
                )

    @dp.callback_query(
        F.data == "binance"
    )
    async def binance(
        callback: CallbackQuery,
    ):
        await callback.answer()

        await callback.message.answer(
            "Выберите инструмент:",
            reply_markup=symbol_kb,
        )

    @dp.callback_query(
        F.data.startswith("sym:")
    )
    async def symbol(
        callback: CallbackQuery,
    ):
        symbol_name = (
            callback.data.split(
                ":",
                1,
            )[1]
        )

        await callback.answer()

        await callback.message.answer(
            (
                f"{symbol_name}: "
                "выберите timeframe"
            ),
            reply_markup=tf_kb(
                symbol_name
            ),
        )

    @dp.callback_query(
        F.data.startswith("fetch:")
    )
    async def fetch(
        callback: CallbackQuery,
    ):
        _, symbol_name, timeframe = (
            callback.data.split(":")
        )

        await callback.answer()

        await callback.message.answer(
            (
                "⏳ Binance: "
                f"{symbol_name} / "
                f"{timeframe}, "
                "загружаю "
                "1,000 свечей…"
            )
        )

        try:
            validated = (
                await asyncio.to_thread(
                    fetch_binance,
                    symbol_name,
                    timeframe,
                    1000,
                )
            )

            user_data[
                callback.message.chat.id
            ] = validated.data

            user_meta[
                callback.message.chat.id
            ] = {
                "source":
                    "Binance public API",
                "symbol":
                    symbol_name,
                "timeframe":
                    timeframe,
            }

            await callback.message.answer(
                (
                    f"✅ {symbol_name}/"
                    f"{timeframe}: "
                    f"{len(validated.data)} "
                    "свечей загружено."
                ),
                reply_markup=main_kb,
            )

        except Exception as exc:
            await callback.message.answer(
                (
                    "❌ Binance error: "
                    f"{exc}"
                )
            )

    @dp.callback_query(
        F.data == "full"
    )
    async def full(
        callback: CallbackQuery,
    ):
        await callback.answer()

        await full_report(
            callback.message
        )

    @dp.callback_query(
        F.data == "longshort"
    )
    async def long_short(
        callback: CallbackQuery,
    ):
        await callback.answer()

        df, _ = await require_data(
            callback
        )

        if df is not None:
            await callback.message.answer(
                (
                    "Выберите торговый "
                    "горизонт:"
                ),
                reply_markup=mode_kb,
            )

    @dp.callback_query(
        F.data.startswith("mode:")
    )
    async def mode(
        callback: CallbackQuery,
    ):
        intent = (
            callback.data.split(":")[1]
        )

        await callback.answer()

        df, meta = await require_data(
            callback
        )

        if df is None:
            return

        result = await asyncio.to_thread(
            analyze,
            df,
        )

        cards = result["cards"][:2]

        card = max(
            cards,
            key=lambda item:
                item.confidence,
        )

        label = (
            "⚡ SCALP"
            if intent == "scalp"
            else "📈 SWING"
        )

        text = (
            label
            + "\n\n"
            + render_short(
                meta["symbol"],
                meta["timeframe"],
                float(
                    result["data"][
                        "close"
                    ].iloc[-1]
                ),
                card,
            )
        )

        if (
            card.entry_low
            is not None
            and card.invalidation
            is not None
        ):
            risk = abs(
                (
                    (
                        card.entry_low
                        + card.entry_high
                    )
                    / 2
                )
                - card.invalidation
            )

            text += (
                "\nPosition-size hint: "
                "при риске 1% "
                "размер позиции = "
                "капитал×0.01 / "
                f"{risk:.2f}."
            )

        path = await asyncio.to_thread(
            render_trade_plan_chart,
            result["data"],
            Path("output")
            / (
                "trade_"
                f"{callback.message.chat.id}"
                ".png"
            ),
            card,
        )

        await callback.message.answer(
            text
        )

        await callback.message.answer_photo(
            FSInputFile(path),
            caption=(
                "Entry / invalidation "
                "/ TP1 / TP2"
            ),
        )

    @dp.callback_query(
        F.data == "invest"
    )
    async def invest(
        callback: CallbackQuery,
    ):
        await callback.answer()

        df, meta = await require_data(
            callback
        )

        if df is None:
            return

        result = await asyncio.to_thread(
            analyze,
            df,
        )

        price = float(
            result["data"][
                "close"
            ].iloc[-1]
        )

        sma = result["data"][
            "sma_200"
        ].iloc[-1]

        regime = (
            "bull"
            if (
                pd.notna(sma)
                and price > sma
            )
            else "bear/defensive"
        )

        confluence = [
            fib
            for fib in result["fibs"]
            if (
                fib.confluence
                and fib.ratio
                in (.618, .786)
            )
        ]

        zones = (
            ", ".join(
                f"{item.price:,.2f}"
                for item
                in confluence
            )
            or (
                "нет подтверждённой "
                "Fib 0.618/0.786 "
                "confluence — "
                "не форсировать вход"
            )
        )

        await callback.message.answer(
            (
                "📅 LONG-TERM / INVEST\n\n"
                f"{meta['symbol']} "
                f"{meta['timeframe']}\n"
                "Regime vs SMA-200: "
                f"{regime}\n"
                "DCA accumulation zones: "
                f"{zones}\n"
                "Risk: распределяйте вход "
                "по частям; тезис "
                "пересматривается при сломе "
                "долгосрочной структуры."
                "\n\nNot financial advice — "
                "educational tool."
            )
        )

    @dp.callback_query(
        F.data == "backtest"
    )
    async def backtest(
        callback: CallbackQuery,
    ):
        await callback.answer()

        df, meta = await require_data(
            callback
        )

        if df is None:
            return

        enriched = add_indicators(
            df
        )

        signals = pd.Series(
            0,
            index=enriched.index,
            dtype=int,
        )

        valid = (
            enriched.sma_20.notna()
            & enriched.sma_50.notna()
        )

        signals.loc[
            valid
            & (
                enriched.sma_20
                > enriched.sma_50
            )
        ] = 1

        signals.loc[
            valid
            & (
                enriched.sma_20
                < enriched.sma_50
            )
        ] = -1

        split = max(
            1,
            int(
                len(enriched)
                * 0.7
            ),
        )

        oos = (
            enriched.iloc[split:]
            .reset_index(drop=True)
        )

        oos_signals = (
            signals.iloc[split:]
            .reset_index(drop=True)
        )

        result = simulate_signals(
            oos,
            oos_signals,
            fee_rate=0.001,
            slippage_rate=0.0005,
        )

        profit_factor = (
            "∞"
            if result.profit_factor
            == float("inf")
            else (
                f"{result.profit_factor:.2f}"
            )
        )

        await callback.message.answer(
            (
                "🧪 BACKTEST — 70/30 OOS\n"
                f"{meta['symbol']} "
                f"{meta['timeframe']}\n"
                f"OOS bars: {len(oos)} "
                "| trades: "
                f"{len(result.trades)}\n"
                "Win rate: "
                f"{result.win_rate * 100:.1f}%\n"
                "Profit factor: "
                f"{profit_factor}\n"
                "Max drawdown: "
                f"{result.max_drawdown * 100:.2f}%\n"
                "Sortino: "
                f"{result.sortino:.2f}\n"
                "Expectancy: "
                f"{result.expectancy * 100:.3f}%\n"
                "OOS return: "
                f"{result.total_return * 100:.2f}%\n"
                "Buy & Hold OOS: "
                f"{buy_and_hold(oos) * 100:.2f}%\n"
                "Costs: 0.1% fee + "
                "0.05% slippage/side "
                "assumption. "
                "No same-bar execution."
            )
        )

    @dp.callback_query(
        F.data == "alert"
    )
    async def alert(
        callback: CallbackQuery,
    ):
        await callback.answer()

        await callback.message.answer(
            (
                "🔔 Отправьте: "
                "ALERT BTCUSDT "
                "100000 above\n"
                "или ALERT BTCUSDT "
                "90000 below"
            )
        )

    @dp.message(
        F.text.regexp(
            (
                r"(?i)^ALERT\s+"
                r"[A-Z0-9]{5,15}\s+"
                r"\d+(\.\d+)?\s+"
                r"(above|below)$"
            )
        )
    )
    async def save_alert(
        message: Message,
    ):
        _, symbol_name, level, direction = (
            message.text.split()
        )

        alert_id = repo.add_alert(
            message.chat.id,
            symbol_name,
            float(level),
            direction.lower(),
        )

        await message.answer(
            (
                f"✅ Alert #{alert_id}: "
                f"{symbol_name.upper()} "
                f"{direction.lower()} "
                f"{float(level):g}. "
                "Фоновая проверка включена."
            )
        )

    _bot = bot
    _dp = dp
    _repo = repo
    _initialized = True

    return bot, dp, repo


async def alert_worker():
    """
    Background price-alert checker.

    Note:
    on free hosting this runs only while the web
    service process itself is awake.
    """
    bot, _, repo = create_runtime()

    while True:
        try:
            rows = repo.conn.execute(
                (
                    "SELECT DISTINCT symbol "
                    "FROM alerts "
                    "WHERE active=1"
                )
            ).fetchall()

            from data.loaders import (
                fetch_binance,
            )

            for (symbol,) in rows:
                try:
                    validated = (
                        await asyncio.to_thread(
                            fetch_binance,
                            symbol,
                            "1m",
                            2,
                        )
                    )

                    price = float(
                        validated.data[
                            "close"
                        ].iloc[-1]
                    )

                    for alert in (
                        repo.triggered_alerts(
                            symbol,
                            price,
                        )
                    ):
                        await bot.send_message(
                            alert["chat_id"],
                            (
                                "🔔 PRICE ALERT\n"
                                f"{symbol}: "
                                f"{price:,.2f} "
                                "crossed "
                                f"{alert['direction']} "
                                f"{alert['level']:,.2f}"
                            ),
                        )

                        repo.deactivate_alert(
                            alert["id"]
                        )

                except Exception as exc:
                    print(
                        "Alert check error:",
                        symbol,
                        exc,
                    )

        except asyncio.CancelledError:
            raise

        except Exception as exc:
            print(
                "Alert worker error:",
                exc,
            )

        await asyncio.sleep(60)


async def start_background_tasks():
    global _alert_worker_task

    create_runtime()

    if (
        _alert_worker_task is None
        or _alert_worker_task.done()
    ):
        _alert_worker_task = (
            asyncio.create_task(
                alert_worker()
            )
        )


async def stop_background_tasks():
    global _alert_worker_task

    if _alert_worker_task:
        _alert_worker_task.cancel()

        try:
            await _alert_worker_task
        except asyncio.CancelledError:
            pass

        _alert_worker_task = None


async def close_runtime():
    global _bot, _dp, _repo

    await stop_background_tasks()

    if _bot is not None:
        await _bot.session.close()

    if _repo is not None:
        _repo.close()


async def main():
    """
    Local-development mode.

    Render production deployment should use
    FastAPI webhook mode instead.
    """
    bot, dp, _ = create_runtime()

    await bot.delete_webhook(
        drop_pending_updates=False
    )

    await start_background_tasks()

    try:
        await dp.start_polling(bot)

    finally:
        await close_runtime()


if __name__ == "__main__":
    asyncio.run(main())