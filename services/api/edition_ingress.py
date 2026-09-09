"""Edition backends accept only authenticated gateway traffic (health is read-only)."""
import hmac
import os
from starlette.responses import JSONResponse


class EditionIngress:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        edition = os.environ.get('FARMTACT_EDITION')
        if scope['type'] != 'http' or not edition or scope['path'] == '/api/v1/health':
            return await self.app(scope, receive, send)
        headers = dict(scope['headers'])
        expected = os.environ.get('FARMTACT_CONTROL_SECRET', '')
        supplied = headers.get(b'x-farmtact-gateway', b'').decode('ascii', errors='ignore')
        if not expected or not hmac.compare_digest(expected, supplied):
            return await JSONResponse({'detail': 'Edition gateway required'}, 403)(scope, receive, send)
        # Flycast's client is the gateway; only the authenticated gateway can relay
        # the original public peer. Never trust an external forwarded header.
        forwarded = headers.get(b'x-farmtact-client-ip', b'')
        scope = dict(scope)
        scope['headers'] = [(k, v) for k, v in scope['headers'] if k not in (b'fly-client-ip', b'x-farmtact-gateway', b'x-farmtact-client-ip')]
        scope['headers'].append((b'fly-client-ip', forwarded))
        return await self.app(scope, receive, send)
