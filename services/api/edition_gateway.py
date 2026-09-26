"""Public latest-edition router. Game state lives in private edition apps."""
import asyncio
import os
import re
from contextlib import asynccontextmanager
from http.cookies import SimpleCookie
from http.cookiejar import CookieJar, DefaultCookiePolicy
from urllib.parse import urlsplit

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask

from services.api.release_registry import ROOT, active_registry, history_registry, latest_only_policy, upstream
from services.api.security import client_network, is_event_stream

HOP = {'host', 'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization', 'te', 'trailer', 'transfer-encoding', 'upgrade', 'content-length', 'content-encoding'}
METHODS = ['GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']
PUBLIC_ASSETS = ('assets', 'art', 'review-evidence', 'research-evidence', 'audio', 'explainers')


class NoUpstreamCookies(DefaultCookiePolicy):
    def set_ok(self, cookie, request): return False


def create_gateway(store=None, transport=None):
    from services.api.store import Store
    store = store or Store()

    @asynccontextmanager
    async def lifespan(app):
        yield
        await app.state.client.aclose()

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.client = httpx.AsyncClient(transport=transport, cookies=CookieJar(policy=NoUpstreamCookies()), timeout=httpx.Timeout(365, connect=15), follow_redirects=False, trust_env=False)
    app.state.store = store
    app.state.streams = {}

    @app.middleware('http')
    async def boundaries(request, call_next):
        if os.environ.get('FARMTACT_TRUST_FLY_PROXY') == 'true' and request.headers.get('host') == 'farmtact.fly.dev' and request.headers.get('x-forwarded-proto') == 'http':
            return RedirectResponse('https://farmtact.fly.dev' + request.url.path + ('?' + request.url.query if request.url.query else ''), 307)
        if request.url.path.startswith('/_control/'):
            import ipaddress
            try:
                trusted = os.environ.get('FARMTACT_TRUST_FLY_PROXY') == 'true'
                private = trusted and ipaddress.ip_address(client_network(request, True).split('/')[0]).is_private
            except ValueError:
                private = False
            local = os.environ.get('FARMTACT_LOCAL_EDITIONS') == 'true' and request.client.host == '127.0.0.1' and request.headers.get('host') == 'farmtact-local-control.flycast:8080'
            if not local and (request.headers.get('host') != 'farmtact.flycast' or not private):
                return JSONResponse({'detail': 'Not found'}, 404)
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['Cache-Control'] = 'no-store' if request.url.path.startswith(('/api/', '/_control/')) else response.headers.get('Cache-Control', 'public, max-age=60')
        response.headers['Content-Security-Policy'] = "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; media-src 'self'; frame-ancestors 'none'; base-uri 'self'"
        return response

    from services.api.edition_control import install_control_routes
    install_control_routes(app, store)

    def current_release():
        active = active_registry()
        return active if latest_only_policy(active) else None

    def latest_only_candidate_staged() -> bool:
        staged = os.environ.get('FARMTACT_STAGED_EDITION', '')
        return bool(re.fullmatch(r'v[1-9][0-9]*', staged)) and int(staged[1:]) >= 14

    def same_public_origin(request: Request) -> bool:
        supplied = request.headers.get('origin')
        if not supplied:
            return True
        expected = os.environ.get('FARMTACT_PUBLIC_ORIGIN', 'https://farmtact.fly.dev').rstrip('/')
        return supplied.rstrip('/') == expected

    async def proxy(request: Request, edition: str, path: str, *, public_current=False):
        entries = active_registry()['editions']
        if not any(e['id'] == edition and e.get('status') == 'published' for e in entries):
            published = {e['id'] for e in history_registry()['editions']}
            if edition in published:
                choices = active_registry()['editions']
                links = ''.join(f'<li><a href="/{e["id"]}/">{e["id"]}</a></li>' for e in choices)
                return HTMLResponse(f'<h1>Edition retired</h1><p>{edition} is preserved in release history but is no longer running.</p><ul>{links}</ul>', 410)
            return HTMLResponse('<h1>Edition unavailable</h1><p>This edition is not published.</p><a href="/">Open FarmTact</a>', 404)
        if not same_public_origin(request):
            return JSONResponse({'detail': 'Origin not allowed'}, 403)
        secret = os.environ.get('FARMTACT_CONTROL_SECRET', '')
        if not secret:
            return JSONResponse({'detail': 'Edition routing unavailable'}, 503)
        try:
            network = client_network(request, os.environ.get('FARMTACT_TRUST_FLY_PROXY') == 'true')
        except ValueError:
            return JSONResponse({'detail': 'Invalid client address'}, 400)
        network = network.split('/')[0]
        stream = is_event_stream(request)
        if stream and (app.state.streams.get(network, 0) >= 4 or sum(app.state.streams.values()) >= 32):
            return JSONResponse({'detail': 'Too many active event streams'}, 429, headers={'Retry-After': '5'})
        headers = {k: v for k, v in request.headers.items() if k.lower() not in HOP | {'cookie', 'authorization', 'fly-client-ip', 'origin'} and not k.lower().startswith(('x-farmtact-', 'x-forwarded-'))}
        public_host = urlsplit(os.environ.get('FARMTACT_PUBLIC_ORIGIN', 'https://farmtact.fly.dev')).netloc
        headers.update({'host': public_host, 'x-farmtact-gateway': secret, 'x-farmtact-client-ip': network, 'accept-encoding': 'identity', 'cookie': ''})
        cookie_name = f'farmtact_{edition}_session'
        cookie = request.cookies.get(cookie_name)
        legacy = not public_current and edition == 'v1' and not cookie and request.cookies.get('farmtact_session')
        if legacy:
            cookie = legacy
        if cookie and re.fullmatch(r'[A-Za-z0-9_-]{20,200}', cookie):
            headers['cookie'] = f'farmtact_session={cookie}'
        body = bytearray()
        try:
            async with asyncio.timeout(15):
                async for chunk in request.stream():
                    body.extend(chunk)
                    if len(body) > 1048576:
                        return JSONResponse({'detail': 'Upload exceeds 1 MiB'}, 413)
        except TimeoutError:
            return JSONResponse({'detail': 'Request body timed out'}, 408)
        url = upstream(edition).rstrip('/') + '/' + path
        if request.url.query:
            url += '?' + request.url.query
        try:
            if stream:
                app.state.streams[network] = app.state.streams.get(network, 0) + 1
            response = await app.state.client.send(app.state.client.build_request(request.method, url, headers=headers, content=bytes(body)), stream=True)
        except httpx.RequestError:
            if stream:
                app.state.streams[network] -= 1
            return JSONResponse({'detail': 'This edition is temporarily unavailable. Your saved farm remains in this edition.'}, 503)

        async def close_response():
            await response.aclose()
            if stream:
                app.state.streams[network] -= 1
                if not app.state.streams[network]:
                    del app.state.streams[network]

        output_headers = {k: v for k, v in response.headers.items() if k.lower() not in HOP | {'set-cookie'}}
        location = output_headers.get('location')
        if location and location.startswith('/') and not location.startswith('//') and not public_current:
            output_headers['location'] = f'/{edition}' + location
        content_type = response.headers.get('content-type', '')
        if 'text/html' in content_type:
            content = (await response.aread()).decode('utf-8')
            if not public_current:
                content = re.sub(r'((?:src|href)=["\'])/(assets|art|audio)/', rf'\1/{edition}/\2/', content)
            await close_response()
            result = HTMLResponse(content, response.status_code, headers=output_headers)
        else:
            result = StreamingResponse(response.aiter_bytes(), status_code=response.status_code, headers=output_headers, background=BackgroundTask(close_response))
        cookie_path = '/' if public_current else f'/{edition}/'
        for raw in response.headers.get_list('set-cookie'):
            parsed = SimpleCookie()
            parsed.load(raw)
            if 'farmtact_session' in parsed:
                result.set_cookie(cookie_name, parsed['farmtact_session'].value, path=cookie_path, httponly=True, secure=True, samesite='strict', max_age=86400)
        if legacy and path == 'api/v1/bootstrap' and response.status_code == 200 and not response.headers.get_list('set-cookie'):
            result.set_cookie(cookie_name, cookie, path='/v1/', httponly=True, secure=True, samesite='strict', max_age=86400)
            result.delete_cookie('farmtact_session', path='/')
        result.headers['X-Farmtact-Edition'] = edition
        return result

    dist = ROOT / 'apps/web/dist'
    static_apps = {name: StaticFiles(directory=dist / name) for name in PUBLIC_ASSETS if (dist / name).is_dir()}

    @app.api_route('/api/v1/health', methods=['GET', 'HEAD'])
    async def health(request: Request):
        current = current_release()
        if current:
            return await proxy(request, current['latest'], 'api/v1/health', public_current=True)
        return JSONResponse({'status': 'ok', 'role': 'edition_gateway'})

    @app.get('/api/releases')
    def releases():
        if current_release():
            return JSONResponse({'detail': 'Not found'}, 404)
        return active_registry()

    @app.get('/api/releases/history')
    def release_history():
        if current_release():
            return JSONResponse({'detail': 'Not found'}, 404)
        return history_registry()

    @app.api_route('/api/v1/reviews', methods=METHODS)
    async def reviews(request: Request):
        current = current_release()
        if current:
            return await proxy(request, current['latest'], 'api/v1/reviews', public_current=True)
        if request.method not in ('GET', 'HEAD'):
            return JSONResponse({'detail': 'Method not allowed'}, 405)
        import json
        return JSONResponse(json.loads((ROOT / 'config/review_panel.json').read_text()))

    @app.api_route('/api/v1/{path:path}', methods=METHODS)
    async def current_api(request: Request, path: str):
        current = current_release()
        if not current:
            return JSONResponse({'detail': 'Not found'}, 404)
        return await proxy(request, current['latest'], 'api/v1/' + path, public_current=True)

    for asset_name in PUBLIC_ASSETS:
        async def public_asset(request: Request, path: str, name=asset_name):
            current = current_release()
            if current:
                return await proxy(request, current['latest'], f'{name}/{path}', public_current=True)
            if latest_only_candidate_staged():
                return JSONResponse({'detail': 'Not found'}, 404)
            static = static_apps.get(name)
            return await static.get_response(path, request.scope) if static else JSONResponse({'detail': 'Not found'}, 404)
        app.add_api_route(f'/{asset_name}/{{path:path}}', public_asset, methods=['GET', 'HEAD'], name=f'public-{asset_name}')

    @app.api_route('/', methods=['GET', 'HEAD'])
    @app.api_route('/play', methods=['GET', 'HEAD'])
    @app.api_route('/play/', methods=['GET', 'HEAD'])
    @app.api_route('/review', methods=['GET', 'HEAD'])
    @app.api_route('/review/', methods=['GET', 'HEAD'])
    async def index(request: Request):
        current = current_release()
        if current:
            return await proxy(request, current['latest'], request.url.path.lstrip('/'), public_current=True)
        if latest_only_candidate_staged():
            latest = active_registry()['latest']
            destination = f'/{latest}/review' if request.url.path.startswith('/review') else f'/{latest}/'
            return RedirectResponse(destination, status_code=307)
        if request.url.path.startswith('/play'):
            return JSONResponse({'detail': 'Not found'}, 404)
        return FileResponse(dist / 'index.html')

    @app.api_route('/{edition}/{path:path}', methods=METHODS)
    async def versioned(request: Request, edition: str, path: str):
        if not re.fullmatch(r'v[1-9][0-9]*', edition):
            return JSONResponse({'detail': 'Not found'}, 404)
        current = current_release()
        if current:
            if edition == current['latest'] and request.method in ('GET', 'HEAD'):
                return RedirectResponse('/play', status_code=308)
            if edition == current['latest']:
                return JSONResponse({'detail': 'Use the unversioned current API'}, 404)
            if edition in {item['id'] for item in history_registry()['editions']}:
                return HTMLResponse('<h1>Edition retired</h1><p>This preserved edition is no longer publicly accessible.</p><a href="/">Open FarmTact</a>', 410)
            return JSONResponse({'detail': 'Not found'}, 404)
        return await proxy(request, edition, path)

    @app.api_route('/{edition}', methods=METHODS)
    async def slash(request: Request, edition: str):
        if not re.fullmatch(r'v[1-9][0-9]*', edition):
            return JSONResponse({'detail': 'Not found'}, 404)
        current = current_release()
        if current:
            if edition == current['latest'] and request.method in ('GET', 'HEAD'):
                return RedirectResponse('/play', status_code=308)
            if edition == current['latest']:
                return JSONResponse({'detail': 'Use the unversioned current API'}, 404)
            if edition in {item['id'] for item in history_registry()['editions']}:
                return HTMLResponse('<h1>Edition retired</h1><p>This preserved edition is no longer publicly accessible.</p><a href="/">Open FarmTact</a>', 410)
            return JSONResponse({'detail': 'Not found'}, 404)
        if edition not in {e['id'] for e in active_registry()['editions']}:
            return await proxy(request, edition, '')
        return RedirectResponse(f'/{edition}/', status_code=307)
    return app
