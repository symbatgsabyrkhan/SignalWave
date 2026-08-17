# SignalWave — Assignment Acceptance Checklist

## Core product

- [x] Koyfin-style CSV auto-detection and validation
- [x] Binance public klines, up to 1,000 candles/request
- [x] Inline Telegram flow after `/start`
- [x] Full report with annotated charts
- [x] Web dashboard
- [x] SignalWave AI assistant
- [x] Gemini API integration
- [x] KZ / RU / ENG interface support
- [x] Persistent price alerts with Binance polling

## Technical analysis

- [x] SMA / EMA
- [x] RSI
- [x] MACD
- [x] Bollinger Bands
- [x] ATR
- [x] Volume context
- [x] Pivots / ZigZag
- [x] Support / Resistance zones
- [x] Trendlines
- [x] Fibonacci retracements and extensions
- [x] Fibonacci confluence
- [x] Probabilistic Elliott Wave count with cardinal rules
- [x] Scalp / Swing analysis
- [x] Long-term SMA-200 regime analysis
- [x] Entry / invalidation / TP1 / TP2
- [x] Risk:Reward calculation
- [x] Position-size hint

## Backtesting and research

- [x] Future-blind next-bar execution
- [x] Fees modeled
- [x] Slippage modeled
- [x] True SMA20/SMA50 crossover events
- [x] BTCUSDT real Binance backtest
- [x] ETHUSDT real Binance backtest
- [x] BNBUSDT real Binance backtest
- [x] Rolling chronological walk-forward evaluation
- [x] 4 walk-forward folds per market
- [x] 600 OOS bars per market
- [x] 95% Wilson confidence intervals
- [x] Profit Factor
- [x] Maximum Drawdown
- [x] Drawdown Duration
- [x] Sortino
- [x] Expectancy
- [x] Buy & Hold benchmark
- [x] Bull / Bear / Sideways regime breakdown
- [x] Reproducible CSV research outputs

Research outputs:

- `output/walk_forward_summary.csv`
- `output/walk_forward_folds.csv`
- `output/walk_forward_regimes.csv`

## Performance

- [x] 20 concurrent analysis requests tested
- [x] 20/20 requests successful
- [x] 0 failed requests
- [x] Measured p95 latency < 5 seconds

Measured local result:

- p95: **4.512 s**
- mean: **4.295 s**
- median: **4.320 s**
- max: **4.517 s**
- total wall time: **4.532 s**

Result: **PASS**

## Engineering

- [x] 100+ automated tests
- [x] Full supplied pytest suite passes
- [x] GitHub Actions CI configuration
- [x] Dockerfile
- [x] docker-compose.yml
- [x] SQLite persistence
- [x] Background async price-alert worker
- [x] Modular analysis pipeline
- [x] Telegram and Web use the Python analysis stack

Note:

Docker configuration exists, but local Docker build was not executed because
Docker CLI / Docker Desktop was not available on the validation machine.

## Research documentation

- [x] Final 15–25 page research report
- [x] Final report length: 24 pages
- [x] Research methodology documented
- [x] Backtesting limitations acknowledged
- [x] Statistical uncertainty acknowledged
- [x] Architecture documented
- [x] ADR directory included
- [x] Acceptance checklist included

Final report:

`docs/SignalWave_Research_Report.docx`

## Remaining / external validation

- [ ] Replace lightweight S/R clustering with DBSCAN and complete parameter sensitivity study
- [ ] PostgreSQL production persistence
- [ ] Redis / Celery production job queue
- [ ] Local Docker runtime validation when Docker Desktop is available
- [ ] Mentor code review
- [ ] Final mentor demo / approval

## Important interpretation

Passing unit tests does not by itself prove trading profitability.

The walk-forward experiment contains relatively few crossover trades, and the
95% confidence intervals remain wide. Results must therefore be interpreted as
experimental evidence rather than proof of a persistent market edge.

SignalWave is an educational/research technical-analysis system and does not
execute trades or guarantee investment returns.