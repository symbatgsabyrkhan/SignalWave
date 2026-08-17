import pytest
from analysis.scenarios import confidence_score,confidence_label,risk_reward,make_card,three_scenarios,DISCLAIMER

@pytest.mark.parametrize('v,expected',[({'trend':0},0),({'trend':1},100),({'trend':0.5},50),({'trend':.8,'structure':.8},80)])
def test_confidence(v,expected): assert confidence_score(v)==expected

def test_unknown_vote():
    with pytest.raises(ValueError): confidence_score({'foo':1})
@pytest.mark.parametrize('score,label',[ (0,'нет преимущества, воздержаться'),(44,'нет преимущества, воздержаться'),(45,'нейтральное наблюдение'),(69,'нейтральное наблюдение'),(70,'план действий'),(100,'план действий')])
def test_labels(score,label): assert confidence_label(score)==label
@pytest.mark.parametrize('score',[-1,101])
def test_label_bad(score):
    with pytest.raises(ValueError): confidence_label(score)
@pytest.mark.parametrize('direction,entry,inv,target,expected',[('up',100,90,120,2),('down',100,110,80,2),('up',100,110,120,0),('down',100,90,80,0)])
def test_rr(direction,entry,inv,target,expected): assert risk_reward(entry,inv,target,direction)==pytest.approx(expected)

def test_rr_bad_direction():
    with pytest.raises(ValueError): risk_reward(1,2,3,'x')

def test_card_actionable():
    c=make_card('up',(99,101),90,[120],{'trend':1,'structure':1,'fibonacci':1,'momentum':1,'volume':1},['yes'],['risk']); assert c.actionable

def test_card_reject_low_rr():
    c=make_card('up',(99,101),90,[110],{'trend':1,'structure':1,'fibonacci':1,'momentum':1,'volume':1},['yes'],['risk']); assert not c.actionable

def test_three_scenarios():
    cards=three_scenarios(100,5,{'trend':.8,'structure':.7,'fibonacci':.6,'momentum':.7,'volume':.5}); assert [c.direction for c in cards]==['up','down','unclear'] and all(c.disclaimer==DISCLAIMER for c in cards)
