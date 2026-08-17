from pathlib import Path
import pytest
from analysis.indicators import add_indicators
from analysis.structure import Pivot,support_resistance_zones,fit_trendline
from analysis.fibonacci import fib_levels
from charts.plotter import render_chart
from pipeline import analyze

@pytest.mark.parametrize('zones_n',[0,1,3,8])
def test_render_png(tmp_path,candles,zones_n):
    d=add_indicators(candles); piv=[Pivot(i,100+i,'low' if i%2==0 else 'high') for i in range(max(2,zones_n+2))]; zones=support_resistance_zones(piv,0.5)[:zones_n]; p=render_chart(d,tmp_path/f'g{zones_n}.png',zones=zones,fibs=fib_levels(100,150)); assert p.exists() and p.stat().st_size>1000

def test_empty_render(tmp_path,candles):
    with pytest.raises(ValueError): render_chart(candles.iloc[:0],tmp_path/'x.png')

def test_pipeline_keys(candles):
    r=analyze(candles); assert {'data','pivots','zones','fibs','elliott','cards','votes'}<=set(r)

def test_pipeline_three_cards(candles): assert len(analyze(candles)['cards'])==3

def test_pipeline_zone_limit(candles): assert len(analyze(candles)['zones'])<=6
