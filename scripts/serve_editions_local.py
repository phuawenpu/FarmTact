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
os.environ['FARMTACT_CONTROL_SECRET'] = Path('/tmp/farmtact-edition-control-secret').read_text().strip()
os.environ['FARMTACT_PUBLIC_ORIGIN'] = 'http://127.0.0.1:8080'
os.environ['FARMTACT_TRUST_FLY_PROXY'] = 'false'
os.environ['FARMTACT_SECURE_COOKIES'] = 'false'
os.environ['FARMTACT_LOCAL_EDITIONS'] = 'true'
os.environ['FARMTACT_DATABASE_URL'] = f'postgresql+psycopg://sprite@/farmtact_edition_{kind}?host=/tmp/farmtact-pg'
if kind == 'gateway':
    os.environ['FARMTACT_ROLE'] = 'gateway'
    registry = json.loads(Path(os.environ.get('FARMTACT_RELEASE_REGISTRY', root / 'config/releases/registry.json')).read_text())
    os.environ['FARMTACT_EDITION_UPSTREAMS'] = json.dumps({e['id']: f"http://farmtact-local-{e['id']}.flycast:{8080 + int(e['id'][1:])}" for e in registry['editions']})
else:
    os.environ['FARMTACT_EDITION'] = kind
    os.environ['FARMTACT_CONTROL_URL'] = 'http://farmtact-local-control.flycast:8080'
    os.environ['FARMTACT_PORT'] = str(8080 + int(kind[1:]))
runpy.run_path(str(root / 'scripts/serve.py'), run_name='__main__')
