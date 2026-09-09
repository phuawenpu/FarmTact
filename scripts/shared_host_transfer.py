"""Fixed-path operator-only logical transfer for immutable edition containers.

Run as farmtact over authenticated SSH, never from HTTP. Copies all public-schema
tables including shared budgets; source and destination use the same exact image.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import tarfile
import psycopg
from psycopg import sql

DIRECTORY = Path('/data/shared-transfer')


def database():
    return 'farmtact_control' if os.environ.get('FARMTACT_ROLE') == 'gateway' else 'farmtact'


def connect():
    return psycopg.connect(host='/tmp/farmtact-pg', user='farmtact', dbname=database())


def fingerprint():
    result = {}
    with connect() as c:
        for (table,) in c.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"):
            rows = c.execute(sql.SQL('SELECT row_to_json(t)::text FROM {} t ORDER BY row_to_json(t)::text').format(sql.Identifier(table))).fetchall()
            result[table] = dict(rows=len(rows),sha256=hashlib.sha256('\n'.join(row[0] for row in rows).encode()).hexdigest())
    return result


def cache_hashes():
    root=Path('/data/public-data')
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file() and not p.is_symlink()}


def freeze():
    pids=[]
    for p in Path('/proc').glob('[0-9]*/cmdline'):
        try:args=p.read_bytes().split(b'\0')
        except (FileNotFoundError,PermissionError):continue
        if any(x in args for x in [b'/app/scripts/serve.py',b'/app/scripts/refresh_news.py',b'/app/scripts/build_dataset.py']):
            pid=int(p.parent.name);os.kill(pid,signal.SIGSTOP);pids.append(pid)
    if not pids:raise RuntimeError('No owned service process found')
    (DIRECTORY/'frozen.json').write_text(json.dumps(pids))
    with connect() as c:
        tables={r[0] for r in c.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")}
        for table in ('planning_runs','scenario_branches','conversation_requests'):
            if table not in tables:continue
            columns={r[0] for r in c.execute('SELECT column_name FROM information_schema.columns WHERE table_name=%s',(table,))}
            if 'status' in columns:
                count=c.execute(sql.SQL("SELECT count(*) FROM {} WHERE status IN ('CREATED','QUEUED','RUNNING')").format(sql.Identifier(table))).fetchone()[0]
                if count:
                    resume();raise RuntimeError('Active jobs resumed; wait for completion before cutover')
    print('Owned writes frozen; no active jobs.')


def resume():
    for pid in json.loads((DIRECTORY/'frozen.json').read_text()):
        try:os.kill(pid,signal.SIGCONT)
        except ProcessLookupError:pass
    print('Owned processes resumed.')


def export():
    if not (DIRECTORY/'frozen.json').exists():raise RuntimeError('Freeze before export')
    subprocess.run(['pg_dump','-h','/tmp/farmtact-pg','-U','farmtact','-Fc','-f',str(DIRECTORY/'database.dump'),database()],check=True)
    evidence=dict(database=database(),tables=fingerprint(),cache=cache_hashes())
    (DIRECTORY/'fingerprint.json').write_text(json.dumps(evidence,indent=2))
    with tarfile.open(DIRECTORY/'cache.tar.gz','w:gz') as t:t.add('/data/public-data',arcname='public-data')
    print('Database, cache and fingerprints exported privately.')


def restore():
    if os.environ.get('FARMTACT_PUBLIC_ORIGIN') != 'http://127.0.0.1:8088' or not os.environ.get('FARMTACT_CONTAINER'):
        raise RuntimeError('Restore requires the private candidate deployment')
    if not (DIRECTORY/'frozen.json').exists():raise RuntimeError('Freeze candidate before restore')
    expected=json.loads((DIRECTORY/'fingerprint.json').read_text())
    if expected['database']!=database():raise RuntimeError('Wrong database kind')
    subprocess.run(['pg_restore','-h','/tmp/farmtact-pg','-U','farmtact','-d',database(),'--clean','--if-exists','--single-transaction','--exit-on-error',str(DIRECTORY/'database.dump')],check=True)
    # Candidate cache is disposable; archive restores source bytes in fixed root.
    import shutil
    for child in Path('/data/public-data').iterdir():
        if child.is_dir() and not child.is_symlink():shutil.rmtree(child)
        else:child.unlink()
    with tarfile.open(DIRECTORY/'cache.tar.gz') as t:
        members=t.getmembers()
        if any(not (m.name=='public-data' or m.name.startswith('public-data/')) or m.issym() or m.islnk() for m in members):
            raise RuntimeError('Unexpected cache archive member')
        t.extractall('/data',filter='data')
    verify()


def verify():
    expected=json.loads((DIRECTORY/'fingerprint.json').read_text())
    if expected['tables']!=fingerprint() or expected['cache']!=cache_hashes():raise RuntimeError('Transfer fingerprint mismatch')
    print('All table rows and cache bytes match source.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','resume','export','restore','verify']);a=p.parse_args();os.umask(0o077)
    if os.geteuid()==0 or not DIRECTORY.is_dir():raise SystemExit('Prepare private owned transfer directory and run as farmtact')
    globals()[a.action]()
