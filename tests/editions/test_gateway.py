import json
import httpx
import pytest
from fastapi.testclient import TestClient
from services.api.store import Store


@pytest.fixture
def gateway(monkeypatch, tmp_path):
    from services.api.edition_gateway import create_gateway
    # Keep this two-edition proxy fixture independent of future publications.
    from services.api.release_registry import ROOT
    releases=json.loads((ROOT/'config/releases/registry.json').read_text())
    fixture=tmp_path/'registry.json'
    fixture.write_text(json.dumps({'latest':'v2','editions':releases['editions'][:2]}))
    active=tmp_path/'active.json'; active.write_text(json.dumps({'previous':'v1','latest':'v2'}))
    monkeypatch.setenv('FARMTACT_RELEASE_REGISTRY',str(fixture))
    monkeypatch.setenv('FARMTACT_ACTIVE_EDITIONS',str(active))
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
    assert not seen[-1].headers.get('cookie')
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


def test_retired_editions_are_gone_for_reads_and_mutations(gateway, monkeypatch, tmp_path):
    client, seen = gateway
    active = tmp_path / 'active.json'; active.write_text(json.dumps({'previous': None, 'latest': 'v2'}))
    monkeypatch.setenv('FARMTACT_ACTIVE_EDITIONS', str(active))
    for method in ('get', 'post', 'delete'):
        response = getattr(client, method)('/v1/api/v1/bootstrap')
        assert response.status_code == 410
        assert '/v2/' in response.text
    assert not seen


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


def test_gateway_never_reuses_upstream_cookie_between_visitors(gateway):
    client, seen = gateway
    client.get('/v1/api/v1/new')
    client.cookies.clear()
    client.get('/v1/api/v1/bootstrap')
    assert not seen[-1].headers.get('cookie')
    client.get('/v2/api/v1/bootstrap')
    assert not seen[-1].headers.get('cookie')


def test_staged_admission_does_not_publish_route(gateway, monkeypatch):
    client, seen = gateway
    monkeypatch.setenv('FARMTACT_STAGED_EDITION', 'v3')
    assert client.get('/v3/api/v1/bootstrap').status_code == 404
    assert [item['id'] for item in client.get('/api/releases').json()['editions']] == ['v1', 'v2']
    assert not seen


def test_staged_v14_never_exposes_candidate_root_bundle(gateway, monkeypatch):
    client, seen = gateway
    monkeypatch.setenv('FARMTACT_STAGED_EDITION', 'v14')
    response = client.get('/', follow_redirects=False)
    assert response.status_code == 307
    assert response.headers['location'] == '/v2/'
    assert client.get('/play', follow_redirects=False).headers['location'] == '/v2/'
    assert client.get('/review', follow_redirects=False).headers['location'] == '/v2/review'
    assert client.get('/assets/candidate.js').status_code == 404
    assert not seen


def test_single_public_bundle_controls_history_and_active_together(gateway, monkeypatch, tmp_path):
    client, _seen = gateway
    history = json.loads(client.get('/api/releases/history').text)
    bundle = tmp_path / 'public.json'
    bundle.write_text(json.dumps({'history': history, 'active': {'previous': None, 'latest': 'v2'}}))
    monkeypatch.setenv('FARMTACT_PUBLIC_RELEASES', str(bundle))
    assert [item['id'] for item in client.get('/api/releases').json()['editions']] == ['v2']
    assert client.get('/v1/').status_code == 410
    assert len(client.get('/api/releases/history').json()['editions']) == 2


@pytest.fixture(params=[14, 15])
def current_gateway(monkeypatch, tmp_path, request):
    from services.api.edition_gateway import create_gateway
    from services.api.release_registry import ROOT
    history = json.loads((ROOT / 'config/releases/registry.json').read_text())
    edition = f'v{request.param}'
    prior = [entry for entry in history['editions'] if int(entry['id'][1:]) < request.param]
    candidate = dict(history['editions'][-1])
    candidate.update(id=edition, title='Current', status='published')
    history = {'latest': edition, 'editions': [*prior, candidate]}
    bundle = tmp_path / 'public.json'
    bundle.write_text(json.dumps({'history': history, 'active': {'previous': None, 'latest': edition}}))
    monkeypatch.setenv('FARMTACT_PUBLIC_RELEASES', str(bundle))
    monkeypatch.setenv('FARMTACT_CONTROL_SECRET', 'test-control-secret-long-enough')
    monkeypatch.setenv('FARMTACT_PUBLIC_ORIGIN', 'https://farmtact.fly.dev')
    seen = []

    async def handle(request):
        seen.append(request)
        if request.url.path in ('/', '/play'):
            return httpx.Response(200, text='<script src="/assets/game.js"></script>', headers={'content-type': 'text/html'})
        if request.url.path == '/assets/game.js':
            return httpx.Response(200, content=b'current-asset', headers={'content-type': 'text/javascript'})
        if request.url.path == '/explainers/observe-decide.mp4':
            if request.headers.get('range') == 'bytes=0-7':
                return httpx.Response(206, content=b'video123', headers={
                    'content-type': 'video/mp4', 'content-range': 'bytes 0-7/80',
                    'accept-ranges': 'bytes',
                })
            return httpx.Response(200, content=b'video123', headers={'content-type': 'video/mp4'})
        headers = {'set-cookie': 'farmtact_session=current_session_123456789; HttpOnly; Path=/; SameSite=Strict'} if request.url.path.endswith('/new') else {}
        return httpx.Response(200, json={'path': request.url.path}, headers=headers)

    app = create_gateway(Store('sqlite://'), httpx.MockTransport(handle))
    with TestClient(app, client=('127.0.0.1', 5000), base_url='https://farmtact.fly.dev') as client:
        client.current_edition = edition
        yield client, seen


def test_v14_current_routes_proxy_without_version_prefix(current_gateway):
    client, seen = current_gateway
    assert client.get('/').status_code == 200
    assert '/assets/game.js' in client.get('/play').text
    assert client.get('/api/v1/bootstrap').json()['path'] == '/api/v1/bootstrap'
    assert client.get('/assets/game.js').content == b'current-asset'
    assert [request.url.path for request in seen[-4:]] == ['/', '/play', '/api/v1/bootstrap', '/assets/game.js']


def test_current_guides_support_playback_download_and_seek(current_gateway):
    client, seen = current_gateway
    video = client.get('/explainers/observe-decide.mp4')
    assert video.status_code == 200
    assert video.headers['content-type'] == 'video/mp4'
    assert video.content == b'video123'
    assert client.head('/explainers/observe-decide.mp4').status_code == 200
    partial = client.get('/explainers/observe-decide.mp4', headers={'range': 'bytes=0-7'})
    assert partial.status_code == 206
    assert partial.headers['content-range'] == 'bytes 0-7/80'
    assert partial.headers['accept-ranges'] == 'bytes'
    assert seen[-1].headers['range'] == 'bytes=0-7'
    for path in ('/explainers/observe-decide.png', '/explainers/observe-decide.vtt',
                 '/explainers/transcripts.json', '/research-evidence/storyboard.png'):
        assert client.get(path).json()['path'] == path
    # This remains a named-asset allowlist, never an arbitrary filesystem server.
    assert client.get('/.env').status_code == 404
    assert client.get('/scripts/serve.py').status_code == 404


def test_v14_cookie_origin_and_header_boundaries(current_gateway):
    client, seen = current_gateway
    response = client.get('/api/v1/new')
    assert f'farmtact_{client.current_edition}_session=' in response.headers['set-cookie']
    assert 'Path=/' in response.headers['set-cookie']
    client.cookies.set('farmtact_v13_session', 'old_session_123456789012345')
    client.cookies.set(f'farmtact_{client.current_edition}_session', 'new_session_123456789012345')
    client.get('/api/v1/bootstrap', headers={
        'authorization': 'Bearer attacker', 'x-farmtact-gateway': 'attacker',
    })
    assert seen[-1].headers['cookie'] == 'farmtact_session=new_session_123456789012345'
    assert 'authorization' not in seen[-1].headers
    assert seen[-1].headers['x-farmtact-gateway'] != 'attacker'
    before = len(seen)
    assert client.post('/api/v1/bootstrap', headers={'origin': 'https://evil.example'}).status_code == 403
    assert len(seen) == before


def test_v14_hides_history_and_retires_numbered_routes(current_gateway):
    client, seen = current_gateway
    assert client.get('/api/releases').status_code == 404
    assert client.get('/api/releases/history').status_code == 404
    for method in ('get', 'post', 'delete'):
        response = getattr(client, method)('/v13/api/v1/bootstrap')
        assert response.status_code == 410
        assert response.text.count('<a ') == 1
        assert 'href="/"' in response.text and '<li>' not in response.text
    response = client.get(f'/{client.current_edition}/', follow_redirects=False)
    assert response.status_code == 308 and response.headers['location'] == '/play'
    assert client.post(f'/{client.current_edition}/api/v1/bootstrap').status_code == 404
    assert not seen
