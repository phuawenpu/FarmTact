import json
import httpx
import pytest
from fastapi.testclient import TestClient
from services.api.store import Store


@pytest.fixture
def gateway(monkeypatch):
    from services.api.edition_gateway import create_gateway
    monkeypatch.setenv('FARMTACT_CONTROL_SECRET', 'test-control-secret-long-enough')
    monkeypatch.delenv('FARMTACT_TRUST_FLY_PROXY', raising=False)
    seen = []
    async def handle(request):
        seen.append(request)
        if request.url.path == '/':
            return httpx.Response(200, text='<script src="/assets/game.js"></script>', headers={'content-type': 'text/html'})
        if request.url.path.endswith('events'):
            return httpx.Response(200, content=b'data: hello\n\n', headers={'content-type': 'text/event-stream'})
        headers = {'set-cookie': 'farmtact_session=new_session_value_123456789; HttpOnly; Path=/; SameSite=Strict'} if request.url.path.endswith('new') else {}
        return httpx.Response(200, json={'ok': True}, headers=headers)
    app = create_gateway(Store('sqlite://'), httpx.MockTransport(handle))
    with TestClient(app, client=('127.0.0.1', 5000), base_url='https://farmtact.fly.dev') as client:
        yield client, seen


def test_asset_prefix_and_distinct_cookies(gateway):
    client, seen = gateway
    assert '/v1/assets/game.js' in client.get('/v1/').text
    client.cookies.set('farmtact_v1_session', 'one_session_123456789012345')
    client.cookies.set('farmtact_v2_session', 'two_session_123456789012345')
    client.get('/v1/api/v1/bootstrap')
    assert seen[-1].headers['cookie'] == 'farmtact_session=one_session_123456789012345'
    client.get('/v2/api/v1/bootstrap')
    assert seen[-1].headers['cookie'] == 'farmtact_session=two_session_123456789012345'
    response = client.get('/v2/api/v1/new')
    assert 'farmtact_v2_session=' in response.headers['set-cookie']
    assert 'Path=/v2/' in response.headers['set-cookie']


def test_legacy_only_reaches_v1(gateway):
    client, seen = gateway
    client.cookies.set('farmtact_session', 'legacy_session_123456789012345')
    client.get('/v2/api/v1/bootstrap')
    assert 'cookie' not in seen[-1].headers
    response = client.get('/v1/api/v1/bootstrap')
    assert seen[-1].headers['cookie'].startswith('farmtact_session=legacy')
    assert any('farmtact_v1_session=' in h for h in response.headers.get_list('set-cookie'))


def test_unknown_edition_no_fallback_and_stream(gateway):
    client, seen = gateway
    assert client.get('/v999/').status_code == 404
    assert not seen
    response = client.get('/v1/api/v1/planning-runs/id/events')
    assert response.text == 'data: hello\n\n'
    assert response.headers['x-farmtact-edition'] == 'v1'


def test_upstream_headers_and_body_guard(gateway):
    client, seen = gateway
    client.get('/v2/api/v1/bootstrap', headers={'x-farmtact-client-ip': '1.2.3.4', 'x-farmtact-gateway': 'attacker', 'authorization': 'Bearer attacker'})
    assert seen[-1].headers['x-farmtact-client-ip'] == '127.0.0.1'
    assert seen[-1].headers['x-farmtact-gateway'] != 'attacker'
    assert 'authorization' not in seen[-1].headers
    assert client.post('/v2/api/v1/imports', content=b'a' * 1048577).status_code == 413


def test_chooser_metadata_does_not_bootstrap(gateway):
    client, seen = gateway
    response = client.get('/api/releases')
    assert [e['id'] for e in response.json()['editions']] == ['v1', 'v2']
    assert not client.cookies and not seen
    assert 'flycast' not in response.text
