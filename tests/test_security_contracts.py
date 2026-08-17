from pathlib import Path
import pytest
from analysis.scenarios import DISCLAIMER,confidence_label

ROOT=Path(__file__).resolve().parents[1]

def test_no_exchange_secret_in_env_example():
    t=(ROOT/'.env.example').read_text(); assert 'SECRET' not in t.upper() and 'TELEGRAM_BOT_TOKEN' in t

def test_readme_no_auto_orders(): assert 'No automatic orders' in (ROOT/'README.md').read_text()
def test_disclaimer_exact(): assert DISCLAIMER=='Не является финансовой консультацией — образовательный инструмент'
@pytest.mark.parametrize('s',[0,10,20,30,40,44])
def test_abstain_band(s): assert 'воздержаться' in confidence_label(s)
@pytest.mark.parametrize('s',[45,50,60,69])
def test_neutral_band(s): assert 'нейтральное' in confidence_label(s)
@pytest.mark.parametrize('s',[70,80,90,100])
def test_action_band(s): assert 'план действий' in confidence_label(s)
