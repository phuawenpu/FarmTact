"""Verify isolated edition APIs and save only private browser authentication state."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
from urllib.parse import urlsplit

import httpx

parser = argparse.ArgumentParser()
parser.add_argument('--url', default='http://127.0.0.1:8080')
parser.add_argument('--report', default='reports/editions/isolation.json')
parser.add_argument('--state', default='/tmp/farmtact-edition-browser-state.json')
parser.add_argument('--legacy-state')
args = parser.parse_args()
report = {'status': 'RUNNING', 'base': args.url, 'checks': []}


def check(name, passed):
    report['checks'].append({'name': name, 'pass': bool(passed)})
    if not passed: raise AssertionError(name)


def digest(value): return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


try:
    with httpx.Client(base_url=args.url, timeout=30, follow_redirects=True) as client:
        check('Root chooser creates no farm session', client.get('/').status_code == 200 and not client.cookies)
        check('Published registry contains v1 and v2', {'v1', 'v2'} <= {e['id'] for e in client.get('/api/releases').json()['editions']})
        check('Private controls are not publicly accessible', client.post('/_control/reserve', json={}).status_code in (401, 404))
        check('Unknown edition never falls back', client.get('/v999/').status_code == 404)
        tokens = {}
        old = json.loads(Path(args.legacy_state).read_text()) if args.legacy_state else None
        for edition in ('v1', 'v2'):
            headers = {'Cookie': f'farmtact_session={old["cookie"]}'} if old and edition == 'v1' else {}
            response = client.get(f'/{edition}/api/v1/bootstrap', headers=headers)
            check(edition + ' bootstrap succeeds', response.status_code == 200)
            tokens[edition] = client.cookies.get(f'farmtact_{edition}_session')
            check(edition + ' uses its own named session', bool(tokens[edition]))
        check('Edition session tokens differ', tokens['v1'] != tokens['v2'])
        def get(edition, path): return client.get(f'/{edition}/api/v1/{path}', headers={'Cookie': f'farmtact_{edition}_session={tokens[edition]}'})
        before = {e: get(e, 'farms/demo-farm/snapshot').json() for e in tokens}
        if old:
            check('Legacy farm preserved in v1', before['v1'] == old['farm'])
            run = get('v1', 'planning-runs/' + old['run_id']).json()
            check('Legacy numerical run preserved', digest(run['strategies']) == old['strategies_hash'])
            scenario = get('v1', 'scenarios/' + old['scenario_id']).json()
            check('Legacy branch result preserved', digest(scenario['result']) == old['scenario_result_hash'])
            check('Legacy conversation preserved', get('v1', 'conversations/' + old['conversation_id']).status_code == 200)
            check('Legacy quest progress preserved', next(q for q in get('v1', 'quests').json()['quests'] if q['id'] == 'tight_budget')['status'] == 'completed')
            check('V2 cannot read legacy run', get('v2', 'planning-runs/' + old['run_id']).status_code == 404)
        response = client.post('/v2/api/v1/data-explorer/snapshots', headers={'Cookie': f'farmtact_v2_session={tokens["v2"]}', 'Idempotency-Key': secrets.token_hex(16)}, json={'name': 'Edition isolation verification', 'generator_settings': {'history_multiplier': 1.12, 'history_trend': 0, 'pattern_amplitude': 1, 'orders_multiplier': 1, 'price_multiplier': 1}, 'forecast_settings': {'alpha': .45}})
        check('V2 saves its own reproducible dataset', response.status_code == 201)
        saved = response.json()
        check('Saved dataset survives reloading v2', get('v2', 'data-explorer/snapshots/' + saved['id']).json()['content_hash'] == saved['content_hash'])
        check('V1 cannot read v2 dataset', get('v1', 'data-explorer/snapshots/' + saved['id']).status_code == 404)
        check('V1 remains unchanged by v2 save', get('v1', 'farms/demo-farm/snapshot').json() == before['v1'])
        check('V2 sandbox save leaves its main farm unchanged', get('v2', 'farms/demo-farm/snapshot').json() == before['v2'])
        swapped = client.get('/v2/api/v1/data-explorer/snapshots', headers={'Cookie': f'farmtact_v2_session={tokens["v1"]}'})
        check('Manually swapped edition credential is rejected', swapped.status_code == 401)
        parsed = urlsplit(args.url)
        state = {'cookies': [{'name': f'farmtact_{e}_session', 'value': t, 'domain': parsed.hostname, 'path': f'/{e}/', 'httpOnly': True, 'secure': parsed.scheme == 'https', 'sameSite': 'Strict', 'expires': -1} for e, t in tokens.items()], 'origins': []}
        fd = os.open(args.state, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'w') as out: json.dump(state, out)
        report['status'] = 'PASS'
except Exception:
    report['status'] = 'FAIL'
    raise
finally:
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'checks': len(report['checks'])}))
