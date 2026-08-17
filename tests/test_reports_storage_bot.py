import pytest
from analysis.scenarios import make_card,DISCLAIMER
from reports.render import render_short,render_detailed
from storage.repository import Repository
from bot.handlers import MENU,start_text,csv_prompt,validate_menu_choice

def card(): return make_card('up',(99,101),90,[120,130],{'trend':1,'structure':1,'fibonacci':1,'momentum':1,'volume':1},['support'],['news risk'],'hold support')

def test_short_has_disclaimer(): assert DISCLAIMER in render_short('BTCUSDT','1d',100,card())
def test_short_has_rr(): assert 'R:R' in render_short('BTCUSDT','1d',100,card())
def test_detailed_sections():
    t=render_detailed({'source':'csv'},[card()],{'RSI':'neutral'},['news']); assert 'Сценарии' in t and 'Ограничения' in t and DISCLAIMER in t

def test_repo_analysis_roundtrip():
    r=Repository(); i=r.save_analysis('abc',{'a':1},{'b':2}); assert r.get_analysis(i)['result']=={'b':2}; r.close()

def test_repo_missing():
    r=Repository(); assert r.get_analysis(999) is None; r.close()
@pytest.mark.parametrize('direction,price,triggered',[('above',110,True),('above',90,False),('below',90,True),('below',110,False)])
def test_alerts(direction,price,triggered):
    r=Repository(); r.add_alert(1,'btc',100,direction); assert bool(r.triggered_alerts('BTC',price)) is triggered; r.close()

def test_bad_alert_direction():
    r=Repository();
    with pytest.raises(ValueError): r.add_alert(1,'BTC',100,'x')
    r.close()
@pytest.mark.parametrize('choice',MENU)
def test_menu_choices(choice): assert validate_menu_choice(choice)==choice

def test_bad_menu():
    with pytest.raises(ValueError): validate_menu_choice('bad')

def test_start_text(): assert '/start' in start_text()
def test_csv_prompt(): assert 'CSV' in csv_prompt()
