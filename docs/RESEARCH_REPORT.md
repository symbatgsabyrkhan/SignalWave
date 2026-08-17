# SignalWave — Research Report (engineering draft)

## Scope
This report records the research decisions behind the implemented SignalWave pipeline. It is deliberately separated from marketing claims: every numeric output in the bot is computed from the current dataset, Elliott Wave is probabilistic, and backtest results are reported as historical measurements rather than forecasts.

## 1. Trend and moving averages
SignalWave computes SMA/EMA 20, 50, 100 and 200. SMA-200 is used as a regime filter rather than as a standalone entry trigger. Shorter averages react faster but are noisier; longer averages reduce noise at the cost of lag. Parameter sensitivity must therefore be evaluated per asset/timeframe instead of assuming one period is universally optimal.

## 2. Momentum — RSI and MACD
RSI(14) is treated as context and divergence evidence, not a deterministic reversal signal. MACD(12,26,9) is confirmation. TA-Lib's documented defaults provide the reference convention for verification. Official reference: https://ta-lib.github.io/ta-lib-python/func_groups/momentum_indicators.html

## 3. Support / Resistance and pivots
The implementation first extracts local extrema and then applies a ZigZag-style minimum-move filter. SciPy documents `argrelextrema` and its `order` parameter as the number of points on each side used to qualify an extremum: https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.argrelextrema.html . Price areas are represented as zones, not exact lines. The next research iteration should replace the lightweight 1-D tolerance clustering with DBSCAN and test `eps` sensitivity. DBSCAN reference: https://scikit-learn.org/stable/modules/generated/sklearn.cluster.DBSCAN.html

## 4. Fibonacci
Retracements 0.236, 0.382, 0.5, 0.618 and 0.786 and extensions 1.272/1.618 are derived from the latest confirmed alternating swing leg. A Fibonacci level receives extra significance only when it overlaps independently detected structure. The assignment requires the reliability of these ratios to be tested against chance; this remains an empirical question, not an assumption.

## 5. Elliott Wave
The detector enforces the three cardinal impulse constraints: Wave 2 cannot pass the origin of Wave 1; Wave 3 cannot be the shortest impulse wave; Wave 4 cannot overlap Wave 1 territory in a standard impulse. Soft Fibonacci relationships affect confidence but do not convert a subjective count into certainty. Ambiguous/weak counts must be labelled probabilistic and allow an alternate interpretation.

## 6. Signal combination
The current model combines trend, structure, Fibonacci, momentum and volume/volatility votes into a 0–100 score. Correlated indicators must not be treated as independent evidence. Calibration should be performed only on in-sample windows, then frozen for OOS evaluation. Decision policy: <45 abstain, 45–69 watch, >=70 candidate; a directional trade plan additionally needs R:R >=1.5.

## 7. Backtesting rigor
Execution begins after the signal bar, includes explicit fee/slippage assumptions and reports an OOS segment. The assignment's final evaluation additionally requires walk-forward testing across at least three tickers, confidence intervals, regime breakdowns and parameter sensitivity. A single profitable run is not evidence of generalization.

## 8. Risk and position sizing
The UI gives a fixed-fractional sizing hint based on 1% capital risk divided by entry-to-invalidation distance. It does not place orders. Stops are tied to invalidating structure, not arbitrary percentages. TP levels and R:R are derived from the plan and the bot abstains when the minimum R:R gate fails.

## Source plan for the final 15–25 page submission
The proposal asks for >=10 annotated sources per major technique for an A-level research-depth score. The final bibliography should include: Wilder (1978); Frost & Prechter; Kirkpatrick & Dahlquist; Brock, Lakonishok & LeBaron (1992); Osler (2000); Lopez de Prado; Van Tharp; TA-Lib source/docs; SciPy extrema docs; scikit-learn clustering/calibration docs; Binance Spot API docs; plus peer-reviewed studies for Fibonacci/Elliott automation and parameter-sensitivity experiments generated from this project.

## Reproducibility
The code is deterministic for a fixed CSV and settings. Chart rendering is server-side PNG. Research claims that are not yet demonstrated by the repository are explicitly marked as future empirical work rather than silently presented as complete.
