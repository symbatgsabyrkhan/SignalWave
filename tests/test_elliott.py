import pytest
from analysis.elliott import cardinal_rules,ratio_score,evaluate_impulse
from analysis.structure import Pivot

VALID=[100,120,110,145,130,160]

def test_valid_cardinal(): assert cardinal_rules(VALID,True)[0]
@pytest.mark.parametrize('prices',[ [100,120,99,145,130,160], [100,130,115,135,132,170], [100,120,110,145,115,160] ])
def test_invalid_cardinal(prices): assert not cardinal_rules(prices,True)[0]

def test_bad_length():
    with pytest.raises(ValueError): cardinal_rules([1,2],True)
@pytest.mark.parametrize('scale',[0.5,1,2,10])
def test_ratio_scale_invariant(scale): assert ratio_score([x*scale for x in VALID])==ratio_score(VALID)

def test_evaluate_valid():
    piv=[Pivot(i,p,'low' if i%2==0 else 'high') for i,p in enumerate(VALID)]; r=evaluate_impulse(piv,True); assert r.valid and r.confidence>=50

def test_evaluate_short(): assert not evaluate_impulse([Pivot(0,1,'low')]).valid
