# SignalWave / TA Bot — Final Integrated Project

SignalWave is a research-oriented technical-analysis platform with a Telegram bot, web dashboard, live Binance market data, CSV/Koyfin ingestion, scenario generation, backtesting, price alerts and multilingual support.

The project uses one reusable Python analysis pipeline:

data → indicators → market structure → Fibonacci → Elliott → scenarios → backtesting → charts → reports → storage → Telegram / Web

---

🌐 **Live Website:** https://signalwave-939g.onrender.com

🤖 **Telegram Bot:** https://t.me/signalwave_BOT

SignalWave — платформа для технического анализа криптовалют.

## 1. Project Structure

Open the project root in PyCharm:

```text
ta-bot-final
```

Main structure:

```text
ta-bot-final/
├── analysis/
├── backtest/
├── bot/
├── charts/
├── data/
├── docs/
│   ├── adr/
│   ├── ACCEPTANCE_CHECKLIST.md
│   ├── RESEARCH_REPORT.md
│   └── SignalWave_Research_Report.docx
├── output/
├── reports/
├── storage/
├── tests/
├── web/
├── .github/
│   └── workflows/
├── Dockerfile
├── docker-compose.yml
├── load_test.py
├── pipeline.py
├── requirements.txt
└── README.md
```

---

## 2. Environment Setup

Recommended Python version:

```text
Python 3.12
```

### Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### macOS / Linux

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

---

## 3. Environment Variables

Create a `.env` file in the project root.

Example:

```env
TELEGRAM_BOT_TOKEN=your_telegram_token

AI_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.6-flash
```

OpenAI can also be configured as the dashboard assistant provider:

```env
AI_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-5
```

Do not commit `.env` or expose API keys.

Binance secret API keys are not required. SignalWave uses public market-data endpoints.

---

## 4. Automated Tests

Run:

```powershell
pytest -q
```

The current test suite passes completely.

The tests cover the main analysis pipeline, indicators, market structure, Fibonacci, Elliott Wave, scenarios, loaders, charts, storage, web API and backtesting.

A FastAPI / Starlette TestClient dependency warning may appear during testing. It does not represent a test failure.

GitHub Actions configuration is located at:

```text
.github/workflows/ci.yml
```

The CI workflow performs:

```text
pip install -r requirements.txt
pytest
ruff check .
```

---

## 5. Telegram Bot

Start the Telegram bot from the project root:

```powershell
python -m bot.app
```

Then open the bot in Telegram and send:

```text
/start
```

The main Telegram workflow uses inline buttons.

Available functionality includes:

- CSV / Koyfin-style upload
- Binance market-data loading
- symbol selection
- timeframe selection
- full technical analysis
- annotated charts
- Scalp mode
- Swing mode
- Long-term / Invest mode
- Backtest
- Price Alerts

---

## 6. CSV / Koyfin Data

SignalWave accepts candle data from CSV files.

The data loader validates and normalizes:

- Date / Time
- Open
- High
- Low
- Close
- optional Volume
- chronological ordering
- duplicate rows
- numeric values
- canonical candle structure

Koyfin-style column names are automatically detected when possible.

Indicators are calculated inside SignalWave rather than relying on pre-calculated indicators in the uploaded file.

---

## 7. Binance Market Data

SignalWave supports public Binance candlestick data.

A typical Telegram workflow is:

```text
Binance
→ BTCUSDT
→ 1d
→ Full Analysis
```

The loader supports up to 1,000 candles per request.

Markets used in the multi-market research include:

```text
BTCUSDT
ETHUSDT
BNBUSDT
```

---

## 8. Technical Analysis

### Indicators

Implemented in:

```text
analysis/indicators.py
```

The indicator layer includes:

- SMA
- EMA
- RSI
- MACD
- MACD Signal
- MACD Histogram
- Bollinger Bands
- ATR
- Volume context

Long-term analysis also uses SMA-200 market context.

---

### Market Structure

Implemented in:

```text
analysis/structure.py
```

The structural-analysis layer includes:

- local pivots
- ZigZag-style structure
- support zones
- resistance zones
- strongest-zone filtering
- trend-line estimation

---

### Fibonacci

Implemented in:

```text
analysis/fibonacci.py
```

Includes:

- Fibonacci retracements
- Fibonacci extensions
- structural confluence

Fibonacci levels are treated as contextual evidence rather than deterministic price predictions.

---

### Elliott Wave

Implemented in:

```text
analysis/elliott.py
```

SignalWave contains an experimental rule-based Elliott Wave interpretation with cardinal-rule validation and confidence scoring.

Elliott Wave output is treated as probabilistic and non-guaranteed.

---

## 9. Scenario Engine

Implemented in:

```text
analysis/scenarios.py
```

SignalWave evaluates three scenario types:

```text
up
down
unclear
```

A scenario can include:

- confidence
- entry zone
- invalidation
- target levels
- risk/reward
- supporting evidence
- opposing evidence
- actionable / abstain decision

Confidence interpretation:

```text
< 45      → abstain
45–69     → neutral / watch
>= 70     → action-plan candidate
```

A directional setup is considered actionable only when the first-target risk/reward is at least:

```text
R:R >= 1.5
```

The system presents scenarios rather than guaranteed market predictions.

---

## 10. Full Analysis

The Full Analysis flow generates annotated market charts and a textual analysis summary.

Visual analysis can include:

- price action
- moving averages
- RSI / momentum context
- support / resistance
- trend lines
- Fibonacci levels
- Elliott Wave interpretation

Chart rendering is implemented in:

```text
charts/plotter.py
```

---

## 11. Scalp / Swing Analysis

The Telegram Long / Short workflow provides two analysis modes:

```text
Scalp
Swing
```

A generated trade plan can contain:

- entry zone
- invalidation
- TP1
- TP2
- risk/reward
- confidence
- position-size hint
- annotated trade-plan chart

SignalWave does not execute trades automatically.

---

## 12. Long-Term Analysis

Long-term / Invest mode provides:

- SMA-200 market regime
- long-term structural context
- Fibonacci confluence
- DCA-style accumulation context
- risk information

The output is intended for research and educational analysis.

---

## 13. Price Alerts

SignalWave supports persistent price alerts.

Examples:

```text
ALERT BTCUSDT 100000 above
```

```text
ALERT BTCUSDT 90000 below
```

A background worker periodically checks Binance market prices.

When an active condition is crossed, the Telegram bot sends a notification.

Current local persistence uses SQLite.

---

## 14. Backtesting Engine

Core backtesting implementation:

```text
backtest/engine.py
```

Research runner:

```text
backtest/research.py
```

The backtesting system includes:

- chronological simulation
- future-blind execution
- next-bar entry
- fees
- slippage
- long / short signals
- Win Rate
- Profit Factor
- Maximum Drawdown
- Drawdown Duration
- Sortino
- Expectancy
- Total Return
- Buy & Hold benchmark

No same-bar look-ahead execution is used.

---

## 15. Rolling Walk-Forward Research

SignalWave was evaluated on real Binance daily candle data for:

```text
BTCUSDT
ETHUSDT
BNBUSDT
```

Research configuration:

```text
Maximum candles per market: 1000
Training window: 400 bars
OOS test window: 150 bars
Step: 150 bars
Walk-forward folds per market: 4
OOS bars per market: 600
```

The reproducible experiment uses true SMA20/SMA50 crossover events.

Holding period:

```text
5 bars
```

Execution assumptions:

```text
Next-bar execution
0.10% fee
0.05% slippage per side
```

Run the research:

```powershell
python -m backtest.research
```

Generated files:

```text
output/walk_forward_summary.csv
output/walk_forward_folds.csv
output/walk_forward_regimes.csv
```

---

## 16. Walk-Forward Results

### BTCUSDT

```text
Folds: 4
OOS bars: 600
Trades: 15
Wins: 8
Win rate: 53.33%
95% Wilson CI: 30.12% – 75.19%
Worst max drawdown: 3.57%
Maximum drawdown duration: 3 trades
Compounded OOS return: 52.07%
```

### ETHUSDT

```text
Folds: 4
OOS bars: 600
Trades: 9
Wins: 6
Win rate: 66.67%
95% Wilson CI: 35.42% – 87.94%
Worst max drawdown: 3.10%
Maximum drawdown duration: 1 trade
Compounded OOS return: 56.70%
```

### BNBUSDT

```text
Folds: 4
OOS bars: 600
Trades: 14
Wins: 8
Win rate: 57.14%
95% Wilson CI: 32.59% – 78.62%
Worst max drawdown: 8.24%
Maximum drawdown duration: 3 trades
Compounded OOS return: 1.93%
```

Historical results are not evidence of guaranteed future performance.

The number of crossover trades remains relatively small, so confidence intervals are wide and the results must be interpreted with appropriate statistical caution.

---

## 17. Market Regime Analysis

Walk-forward results are also separated by market regime.

The current classification uses SMA-200 direction and price location.

### Bull

```text
Price > SMA200
and
SMA200 rising
```

### Bear

```text
Price < SMA200
and
SMA200 falling
```

### Sideways

Other classified conditions.

Regime results are exported to:

```text
output/walk_forward_regimes.csv
```

This provides a basic comparison of strategy behavior across different market environments.

---

## 18. Statistical Uncertainty

SignalWave reports Wilson 95% confidence intervals for observed win rates.

This is important because an observed win rate from a small number of trades can have substantial uncertainty.

The research therefore reports both the point estimate and its confidence interval instead of treating the observed win rate as an exact underlying probability.

---

## 19. Web Dashboard

SignalWave includes a browser dashboard powered by the same Python analysis stack.

Start the server:

```powershell
python -m uvicorn web.app:app --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

The dashboard supports:

- Binance market data
- market cards
- candlestick visualization
- moving averages
- support / resistance
- Fibonacci overlays
- RSI
- MACD
- scenario cards
- Elliott confidence
- backtest information
- CSV upload
- interactive navigation

Telegram remains the alert and notification interface.

---

## 20. Dashboard Assistant

The web dashboard includes an optional assistant for explaining the current SignalWave analysis.

Supported providers:

```text
Gemini
OpenAI
```

The provider is configured through `.env`.

The assistant receives a compact snapshot of the analysis currently calculated by SignalWave, including:

- symbol
- timeframe
- latest price
- indicators
- scenarios
- support / resistance
- Fibonacci context
- Elliott output
- confidence values

The assistant is intended to explain the calculated dashboard information and uncertainty.

It does not execute trades.

---

## 21. Languages

The web dashboard supports three interface languages:

```text
ҚАЗ
РУС
ENG
```

The language selector changes the dashboard interface and the language used for assistant interaction.

---

## 22. Performance Test

A local concurrency test is provided in:

```text
load_test.py
```

Start the web server first:

```powershell
python -m uvicorn web.app:app --host 127.0.0.1 --port 8000
```

Then run in another terminal:

```powershell
python load_test.py
```

Validated local result:

```text
Concurrent requests: 20

Successful: 20/20
Failed: 0

Total wall time: 4.532 s
Mean latency: 4.295 s
Median latency: 4.320 s
p95 latency: 4.512 s
Max latency: 4.517 s
```

Result:

```text
PASS
```

Performance target:

```text
p95 < 5 seconds under 20 concurrent analyses
```

The target was met during the recorded local validation run.

---

## 23. Storage

Local persistence is implemented in:

```text
storage/repository.py
```

SQLite is currently used for persistent local data such as price alerts.

The current project does not claim to provide a completed production PostgreSQL / Redis / Celery deployment.

Those components remain possible production infrastructure extensions.

---

## 24. Docker

The repository includes:

```text
Dockerfile
docker-compose.yml
```

The Dockerfile currently uses the Telegram bot as its entry point:

```text
python -m bot.app
```

The Compose configuration loads environment variables from `.env`.

Local Docker runtime validation was not performed on the development machine because Docker CLI / Docker Desktop was unavailable.

---

## 25. Continuous Integration

GitHub Actions configuration is located at:

```text
.github/workflows/ci.yml
```

The workflow installs project dependencies and runs:

```text
pytest
ruff check .
```

The local test suite passes completely.

---

## 26. Research Documentation

The final research report is located at:

```text
docs/SignalWave_Research_Report.docx
```

The report contains 24 pages and covers the main research areas of the project, including:

1. Trend and Moving Averages
2. RSI / MACD momentum analysis
3. Support / Resistance
4. Fibonacci
5. Elliott Wave
6. Signal Combination
7. Backtesting Rigor
8. Risk and Position Sizing

It also documents:

- architecture
- methodology
- walk-forward evaluation
- BTC / ETH / BNB results
- statistical uncertainty
- limitations
- architectural decisions
- acceptance criteria

Additional repository documentation:

```text
docs/RESEARCH_REPORT.md
docs/ACCEPTANCE_CHECKLIST.md
docs/adr/
```

---

## 27. Architecture Summary

### `data/`

CSV/Koyfin and Binance data loading and canonical validation.

### `analysis/indicators.py`

Technical indicators.

### `analysis/structure.py`

Pivots, ZigZag, support/resistance and trend lines.

### `analysis/fibonacci.py`

Retracements, extensions and confluence.

### `analysis/elliott.py`

Experimental Elliott Wave interpretation.

### `analysis/scenarios.py`

Scenario confidence and trade-plan logic.

### `backtest/engine.py`

Chronological future-blind backtesting engine.

### `backtest/research.py`

Multi-market rolling walk-forward research.

### `charts/plotter.py`

Annotated chart rendering.

### `reports/render.py`

Short and detailed textual reports.

### `storage/repository.py`

Local persistence and price alerts.

### `pipeline.py`

Reusable end-to-end analysis pipeline.

### `bot/app.py`

Telegram interface.

### `web/app.py`

FastAPI web application and dashboard backend.

---

## 28. Safety and Product Rules

SignalWave follows the following design rules:

- no automatic order execution
- no withdrawal functionality
- no leverage control
- no exchange secret trading keys
- scenarios are not guarantees
- invalidation is explicitly represented
- opposing evidence can be shown
- low-confidence setups may abstain
- Elliott Wave is experimental
- backtests include transaction costs
- future-blind execution is used
- statistical uncertainty is disclosed
- dashboard assistant responses must not promise profits

---

## 29. Limitations

SignalWave is a research and educational technical-analysis project.

Important limitations include:

- historical performance does not guarantee future performance
- market regimes can change
- technical indicators may be correlated
- Fibonacci relationships may occur by chance
- support / resistance detection depends on algorithm parameters
- Elliott Wave interpretation contains uncertainty
- small trade samples produce wide confidence intervals
- transaction-cost assumptions may differ from real execution
- local SQLite persistence is not a complete production infrastructure
- Docker runtime was not locally validated because Docker was unavailable
- final mentor review and approval are external validation steps

---

## 30. Quick Demo

### Telegram

Start:

```powershell
python -m bot.app
```

Then in Telegram:

```text
/start
```

Suggested demonstration flow:

```text
Binance
→ BTCUSDT
→ 1d
→ Full Analysis
→ Long / Short
→ Backtest
→ Price Alert
```

---

### Web Dashboard

Start:

```powershell
python -m uvicorn web.app:app --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

Suggested demonstration:

- live market cards
- candlestick chart
- technical analysis
- scenarios
- backtest
- language switch
- dashboard assistant

---

### Walk-Forward Research

Run:

```powershell
python -m backtest.research
```

Review:

```text
WALK-FORWARD SUMMARY
REGIME BREAKDOWN
```

and the generated files in:

```text
output/
```

---

### Tests

Run:

```powershell
pytest -q
```

Expected result:

```text
100% passed
```

---

### Performance

With the web server running:

```powershell
python load_test.py
```

Recorded validation result:

```text
20/20 successful
0 failed
p95 = 4.512 s
PASS
```

---

## 31. Project Status

Implemented and validated:

- Telegram interface
- CSV / Koyfin ingestion
- Binance public market data
- technical indicators
- market structure
- Fibonacci analysis
- Elliott Wave analysis
- scenario engine
- Scalp / Swing analysis
- Long-term mode
- price alerts
- annotated charts
- backtesting engine
- BTC / ETH / BNB multi-market research
- rolling walk-forward OOS evaluation
- fees and slippage
- Wilson 95% confidence intervals
- regime breakdown
- drawdown duration
- web dashboard
- optional Gemini / OpenAI dashboard assistant
- ҚАЗ / РУС / ENG interface
- automated tests
- GitHub Actions CI configuration
- Docker configuration
- concurrency performance test
- final research report

Production / external items not claimed as completed:

- production PostgreSQL deployment
- production Redis / Celery job queue
- local Docker runtime validation on a machine with Docker installed
- mentor code review
- mentor demo / approval

---

## Disclaimer

SignalWave is an educational and research technical-analysis system.

It does not guarantee market movements or investment returns and does not constitute financial advice.
- No automatic orders, leverage, or withdrawal functionality.
