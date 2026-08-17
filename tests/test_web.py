from fastapi.testclient import TestClient

from web.app import app

client = TestClient(app)

def test_web_health():
    r = client.get("/health")
    assert r.status_code == 200

    data = r.json()

    assert data["status"] == "ok"
    assert data["ai_provider"] in {"openai", "gemini"}

def test_dashboard_loads():
    r = client.get('/')
    assert r.status_code == 200
    assert 'SignalWave' in r.text
    assert 'Technical Analysis' in r.text
    assert 'Long / Short' in r.text

def test_csv_rejects_non_csv():
    r = client.post('/api/csv', files={'file': ('bad.txt', b'hello', 'text/plain')})
    assert r.status_code == 400

def test_assistant_status_has_provider_and_configured():
    r = client.get('/api/assistant/status')
    assert r.status_code == 200
    data = r.json()
    assert data['provider'] in {'openai', 'gemini'}
    assert isinstance(data['configured'], bool)
    assert isinstance(data['model'], str)


def test_assistant_requires_key_when_unconfigured(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER', 'openai')
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    r = client.post('/api/assistant', json={'message': 'Explain RSI', 'language': 'en', 'context': {}})
    assert r.status_code == 503
    assert 'OPENAI_API_KEY' in r.json()['detail']
