/* ============================================================
   SIGNALWAVE WEB DASHBOARD
   Live Binance + Analysis + Charts + Backtest + AI + RU/KK/EN
   ============================================================ */

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

const COLORS = {
    green: "#00e676",
    red: "#ff2d36",
    yellow: "#ffbd21",
    purple: "#9b5cff",
    blue: "#2688ff",
};

const histories = {
    BTCUSDT: [],
    ETHUSDT: [],
    SOLUSDT: [],
    BNBUSDT: [],
};

let current = {
    symbol: "BTCUSDT",
    timeframe: "1d",
};

let payload = null;
let klineSocket = null;
let tickerSocket = null;

let assistantStatus = {
    provider: "unknown",
    configured: false,
    model: "",
};

let currentLang =
    localStorage.getItem("signalwaveLang") || "en";


/* ============================================================
   UTILITIES
   ============================================================ */

function safe(selector) {
    return document.querySelector(selector);
}

function num(value, digits = 2) {
    const n = Number(value);

    if (!Number.isFinite(n)) {
        return "—";
    }

    return n.toLocaleString(undefined, {
        maximumFractionDigits: digits,
    });
}

function pct(value) {
    const n = Number(value);

    if (!Number.isFinite(n)) {
        return "—";
    }

    return `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`;
}

function setText(selector, value) {
    const el = safe(selector);

    if (el) {
        el.textContent = value;
    }
}

function clearError() {
    const el = safe("#error");

    if (el) {
        el.classList.add("hidden");
    }
}

function showError(message) {
    const el = safe("#error");

    if (!el) {
        console.error(message);
        return;
    }

    el.textContent = message;
    el.classList.remove("hidden");
}

function scrollToTarget(selector) {
    const target = safe(selector);

    if (!target) {
        return;
    }

    target.scrollIntoView({
        behavior: "smooth",
        block: "start",
    });
}

function line(x, y, color, name, width = 1.1) {
    return {
        x,
        y,
        type: "scatter",
        mode: "lines",
        name,
        line: {
            color,
            width,
        },
        hovertemplate:
            `${name}: %{y:.2f}<extra></extra>`,
    };
}


/* ============================================================
   PLOTLY BASE
   ============================================================ */

const layoutBase = {
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",

    font: {
        family: "Inter, Arial",
        color: "#71817e",
        size: 9,
    },

    showlegend: false,

    margin: {
        l: 36,
        r: 52,
        t: 6,
        b: 25,
    },

    xaxis: {
        gridcolor: "rgba(130,160,153,.06)",
        zeroline: false,
        linecolor: "rgba(255,255,255,.03)",
    },

    yaxis: {
        gridcolor: "rgba(130,160,153,.06)",
        zeroline: false,
        linecolor: "rgba(255,255,255,.03)",
        side: "right",
    },

    hoverlabel: {
        bgcolor: "#091416",
        bordercolor: "rgba(255,255,255,.12)",
        font: {
            color: "#fff",
        },
    },
};


/* ============================================================
   CLOCK
   ============================================================ */

function updateClock() {
    const now = new Date();

    setText(
        "#clock",
        now.toLocaleTimeString([], {
            hour12: false,
        })
    );

    setText(
        "#date",
        now.toLocaleDateString()
    );
}


/* ============================================================
   LIVE BINANCE TICKER
   ============================================================ */

function startTicker() {
    if (tickerSocket) {
        try {
            tickerSocket.close();
        } catch (_) {}
    }

    const streams = [
        "btcusdt@ticker",
        "ethusdt@ticker",
        "solusdt@ticker",
        "bnbusdt@ticker",
    ].join("/");

    tickerSocket = new WebSocket(
        `wss://stream.binance.com:9443/stream?streams=${streams}`
    );

    tickerSocket.onmessage = (event) => {
        try {
            const envelope =
                JSON.parse(event.data);

            const d = envelope.data;

            if (!d || !d.s) {
                return;
            }

            const symbol = d.s;
            const price = Number(d.c);
            const change = Number(d.P);

            if (!histories[symbol]) {
                return;
            }

            histories[symbol].push(price);

            if (
                histories[symbol].length > 90
            ) {
                histories[symbol].shift();
            }

            updateTickerCard(
                symbol,
                price,
                change
            );

            drawSpark(symbol);

            if (
                symbol === current.symbol
            ) {
                updateCurrentMarket({
                    symbol,
                    price,
                    change,
                    high: Number(d.h),
                    low: Number(d.l),
                    volume: Number(d.q),
                });
            }

        } catch (error) {
            console.error(
                "Ticker message error:",
                error
            );
        }
    };

    tickerSocket.onerror = () => {
        console.warn(
            "Binance ticker websocket error"
        );
    };

    tickerSocket.onclose = () => {
        console.warn(
            "Binance ticker disconnected"
        );
    };
}


function findTickerCard(symbol) {
    return (
        document.querySelector(
            `[data-symbol="${symbol}"]`
        )
    );
}


function updateTickerCard(
    symbol,
    price,
    change
) {
    const card =
        findTickerCard(symbol);

    if (card) {
        const priceEl =
            card.querySelector("b") ||
            card.querySelector("strong");

        const changeEl =
            card.querySelector("em") ||
            card.querySelector("small");

        if (priceEl) {
            priceEl.textContent =
                "$" + num(price);
        }

        if (changeEl) {
            changeEl.textContent =
                pct(change);

            changeEl.classList.remove(
                "pos",
                "neg",
                "positive",
                "negative"
            );

            changeEl.classList.add(
                change >= 0
                    ? "pos"
                    : "neg"
            );
        }
    }

    const miniIds = {
        BTCUSDT: "#miniBtcPrice",
        ETHUSDT: "#miniEthPrice",
        SOLUSDT: "#miniSolPrice",
        BNBUSDT: "#miniBnbPrice",
    };

    if (miniIds[symbol]) {
        setText(
            miniIds[symbol],
            "$" + num(price)
        );
    }
}


function updateCurrentMarket(data) {
    setText(
        "#marketSymbol",
        data.symbol
    );

    setText(
        "#marketPrice",
        "$" + num(data.price)
    );

    setText(
        "#keyPrice",
        "$" + num(data.price)
    );

    setText(
        "#high24",
        "$" + num(data.high)
    );

    setText(
        "#low24",
        "$" + num(data.low)
    );

    setText(
        "#volume24",
        num(data.volume, 0)
    );

    const change =
        safe("#marketChange");

    if (change) {
        change.textContent =
            pct(data.change);

        change.className =
            "market-change " +
            (
                data.change >= 0
                    ? "pos"
                    : "neg"
            );
    }
}


/* ============================================================
   SPARKLINES
   ============================================================ */

function drawSpark(symbol) {
    if (
        typeof Plotly === "undefined"
    ) {
        return;
    }

    const ids = {
        BTCUSDT: [
            "spark-btc",
            "mini-btc",
        ],

        ETHUSDT: [
            "spark-eth",
            "mini-eth",
        ],

        SOLUSDT: [
            "spark-sol",
            "mini-sol",
        ],

        BNBUSDT: [
            "spark-bnb",
            "mini-bnb",
        ],
    };

    const values =
        histories[symbol];

    if (
        !values ||
        values.length < 2
    ) {
        return;
    }

    const positive =
        values.at(-1) >= values[0];

    const color =
        positive
            ? COLORS.green
            : COLORS.red;

    for (
        const id
        of ids[symbol] || []
    ) {
        const target =
            document.getElementById(id);

        if (!target) {
            continue;
        }

        Plotly.react(
            target,
            [
                {
                    y: values,
                    type: "scatter",
                    mode: "lines",

                    line: {
                        color,
                        width: 1.2,
                    },

                    hoverinfo: "skip",
                },
            ],

            {
                paper_bgcolor:
                    "rgba(0,0,0,0)",

                plot_bgcolor:
                    "rgba(0,0,0,0)",

                margin: {
                    l: 0,
                    r: 0,
                    t: 0,
                    b: 0,
                },

                xaxis: {
                    visible: false,
                },

                yaxis: {
                    visible: false,
                },

                showlegend: false,
            },

            {
                displayModeBar: false,
                responsive: true,
            }
        );
    }
}


/* ============================================================
   BINANCE ANALYSIS
   ============================================================ */

async function analyze() {
    clearError();

    const symbolSelect =
        safe("#symbol");

    const timeframeSelect =
        safe("#timeframe");

    if (symbolSelect) {
        current.symbol =
            symbolSelect.value;
    }

    if (timeframeSelect) {
        current.timeframe =
            timeframeSelect.value;
    }

    try {
        const url =
            "/api/binance" +
            `?symbol=${encodeURIComponent(
                current.symbol
            )}` +
            `&timeframe=${encodeURIComponent(
                current.timeframe
            )}`;

        const response =
            await fetch(url);

        const data =
            await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail ||
                "Analysis failed"
            );
        }

        payload = data;

        render(data);
        connectKline();

    } catch (error) {
        console.error(error);
        showError(error.message);
    }
}


/* ============================================================
   CSV ANALYSIS
   ============================================================ */

async function analyzeCsv(file) {
    if (!file) {
        return;
    }

    clearError();

    try {
        const form =
            new FormData();

        form.append(
            "file",
            file
        );

        const response =
            await fetch(
                "/api/csv",
                {
                    method: "POST",
                    body: form,
                }
            );

        const data =
            await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail ||
                "CSV analysis failed"
            );
        }

        payload = data;

        render(data);

    } catch (error) {
        console.error(error);
        showError(error.message);
    }
}


/* ============================================================
   MAIN RENDER
   ============================================================ */

function render(data) {
    if (!data) {
        return;
    }

    const series =
        data.series || {};

    const time =
        data.time || [];

    current.symbol =
        data.market?.symbol ||
        current.symbol;

    current.timeframe =
        data.market?.timeframe ||
        current.timeframe;

    setText(
        "#chartTitle",
        `${current.symbol} · ${String(
            current.timeframe
        ).toUpperCase()}`
    );

    setText(
        "#marketSymbol",
        current.symbol
    );

    setText(
        "#marketPrice",
        "$" + num(
            data.market?.price
        )
    );

    setText(
        "#keyPrice",
        "$" + num(
            data.market?.price
        )
    );

    setText(
        "#lastUpdate",
        new Date().toLocaleTimeString(
            [],
            {
                hour12: false,
            }
        )
    );

    setText(
        "#openValue",
        num(series.open?.at(-1))
    );

    setText(
        "#highValue",
        num(series.high?.at(-1))
    );

    setText(
        "#lowValue",
        num(series.low?.at(-1))
    );

    setText(
        "#closeValue",
        num(series.close?.at(-1))
    );

    renderPriceChart(
        time,
        series,
        data
    );

    renderRsi(
        time,
        series
    );

    renderMacd(
        time,
        series
    );

    renderZones(
        data.zones || []
    );

    renderFibs(
        data.fibs || []
    );

    renderCards(
        data.cards || []
    );

    renderElliott(
        data.elliott
    );

    renderKeyLevels(series);
}


/* ============================================================
   PRICE CHART
   ============================================================ */

function renderPriceChart(
    time,
    series,
    data
) {
    const target =
        safe("#priceChart");

    if (
        !target ||
        typeof Plotly === "undefined"
    ) {
        return;
    }

    const traces = [];

    traces.push({
        x: time,

        open: series.open,
        high: series.high,
        low: series.low,
        close: series.close,

        type: "candlestick",
        name: "Price",
        yaxis: "y",

        increasing: {
            line: {
                color: COLORS.green,
                width: 1,
            },

            fillcolor:
                "rgba(0,230,118,.55)",
        },

        decreasing: {
            line: {
                color: COLORS.red,
                width: 1,
            },

            fillcolor:
                "rgba(255,45,54,.55)",
        },
    });

    if (series.sma_20) {
        traces.push({
            ...line(
                time,
                series.sma_20,
                COLORS.green,
                "SMA 20",
                1
            ),
            yaxis: "y",
        });
    }

    if (series.sma_50) {
        traces.push({
            ...line(
                time,
                series.sma_50,
                COLORS.yellow,
                "SMA 50",
                1
            ),
            yaxis: "y",
        });
    }

    if (series.sma_200) {
        traces.push({
            ...line(
                time,
                series.sma_200,
                COLORS.red,
                "SMA 200",
                1.1
            ),
            yaxis: "y",
        });
    }

    if (series.volume) {
        traces.push({
            x: time,
            y: series.volume,

            type: "bar",
            yaxis: "y2",

            marker: {
                color:
                    series.close.map(
                        (close, index) =>
                            close >=
                            series.open[index]
                                ? "rgba(0,230,118,.38)"
                                : "rgba(255,45,54,.38)"
                    ),
            },

            hovertemplate:
                "Volume %{y}<extra></extra>",
        });
    }

    const shapes = [];

    for (
        const zone
        of (data.zones || []).slice(
            0,
            6
        )
    ) {
        const resistance =
            zone.type ===
            "resistance";

        shapes.push({
            type: "rect",
            xref: "x",
            yref: "y",

            x0: time[0],
            x1: time.at(-1),

            y0: zone.low,
            y1: zone.high,

            fillcolor:
                resistance
                    ? "rgba(0,230,118,.045)"
                    : "rgba(255,45,54,.05)",

            line: {
                color:
                    resistance
                        ? "rgba(0,230,118,.35)"
                        : "rgba(255,45,54,.35)",

                width: 1,
            },
        });
    }

    for (
        const fib
        of (data.fibs || [])
    ) {
        if (
            fib.kind !==
            "retracement"
        ) {
            continue;
        }

        shapes.push({
            type: "line",
            xref: "x",
            yref: "y",

            x0: time[0],
            x1: time.at(-1),

            y0: fib.price,
            y1: fib.price,

            line: {
                color:
                    fib.confluence
                        ? "rgba(255,189,33,.45)"
                        : "rgba(255,189,33,.14)",

                width:
                    fib.confluence
                        ? 1.2
                        : 0.7,

                dash: "dot",
            },
        });
    }

    Plotly.react(
        target,
        traces,

        {
            ...layoutBase,

            shapes,

            xaxis: {
                ...layoutBase.xaxis,

                rangeslider: {
                    visible: false,
                },
            },

            yaxis: {
                ...layoutBase.yaxis,
                domain: [0.24, 1],
                tickprefix: "$",
            },

            yaxis2: {
                domain: [0, 0.18],
                side: "right",

                gridcolor:
                    "rgba(130,160,153,.04)",

                zeroline: false,
            },
        },

        {
            responsive: true,
            displayModeBar: false,
            scrollZoom: true,
        }
    );
}


/* ============================================================
   RSI
   ============================================================ */

function renderRsi(time, series) {
    if (!series.rsi_14) {
        return;
    }

    const last =
        [...series.rsi_14]
            .reverse()
            .find(
                (value) =>
                    value != null
            );

    setText(
        "#rsiValue",
        last == null
            ? "—"
            : Number(last).toFixed(2)
    );

    setText(
        "#keyRsi",
        last == null
            ? "—"
            : Number(last).toFixed(2)
    );

    const target =
        safe("#rsiChart");

    if (
        !target ||
        typeof Plotly === "undefined"
    ) {
        return;
    }

    Plotly.react(
        target,

        [
            line(
                time,
                series.rsi_14,
                COLORS.green,
                "RSI",
                1.2
            ),
        ],

        {
            ...layoutBase,

            margin: {
                l: 25,
                r: 38,
                t: 4,
                b: 24,
            },

            yaxis: {
                ...layoutBase.yaxis,
                range: [0, 100],
            },

            shapes: [
                {
                    type: "line",

                    x0: time[0],
                    x1: time.at(-1),

                    y0: 70,
                    y1: 70,

                    line: {
                        color:
                            "rgba(255,45,54,.4)",
                        dash: "dot",
                    },
                },

                {
                    type: "line",

                    x0: time[0],
                    x1: time.at(-1),

                    y0: 30,
                    y1: 30,

                    line: {
                        color:
                            "rgba(0,230,118,.4)",
                        dash: "dot",
                    },
                },
            ],
        },

        {
            responsive: true,
            displayModeBar: false,
        }
    );
}


/* ============================================================
   MACD
   ============================================================ */

function renderMacd(time, series) {
    if (
        !series.macd ||
        !series.macd_signal
    ) {
        return;
    }

    const histogram =
        series.macd.map(
            (value, index) => {
                const signal =
                    series.macd_signal[index];

                if (
                    value == null ||
                    signal == null
                ) {
                    return null;
                }

                return value - signal;
            }
        );

    const target =
        safe("#macdChart");

    if (
        target &&
        typeof Plotly !== "undefined"
    ) {
        Plotly.react(
            target,

            [
                {
                    x: time,
                    y: histogram,
                    type: "bar",

                    marker: {
                        color:
                            histogram.map(
                                (value) =>
                                    value >= 0
                                        ? "rgba(0,230,118,.48)"
                                        : "rgba(255,45,54,.48)"
                            ),
                    },
                },

                line(
                    time,
                    series.macd,
                    COLORS.green,
                    "MACD",
                    1
                ),

                line(
                    time,
                    series.macd_signal,
                    COLORS.red,
                    "Signal",
                    1
                ),
            ],

            {
                ...layoutBase,

                margin: {
                    l: 25,
                    r: 38,
                    t: 4,
                    b: 24,
                },
            },

            {
                responsive: true,
                displayModeBar: false,
            }
        );
    }

    const latest =
        [...series.macd]
            .reverse()
            .find(
                (value) =>
                    value != null
            );

    const el =
        safe("#keyMacd");

    if (el) {
        const bullish =
            Number(latest) >= 0;

        el.textContent =
            bullish
                ? tr("bullish")
                : tr("bearish");

        el.className =
            bullish
                ? "pos"
                : "neg";
    }
}


/* ============================================================
   STRUCTURE
   ============================================================ */

function renderZones(zones) {
    const target =
        safe("#zones");

    if (!target) {
        return;
    }

    target.innerHTML =
        zones
            .slice(0, 6)
            .map((zone) => {
                const resistance =
                    zone.type ===
                    "resistance";

                return `
                    <div class="table-row">
                        <span class="${
                            resistance
                                ? "resistance"
                                : "support"
                        }">
                            ${
                                resistance
                                    ? tr("resistance")
                                    : tr("support")
                            }
                        </span>

                        <b>
                            ${num(zone.low)}
                            –
                            ${num(zone.high)}
                        </b>

                        <span>
                            ${Math.round(
                                (zone.strength || 0) *
                                100
                            )}%
                        </span>
                    </div>
                `;
            })
            .join("") ||
        `<span>${tr("noZones")}</span>`;
}


function renderFibs(fibs) {
    const target =
        safe("#fibs");

    if (!target) {
        return;
    }

    target.innerHTML =
        fibs
            .slice(0, 8)
            .map((fib) => `
                <div class="table-row fib-row">

                    <span>
                        ${fib.ratio}
                        ${
                            fib.confluence
                                ? " · confluence"
                                : ""
                        }
                    </span>

                    <b>
                        ${num(fib.price)}
                    </b>

                </div>
            `)
            .join("") ||
        `<span>${tr("fibWaiting")}</span>`;
}


/* ============================================================
   SCENARIOS
   ============================================================ */

function renderCards(cards) {
    const target =
        safe("#cards");

    if (!target) {
        return;
    }

    target.innerHTML =
        cards
            .slice(0, 3)
            .map((card) => {

                let title;

                if (
                    card.direction ===
                    "up"
                ) {
                    title =
                        tr(
                            "bullishScenario"
                        );
                }

                else if (
                    card.direction ===
                    "down"
                ) {
                    title =
                        tr(
                            "bearishScenario"
                        );
                }

                else {
                    title =
                        tr(
                            "unclearScenario"
                        );
                }

                const entry =
                    card.entry_low
                        ? (
                            num(
                                card.entry_low
                            )
                            +
                            " – "
                            +
                            num(
                                card.entry_high
                            )
                        )
                        : tr(
                            "waitTrigger"
                        );

                return `
                    <div class="card ${card.direction}">

                        <h4>
                            ${title}
                        </h4>

                        <div class="confidence">
                            ${card.confidence}%
                        </div>

                        <div class="row">
                            <span>
                                ${tr("entry")}
                            </span>

                            <b>
                                ${entry}
                            </b>
                        </div>

                        <div class="row">
                            <span>
                                ${tr("invalidation")}
                            </span>

                            <b>
                                ${num(
                                    card.invalidation
                                )}
                            </b>
                        </div>

                        <div class="row">
                            <span>
                                ${tr("targets")}
                            </span>

                            <b>
                                ${
                                    (
                                        card.targets ||
                                        []
                                    )
                                    .map(num)
                                    .join(" / ")
                                    ||
                                    "—"
                                }
                            </b>
                        </div>

                        <div class="row">
                            <span>
                                ${tr("riskReward")}
                            </span>

                            <b>
                                ${
                                    card.risk_reward
                                        ? Number(
                                            card.risk_reward
                                        ).toFixed(2)
                                        : "—"
                                }
                            </b>
                        </div>

                    </div>
                `;
            })
            .join("");
}


/* ============================================================
   ELLIOTT
   ============================================================ */

function renderElliott(elliott) {
    const target =
        safe("#elliott");

    if (
        !target ||
        !elliott
    ) {
        return;
    }

    target.innerHTML = `
        <b>
            Confidence:
            ${elliott.confidence}%
        </b>

        <p>
            ${
                elliott.valid
                    ? tr("elliottValid")
                    : tr("elliottInvalid")
            }

            <br><br>

            ${
                (
                    elliott.notes ||
                    []
                ).join("<br>")
            }

            <br><br>

            ${
                elliott.alternate
                    ? tr("elliottAlt")
                    : ""
            }
        </p>
    `;
}


/* ============================================================
   KEY LEVELS
   ============================================================ */

function renderKeyLevels(series) {
    const close =
        series.close?.at(-1);

    const sma200 =
        series.sma_200?.at(-1);

    const regimeEl =
        safe("#keyRegime");

    if (
        regimeEl &&
        close != null &&
        sma200 != null
    ) {
        const bullish =
            Number(close) >=
            Number(sma200);

        regimeEl.textContent =
            bullish
                ? tr("bullish")
                : tr("bearish");

        regimeEl.className =
            bullish
                ? "pos"
                : "neg";
    }

    if (series.atr_14) {
        const atr =
            [...series.atr_14]
                .reverse()
                .find(
                    (value) =>
                        value != null
                );

        setText(
            "#keyAtr",
            num(atr)
        );
    }

    if (series.volume) {
        setText(
            "#keyVolume",
            num(
                series.volume.at(-1),
                0
            )
        );
    }
}


/* ============================================================
   LIVE KLINE
   ============================================================ */

function connectKline() {
    if (klineSocket) {
        try {
            klineSocket.close();
        } catch (_) {}
    }

    const stream =
        `${current.symbol.toLowerCase()}` +
        `@kline_${current.timeframe}`;

    klineSocket =
        new WebSocket(
            `wss://stream.binance.com:9443/ws/${stream}`
        );

    klineSocket.onmessage =
        (event) => {
            try {
                const parsed =
                    JSON.parse(
                        event.data
                    );

                const k =
                    parsed.k;

                if (!k) {
                    return;
                }

                setText(
                    "#openValue",
                    num(k.o)
                );

                setText(
                    "#highValue",
                    num(k.h)
                );

                setText(
                    "#lowValue",
                    num(k.l)
                );

                setText(
                    "#closeValue",
                    num(k.c)
                );

                setText(
                    "#lastUpdate",
                    new Date()
                        .toLocaleTimeString(
                            [],
                            {
                                hour12:
                                    false,
                            }
                        )
                );

                if (!payload) {
                    return;
                }

                const time =
                    new Date(
                        k.t
                    ).toISOString();

                const series =
                    payload.series;

                const times =
                    payload.time;

                if (
                    times.at(-1) === time
                ) {
                    const i =
                        series.close.length -
                        1;

                    series.open[i] =
                        Number(k.o);

                    series.high[i] =
                        Number(k.h);

                    series.low[i] =
                        Number(k.l);

                    series.close[i] =
                        Number(k.c);

                    if (
                        series.volume
                    ) {
                        series.volume[i] =
                            Number(k.v);
                    }
                }

                if (
                    typeof Plotly !==
                    "undefined"
                ) {
                    Plotly.restyle(
                        "priceChart",

                        {
                            open: [
                                series.open
                            ],

                            high: [
                                series.high
                            ],

                            low: [
                                series.low
                            ],

                            close: [
                                series.close
                            ],

                            x: [
                                times
                            ],
                        },

                        [0]
                    );
                }

            } catch (error) {
                console.error(
                    "Kline update error:",
                    error
                );
            }
        };
}


/* ============================================================
   BACKTEST
   ============================================================ */

async function backtest() {
    clearError();

    try {
        const response =
            await fetch(
                `/api/backtest` +
                `?symbol=${encodeURIComponent(
                    current.symbol
                )}` +
                `&timeframe=${encodeURIComponent(
                    current.timeframe
                )}`
            );

        const data =
            await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail ||
                "Backtest failed"
            );
        }

        renderBacktestMetrics(data);

    } catch (error) {
        console.error(error);
        showError(error.message);
    }
}


function renderBacktestMetrics(data) {
    const target =
        safe("#metrics");

    if (!target) {
        return;
    }

    const values = [
        [
            tr("trades"),
            data.trades,
        ],

        [
            tr("winRate"),
            data.win_rate == null
                ? "—"
                : (
                    data.win_rate *
                    100
                ).toFixed(1) +
                "%",
        ],

        [
            tr("profitFactor"),
            data.profit_factor == null
                ? "—"
                : Number(
                    data.profit_factor
                ).toFixed(2),
        ],

        [
            tr("totalReturn"),
            data.total_return == null
                ? "—"
                : (
                    data.total_return *
                    100
                ).toFixed(2) +
                "%",
        ],

        [
            tr("maxDrawdown"),
            data.max_drawdown == null
                ? "—"
                : (
                    data.max_drawdown *
                    100
                ).toFixed(2) +
                "%",
        ],

        [
            "SORTINO",
            data.sortino == null
                ? "—"
                : Number(
                    data.sortino
                ).toFixed(2),
        ],
    ];

    target.innerHTML =
        values
            .map(
                ([label, value]) => `
                    <div>
                        <small>
                            ${label}
                        </small>

                        <b>
                            ${value}
                        </b>
                    </div>
                `
            )
            .join("");

    target.dataset.values =
        JSON.stringify(data);
}


/* ============================================================
   LANGUAGES
   ============================================================ */

const I18N = {
    en: {
        runAnalysis: "Run Analysis",
        backtest: "Backtest",
        uploadCsv: "Upload CSV",

        support: "Support",
        resistance: "Resistance",
        noZones: "No confirmed zones",

        fibWaiting:
            "Waiting for confirmed impulse",

        bullishScenario:
            "BULLISH SCENARIO",

        bearishScenario:
            "BEARISH SCENARIO",

        unclearScenario:
            "UNCLEAR SCENARIO",

        entry: "ENTRY",
        invalidation: "INVALIDATION",
        targets: "TARGETS",
        riskReward: "RISK / REWARD",

        waitTrigger:
            "Wait for trigger",

        bullish: "Bullish",
        bearish: "Bearish",

        elliottValid:
            "Primary count satisfies the implemented cardinal rules.",

        elliottInvalid:
            "No complete valid impulse is confirmed.",

        elliottAlt:
            "Alternate count should also be considered.",

        aiConfig:
            "AI is not configured. Add an API key to .env and restart the server.",

        aiNeedAnalysis:
            "Run market analysis first so I can explain the computed SignalWave values.",

        aiError:
            "AI assistant error",

        quickExplain:
            "Explain the current chart and strongest signals in beginner-friendly language.",

        quickScenario:
            "Explain why the highest-confidence SignalWave scenario has its current confidence, including evidence for and against it.",

        quickRisk:
            "Explain the main risks, invalidation level and risk/reward without giving a guaranteed trading instruction.",

        alertInfo:
            "Price alerts are currently handled by the SignalWave Telegram bot.",
    },

    ru: {
        runAnalysis:
            "Запустить анализ",

        backtest:
            "Бэктест",

        uploadCsv:
            "Загрузить CSV",

        support:
            "Поддержка",

        resistance:
            "Сопротивление",

        noZones:
            "Подтверждённых зон нет",

        fibWaiting:
            "Ожидается подтверждённый импульс",

        bullishScenario:
            "СЦЕНАРИЙ РОСТА",

        bearishScenario:
            "СЦЕНАРИЙ ПАДЕНИЯ",

        unclearScenario:
            "НЕЯСНЫЙ СЦЕНАРИЙ",

        entry:
            "ВХОД",

        invalidation:
            "ИНВАЛИДАЦИЯ",

        targets:
            "ЦЕЛИ",

        riskReward:
            "РИСК / ДОХОДНОСТЬ",

        waitTrigger:
            "Ждать подтверждения",

        bullish:
            "Бычий",

        bearish:
            "Медвежий",

        elliottValid:
            "Основной волновой счёт соблюдает реализованные кардинальные правила.",

        elliottInvalid:
            "Полный валидный импульс пока не подтверждён.",

        elliottAlt:
            "Также следует учитывать альтернативный волновой счёт.",

        aiConfig:
            "AI пока не настроен. Добавь API-ключ в .env и перезапусти сервер.",

        aiNeedAnalysis:
            "Сначала запусти анализ рынка, чтобы я объяснял вычисленные значения SignalWave.",

        aiError:
            "Ошибка AI-помощника",

        quickExplain:
            "Объясни текущий график и самые сильные сигналы простым языком для новичка.",

        quickScenario:
            "Объясни, почему сценарий SignalWave с самой высокой уверенностью получил именно такую оценку, включая аргументы за и против.",

        quickRisk:
            "Объясни основные риски, уровень инвалидации и risk/reward текущих сценариев без гарантированной торговой рекомендации.",

        alertInfo:
            "Price Alerts сейчас работают через Telegram-бот SignalWave.",
    },

    kk: {
        runAnalysis:
            "Талдауды іске қосу",

        backtest:
            "Бэктест",

        uploadCsv:
            "CSV жүктеу",

        support:
            "Қолдау",

        resistance:
            "Қарсылық",

        noZones:
            "Расталған аймақтар жоқ",

        fibWaiting:
            "Расталған импульс күтілуде",

        bullishScenario:
            "ӨСУ СЦЕНАРИЙІ",

        bearishScenario:
            "ТӨМЕНДЕУ СЦЕНАРИЙІ",

        unclearScenario:
            "БЕЛГІСІЗ СЦЕНАРИЙ",

        entry:
            "КІРУ",

        invalidation:
            "ИНВАЛИДАЦИЯ",

        targets:
            "МАҚСАТТАР",

        riskReward:
            "ТӘУЕКЕЛ / СЫЙАҚЫ",

        waitTrigger:
            "Растауды күту",

        bullish:
            "Өсу",

        bearish:
            "Төмендеу",

        elliottValid:
            "Негізгі толқын есебі енгізілген негізгі ережелерге сәйкес келеді.",

        elliottInvalid:
            "Толық жарамды импульс әлі расталмады.",

        elliottAlt:
            "Балама толқын есебін де ескеру керек.",

        aiConfig:
            "AI әлі бапталмаған. API кілтін .env файлына қосып, серверді қайта іске қосыңыз.",

        aiNeedAnalysis:
            "SignalWave есептеген мәндерді түсіндіру үшін алдымен нарық талдауын іске қосыңыз.",

        aiError:
            "AI көмекшісінің қатесі",

        quickExplain:
            "Ағымдағы график пен ең күшті сигналдарды бастаушыға түсінікті тілмен түсіндір.",

        quickScenario:
            "Ең жоғары сенімділікке ие SignalWave сценарийінің бағасын және қолдайтын/қарсы дәлелдерді түсіндір.",

        quickRisk:
            "Кепілді сауда нұсқауын бермей, негізгі тәуекелдерді, инвалидация деңгейін және risk/reward көрсеткішін түсіндір.",

        alertInfo:
            "Price Alerts қазір SignalWave Telegram ботында жұмыс істейді.",
    },
};


function tr(key) {
    return (
        I18N[currentLang]?.[key] ||
        I18N.en[key] ||
        key
    );
}


function applyLanguage(language) {
    currentLang =
        I18N[language]
            ? language
            : "en";

    localStorage.setItem(
        "signalwaveLang",
        currentLang
    );

    document.documentElement.lang =
        currentLang;

    $$("[data-i18n]")
        .forEach((element) => {
            const key =
                element.dataset.i18n;

            if (I18N[currentLang]?.[key]) {
                element.textContent =
                    tr(key);
            }
        });

    $$("[data-i18n-placeholder]")
        .forEach((element) => {
            const key =
                element.dataset
                    .i18nPlaceholder;

            element.placeholder =
                tr(key);
        });

    $$(".language-switch button")
        .forEach((button) => {
            button.classList.toggle(
                "active",
                button.dataset.lang ===
                currentLang
            );
        });

    if (payload) {
        render(payload);
    }

    const metrics =
        safe("#metrics");

    if (
        metrics?.dataset?.values
    ) {
        try {
            renderBacktestMetrics(
                JSON.parse(
                    metrics.dataset.values
                )
            );
        } catch (_) {}
    }
}


/* ============================================================
   AI ASSISTANT
   ============================================================ */

function openAssistant() {
    const drawer =
        safe("#assistantDrawer");

    if (drawer) {
        drawer.classList.add("open");
    }

    const input =
        safe("#assistantInput");

    if (input) {
        setTimeout(
            () => input.focus(),
            100
        );
    }
}


function closeAssistant() {
    const drawer =
        safe("#assistantDrawer");

    if (drawer) {
        drawer.classList.remove(
            "open"
        );
    }
}


function addAssistantMessage(
    text,
    role = "assistant"
) {
    const box =
        safe("#assistantMessages");

    if (!box) {
        return null;
    }

    const node =
        document.createElement(
            "div"
        );

    node.className =
        `ai-message ${role}`;

    node.textContent =
        text;

    box.appendChild(node);

    box.scrollTop =
        box.scrollHeight;

    return node;
}


async function loadAssistantStatus() {
    try {
        const response =
            await fetch(
                "/api/assistant/status"
            );

        assistantStatus =
            await response.json();

        const el =
            safe(
                "#assistantProvider"
            );

        if (el) {
            el.textContent =
                `${assistantStatus.provider.toUpperCase()}` +
                ` · ${assistantStatus.model}` +
                (
                    assistantStatus.configured
                        ? " · READY"
                        : " · KEY REQUIRED"
                );

            el.classList.toggle(
                "ai-config-warning",
                !assistantStatus.configured
            );
        }

    } catch (error) {
        console.error(error);

        setText(
            "#assistantProvider",
            "Provider unavailable"
        );
    }
}


async function askAssistant(message) {
    const question =
        String(message || "")
            .trim();

    if (!question) {
        return;
    }

    openAssistant();

    addAssistantMessage(
        question,
        "user"
    );

    const input =
        safe("#assistantInput");

    if (input) {
        input.value = "";
    }

    if (
        !assistantStatus.configured
    ) {
        addAssistantMessage(
            tr("aiConfig"),
            "error"
        );

        return;
    }

    if (!payload) {
        addAssistantMessage(
            tr("aiNeedAnalysis"),
            "assistant"
        );

        return;
    }

    const typing =
        addAssistantMessage(
            "•••",
            "typing"
        );

    try {
        const response =
            await fetch(
                "/api/assistant",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json",
                    },

                    body:
                        JSON.stringify({
                            message:
                                question,

                            language:
                                currentLang,

                            context:
                                payload,
                        }),
                }
            );

        const data =
            await response.json();

        typing?.remove();

        if (!response.ok) {
            throw new Error(
                data.detail ||
                tr("aiError")
            );
        }

        addAssistantMessage(
            data.answer,
            "assistant"
        );

    } catch (error) {
        typing?.remove();

        addAssistantMessage(
            `${tr("aiError")}: ${error.message}`,
            "error"
        );
    }
}


/* ============================================================
   NAVIGATION
   ============================================================ */

function showNotice(message) {
    let notice =
        safe("#dashboardNotice");

    if (!notice) {
        notice =
            document.createElement(
                "div"
            );

        notice.id =
            "dashboardNotice";

        Object.assign(
            notice.style,
            {
                position: "fixed",
                right: "24px",
                bottom: "24px",
                zIndex: "99999",
                maxWidth: "360px",
                padding: "14px 18px",
                borderRadius: "8px",
                background: "#0b1416",
                border:
                    "1px solid rgba(255,45,54,.5)",
                color: "#ecf3f1",
                fontSize: "12px",
                lineHeight: "1.5",
                boxShadow:
                    "0 15px 50px rgba(0,0,0,.45)",
            }
        );

        document.body.appendChild(
            notice
        );
    }

    notice.textContent =
        message;

    notice.style.opacity =
        "1";

    clearTimeout(
        window.signalWaveNoticeTimer
    );

    window.signalWaveNoticeTimer =
        setTimeout(
            () => {
                notice.style.opacity =
                    "0";
            },
            3500
        );
}


function detectNavigationAction(button) {
    const explicit =
        button.dataset.nav;

    if (explicit) {
        return explicit.toLowerCase();
    }

    const text =
        button.textContent
            .trim()
            .toLowerCase();

    const title =
        String(
            button.getAttribute(
                "title"
            ) || ""
        ).toLowerCase();

    const aria =
        String(
            button.getAttribute(
                "aria-label"
            ) || ""
        ).toLowerCase();

    const haystack =
        `${text} ${title} ${aria}`;

    if (
        haystack.includes(
            "dashboard"
        )
    ) {
        return "dashboard";
    }

    if (
        haystack.includes(
            "market"
        )
    ) {
        return "markets";
    }

    if (
        haystack.includes(
            "chart"
        )
    ) {
        return "chart";
    }

    if (
        haystack.includes(
            "analysis"
        )
    ) {
        return "analysis";
    }

    if (
        haystack.includes(
            "backtest"
        )
    ) {
        return "backtest";
    }

    if (
        haystack.includes(
            "alert"
        )
    ) {
        return "alerts";
    }

    if (
        haystack.includes(
            "setting"
        )
    ) {
        return "settings";
    }

    return "";
}


function bindNavigation() {
    const buttons = $$(
        [
            ".rail-btn",
            ".side-btn",
            "[data-nav]",
            ".sidebar button",
            ".rail button",
        ].join(",")
    );

    const unique =
        [...new Set(buttons)];

    for (
        const button
        of unique
    ) {
        button.style.cursor =
            "pointer";

        button.addEventListener(
            "click",
            async () => {
                const action =
                    detectNavigationAction(
                        button
                    );

                if (!action) {
                    return;
                }

                unique.forEach(
                    (item) =>
                        item.classList.remove(
                            "active"
                        )
                );

                button.classList.add(
                    "active"
                );

                switch (action) {
                    case "dashboard":
                        window.scrollTo({
                            top: 0,
                            behavior:
                                "smooth",
                        });

                        break;

                    case "markets":
                        scrollToTarget(
                            "#marketsSection"
                        );

                        if (
                            !safe(
                                "#marketsSection"
                            )
                        ) {
                            scrollToTarget(
                                ".top-grid"
                            );
                        }

                        break;

                    case "chart":
                        scrollToTarget(
                            "#priceChart"
                        );
                        break;

                    case "analysis":
                        if (
                            safe(
                                "#analysisSection"
                            )
                        ) {
                            scrollToTarget(
                                "#analysisSection"
                            );
                        }

                        else {
                            scrollToTarget(
                                "#cards"
                            );
                        }

                        break;

                    case "backtest":
                        if (
                            safe(
                                "#backtestSection"
                            )
                        ) {
                            scrollToTarget(
                                "#backtestSection"
                            );
                        }

                        else {
                            scrollToTarget(
                                ".backtest-panel"
                            );
                        }

                        await backtest();

                        break;

                    case "alerts":
                        showNotice(
                            tr(
                                "alertInfo"
                            )
                        );
                        break;

                    case "settings":
                        showNotice(
                            "Settings: language and AI provider are configured from the top bar and server environment."
                        );
                        break;
                }
            }
        );
    }

    console.log(
        "Navigation buttons bound:",
        unique.length
    );
}


/* ============================================================
   MARKET CARD CLICKS
   ============================================================ */

function bindMarketCards() {
    $$("[data-symbol]")
        .forEach((card) => {
            const symbol =
                card.dataset.symbol;

            if (
                !histories[symbol]
            ) {
                return;
            }

            card.style.cursor =
                "pointer";

            card.addEventListener(
                "click",
                async () => {
                    const select =
                        safe("#symbol");

                    if (select) {
                        select.value =
                            symbol;
                    }

                    current.symbol =
                        symbol;

                    await analyze();

                    if (
                        safe(
                            "#marketsSection"
                        )
                    ) {
                        scrollToTarget(
                            "#marketsSection"
                        );
                    }

                    else {
                        scrollToTarget(
                            "#priceChart"
                        );
                    }
                }
            );
        });
}


/* ============================================================
   EVENT BINDING
   ============================================================ */

function bindControls() {
    const analyzeButton =
        safe("#analyze");

    if (analyzeButton) {
        analyzeButton.addEventListener(
            "click",
            analyze
        );
    }

    const backtestButton =
        safe("#runBacktest");

    if (backtestButton) {
        backtestButton.addEventListener(
            "click",
            backtest
        );
    }

    const symbol =
        safe("#symbol");

    if (symbol) {
        symbol.addEventListener(
            "change",
            analyze
        );
    }

    const timeframe =
        safe("#timeframe");

    if (timeframe) {
        timeframe.addEventListener(
            "change",
            analyze
        );
    }

    const csv =
        safe("#csvFile");

    if (csv) {
        csv.addEventListener(
            "change",
            (event) => {
                analyzeCsv(
                    event.target
                        .files?.[0]
                );
            }
        );
    }

    $$(".language-switch button")
        .forEach((button) => {
            button.addEventListener(
                "click",
                () => {
                    applyLanguage(
                        button.dataset.lang
                    );
                }
            );
        });

    const aiOpenIds = [
        "#assistantOpen",
        "#assistantOpenRail",
        "#assistantFab",
    ];

    for (
        const selector
        of aiOpenIds
    ) {
        const element =
            safe(selector);

        if (element) {
            element.addEventListener(
                "click",
                openAssistant
            );
        }
    }

    const close =
        safe("#assistantClose");

    if (close) {
        close.addEventListener(
            "click",
            closeAssistant
        );
    }

    const form =
        safe("#assistantForm");

    if (form) {
        form.addEventListener(
            "submit",
            (event) => {
                event.preventDefault();

                askAssistant(
                    safe(
                        "#assistantInput"
                    )?.value
                );
            }
        );
    }

    const input =
        safe("#assistantInput");

    if (input) {
        input.addEventListener(
            "keydown",
            (event) => {
                if (
                    event.key ===
                        "Enter" &&
                    !event.shiftKey
                ) {
                    event.preventDefault();

                    askAssistant(
                        input.value
                    );
                }
            }
        );
    }

    $$("[data-ai-quick]")
        .forEach((button) => {
            button.addEventListener(
                "click",
                () => {
                    let question =
                        tr(
                            "quickExplain"
                        );

                    if (
                        button.dataset
                            .aiQuick ===
                        "scenario"
                    ) {
                        question =
                            tr(
                                "quickScenario"
                            );
                    }

                    if (
                        button.dataset
                            .aiQuick ===
                        "risk"
                    ) {
                        question =
                            tr(
                                "quickRisk"
                            );
                    }

                    askAssistant(
                        question
                    );
                }
            );
        });
}


/* ============================================================
   START
   ============================================================ */

async function startSignalWave() {
    console.log(
        "Starting SignalWave dashboard..."
    );

    updateClock();

    setInterval(
        updateClock,
        1000
    );

    applyLanguage(
        currentLang
    );

    bindControls();
    bindNavigation();
    bindMarketCards();

    await loadAssistantStatus();

    startTicker();

    await analyze();

    console.log(
        "SignalWave dashboard ready."
    );
}


if (
    document.readyState ===
    "loading"
) {
    document.addEventListener(
        "DOMContentLoaded",
        startSignalWave
    );
}

else {
    startSignalWave();
}