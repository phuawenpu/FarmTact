"""Bounded v1 cutover helper, run as farmtact on an owned Fly machine.

Backups never enter the repository or public HTTP directories. It only handles
fixed application database/cache locations; no request can invoke this script.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tarfile

import psycopg
from psycopg import sql

DIRECTORY = Path('/data/edition-transfer')
DATABASE = 'host=/tmp/farmtact-pg user=farmtact dbname=farmtact'
CONTROL = {'inference_budget', 'abuse_rate_counters', 'abuse_security_settings', 'edition_control_reservations', 'edition_control_releases'}


def fingerprint():
    result = {}
    with psycopg.connect(DATABASE) as connection:
        tables = connection.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").fetchall()
        for (table,) in tables:
            if table in CONTROL: continue
            rows = connection.execute(sql.SQL('SELECT row_to_json(t)::text FROM {} t ORDER BY row_to_json(t)::text').format(sql.Identifier(table))).fetchall()
            value = '\n'.join(row[0] for row in rows).encode()
            result[table] = {'rows': len(rows), 'sha256': hashlib.sha256(value).hexdigest()}
    return result


def freeze():
    with psycopg.connect(DATABASE) as connection:
        tables = {row[0] for row in connection.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")}
        for table in ('planning_runs', 'scenario_branches', 'conversation_requests'):
            if table not in tables: continue
            columns = {row[0] for row in connection.execute('SELECT column_name FROM information_schema.columns WHERE table_name=%s', (table,))}
            if 'status' in columns:
                count = connection.execute(sql.SQL("SELECT count(*) FROM {} WHERE status IN ('CREATED','QUEUED','RUNNING')").format(sql.Identifier(table))).fetchone()[0]
                if count: raise RuntimeError('Active jobs must finish before cutover')
    processes = []
    for directory in Path('/proc').iterdir():
        if not directory.name.isdigit(): continue
        try: args = (directory / 'cmdline').read_bytes().split(b'\0')
        except (FileNotFoundError, PermissionError): continue
        if b'/app/scripts/serve.py' in args:
            processes.append(int(directory.name))
    if len(processes) != 1: raise RuntimeError('Expected one owned application process')
    os.kill(processes[0], signal.SIGSTOP)
    (DIRECTORY / 'frozen.json').write_text(json.dumps(processes))
    print('Application writes paused after active-job check.')


def resume():
    for pid in json.loads((DIRECTORY / 'frozen.json').read_text()):
        try: os.kill(pid, signal.SIGCONT)
        except ProcessLookupError: pass
    print('Owned application process resumed.')


def export():
    if not (DIRECTORY / 'frozen.json').is_file(): raise RuntimeError('Freeze before export')
    subprocess.run(['pg_dump', '-h', '/tmp/farmtact-pg', '-U', 'farmtact', '-Fc', '-f', str(DIRECTORY / 'farm.dump'), 'farmtact'], check=True)
    (DIRECTORY / 'fingerprint.json').write_text(json.dumps(fingerprint(), indent=2))
    with tarfile.open(DIRECTORY / 'public-cache.tar.gz', 'w:gz') as archive:
        archive.add('/data/public-data', arcname='public-data')
    print('Created fixed-path database backup, cache archive and game-table fingerprints.')


def restore():
    if not os.environ.get('FARMTACT_EDITION') == 'v1': raise RuntimeError('Restore is restricted to the initial v1 deployment')
    expected = json.loads((DIRECTORY / 'fingerprint.json').read_text())
    current = fingerprint()
    if any(value['rows'] for value in current.values()):
        if current == expected:
            print('Verified prior restore; no overwrite performed.'); return
        raise RuntimeError('Refusing to overwrite a nonempty edition database')
    subprocess.run(['pg_restore', '-h', '/tmp/farmtact-pg', '-U', 'farmtact', '-d', 'farmtact', '--clean', '--if-exists', '--single-transaction', '--exit-on-error', str(DIRECTORY / 'farm.dump')], check=True)
    with tarfile.open(DIRECTORY / 'public-cache.tar.gz', 'r:gz') as archive:
        archive.extractall('/data', filter='data')
    if fingerprint() != expected: raise RuntimeError('Restored game-table fingerprints do not match')
    print('Restored v1 database and cache; all game-table counts and hashes match.')


def control():
    if os.environ.get('FARMTACT_EDITION'): raise RuntimeError('Control migration runs only on the original gateway machine')
    with psycopg.connect('host=/tmp/farmtact-pg user=farmtact dbname=postgres', autocommit=True) as connection:
        if not connection.execute("SELECT 1 FROM pg_database WHERE datname='farmtact_control'").fetchone():
            connection.execute('CREATE DATABASE farmtact_control')
    sys.path.insert(0, '/app')
    from services.api.store import Store
    Store('postgresql+psycopg://farmtact@/farmtact_control?host=/tmp/farmtact-pg')
    copied = {}
    with psycopg.connect(DATABASE) as source, psycopg.connect('host=/tmp/farmtact-pg user=farmtact dbname=farmtact_control') as target:
        for table in ('inference_budget', 'abuse_security_settings', 'abuse_rate_counters'):
            rows = source.execute(sql.SQL('SELECT * FROM {}').format(sql.Identifier(table))).fetchall()
            if target.execute(sql.SQL('SELECT count(*) FROM {}').format(sql.Identifier(table))).fetchone()[0]:
                raise RuntimeError('Refusing to overwrite existing shared operational counters')
            if rows:
                with target.cursor() as cursor:
                    cursor.executemany(sql.SQL('INSERT INTO {} VALUES ({})').format(sql.Identifier(table), sql.SQL(',').join(sql.Placeholder() for _ in rows[0])), rows)
            copied[table] = len(rows)
    print('Preserved operational counters in separate control database; no farm rows copied.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['freeze', 'resume', 'export', 'restore', 'verify', 'control'])
    args = parser.parse_args(); os.umask(0o077)
    if not DIRECTORY.is_dir(): raise SystemExit('Prepare owned private transfer directory first')
    if args.action == 'verify':
        assert fingerprint() == json.loads((DIRECTORY / 'fingerprint.json').read_text())
        print('All game-table counts and hashes match the source backup.')
    else: globals()[args.action]()
