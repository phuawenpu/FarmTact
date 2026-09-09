"""Supervise the single-instance Fly development app and local PostgreSQL.

The persistent volume holds the database and public snapshots. The web process
retains its own egress policy; public ingestion runs separately without secrets.
"""
from __future__ import annotations

import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
PGDATA = Path('/data/postgres')
SOCKET = '/tmp/farmtact-pg'
SECRET_NAMES = ('DEEPSEEK_API_KEY', 'GH_TOKEN', 'GITHUB_TOKEN', 'FLY_API_TOKEN',
                'FLY_ACCESS_TOKEN', 'MOONSHOT_API_KEY', 'MINIMAX_API_KEY', 'FARMTACT_CONTROL_SECRET')


def public_environment():
    env = os.environ.copy()
    for name in SECRET_NAMES:
        env.pop(name, None)
    return env


def web_environment():
    env = public_environment()
    if os.environ.get('DEEPSEEK_API_KEY') and os.environ.get('FARMTACT_ROLE') != 'gateway':
        env['DEEPSEEK_API_KEY'] = os.environ['DEEPSEEK_API_KEY']
    if os.environ.get('FARMTACT_CONTROL_SECRET') and (os.environ.get('FARMTACT_EDITION') or os.environ.get('FARMTACT_ROLE') == 'gateway'):
        env['FARMTACT_CONTROL_SECRET'] = os.environ['FARMTACT_CONTROL_SECRET']
    return env


def postgres_command():
    return ['postgres', '-D', str(PGDATA), '-c', 'listen_addresses=',
            '-c', f'unix_socket_directories={SOCKET}', '-c', 'shared_buffers=128MB',
            '-c', 'max_connections=40', '-c', 'log_min_error_statement=panic']


def stop_process(process, timeout=15, sig=signal.SIGTERM):
    if process is None or process.poll() is not None:
        return
    process.send_signal(sig)
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main():
    if os.geteuid() == 0:
        raise RuntimeError('Fly runtime must run as the unprivileged farmtact user')
    stopping = False
    def on_stop(signum, frame):
        nonlocal stopping
        stopping = True
    signal.signal(signal.SIGTERM, on_stop)
    signal.signal(signal.SIGINT, on_stop)
    PGDATA.mkdir(parents=True, exist_ok=True)
    for part in ('raw', 'normalized', 'manifests', 'reports', 'runtime'):
        (Path('/data/public-data') / part).mkdir(parents=True, exist_ok=True)
    safe_env = public_environment()
    if not (PGDATA / 'PG_VERSION').exists():
        # initdb refuses a nonempty unknown directory; never overwrite it.
        subprocess.run(['initdb', '-D', str(PGDATA), '--username=farmtact',
                        '--auth-local=peer', '--auth-host=reject', '--encoding=UTF8',
                        '--no-locale'], check=True, env=safe_env, timeout=45)
    elif (PGDATA / 'PG_VERSION').read_text().strip() != '18':
        raise RuntimeError('Existing PostgreSQL major version requires an explicit migration')
    if stopping:
        return 0
    database = web = refresh = None
    try:
        database = subprocess.Popen(postgres_command(), env=safe_env)
        deadline = time.monotonic() + 30
        while not stopping:
            if database.poll() is not None:
                raise RuntimeError('PostgreSQL exited during startup')
            ready = subprocess.run(['pg_isready', '-h', SOCKET, '-U', 'farmtact', '-d', 'postgres'],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   env=safe_env, timeout=3)
            if ready.returncode == 0:
                break
            if time.monotonic() > deadline:
                raise RuntimeError('PostgreSQL readiness deadline exceeded')
            time.sleep(.2)
        if stopping:
            return 0
        exists = subprocess.run(['psql', '-h', SOCKET, '-U', 'farmtact', '-d', 'postgres',
                                 '-Atc', "SELECT 1 FROM pg_database WHERE datname='farmtact'"],
                                capture_output=True, text=True, check=True, env=safe_env, timeout=10)
        if stopping:
            return 0
        if exists.stdout.strip() != '1':
            subprocess.run(['createdb', '-h', SOCKET, '-U', 'farmtact', 'farmtact'],
                           check=True, env=safe_env, timeout=15)
        if stopping:
            return 0
        subprocess.run([sys.executable, str(ROOT / 'scripts/initialize_database.py')],
                       cwd=ROOT, check=True, env={k:v for k,v in safe_env.items() if k not in ('FARMTACT_EDITION','FARMTACT_CONTROL_URL')}, timeout=30)
        if stopping:
            return 0
        web = subprocess.Popen([sys.executable, str(ROOT / 'scripts/serve.py')], cwd=ROOT, env=web_environment())
        if stopping:
            return 0
        # One bounded public refresh per boot. Existing snapshots survive restarts;
        # failed/missing sources stay visibly unavailable or stale in the UI.
        if not os.environ.get('FARMTACT_EDITION') and os.environ.get('FARMTACT_ROLE') != 'gateway':
            refresh = subprocess.Popen([sys.executable, str(ROOT / 'scripts/build_dataset.py'),
                                        '--with-power'], cwd=ROOT, env=safe_env)
        refresh_deadline = time.monotonic() + 120
        while not stopping:
            if database.poll() is not None or web.poll() is not None:
                raise RuntimeError('A required Fly service exited')
            if refresh and refresh.poll() is None and time.monotonic() > refresh_deadline:
                stop_process(refresh, timeout=2)
                print('Public refresh deadline reached; cached/unavailable provenance retained.', flush=True)
            time.sleep(.5)
        return 0
    finally:
        stop_process(refresh, timeout=2)
        stop_process(web, timeout=20)
        stop_process(database, timeout=15, sig=signal.SIGINT)


if __name__ == '__main__':
    raise SystemExit(main())
