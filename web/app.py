"""FastAPI web dashboard for SignalWave."""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Literal

import httpx
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from analysis.indicators import add_indicators
from backtest.engine import buy_and_hold, simulate_signals
from data.loaders import fetch_binance, load_csv
from pipeline import analyze


ROOT = Path(__file__).resolve().parent

# IMPORTANT:
# Always load .env from the root of ta-bot-final.
# This allows Gemini/OpenAI settings to work regardless
# of the directory from which uvicorn was launched.
load_dotenv(
    dotenv_path=ROOT.parent / ".env",
    override=True,
)

app = FastAPI(
    title="SignalWave Dashboard",
    version="1.2.1",
)

app.mount(
    "/static",
    StaticFiles(directory=ROOT / "static"),
    name="static",
)


class AssistantRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    language: Literal["en", "ru", "kk"] = "en"
    context: dict[str, Any] | None = None


def _clean(value):
    if value is None:
        return None

    if isinstance(value, float) and (
        math.isnan(value) or math.isinf(value)
    ):
        return None

    return value


def _card(card):
    return {
        "direction": card.direction,
        "condition": card.condition,
        "entry_low": _clean(card.entry_low),
        "entry_high": _clean(card.entry_high),
        "invalidation": _clean(card.invalidation),
        "targets": [_clean(x) for x in card.targets],
        "risk_reward": _clean(card.risk_reward),
        "confidence": card.confidence,
        "label": card.label,
        "reasons_for": list(card.reasons_for),
        "reasons_against": list(card.reasons_against),
        "actionable": card.actionable,
    }


def _payload(
    df: pd.DataFrame,
    symbol: str,
    timeframe: str,
    source: str,
) -> dict:

    result = analyze(df)

    d = result["data"].tail(500).copy()

    series = {}

    for col in (
        "open",
        "high",
        "low",
        "close",
        "volume",
        "sma_20",
        "sma_50",
        "sma_100",
        "sma_200",
        "ema_20",
        "rsi_14",
        "macd",
        "macd_signal",
        "macd_hist",
        "bb_upper",
        "bb_middle",
        "bb_lower",
        "atr_14",
    ):
        if col in d:
            series[col] = [
                _clean(float(v))
                if pd.notna(v)
                else None
                for v in d[col]
            ]

    times = [
        pd.Timestamp(v).isoformat()
        for v in d["time"]
    ]

    zones = [
        {
            "low": z.low,
            "high": z.high,
            "center": z.center,
            "touches": z.touches,
            "strength": z.strength,
            "type": z.kind,
        }
        for z in result["zones"]
    ]

    fibs = [
        {
            "ratio": f.ratio,
            "price": f.price,
            "kind": f.kind,
            "confluence": f.confluence,
        }
        for f in result["fibs"]
    ]

    ell = result["elliott"]

    return {
        "market": {
            "symbol": symbol,
            "timeframe": timeframe,
            "source": source,
            "price": float(d["close"].iloc[-1]),
            "rows": len(df),
            "start": pd.Timestamp(
                d["time"].iloc[0]
            ).isoformat(),
            "end": pd.Timestamp(
                d["time"].iloc[-1]
            ).isoformat(),
        },

        "time": times,
        "series": series,
        "zones": zones,
        "fibs": fibs,

        "cards": [
            _card(c)
            for c in result["cards"]
        ],

        "votes": result["votes"],

        "elliott": {
            "confidence": ell.confidence,
            "valid": ell.valid,
            "notes": list(ell.reasons),
            "labels": list(ell.labels),
            "alternate": ell.alternate,
        },
    }


def _assistant_context(
    raw: dict[str, Any] | None,
) -> dict[str, Any]:

    if not raw:
        return {}

    market = raw.get("market") or {}
    series = raw.get("series") or {}

    def last(name: str):

        values = series.get(name) or []

        for value in reversed(values):
            if value is not None:
                return value

        return None

    return {
        "market": {
            "symbol": market.get("symbol"),
            "timeframe": market.get("timeframe"),
            "source": market.get("source"),
            "price": market.get("price"),
            "start": market.get("start"),
            "end": market.get("end"),
            "rows": market.get("rows"),
        },

        "latest_indicators": {
            "sma_20": last("sma_20"),
            "sma_50": last("sma_50"),
            "sma_200": last("sma_200"),
            "rsi_14": last("rsi_14"),
            "macd": last("macd"),
            "macd_signal": last("macd_signal"),
            "atr_14": last("atr_14"),
            "volume": last("volume"),
        },

        "scenarios": (
            raw.get("cards") or []
        )[:3],

        "zones": (
            raw.get("zones") or []
        )[:6],

        "fibonacci": (
            raw.get("fibs") or []
        )[:8],

        "elliott":
            raw.get("elliott") or {},

        "votes":
            raw.get("votes") or {},
    }


def _assistant_instructions(
    language: str,
) -> str:

    language_name = {
        "en": "English",
        "ru": "Russian",
        "kk": "Kazakh",
    }[language]

    return f"""
You are SignalWave AI, an educational market-analysis
assistant embedded in SignalWave.

Reply in {language_name}.

Use only the computed SignalWave context supplied with
the user's question for market-specific claims.

If context is missing, say that a market analysis must
be run first.

Explain indicators, scenarios, invalidation, targets,
risk/reward, support/resistance, Fibonacci, Elliott Wave
and backtest results clearly.

Never claim certainty or guaranteed profit.

Do not invent prices, indicators, news or fundamentals.

Distinguish computed facts from interpretation.

Elliott Wave must always be described as experimental
and probabilistic.

Keep answers concise and useful.

For market-specific answers include a brief reminder
that SignalWave is an educational tool and not
financial advice.
""".strip()


async def _call_openai(
    message: str,
    language: str,
    context: dict[str, Any],
) -> str:

    api_key = os.getenv(
        "OPENAI_API_KEY"
    )

    if not api_key:
        raise HTTPException(
            status_code=503,
            detail=(
                "OPENAI_API_KEY "
                "is not configured"
            ),
        )

    model = os.getenv(
        "OPENAI_MODEL",
        "gpt-5",
    )

    body = {
        "model": model,
        "store": False,

        "instructions":
            _assistant_instructions(
                language
            ),

        "input": (
            "SignalWave computed context:\n"
            + json.dumps(
                context,
                ensure_ascii=False,
                separators=(",", ":"),
            )
            + "\n\nUser question:\n"
            + message
        ),
    }

    async with httpx.AsyncClient(
        timeout=45.0
    ) as client:

        response = await client.post(
            "https://api.openai.com/v1/responses",

            headers={
                "Authorization":
                    f"Bearer {api_key}",

                "Content-Type":
                    "application/json",
            },

            json=body,
        )

    if response.status_code >= 400:

        if response.headers.get(
            "content-type",
            "",
        ).startswith(
            "application/json"
        ):
            detail = (
                response.json()
                .get("error", {})
                .get("message")
            )
        else:
            detail = response.text

        raise HTTPException(
            status_code=502,
            detail=(
                f"OpenAI error: "
                f"{detail or response.status_code}"
            ),
        )

    data = response.json()

    text = data.get(
        "output_text"
    )

    if not text:

        parts = []

        for item in data.get(
            "output",
            [],
        ):
            for content in item.get(
                "content",
                [],
            ):
                if (
                    content.get("type")
                    == "output_text"
                    and content.get("text")
                ):
                    parts.append(
                        content["text"]
                    )

        text = "\n".join(parts)

    if not text:
        raise HTTPException(
            status_code=502,
            detail=(
                "OpenAI returned no text"
            ),
        )

    return text


async def _call_gemini(
    message: str,
    language: str,
    context: dict[str, Any],
) -> str:

    api_key = os.getenv(
        "GEMINI_API_KEY"
    )

    if not api_key:
        raise HTTPException(
            status_code=503,
            detail=(
                "GEMINI_API_KEY "
                "is not configured"
            ),
        )

    model = os.getenv(
        "GEMINI_MODEL",
        "gemini-2.5-flash",
    )

    body = {
        "system_instruction": {
            "parts": [
                {
                    "text":
                        _assistant_instructions(
                            language
                        )
                }
            ]
        },

        "contents": [
            {
                "role": "user",

                "parts": [
                    {
                        "text": (
                            "SignalWave computed "
                            "context:\n"
                            + json.dumps(
                                context,
                                ensure_ascii=False,
                                separators=(
                                    ",",
                                    ":",
                                ),
                            )
                            + "\n\nUser question:\n"
                            + message
                        )
                    }
                ],
            }
        ],
    }

    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{model}:generateContent"
    )

    async with httpx.AsyncClient(
        timeout=45.0
    ) as client:

        response = await client.post(
            url,

            headers={
                "x-goog-api-key":
                    api_key,

                "Content-Type":
                    "application/json",
            },

            json=body,
        )

    if response.status_code >= 400:

        if response.headers.get(
            "content-type",
            "",
        ).startswith(
            "application/json"
        ):
            detail = (
                response.json()
                .get("error", {})
                .get("message")
            )
        else:
            detail = response.text

        raise HTTPException(
            status_code=502,
            detail=(
                f"Gemini error: "
                f"{detail or response.status_code}"
            ),
        )

    data = response.json()

    try:
        text = "\n".join(
            part.get("text", "")

            for candidate
            in data.get(
                "candidates",
                [],
            )

            for part
            in candidate.get(
                "content",
                {},
            ).get(
                "parts",
                [],
            )

            if part.get("text")
        ).strip()

    except (
        TypeError,
        AttributeError,
    ):
        text = ""

    if not text:
        raise HTTPException(
            status_code=502,
            detail=(
                "Gemini returned no text"
            ),
        )

    return text


@app.get(
    "/",
    response_class=HTMLResponse,
)
def index():

    return (
        ROOT
        / "templates"
        / "index.html"
    ).read_text(
        encoding="utf-8"
    )


@app.get("/health")
def health():

    return {
        "status": "ok",
        "ai_provider":
            os.getenv(
                "AI_PROVIDER",
                "openai",
            ).strip().lower(),
    }


@app.get(
    "/api/assistant/status"
)
def assistant_status():

    provider = os.getenv(
        "AI_PROVIDER",
        "openai",
    ).strip().lower()

    if provider not in {
        "openai",
        "gemini",
    }:
        provider = "openai"

    if provider == "openai":

        configured = bool(
            os.getenv(
                "OPENAI_API_KEY"
            )
        )

        model = os.getenv(
            "OPENAI_MODEL",
            "gpt-5",
        )

    else:

        configured = bool(
            os.getenv(
                "GEMINI_API_KEY"
            )
        )

        model = os.getenv(
            "GEMINI_MODEL",
            "gemini-2.5-flash",
        )

    return {
        "provider": provider,
        "configured": configured,
        "model": model,
    }


@app.post("/api/assistant")
async def assistant_chat(
    request: AssistantRequest,
):

    provider = os.getenv(
        "AI_PROVIDER",
        "openai",
    ).strip().lower()

    context = _assistant_context(
        request.context
    )

    if provider == "gemini":

        answer = await _call_gemini(
            request.message,
            request.language,
            context,
        )

    elif provider == "openai":

        answer = await _call_openai(
            request.message,
            request.language,
            context,
        )

    else:

        raise HTTPException(
            status_code=500,
            detail=(
                "AI_PROVIDER must be "
                "'openai' or 'gemini'"
            ),
        )

    return {
        "answer": answer,
        "provider": provider,
    }


@app.get("/api/binance")
def binance_analysis(
    symbol: str = Query(
        "BTCUSDT",
        pattern=r"^[A-Za-z0-9]{5,15}$",
    ),

    timeframe: str = Query(
        "1d",
        pattern=(
            r"^(1m|5m|15m|30m|"
            r"1h|4h|1d|1w)$"
        ),
    ),
):

    try:

        vr = fetch_binance(
            symbol,
            timeframe,
            1000,
        )

        return _payload(
            vr.data,
            symbol.upper(),
            timeframe,
            "Binance Public Market Data",
        )

    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail=(
                "Binance data error: "
                f"{exc}"
            ),
        ) from exc


@app.post("/api/csv")
async def csv_analysis(
    file: UploadFile = File(...),
):

    if not (
        file.filename or ""
    ).lower().endswith(
        ".csv"
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Please upload a CSV file"
            ),
        )

    raw = await file.read()

    if len(raw) > (
        10 * 1024 * 1024
    ):

        raise HTTPException(
            status_code=413,
            detail=(
                "CSV is too large "
                "(10 MB max)"
            ),
        )

    tmp = None

    try:

        with NamedTemporaryFile(
            suffix=".csv",
            delete=False,
        ) as f:

            f.write(raw)

            tmp = Path(
                f.name
            )

        vr = load_csv(
            tmp,
            source="web_csv",
        )

        if "symbol" in vr.data:

            symbol = str(
                vr.data[
                    "symbol"
                ].iloc[-1]
            )

        else:

            symbol = "CSV"

        if "timeframe" in vr.data:

            timeframe = str(
                vr.data[
                    "timeframe"
                ].iloc[-1]
            )

        else:

            timeframe = "unknown"

        return _payload(
            vr.data,
            symbol,
            timeframe,
            "Uploaded CSV",
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    finally:

        if (
            tmp
            and tmp.exists()
        ):

            tmp.unlink(
                missing_ok=True
            )


@app.get("/api/backtest")
def backtest(
    symbol: str = "BTCUSDT",
    timeframe: str = "1d",
):

    try:

        df = fetch_binance(
            symbol,
            timeframe,
            1000,
        ).data

        enriched = add_indicators(
            df
        )

        signals = pd.Series(
            0,
            index=enriched.index,
            dtype=int,
        )

        valid = (
            enriched[
                "sma_20"
            ].notna()
            &
            enriched[
                "sma_50"
            ].notna()
        )

        signals.loc[
            valid
            &
            (
                enriched["sma_20"]
                >
                enriched["sma_50"]
            )
        ] = 1

        signals.loc[
            valid
            &
            (
                enriched["sma_20"]
                <
                enriched["sma_50"]
            )
        ] = -1

        r = simulate_signals(
            enriched,
            signals,
            hold_bars=5,
            fee_rate=0.001,
            slippage_rate=0.0005,
        )

        return {
            "trades":
                len(r.trades),

            "win_rate":
                r.win_rate,

            "profit_factor":
                _clean(
                    r.profit_factor
                ),

            "total_return":
                r.total_return,

            "max_drawdown":
                r.max_drawdown,

            "sortino":
                _clean(
                    r.sortino
                ),

            "expectancy":
                r.expectancy,

            "buy_hold":
                buy_and_hold(
                    enriched,
                    fee_rate=0.001,
                ),
        }

    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail=(
                "Backtest error: "
                f"{exc}"
            ),
        ) from exc
    # ============================================================
    # TELEGRAM WEBHOOK
    # ============================================================

from aiogram.types import Update

from bot.app import (
    close_runtime,
    create_runtime,
    start_background_tasks,
)

TELEGRAM_WEBHOOK_PATH = "/telegram/webhook"

@app.on_event("startup")
async def telegram_startup():

    token = os.getenv(
        "TELEGRAM_BOT_TOKEN"
    )

    if not token:
        print(
            "Telegram webhook disabled: "
            "TELEGRAM_BOT_TOKEN is not configured."
        )
        return

    bot, _, _ = create_runtime()

    external_url = os.getenv(
        "TELEGRAM_WEBHOOK_URL"
    )

    if not external_url:

        render_url = os.getenv(
            "RENDER_EXTERNAL_URL"
        )

        if render_url:
            external_url = (
                    render_url.rstrip("/")
                    + TELEGRAM_WEBHOOK_PATH
            )

    if not external_url:
        print(
            "Telegram webhook disabled: "
            "TELEGRAM_WEBHOOK_URL or "
            "RENDER_EXTERNAL_URL is required."
        )
        return

    secret = os.getenv(
        "TELEGRAM_WEBHOOK_SECRET"
    )

    kwargs = {
        "url": external_url,
        "drop_pending_updates": False,
        "allowed_updates": [
            "message",
            "callback_query",
        ],
    }

    if secret:
        kwargs[
            "secret_token"
        ] = secret

    await bot.set_webhook(
        **kwargs
    )

    await start_background_tasks()

    print(
        "Telegram webhook configured:",
        external_url,
    )

@app.on_event("shutdown")
async def telegram_shutdown():

    token = os.getenv(
        "TELEGRAM_BOT_TOKEN"
    )

    if token:
        await close_runtime()

@app.post(
    TELEGRAM_WEBHOOK_PATH
)
async def telegram_webhook(
        request: Request,
):

    bot, dispatcher, _ = (
        create_runtime()
    )

    expected_secret = os.getenv(
        "TELEGRAM_WEBHOOK_SECRET"
    )

    if expected_secret:

        received_secret = (
            request.headers.get(
                "X-Telegram-Bot-Api-Secret-Token"
            )
        )

        if (
                received_secret
                != expected_secret
        ):
            raise HTTPException(
                status_code=403,
                detail=(
                    "Invalid Telegram "
                    "webhook secret"
                ),
            )

    payload = await request.json()

    update = (
        Update.model_validate(
            payload,
            context={
                "bot": bot
            },
        )
    )

    await dispatcher.feed_update(
        bot,
        update,
    )

    return {
        "ok": True
    }
