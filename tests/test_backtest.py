import numpy as np
import pandas as pd
import pytest
from backtest.engine import simulate_signals,walk_forward_splits,buy_and_hold

@pytest.mark.parametrize('hold',[1,2,5,10])
def test_sim_runs(candles,hold):
    sig=pd.Series([1 if i%20==0 else 0 for i in range(len(candles))]); r=simulate_signals(candles,sig,hold); assert 0<=r.win_rate<=1 and r.max_drawdown>=0
@pytest.mark.parametrize('hold',[0,-1])
def test_bad_hold(candles,hold):
    with pytest.raises(ValueError): simulate_signals(candles,pd.Series(0,index=range(len(candles))),hold)
@pytest.mark.parametrize('fee,slip',[(-.1,0),(0,-.1)])
def test_bad_costs(candles,fee,slip):
    with pytest.raises(ValueError): simulate_signals(candles,pd.Series(0,index=range(len(candles))),5,fee,slip)

def test_no_signals(candles):
    r=simulate_signals(candles,pd.Series(0,index=range(len(candles)))); assert len(r.trades)==0 and r.total_return==0

def test_future_blind_entry_next_bar(candles):
    sig=pd.Series(0,index=range(len(candles))); sig.iloc[10]=1; r=simulate_signals(candles,sig,2,0,0); assert r.trades[0].entry_i==11
@pytest.mark.parametrize('n,train,test,expected',[(100,60,20,2),(50,20,10,3),(30,20,10,1)])
def test_splits(n,train,test,expected): assert len(list(walk_forward_splits(n,train,test)))==expected
@pytest.mark.parametrize('args',[(0,1,1),(10,0,1),(10,1,0)])
def test_split_bad(args):
    with pytest.raises(ValueError): list(walk_forward_splits(*args))

def test_buy_hold(candles): assert buy_and_hold(candles)==pytest.approx(candles.close.iloc[-1]/candles.close.iloc[0]-1-.002)
