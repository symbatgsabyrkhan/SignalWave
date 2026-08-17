import numpy as np
import pandas as pd
import pytest
from analysis.indicators import sma,ema,rsi,macd,bollinger,true_range,atr,volume_features,add_indicators

@pytest.mark.parametrize('period',[2,3,5,10,20,50,100,200])
def test_sma_matches_rolling(candles,period):
    got=sma(candles.close,period)
    exp=candles.close.rolling(period,min_periods=period).mean()
    pd.testing.assert_series_equal(got,exp)

@pytest.mark.parametrize('period',[2,5,14,20,50])
def test_ema_last_finite(candles,period):
    assert np.isfinite(ema(candles.close,period).iloc[-1])

@pytest.mark.parametrize('period',[0,-1,-5])
def test_bad_periods(period,candles):
    with pytest.raises(ValueError): sma(candles.close,period)

@pytest.mark.parametrize('period',[5,14,20])
def test_rsi_bounds(candles,period):
    x=rsi(candles.close,period).dropna(); assert ((x>=0)&(x<=100)).all()

def test_rsi_increasing_is_100():
    s=pd.Series(np.arange(1,40,dtype=float)); assert rsi(s,14).dropna().iloc[-1]==100

def test_macd_columns(candles): assert list(macd(candles.close).columns)==['macd','signal','histogram']
@pytest.mark.parametrize('fast,slow,signal',[(0,26,9),(12,12,9),(26,12,9),(12,26,0)])
def test_macd_invalid(candles,fast,slow,signal):
    with pytest.raises(ValueError): macd(candles.close,fast,slow,signal)

@pytest.mark.parametrize('p,k',[(5,1),(10,2),(20,2),(30,2.5)])
def test_bollinger_order(candles,p,k):
    b=bollinger(candles.close,p,k).dropna(); assert (b.upper>=b.middle).all() and (b.middle>=b.lower).all()

def test_true_range_first(candles): assert true_range(candles).iloc[0]==pytest.approx(candles.high.iloc[0]-candles.low.iloc[0])
@pytest.mark.parametrize('p',[2,5,14,30])
def test_atr_positive(candles,p): assert (atr(candles,p).dropna()>0).all()
@pytest.mark.parametrize('p',[2,5,20])
def test_volume_features(candles,p):
    v=volume_features(candles.volume,p); assert {'volume_ma','volume_ratio','volume_spike'}==set(v.columns)

def test_add_indicators_columns(candles):
    out=add_indicators(candles); expected={'sma_20','sma_50','sma_100','sma_200','ema_20','rsi_14','macd','bb_upper','atr_14','volume_ratio'}; assert expected<=set(out.columns)
