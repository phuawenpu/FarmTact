"""Temporary private 6PN relay used only for pre-cutover capacity checks.

The fixed application port is the only destination. There are no file routes,
configuration endpoints or request-controlled upstreams. Production uses Fly
Proxy and excludes this container.
"""
import os
from pathlib import Path
import pwd
import select
import subprocess
import socket
import socketserver


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        with socket.create_connection(('127.0.0.1', 8080), timeout=5) as upstream:
            self.request.settimeout(180)
            upstream.settimeout(180)
            sockets = [self.request, upstream]
            while True:
                ready, _, _ = select.select(sockets, [], [], 180)
                if not ready:return
                for source in ready:
                    data = source.recv(65536)
                    if not data:return
                    (upstream if source is self.request else self.request).sendall(data)


class Server(socketserver.ThreadingTCPServer):
    address_family=socket.AF_INET6
    daemon_threads=True
    allow_reuse_address=True
    def server_bind(self):
        self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        super().server_bind()


if __name__=='__main__':
    if os.geteuid()!=0:raise RuntimeError('Relay isolation requires root preparation')
    subprocess.run(['umount','/persist'],check=True)
    if Path('/persist').is_mount() or any(Path('/persist').iterdir()):raise RuntimeError('Shared storage remains visible')
    account=pwd.getpwnam('farmtact')
    os.environ.clear()
    os.setgroups([]);os.setgid(account.pw_gid);os.setuid(account.pw_uid)
    with Server(('fly-local-6pn',8080), Handler) as server:server.serve_forever()
