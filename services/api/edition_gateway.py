"""Public edition chooser and streaming router. Game state lives in private apps."""
import asyncio
import os
import re
from contextlib import asynccontextmanager
from http.cookies import SimpleCookie

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask

from services.api.release_registry import ROOT, registry, upstream
from services.api.security import client_network

HOP = {'host', 'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization', 'te', 'trailer', 'transfer-encoding', 'upgrade', 'content-length', 'content-encoding'}


def create_gateway(store=None, transport=None):
    from services.api.store import Store
    store = store or Store()
    @asynccontextmanager
    async def lifespan(app):
        yield
        await app.state.client.aclose()

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.client = httpx.AsyncClient(transport=transport, timeout=httpx.Timeout(365, connect=15), follow_redirects=False, trust_env=False)
    app.state.store = store
    @app.middleware('http')
    async def boundaries(request, call_next):
        if os.environ.get('FARMTACT_TRUST_FLY_PROXY') == 'true' and request.headers.get('host') == 'farmtact.fly.dev' and request.headers.get('x-forwarded-proto') == 'http':
            return RedirectResponse('https://farmtact.fly.dev' + request.url.path + ('?' + request.url.query if request.url.query else ''), 307)
        if request.url.path.startswith('/_control/'):
            import ipaddress
            try:
                trusted = os.environ.get('FARMTACT_TRUST_FLY_PROXY') == 'true'
                private = trusted and ipaddress.ip_address(client_network(request, True).split('/')[0]).is_private
            except ValueError: private = False
            local = os.environ.get('FARMTACT_LOCAL_EDITIONS') == 'true' and request.client.host == '127.0.0.1' and request.headers.get('host') == 'farmtact-local-control.flycast:8080'
            if not local and (request.headers.get('host') != 'farmtact.flycast' or not private):
                return JSONResponse({'detail': 'Not found'}, 404)
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['Cache-Control'] = 'no-store' if request.url.path.startswith(('/api/', '/_control/')) else response.headers.get('Cache-Control', 'public, max-age=60')
        response.headers['Content-Security-Policy'] = "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; media-src 'self'; frame-ancestors 'none'; base-uri 'self'"
        return response
    # Internal control endpoints are installed independently; they authenticate
    # themselves and expose no game records.
    from services.api.edition_control import install_control_routes
    install_control_routes(app, store)

    @app.get('/api/v1/health')
    def health(): return {'status': 'ok', 'role': 'edition_gateway'}

    @app.get('/api/releases')
    def releases(): return registry()

    @app.get('/api/v1/reviews')
    def reviews():
        import json
        return json.loads((ROOT / 'config/review_panel.json').read_text())

    dist = ROOT / 'apps/web/dist'
    for name in ('assets', 'art', 'review-evidence', 'audio'):
        if (dist / name).is_dir(): app.mount('/' + name, StaticFiles(directory=dist / name), name=name)

    @app.get('/')
    @app.get('/review')
    @app.get('/review/')
    def index(): return FileResponse(dist / 'index.html')

    async def proxy(request, edition, path):
        entries = registry()['editions']
        if not any(e['id'] == edition and e.get('status') == 'published' for e in entries):
            return HTMLResponse('<h1>Edition unavailable</h1><p>This edition is not published.</p><a href="/">Choose an edition</a>', 404)
        secret = os.environ.get('FARMTACT_CONTROL_SECRET', '')
        if not secret: return JSONResponse({'detail': 'Edition routing unavailable'}, 503)
        try: network = client_network(request, os.environ.get('FARMTACT_TRUST_FLY_PROXY') == 'true')
        except ValueError: return JSONResponse({'detail': 'Invalid client address'}, 400)
        # client_network aggregates IPv6 for rate limiting; send a parseable host
        # representation to the backend, whose limiter applies the same grouping.
        network = network.split('/')[0]
        headers = {k: v for k, v in request.headers.items() if k.lower() not in HOP | {'cookie', 'authorization', 'fly-client-ip'} and not k.lower().startswith(('x-farmtact-', 'x-forwarded-'))}
        from urllib.parse import urlsplit
        public_host = urlsplit(os.environ.get('FARMTACT_PUBLIC_ORIGIN', 'https://farmtact.fly.dev')).netloc
        headers.update({'host': public_host, 'x-farmtact-gateway': secret, 'x-farmtact-client-ip': network, 'accept-encoding': 'identity'})
        cookie_name = f'farmtact_{edition}_session'
        cookie = request.cookies.get(cookie_name)
        legacy = edition == 'v1' and not cookie and request.cookies.get('farmtact_session')
        if legacy: cookie = legacy
        if cookie and re.fullmatch(r'[A-Za-z0-9_-]{20,200}', cookie): headers['cookie'] = f'farmtact_session={cookie}'
        body = bytearray()
        try:
            async with asyncio.timeout(15):
                async for chunk in request.stream():
                    body.extend(chunk)
                    if len(body) > 1048576: return JSONResponse({'detail': 'Upload exceeds 1 MiB'}, 413)
        except TimeoutError: return JSONResponse({'detail': 'Request body timed out'}, 408)
        url = upstream(edition).rstrip('/') + '/' + path
        if request.url.query: url += '?' + request.url.query
        try:
            response = await app.state.client.send(app.state.client.build_request(request.method, url, headers=headers, content=bytes(body)), stream=True)
        except httpx.RequestError:
            return JSONResponse({'detail': 'This edition is temporarily unavailable. Your saved farm remains in this edition.'}, 503)
        output_headers = {k: v for k, v in response.headers.items() if k.lower() not in HOP | {'set-cookie'}}
        location = output_headers.get('location')
        if location and location.startswith('/') and not location.startswith('//'): output_headers['location'] = f'/{edition}' + location
        content_type = response.headers.get('content-type', '')
        if 'text/html' in content_type:
            content = (await response.aread()).decode('utf-8')
            # Only generated local asset attributes, never arbitrary source rewriting.
            content = re.sub(r'((?:src|href)=["\'])/(assets|art|audio)/', rf'\1/{edition}/\2/', content)
            await response.aclose()
            result = HTMLResponse(content, response.status_code, headers=output_headers)
        else:
            result = StreamingResponse(response.aiter_bytes(), status_code=response.status_code, headers=output_headers, background=BackgroundTask(response.aclose))
        for raw in response.headers.get_list('set-cookie'):
            parsed = SimpleCookie(); parsed.load(raw)
            if 'farmtact_session' in parsed:
                value = parsed['farmtact_session'].value
                result.set_cookie(cookie_name, value, path=f'/{edition}/', httponly=True, secure=True, samesite='strict', max_age=86400)
        # Migrating the valid legacy session does not mint a new tenant. Only v1
        # bootstrap can accept it; other editions never receive the old cookie.
        if legacy and path == 'api/v1/bootstrap' and response.status_code == 200 and not response.headers.get_list('set-cookie'):
            result.set_cookie(cookie_name, cookie, path='/v1/', httponly=True, secure=True, samesite='strict', max_age=86400)
            result.delete_cookie('farmtact_session', path='/')
        result.headers['X-Farmtact-Edition'] = edition
        return result

    @app.api_route('/{edition}/{path:path}', methods=['GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'])
    async def versioned(request: Request, edition: str, path: str):
        if not re.fullmatch(r'v[1-9][0-9]*', edition): return JSONResponse({'detail': 'Not found'}, 404)
        return await proxy(request, edition, path)

    @app.get('/{edition}')
    def slash(edition: str):
        if re.fullmatch(r'v[1-9][0-9]*', edition): return RedirectResponse(f'/{edition}/', status_code=307)
        return JSONResponse({'detail': 'Not found'}, 404)
    return app
