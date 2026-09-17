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
        check('Public root creates no farm session', client.get('/').status_code == 200 and not client.cookies)
        release_response = client.get('/api/releases')
        if release_response.status_code == 404:
            # V14+ intentionally removes release history from public HTTP. The
            # operator CLI retrieves the same immutable bundle over authenticated
            # Fly SSH using the publisher's fixed-origin, fail-closed helper.
            from scripts.publish_edition import remote_active, remote_registry
            history_payload = remote_registry(args.url.rstrip('/'))
            active_manifest = remote_active(args.url.rstrip('/'))
            wanted = {item for item in active_manifest.values() if item}
            active_payload = {
                **active_manifest,
                'editions': [row for row in history_payload['editions'] if row['id'] in wanted],
            }
        else:
            check('Public release metadata succeeds before latest-only mode', release_response.status_code == 200)
            active_payload = release_response.json()
            history_payload = client.get('/api/releases/history').json()
        active = [entry['id'] for entry in active_payload['editions']]
        expected = [edition for edition in (active_payload.get('previous'), active_payload.get('latest')) if edition]
        check('Public registry exposes exactly the active editions', active == expected and 1 <= len(active) <= 2)
        history = [entry['id'] for entry in history_payload['editions']]
        latest_only = int(active_payload['latest'][1:]) >= 14
        check('V14+ has one latest public runtime', not latest_only or active == [active_payload['latest']])
        check('Immutable history remains contiguous through latest',
              history == [f'v{i}' for i in range(1, len(history) + 1)]
              and history_payload['latest'] == history[-1] == active_payload['latest'])
        retired = [edition for edition in history if edition not in active]
        if retired:
            retired_id = retired[-1]
            gone = client.get(f'/{retired_id}/api/v1/bootstrap')
            check('Retired edition read returns 410 with a safe destination',
                  gone.status_code == 410 and (
                      (latest_only and gone.text.count('<a ') == 1 and 'href="/"' in gone.text)
                      or (not latest_only and all(f'/{edition}/' in gone.text for edition in active))))
            check('Retired edition mutation returns 410',
                  client.post(f'/{retired_id}/api/v1/planning-sessions', json={}).status_code == 410)
        check('Private controls are not publicly accessible', client.post('/_control/reserve', json={}).status_code in (401, 404))
        check('Unknown edition never falls back', client.get('/v999/').status_code == 404)
        tokens = {}
        workspaces = {}
        old = json.loads(Path(args.legacy_state).read_text()) if args.legacy_state else None
        for edition in active:
            headers = {'Cookie': f'farmtact_session={old["cookie"]}'} if old and edition == active[0] else {}
            api = '/api/v1' if latest_only and edition == active_payload['latest'] else f'/{edition}/api/v1'
            response = client.get(f'{api}/bootstrap', headers=headers)
            check(edition + ' bootstrap succeeds', response.status_code == 200)
            workspaces[edition] = response.json()
            tokens[edition] = client.cookies.get(f'farmtact_{edition}_session')
            check(edition + ' uses its own named session', bool(tokens[edition]))
        if len(active) == 2:
            check('Edition session tokens differ', tokens[active[0]] != tokens[active[1]])
        def api_path(edition, path):
            prefix = '/api/v1' if latest_only and edition == active_payload['latest'] else f'/{edition}/api/v1'
            return f'{prefix}/{path}'
        def get(edition, path): return client.get(api_path(edition, path), headers={'Cookie': f'farmtact_{edition}_session={tokens[edition]}'})
        before = {e: get(e, 'farms/demo-farm/snapshot').json() for e in tokens}
        if old:
            retained = active[0]
            check('Legacy farm preserved in retained previous edition', workspaces[retained]['farm'] == old['farm'])
            run = get(retained, 'planning-runs/' + old['run_id']).json()
            check('Legacy numerical run preserved', digest(run['strategies']) == old['strategies_hash'])
            scenario = get(retained, 'scenarios/' + old['scenario_id']).json()
            check('Legacy branch result preserved', digest(scenario['result']) == old['scenario_result_hash'])
            check('Legacy conversation preserved', get(retained, 'conversations/' + old['conversation_id']).status_code == 200)
            check('Legacy quest progress preserved', next(q for q in get(retained, 'quests').json()['quests'] if q['id'] == 'tight_budget')['status'] == 'completed')
            if len(active) == 2:
                check('Latest cannot read previous legacy run', get(active[-1], 'planning-runs/' + old['run_id']).status_code == 404)
        latest = active[-1]
        response = client.post(api_path(latest, 'data-explorer/snapshots'), headers={'Cookie': f'farmtact_{latest}_session={tokens[latest]}', 'Idempotency-Key': secrets.token_hex(16)}, json={'name': 'Edition isolation verification', 'generator_settings': {'history_multiplier': 1.12, 'history_trend': 0, 'pattern_amplitude': 1, 'orders_multiplier': 1, 'price_multiplier': 1}, 'forecast_settings': {'alpha': .45}})
        check('Latest saves its own reproducible dataset', response.status_code == 201)
        saved = response.json()
        check('Saved dataset survives reloading latest', get(latest, 'data-explorer/snapshots/' + saved['id']).json()['content_hash'] == saved['content_hash'])
        check('Latest sandbox save leaves its main farm unchanged', get(latest, 'farms/demo-farm/snapshot').json() == before[latest])
        if len(active) == 2:
            previous = active[0]
            check('Previous cannot read latest dataset', get(previous, 'data-explorer/snapshots/' + saved['id']).status_code == 404)
            check('Previous remains unchanged by latest save', get(previous, 'farms/demo-farm/snapshot').json() == before[previous])
            swapped = client.get(f'/{latest}/api/v1/data-explorer/snapshots', headers={'Cookie': f'farmtact_{latest}_session={tokens[previous]}'})
            check('Manually swapped edition credential is rejected', swapped.status_code == 401)
        parsed = urlsplit(args.url)
        state = {'cookies': [{'name': f'farmtact_{e}_session', 'value': t, 'domain': parsed.hostname, 'path': '/' if latest_only and e == active_payload['latest'] else f'/{e}/', 'httpOnly': True, 'secure': parsed.scheme == 'https', 'sameSite': 'Strict', 'expires': -1} for e, t in tokens.items()], 'origins': []}
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
