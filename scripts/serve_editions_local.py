"""Local Sprite service launcher. The private control secret is never an argument."""
import json
import os
from pathlib import Path
import runpy
import re
import sys

root = Path(__file__).resolve().parents[1]
kind = sys.argv[1]
if kind != 'gateway' and not re.fullmatch(r'v[1-9][0-9]?', kind): raise SystemExit('Unknown local service')
registry = json.loads(Path(os.environ.get('FARMTACT_RELEASE_REGISTRY', root / 'config/releases/registry.json')).read_text())
active = json.loads(Path(os.environ.get('FARMTACT_ACTIVE_EDITIONS', root / 'config/releases/active.json')).read_text())
if set(active) != {'previous', 'latest'}:
    raise SystemExit('Invalid active-edition manifest')
history_ids = {entry['id'] for entry in registry['editions']}
active_ids = [edition for edition in (active['previous'], active['latest']) if edition]
if not active_ids or any(edition not in history_ids for edition in active_ids):
    raise SystemExit('Active edition is absent from release history')
staged = os.environ.get('FARMTACT_STAGED_EDITION')
runtime_ids = [*active_ids, *([staged] if staged else [])]
if staged and (staged in history_ids or not re.fullmatch(r'v[1-9][0-9]?', staged)
               or int(staged[1:]) != len(registry['editions']) + 1):
    raise SystemExit('Invalid staged edition')
if kind != 'gateway' and kind not in runtime_ids:
    raise SystemExit('Edition is retired or not staged')
os.environ['FARMTACT_CONTROL_SECRET'] = Path('/tmp/farmtact-edition-control-secret').read_text().strip()
os.environ['FARMTACT_PUBLIC_ORIGIN'] = 'http://127.0.0.1:8080'
os.environ['FARMTACT_TRUST_FLY_PROXY'] = 'false'
os.environ['FARMTACT_SECURE_COOKIES'] = 'false'
os.environ['FARMTACT_LOCAL_EDITIONS'] = 'true'
os.environ['FARMTACT_DATABASE_URL'] = f'postgresql+psycopg://sprite@/farmtact_edition_{kind}?host=/tmp/farmtact-pg'
if kind == 'gateway':
    os.environ['FARMTACT_ROLE'] = 'gateway'
    os.environ['FARMTACT_EDITION_UPSTREAMS'] = json.dumps({edition: f"http://farmtact-local-{edition}.flycast:{8080 + int(edition[1:])}" for edition in runtime_ids})
else:
    os.environ['FARMTACT_EDITION'] = kind
    os.environ['FARMTACT_CONTROL_URL'] = 'http://farmtact-local-control.flycast:8080'
    os.environ['FARMTACT_PORT'] = str(8080 + int(kind[1:]))
runpy.run_path(str(root / 'scripts/serve.py'), run_name='__main__')
