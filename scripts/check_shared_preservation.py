"""Read-only fingerprints of recorded games on the fixed FarmTact shared host.

Only record identifiers and row hashes leave the container, never session cookies
or table contents. Added records are allowed; captured records must be unchanged.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import shlex
import subprocess

ROOT=Path(__file__).resolve().parents[1]
TABLES=[
    'farm_versions','planning_runs','run_events','scenario_branches','quest_progress',
    'conversations','conversation_messages','conversation_requests','conversation_events',
    'explorer_snapshots','council_research_sessions','council_research_jobs',
    'council_research_actions','council_research_history','council_research_action_receipts',
    'simulation_worlds','simulation_events','simulation_receipts','mutation_receipts',
]

def capture(edition):
    code='''import hashlib,json,psycopg
from psycopg import sql
from pathlib import Path
result={"source_commit":Path("/app/config/build-source.txt").read_text().strip(),"tables":{}}
with psycopg.connect(host="/tmp/farmtact-pg",user="farmtact",dbname="farmtact",options="-c statement_timeout=15000") as c:
    existing={r[0] for r in c.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")}
    for table in '''+repr(TABLES)+''':
        if table not in existing:continue
        rows=c.execute(sql.SQL("SELECT row_to_json(t)::text FROM {} t LIMIT 100001").format(sql.Identifier(table))).fetchall()
        if len(rows)>100000:raise RuntimeError("Fingerprint record bound exceeded")
        result["tables"][table]=sorted(hashlib.sha256(row[0].encode()).hexdigest() for row in rows)
print(json.dumps(result))
'''
    cfg=json.loads((ROOT/'config/hosting/shared.json').read_text())
    if cfg['app']!='farmtact' or cfg['machine_id']!='2871575b4544d8':raise RuntimeError('Unexpected host identity')
    cmd=['fly','ssh','console','--app',cfg['app'],'--machine',cfg['machine_id'],'--container',edition,'--command','gosu farmtact python -c '+shlex.quote(code)]
    result=subprocess.run(cmd,capture_output=True,text=True,timeout=90)
    if result.returncode:raise RuntimeError('Read-only preservation probe failed: '+edition)
    return edition,json.loads(result.stdout[result.stdout.index('{'):])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--before',required=True);p.add_argument('--report');a=p.parse_args()
    previous=json.loads(Path(a.before).read_text()) if a.report else None
    editions=list(previous) if previous else [e['id'] for e in json.loads((ROOT/'config/releases/registry.json').read_text())['editions']]
    with ThreadPoolExecutor(max_workers=3) as pool:current=dict(pool.map(capture,editions))
    if previous is None:
        Path(a.before).write_text(json.dumps(current,indent=2)+'\n');print('Captured',len(current),'edition fingerprints.')
    else:
        from collections import Counter
        checks={edition:dict(source_unchanged=current[edition]['source_commit']==old['source_commit'],tables={table:not bool(Counter(hashes)-Counter(current[edition]['tables'].get(table,[]))) for table,hashes in old['tables'].items()},captured_rows=sum(map(len,old['tables'].values()))) for edition,old in previous.items()}
        passed=all(row['source_unchanged'] and all(row['tables'].values()) for row in checks.values())
        Path(a.report).write_text(json.dumps(dict(status='PASS' if passed else 'FAIL',editions=checks,scope='Captured game records preserved; additional records allowed. No cookies or raw rows exported.'),indent=2)+'\n')
        print('PASS' if passed else 'FAIL');raise SystemExit(0 if passed else 1)
