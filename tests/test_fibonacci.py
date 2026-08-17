import pytest
from analysis.structure import Pivot,Zone
from analysis.fibonacci import fib_levels,last_impulse,levels_from_pivots,mark_confluence,RETRACE,EXT

@pytest.mark.parametrize('start,end',[(100,200),(200,100),(50,75),(75,50)])
def test_fib_count(start,end): assert len(fib_levels(start,end))==len(RETRACE)+len(EXT)

def test_fib_equal_error():
    with pytest.raises(ValueError): fib_levels(1,1)
@pytest.mark.parametrize('r',[0.236,0.382,0.5,0.618,0.786,1.272,1.618])
def test_fib_ratio_present(r): assert r in [x.ratio for x in fib_levels(100,200)]

def test_last_impulse():
    a,b=last_impulse([Pivot(0,100,'low'),Pivot(1,120,'high')]); assert (a.price,b.price)==(100,120)
@pytest.mark.parametrize('pivots',[[],[Pivot(0,1,'low')],[Pivot(0,1,'low'),Pivot(1,2,'low')]])
def test_last_impulse_error(pivots):
    with pytest.raises(ValueError): last_impulse(pivots)

def test_confluence():
    levels=fib_levels(100,200); target=levels[0].price; z=[Zone(target-0.1,target+0.1,target,2,1,'support')]; out=mark_confluence(levels,z,0.5); assert out[0].confluence
@pytest.mark.parametrize('tol',[-1,-0.1])
def test_confluence_bad_tol(tol):
    with pytest.raises(ValueError): mark_confluence([],[],tol)
