"""Chronological backtesting utilities with fees/slippage and no future look-ahead."""
from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np
import pandas as pd

@dataclass(frozen=True)
class Trade:
    entry_i:int; exit_i:int; direction:str; entry:float; exit:float; pnl:float; r_multiple:float; outcome:str

@dataclass(frozen=True)
class BacktestResult:
    trades:tuple[Trade,...]; win_rate:float; profit_factor:float; max_drawdown:float; sortino:float; expectancy:float; total_return:float


def simulate_signals(df:pd.DataFrame, signals:pd.Series, hold_bars:int=5, fee_rate:float=0.001, slippage_rate:float=0.0005)->BacktestResult:
    if hold_bars < 1: raise ValueError("hold_bars must be >=1")
    if fee_rate < 0 or slippage_rate < 0: raise ValueError("costs cannot be negative")
    closes=df["close"].astype(float).reset_index(drop=True)
    sig=signals.reset_index(drop=True).reindex(range(len(df)),fill_value=0)
    trades=[]; equity=[1.0]
    for i in range(len(df)-hold_bars):
        direction=1 if sig.iloc[i]>0 else (-1 if sig.iloc[i]<0 else 0)
        if not direction: continue
        # Execution begins on next bar close to avoid same-bar look-ahead.
        entry_i=i+1; exit_i=min(entry_i+hold_bars-1,len(df)-1)
        entry=closes.iloc[entry_i]*(1+slippage_rate*direction)
        exitp=closes.iloc[exit_i]*(1-slippage_rate*direction)
        gross=(exitp-entry)/entry*direction
        net=gross-2*fee_rate
        trades.append(Trade(entry_i,exit_i,"long" if direction>0 else "short",float(entry),float(exitp),float(net),float(net),"win" if net>0 else "loss"))
        equity.append(equity[-1]*(1+net))
    wins=[t.pnl for t in trades if t.pnl>0]; losses=[t.pnl for t in trades if t.pnl<0]
    wr=len(wins)/len(trades) if trades else 0.0
    pf=sum(wins)/abs(sum(losses)) if losses else (math.inf if wins else 0.0)
    arr=np.array(equity); peaks=np.maximum.accumulate(arr); dd=(peaks-arr)/peaks; mdd=float(dd.max()) if len(dd) else 0.0
    rets=np.array([t.pnl for t in trades]); downside=rets[rets<0]
    sortino=float(rets.mean()/downside.std(ddof=0)*math.sqrt(len(rets))) if len(rets)>1 and len(downside)>1 and downside.std(ddof=0)>0 else 0.0
    expectancy=float(rets.mean()) if len(rets) else 0.0
    total=float(equity[-1]-1)
    return BacktestResult(tuple(trades),wr,float(pf),mdd,sortino,expectancy,total)


def walk_forward_splits(n:int,train:int,test:int,step:int|None=None):
    if min(n,train,test) <= 0: raise ValueError("n/train/test must be positive")
    step=step or test
    if step <= 0: raise ValueError("step must be positive")
    start=0
    while start+train+test <= n:
        yield range(start,start+train), range(start+train,start+train+test)
        start += step


def buy_and_hold(df:pd.DataFrame, fee_rate:float=0.001)->float:
    if len(df)<2: return 0.0
    return float(df["close"].iloc[-1]/df["close"].iloc[0]-1-2*fee_rate)
