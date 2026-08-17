"""SignalWave reproducible multi-market walk-forward research backtest."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass

import numpy as np
import pandas as pd

from analysis.indicators import add_indicators
from backtest.engine import simulate_signals
from data.loaders import fetch_binance


SYMBOLS = ("BTCUSDT", "ETHUSDT", "BNBUSDT")
TIMEFRAME = "1d"
LIMIT = 1000

TRAIN_BARS = 400
TEST_BARS = 150
STEP_BARS = 150

HOLD_BARS = 5
FEE_RATE = 0.001
SLIPPAGE_RATE = 0.0005

OUTPUT_DIR = "output"
SUMMARY_FILE = os.path.join(
    OUTPUT_DIR, "walk_forward_summary.csv"
)
FOLDS_FILE = os.path.join(
    OUTPUT_DIR, "walk_forward_folds.csv"
)


@dataclass(frozen=True)
class FoldResult:
    symbol: str
    fold: int
    train_start: int
    train_end: int
    test_start: int
    test_end: int
    regime: str
    trades: int
    wins: int
    win_rate: float
    profit_factor: float
    max_drawdown: float
    drawdown_duration: int
    sortino: float
    expectancy: float
    total_return: float
    buy_hold_return: float


def make_signals(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Create true SMA20/SMA50 crossover events."""
    enriched = add_indicators(df.copy())

    fast = enriched["sma_20"]
    slow = enriched["sma_50"]

    prev_fast = fast.shift(1)
    prev_slow = slow.shift(1)

    valid = (
        fast.notna()
        & slow.notna()
        & prev_fast.notna()
        & prev_slow.notna()
    )

    bullish = (
        valid
        & (prev_fast <= prev_slow)
        & (fast > slow)
    )

    bearish = (
        valid
        & (prev_fast >= prev_slow)
        & (fast < slow)
    )

    signals = pd.Series(
        0, index=enriched.index, dtype=int
    )
    signals.loc[bullish] = 1
    signals.loc[bearish] = -1

    return enriched, signals


def wilson_interval(
    wins: int,
    total: int,
    z: float = 1.96,
) -> tuple[float, float]:
    """95% Wilson confidence interval for win rate."""
    if total <= 0:
        return 0.0, 0.0

    p = wins / total
    z2 = z * z

    denominator = 1.0 + z2 / total
    centre = p + z2 / (2.0 * total)

    margin = z * math.sqrt(
        (
            p * (1.0 - p)
            + z2 / (4.0 * total)
        )
        / total
    )

    low = (centre - margin) / denominator
    high = (centre + margin) / denominator

    return max(0.0, low), min(1.0, high)


def buy_hold_return(df: pd.DataFrame) -> float:
    if len(df) < 2:
        return 0.0

    gross = (
        float(df["close"].iloc[-1])
        / float(df["close"].iloc[0])
        - 1.0
    )

    return gross - 2.0 * FEE_RATE


def classify_regime(df: pd.DataFrame) -> str:
    """
    Simple reproducible market-regime definition.

    bull:
        close above SMA200 and SMA200 rising

    bear:
        close below SMA200 and SMA200 falling

    sideways:
        everything else
    """
    if len(df) < 2:
        return "unknown"

    close = float(df["close"].iloc[-1])

    sma_now = df["sma_200"].iloc[-1]
    sma_prev = df["sma_200"].iloc[-2]

    if pd.isna(sma_now) or pd.isna(sma_prev):
        return "unknown"

    if close > sma_now and sma_now > sma_prev:
        return "bull"

    if close < sma_now and sma_now < sma_prev:
        return "bear"

    return "sideways"


def max_drawdown_duration(trades) -> int:
    """
    Maximum number of consecutive trade-equity observations
    spent below the previous equity peak.
    """
    equity = 1.0
    peak = 1.0

    current_duration = 0
    maximum_duration = 0

    for trade in trades:
        equity *= 1.0 + trade.pnl

        if equity >= peak:
            peak = equity
            current_duration = 0
        else:
            current_duration += 1
            maximum_duration = max(
                maximum_duration,
                current_duration,
            )

    return maximum_duration


def walk_forward_ranges(
    n: int,
):
    start = 0
    fold = 1

    while start + TRAIN_BARS + TEST_BARS <= n:
        train_start = start
        train_end = start + TRAIN_BARS

        test_start = train_end
        test_end = test_start + TEST_BARS

        yield (
            fold,
            train_start,
            train_end,
            test_start,
            test_end,
        )

        fold += 1
        start += STEP_BARS


def run_symbol(symbol: str) -> list[FoldResult]:
    print(f"Downloading {symbol}...")

    validated = fetch_binance(
        symbol,
        TIMEFRAME,
        LIMIT,
    )

    raw = (
        validated.data
        .copy()
        .reset_index(drop=True)
    )

    if len(raw) < TRAIN_BARS + TEST_BARS:
        raise ValueError(
            f"{symbol}: insufficient data "
            f"({len(raw)} candles)"
        )

    enriched, signals = make_signals(raw)

    results: list[FoldResult] = []

    for (
        fold,
        train_start,
        train_end,
        test_start,
        test_end,
    ) in walk_forward_ranges(len(enriched)):

        # Training slice exists to preserve the chronological
        # walk-forward design. No parameter is optimized on OOS.
        train = enriched.iloc[
            train_start:train_end
        ]

        test = (
            enriched.iloc[test_start:test_end]
            .reset_index(drop=True)
        )

        test_signals = (
            signals.iloc[test_start:test_end]
            .reset_index(drop=True)
        )

        result = simulate_signals(
            test,
            test_signals,
            hold_bars=HOLD_BARS,
            fee_rate=FEE_RATE,
            slippage_rate=SLIPPAGE_RATE,
        )

        wins = sum(
            trade.pnl > 0
            for trade in result.trades
        )

        regime = classify_regime(test)

        results.append(
            FoldResult(
                symbol=symbol,
                fold=fold,
                train_start=train_start,
                train_end=train_end - 1,
                test_start=test_start,
                test_end=test_end - 1,
                regime=regime,
                trades=len(result.trades),
                wins=wins,
                win_rate=result.win_rate,
                profit_factor=result.profit_factor,
                max_drawdown=result.max_drawdown,
                drawdown_duration=max_drawdown_duration(
                    result.trades
                ),
                sortino=result.sortino,
                expectancy=result.expectancy,
                total_return=result.total_return,
                buy_hold_return=buy_hold_return(test),
            )
        )

    return results


def safe_pf(values: list[float]) -> float:
    finite = [
        x for x in values
        if not math.isnan(x)
        and not math.isinf(x)
    ]

    if not finite:
        if any(math.isinf(x) for x in values):
            return math.inf
        return 0.0

    return float(np.mean(finite))


def make_summary(
    folds: list[FoldResult],
) -> pd.DataFrame:

    rows = []

    for symbol in SYMBOLS:
        selected = [
            f for f in folds
            if f.symbol == symbol
        ]

        if not selected:
            continue

        total_trades = sum(
            f.trades for f in selected
        )

        total_wins = sum(
            f.wins for f in selected
        )

        low, high = wilson_interval(
            total_wins,
            total_trades,
        )

        rows.append(
            {
                "symbol": symbol,
                "folds": len(selected),
                "oos_bars": (
                    len(selected)
                    * TEST_BARS
                ),
                "trades": total_trades,
                "wins": total_wins,
                "win_rate_pct": round(
                    (
                        total_wins
                        / total_trades
                        * 100
                    )
                    if total_trades
                    else 0.0,
                    2,
                ),
                "win_rate_ci95_low_pct": round(
                    low * 100,
                    2,
                ),
                "win_rate_ci95_high_pct": round(
                    high * 100,
                    2,
                ),
                "avg_profit_factor": round(
                    safe_pf(
                        [
                            f.profit_factor
                            for f in selected
                        ]
                    ),
                    4,
                ),
                "worst_max_drawdown_pct": round(
                    max(
                        f.max_drawdown
                        for f in selected
                    )
                    * 100,
                    2,
                ),
                "max_drawdown_duration_trades": max(
                    f.drawdown_duration
                    for f in selected
                ),
                "avg_sortino": round(
                    float(
                        np.mean(
                            [
                                f.sortino
                                for f in selected
                            ]
                        )
                    ),
                    3,
                ),
                "avg_expectancy_pct": round(
                    float(
                        np.mean(
                            [
                                f.expectancy
                                for f in selected
                            ]
                        )
                    )
                    * 100,
                    4,
                ),
                "compounded_oos_return_pct": round(
                    (
                        np.prod(
                            [
                                1.0 + f.total_return
                                for f in selected
                            ]
                        )
                        - 1.0
                    )
                    * 100,
                    2,
                ),
                "compounded_buy_hold_pct": round(
                    (
                        np.prod(
                            [
                                1.0
                                + f.buy_hold_return
                                for f in selected
                            ]
                        )
                        - 1.0
                    )
                    * 100,
                    2,
                ),
            }
        )

    return pd.DataFrame(rows)


def regime_table(
    folds: list[FoldResult],
) -> pd.DataFrame:

    rows = []

    regimes = (
        "bull",
        "bear",
        "sideways",
        "unknown",
    )

    for symbol in SYMBOLS:
        for regime in regimes:
            selected = [
                f for f in folds
                if (
                    f.symbol == symbol
                    and f.regime == regime
                )
            ]

            if not selected:
                continue

            trades = sum(
                f.trades for f in selected
            )

            wins = sum(
                f.wins for f in selected
            )

            rows.append(
                {
                    "symbol": symbol,
                    "regime": regime,
                    "folds": len(selected),
                    "trades": trades,
                    "win_rate_pct": round(
                        (
                            wins / trades * 100
                        )
                        if trades
                        else 0.0,
                        2,
                    ),
                    "avg_return_pct": round(
                        float(
                            np.mean(
                                [
                                    f.total_return
                                    for f in selected
                                ]
                            )
                        )
                        * 100,
                        2,
                    ),
                    "worst_drawdown_pct": round(
                        max(
                            f.max_drawdown
                            for f in selected
                        )
                        * 100,
                        2,
                    ),
                }
            )

    return pd.DataFrame(rows)


def folds_dataframe(
    folds: list[FoldResult],
) -> pd.DataFrame:

    rows = []

    for f in folds:
        rows.append(
            {
                "symbol": f.symbol,
                "fold": f.fold,
                "train_start": f.train_start,
                "train_end": f.train_end,
                "test_start": f.test_start,
                "test_end": f.test_end,
                "regime": f.regime,
                "trades": f.trades,
                "wins": f.wins,
                "win_rate_pct": round(
                    f.win_rate * 100,
                    2,
                ),
                "profit_factor": (
                    "inf"
                    if math.isinf(
                        f.profit_factor
                    )
                    else round(
                        f.profit_factor,
                        4,
                    )
                ),
                "max_drawdown_pct": round(
                    f.max_drawdown * 100,
                    2,
                ),
                "drawdown_duration_trades":
                    f.drawdown_duration,
                "sortino": round(
                    f.sortino,
                    3,
                ),
                "expectancy_pct": round(
                    f.expectancy * 100,
                    4,
                ),
                "oos_return_pct": round(
                    f.total_return * 100,
                    2,
                ),
                "buy_hold_pct": round(
                    f.buy_hold_return * 100,
                    2,
                ),
            }
        )

    return pd.DataFrame(rows)


def main() -> None:
    print()
    print("=" * 88)
    print(
        "SIGNALWAVE ROLLING WALK-FORWARD "
        "OUT-OF-SAMPLE RESEARCH"
    )
    print("=" * 88)

    print(
        f"Markets: {', '.join(SYMBOLS)}"
    )
    print(f"Timeframe: {TIMEFRAME}")
    print(
        f"Train/Test/Step: "
        f"{TRAIN_BARS}/"
        f"{TEST_BARS}/"
        f"{STEP_BARS} bars"
    )
    print(
        "Strategy: true SMA20/SMA50 "
        "crossover events"
    )
    print(
        f"Holding period: {HOLD_BARS} bars"
    )
    print(
        "Execution: next-bar; "
        "no same-bar look-ahead"
    )
    print(
        "Costs: 0.10% fee + "
        "0.05% slippage per side"
    )
    print()

    all_folds: list[FoldResult] = []

    for symbol in SYMBOLS:
        try:
            all_folds.extend(
                run_symbol(symbol)
            )
        except Exception as exc:
            print(
                f"{symbol} FAILED: {exc}"
            )

    if not all_folds:
        raise SystemExit(
            "No walk-forward folds completed."
        )

    summary = make_summary(all_folds)
    regimes = regime_table(all_folds)
    fold_df = folds_dataframe(all_folds)

    print()
    print("=" * 88)
    print("WALK-FORWARD SUMMARY")
    print("=" * 88)
    print(
        summary.to_string(index=False)
    )

    print()
    print("=" * 88)
    print("REGIME BREAKDOWN")
    print("=" * 88)

    if len(regimes):
        print(
            regimes.to_string(index=False)
        )
    else:
        print(
            "No classified regimes available."
        )

    print()
    print("=" * 88)
    print("METHODOLOGY")
    print("=" * 88)
    print(
        "- Rolling chronological train/test folds."
    )
    print(
        "- Test windows are strictly after "
        "their training windows."
    )
    print(
        "- SMA crossover signals are events, "
        "not repeated trend-state entries."
    )
    print(
        "- Execution occurs on the next bar."
    )
    print(
        "- Fees and slippage are included."
    )
    print(
        "- Win-rate uncertainty uses Wilson 95% CI."
    )
    print(
        "- Regime classification uses "
        "price/SMA200 direction."
    )
    print(
        "- Drawdown duration is measured in "
        "trade-equity observations."
    )
    print(
        "- Small trade samples imply high "
        "statistical uncertainty."
    )

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True,
    )

    summary.to_csv(
        SUMMARY_FILE,
        index=False,
    )

    fold_df.to_csv(
        FOLDS_FILE,
        index=False,
    )

    regime_path = os.path.join(
        OUTPUT_DIR,
        "walk_forward_regimes.csv",
    )

    regimes.to_csv(
        regime_path,
        index=False,
    )

    print()
    print(f"Saved: {SUMMARY_FILE}")
    print(f"Saved: {FOLDS_FILE}")
    print(f"Saved: {regime_path}")
    print()
    print("Research run complete.")


if __name__ == "__main__":
    main()