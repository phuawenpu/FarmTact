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
OWNED = [b'/app/scripts/serve.py',b'/app/scripts/fly_boot.py',b'/app/scripts/refresh_news.py',b'/app/scripts/build_dataset.py']


def database():
    return 'farmtact_control' if os.environ.get('FARMTACT_ROLE') == 'gateway' else 'farmtact'


def connect():
    return psycopg.connect(host='/tmp/farmtact-pg', user='farmtact', dbname=database(),connect_timeout=5,options='-c statement_timeout=15000 -c lock_timeout=3000')


def fingerprint():
    result = {}
    with connect() as c:
        for (table,) in c.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"):
            rows = c.execute(sql.SQL('SELECT row_to_json(t)::text FROM {} t ORDER BY row_to_json(t)::text').format(sql.Identifier(table))).fetchall()
            owner=c.execute('SELECT tableowner FROM pg_tables WHERE schemaname=%s AND tablename=%s',('public',table)).fetchone()[0]
            result[table] = dict(rows=len(rows),owner=owner,sha256=hashlib.sha256('\n'.join(row[0] for row in rows).encode()).hexdigest())
    return result


def identity():
    return dict(container=os.environ.get('FARMTACT_CONTAINER') or os.environ.get('FARMTACT_EDITION') or 'gateway',
                source_commit=Path('/app/config/build-source.txt').read_text().strip())


def metadata_hash():
    queries=[
        "SELECT c.relname,c.relkind,pg_get_userbyid(c.relowner),c.relacl::text FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' ORDER BY c.relname,c.relkind",
        "SELECT nspname,pg_get_userbyid(nspowner),nspacl::text FROM pg_namespace WHERE nspname='public'",
        "SELECT proname,pg_get_userbyid(proowner),proacl::text,pg_get_functiondef(oid) FROM pg_proc WHERE pronamespace='public'::regnamespace ORDER BY proname,oid",
        "SELECT pg_get_userbyid(datdba),datacl::text FROM pg_database WHERE datname=current_database()",
    ]
    with connect() as c:
        rows=[c.execute(query).fetchall() for query in queries]
    return hashlib.sha256(json.dumps(rows,default=str,sort_keys=True).encode()).hexdigest()


def cache_hashes():
    root=Path('/data/public-data')
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file() and not p.is_symlink()}


def freeze():
    pids=[]
    try:
        for p in Path('/proc').glob('[0-9]*/cmdline'):
            try:args=p.read_bytes().split(b'\0')
            except (FileNotFoundError,PermissionError):continue
            if any(x in args for x in OWNED):
                pid=int(p.parent.name)
                try:os.kill(pid,signal.SIGSTOP)
                except ProcessLookupError:continue
                pids.append(pid)
        if not pids:raise RuntimeError('No owned service process found')
        record=dict(pids=pids,database=database(),starts={str(pid):(Path('/proc')/str(pid)/'stat').read_text().split()[21] for pid in pids})
        (DIRECTORY/'frozen.json').write_text(json.dumps(record))
        with connect() as c:
            tables={r[0] for r in c.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")}
            for table in ('planning_runs','scenario_branches','conversation_requests'):
                if table not in tables:continue
                columns={r[0] for r in c.execute('SELECT column_name FROM information_schema.columns WHERE table_name=%s',(table,))}
                if 'status' in columns:
                    count=c.execute(sql.SQL("SELECT count(*) FROM {} WHERE status IN ('CREATED','QUEUED','RUNNING')").format(sql.Identifier(table))).fetchone()[0]
                    if count:raise RuntimeError('Active jobs remain; wait for completion before cutover')
    except BaseException:
        for pid in pids:
            try:os.kill(pid,signal.SIGCONT)
            except ProcessLookupError:pass
        (DIRECTORY/'frozen.json').unlink(missing_ok=True)
        raise
    print('Owned writes frozen; no active jobs.')


def resume():
    for pid in json.loads((DIRECTORY/'frozen.json').read_text())['pids']:
        try:os.kill(pid,signal.SIGCONT)
        except ProcessLookupError:pass
    (DIRECTORY/'frozen.json').unlink(missing_ok=True)
    print('Owned processes resumed.')


def require_frozen():
    record=json.loads((DIRECTORY/'frozen.json').read_text())
    if record['database']!=database() or not record['pids']:raise RuntimeError('Wrong frozen database')
    for pid in record['pids']:
        proc=Path('/proc')/str(pid)
        state=next(line for line in (proc/'status').read_text().splitlines() if line.startswith('State:'))
        args=(proc/'cmdline').read_bytes().split(b'\0')
        if state.split()[1]!='T' or (proc/'stat').read_text().split()[21]!=record['starts'][str(pid)] or not any(x in args for x in OWNED):
            raise RuntimeError('Expected currently stopped owned process')


def export():
    require_frozen()
    subprocess.run(['pg_dump','-h','/tmp/farmtact-pg','-U','farmtact','-Fc','-f',str(DIRECTORY/'database.dump'),database()],check=True,timeout=60)
    evidence=dict(database=database(),identity=identity(),metadata_sha256=metadata_hash(),tables=fingerprint(),cache=cache_hashes(),dump_sha256=hashlib.sha256((DIRECTORY/'database.dump').read_bytes()).hexdigest())
    (DIRECTORY/'fingerprint.json').write_text(json.dumps(evidence,indent=2))
    with tarfile.open(DIRECTORY/'cache.tar.gz','w:gz') as t:t.add('/data/public-data',arcname='public-data')
    print('Database, cache and fingerprints exported privately.')


def restore():
    if os.environ.get('FARMTACT_PUBLIC_ORIGIN') != 'http://127.0.0.1:8088' or not os.environ.get('FARMTACT_CONTAINER'):
        raise RuntimeError('Restore requires the private candidate deployment')
    require_frozen()
    expected=json.loads((DIRECTORY/'fingerprint.json').read_text())
    if expected['database']!=database() or expected['identity']!=identity():raise RuntimeError('Wrong edition/source/database identity')
    if hashlib.sha256((DIRECTORY/'database.dump').read_bytes()).hexdigest()!=expected['dump_sha256']:
        raise RuntimeError('Backup digest mismatch')
    with tarfile.open(DIRECTORY/'cache.tar.gz') as archive:
        members=archive.getmembers()
        if any(not (m.name=='public-data' or m.name.startswith('public-data/')) or '..' in Path(m.name).parts or not (m.isfile() or m.isdir()) for m in members):
            raise RuntimeError('Unexpected cache archive member')
        names={str(Path(m.name).relative_to('public-data')) for m in members if m.isfile()}
        if names!=set(expected['cache']):raise RuntimeError('Cache archive coverage mismatch')
        for member in members:
            if member.isfile():
                payload=archive.extractfile(member).read()
                if hashlib.sha256(payload).hexdigest()!=expected['cache'].get(str(Path(member.name).relative_to('public-data'))):
                    raise RuntimeError('Cache archive digest mismatch')
    subprocess.run(['pg_restore' ,'-h','/tmp/farmtact-pg','-U','farmtact','-d',database(),'--clean','--if-exists','--single-transaction','--exit-on-error',str(DIRECTORY/'database.dump')],check=True,timeout=90)
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
    if expected['identity']!=identity() or expected['metadata_sha256']!=metadata_hash() or expected['tables']!=fingerprint() or expected['cache']!=cache_hashes():raise RuntimeError('Transfer fingerprint mismatch')
    print('All table rows and cache bytes match source.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','resume','export','restore','verify']);a=p.parse_args();os.umask(0o077)
    if os.geteuid()==0 or not DIRECTORY.is_dir():raise SystemExit('Prepare private owned transfer directory and run as farmtact')
    globals()[a.action]()
