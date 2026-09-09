"""Process egress policy for the demo; production also needs OS-level policy.

Only DeepSeek HTTPS and the explicitly configured PostgreSQL destination may
connect. Ingestion runs in a separate process. Unix database sockets are local.
"""
import os
import socket
import sys
import threading
from urllib.parse import urlsplit


def install():
    original = socket.getaddrinfo
    database = urlsplit(os.environ.get('FARMTACT_DATABASE_URL', ''))
    database_host = database.hostname if database.scheme.startswith('postgresql') else None
    database_port = database.port or 5432
    destinations = {'api.deepseek.com': 443}
    # Edition/control hosts are deployment-owned infrastructure, not providers.
    # Only a validated registry id can select a private game upstream.
    if os.environ.get('FARMTACT_ROLE') == 'gateway':
        from services.api.release_registry import registry, upstream
        for entry in registry()['editions']:
            target = urlsplit(upstream(entry['id']))
            destinations[target.hostname] = target.port or 80
    if os.environ.get('FARMTACT_CONTROL_URL'):
        control = urlsplit(os.environ['FARMTACT_CONTROL_URL'])
        if control.scheme != 'http' or not control.hostname or not control.hostname.endswith('.flycast') or control.username or control.password or control.query or control.fragment or control.path not in ('', '/'):
            raise ValueError('Invalid internal control destination')
        destinations[control.hostname] = control.port or (443 if control.scheme == 'https' else 80)
    if database_host:
        if database_host == 'api.deepseek.com':
            raise ValueError('Database and inference destinations must differ')
        destinations[database_host] = database_port
    addresses = {host: set() for host in destinations}
    lock = threading.Lock()

    def resolve(host, port, *args, **kwargs):
        hostname = host.decode('ascii') if isinstance(host, bytes) else host
        if hostname not in destinations and os.environ.get('FARMTACT_ROLE') == 'gateway':
            # New editions can be published atomically without rebuilding the
            # chooser. Recheck only the deployment-owned, validated registry.
            from services.api.release_registry import registry, upstream
            for entry in registry()['editions']:
                candidate = urlsplit(upstream(entry['id']))
                if candidate.hostname == hostname:
                    with lock:
                        destinations[hostname] = candidate.port or 80
                        addresses.setdefault(hostname, set())
                    break
        if hostname not in destinations and hostname not in ('0.0.0.0', None):
            raise PermissionError('Outbound hostname is not permitted for the inference service')
        result = original(host, port, *args, **kwargs)
        if hostname in destinations:
            with lock:
                addresses[hostname].update(row[4][0] for row in result)
        return result

    def audit(event, args):
        if event != 'socket.connect':
            return
        sock, address = args
        if sock.family == socket.AF_UNIX:
            return
        if not isinstance(address, tuple) or len(address) < 2:
            raise PermissionError('Unsupported outbound address')
        host, port = address[:2]
        with lock:
            allowed = any(port == target_port and (host == name or host in addresses[name])
                          for name, target_port in destinations.items())
        if not allowed:
            raise PermissionError('Outbound destination is not permitted for the inference service')

    socket.getaddrinfo = resolve
    sys.addaudithook(audit)
