import pytest
from analysis.structure import Pivot,local_pivots,zigzag,support_resistance_zones,fit_trendline,strongest_zones

def test_local_pivots_nonempty(candles): assert local_pivots(candles,3)
@pytest.mark.parametrize('order',[0,-1])
def test_local_pivots_bad_order(candles,order):
    with pytest.raises(ValueError): local_pivots(candles,order)

def test_short_no_pivots(candles): assert local_pivots(candles.iloc[:3],2)==[]

@pytest.mark.parametrize('threshold',[0,1,2,5])
def test_zigzag_alternates(threshold):
    ps=[Pivot(0,100,'low'),Pivot(1,110,'high'),Pivot(2,105,'low'),Pivot(3,120,'high')]
    out=zigzag(ps,threshold); assert all(a.kind!=b.kind for a,b in zip(out,out[1:]))

def test_zigzag_same_kind_keeps_extreme():
    out=zigzag([Pivot(0,100,'high'),Pivot(1,110,'high'),Pivot(2,90,'low')],0); assert out[0].price==110
@pytest.mark.parametrize('thr',[-0.1,-1])
def test_zigzag_bad_threshold(thr):
    with pytest.raises(ValueError): zigzag([],thr)

def test_zone_cluster():
    ps=[Pivot(0,100,'low'),Pivot(1,100.4,'low'),Pivot(2,120,'high')]; z=support_resistance_zones(ps,1); assert z[0].touches==2
@pytest.mark.parametrize('tol',[0,-1])
def test_zone_bad_tol(tol):
    with pytest.raises(ValueError): support_resistance_zones([],tol)

def test_fit_line():
    ps=[Pivot(i,100+2*i,'low') for i in range(5)]; tl=fit_trendline(ps,'low'); assert tl and tl.slope==pytest.approx(2)
@pytest.mark.parametrize('kind',['x','support','resistance'])
def test_fit_line_bad_kind(kind):
    with pytest.raises(ValueError): fit_trendline([],kind)

def test_fit_line_too_few(): assert fit_trendline([Pivot(0,1,'low')],'low') is None
@pytest.mark.parametrize('limit',[0,1,2])
def test_strongest_limit(limit):
    z=support_resistance_zones([Pivot(0,100,'low'),Pivot(1,100.2,'low'),Pivot(2,120,'high')],1); assert len(strongest_zones(z,limit))<=limit
