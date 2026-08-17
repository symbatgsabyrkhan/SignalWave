import pandas as pd
import pytest

from data.loaders import normalize_csv_frame, parse_binance_klines
from data.validation import validate_candles


@pytest.mark.parametrize('missing',['time','open','high','low','close'])
def test_missing_required(candles,missing):
    with pytest.raises(ValueError): validate_candles(candles.drop(columns=[missing]))

@pytest.mark.parametrize('col',['open','high','low','close'])
def test_reject_nonpositive(candles,col):
    d=candles.copy(); d.loc[0,col]=0
    if col=='high': d.loc[0,'open']=d.loc[0,'close']=-1
    with pytest.raises(ValueError): validate_candles(d)

def test_duplicate_removed(candles):
    d=pd.concat([candles.iloc[:3],candles.iloc[[1]]]); r=validate_candles(d); assert len(r.data)==3 and any('duplicate' in x for x in r.warnings)

def test_sort_warning(candles):
    r=validate_candles(candles.iloc[:4].sort_index(ascending=False)); assert r.data.time.is_monotonic_increasing

def test_volume_missing(candles):
    r=validate_candles(candles.drop(columns=['volume'])); assert any('volume' in x for x in r.warnings)

def test_min_rows_warning(candles): assert any('recommended' in x for x in validate_candles(candles.iloc[:3],10).warnings)

def test_koyfin_detection():
    raw=pd.DataFrame({'Date':['08-10-2026','08-11-2026'],'BTCUSD Open':[100,101],'BTCUSD High':[102,103],'BTCUSD Low':[99,100],'BTCUSD Close':[101,102]})
    r=normalize_csv_frame(raw,symbol='BTCUSD',timeframe='1d',source='koyfin'); assert r.data.symbol.iloc[0]=='BTCUSD' and len(r.data)==2

@pytest.mark.parametrize('vals,expected', [(['1,5','2,5'],[1.5,2.5]),(['1.5','2.5'],[1.5,2.5])])
def test_decimal_formats(vals,expected):
    raw=pd.DataFrame({'time':['2026-01-01','2026-01-02'],'open':vals,'high':['3','4'],'low':['1','2'],'close':['2','3']})
    r=normalize_csv_frame(raw); assert list(r.data.open)==expected

def test_binance_parse():
    rows=[[1700000000000,'100','101','99','100.5','123'],[1700086400000,'100.5','102','100','101','124']]
    r=parse_binance_klines(rows,'BTCUSDT','1d'); assert list(r.data.columns)[-3:]==['symbol','timeframe','source']

@pytest.mark.parametrize('bad',[[],[1],[1,2,3,4,5]])
def test_binance_bad_row(bad):
    with pytest.raises(ValueError): parse_binance_klines([bad],'BTCUSDT','1d')
