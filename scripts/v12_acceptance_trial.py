"""Bounded V12 workflow and paired V11/V12 candidate acceptance trial.

Private mode admits only the fixed local V11/V12 ports. Council inference is
disabled unless ``--review`` is explicit; replay never starts another review.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import time
import uuid

import httpx


def hashed(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class API:
    def __init__(self, base: str, private: bool = False):
        self.base = base.rstrip('/'); headers = {}
        if private:
            if self.base not in ('http://127.0.0.1:8091', 'http://127.0.0.1:8092'):
                raise ValueError('Private acceptance admits only fixed V11/V12 ports 8091/8092')
            headers = {'host': 'farmtact.fly.dev', 'origin': 'https://farmtact.fly.dev',
                       'x-farmtact-gateway': os.environ['FARMTACT_CONTROL_SECRET'],
                       'x-farmtact-client-ip': '198.18.0.12'}
        self.client = httpx.Client(headers=headers, timeout=20)
        self.private = private

    def call(self, method, path, body=None, key=None):
        headers = {'Idempotency-Key': key or uuid.uuid4().hex} if method == 'POST' else {}
        response = self.client.request(method, self.base + '/api/v1' + path, json=body, headers=headers)
        if self.private:
            token = self.client.cookies.get('farmtact_session')
            if token: self.client.headers['cookie'] = 'farmtact_session=' + token
        if response.status_code >= 400:
            raise RuntimeError(f'{method} {path}: HTTP {response.status_code}: {response.text[:300]}')
        return response.json()

    def get(self, path): return self.call('GET', path)
    def post(self, path, body=None, key=None): return self.call('POST', path, body, key)
    def close(self): self.client.close()


def wait_session(api, session_id, deadline=180):
    started = time.monotonic(); last = None
    while time.monotonic() - started < deadline:
        last = api.get('/planning-sessions/' + session_id)
        if last.get('status') not in ('DRAFT', 'QUEUED', 'RUNNING', 'CREATED'):
            return last, round(time.monotonic() - started, 4)
        time.sleep(.8)
    raise TimeoutError(f'planning session exceeded {deadline}s; last status {last.get("status") if last else None}')


def journey(api, review=False):
    initial = api.get('/bootstrap'); farm_before = hashed(initial['farm'])
    session = api.post('/planning-sessions', {'name': 'V12 acceptance workflow', 'workflow': True})
    session_path = '/planning-sessions/' + session['id']
    api.post(session_path + '/calculate', {'revision': session['revision']})
    session, calculation_seconds = wait_session(api, session['id'])
    strategies = session.get('result', {}).get('strategies', [])
    selected = session.get('selected_strategy_id') or next((row.get('id') for row in strategies if row.get('status') == 'FEASIBLE'), None)
    checks = {
        'workflow_session': session.get('workflow') is True,
        'calculation_completed': session.get('status') == 'COMPLETED' and len(strategies) == 3,
        'feasible_strategy_selected': bool(selected),
    }
    council = None
    if review:
        api.post(session_path + '/review', {'revision': session['revision']})
        session, council_seconds = wait_session(api, session['id'], 330)
        council = session.get('review')
        checks['actual_council_completed'] = bool(council) and council.get('status') == 'completed'
        checks['actual_council_bounded'] = 0 < (council or {}).get('request_count', 0) <= 7
        council_hash = hashed(council)
        replay = api.get(session_path).get('review')
        checks['council_replay_identical'] = hashed(replay) == council_hash
    else:
        council_seconds = None

    proposal_key = 'proposal-' + uuid.uuid4().hex
    proposal_body = {'session_id': session['id'], 'base_revision': session['revision'],
        'changes': [{'kind': 'planning_assumptions', 'assumptions': {
            'future_demand': [], 'seasonal': [], 'order_changes': [], 'reservations': []}}],
        'selected_strategy_id': selected, 'idempotency_key': proposal_key}
    proposal = api.post('/farm-workflow/proposals', proposal_body, proposal_key)
    duplicate = api.post('/farm-workflow/proposals', proposal_body, proposal_key)
    checks['proposal_idempotent'] = duplicate['id'] == proposal['id']
    apply_key = 'apply-' + uuid.uuid4().hex
    applied = api.post(f'/farm-workflow/proposals/{proposal["id"]}/apply', {
        'proposal_id': proposal['id'], 'expected_base_revision': proposal['base_revision'],
        'idempotency_key': apply_key}, apply_key)
    session, recalculation_seconds = wait_session(api, session['id'])
    checks['apply_recalculated'] = applied['status'] == 'applied' and session['status'] == 'COMPLETED'
    approve_key = 'approve-' + uuid.uuid4().hex
    approved = api.post(f'/farm-workflow/proposals/{proposal["id"]}/approve-actions', {
        'proposal_id': proposal['id'], 'proposal_revision': applied['proposal_revision'],
        'selected_strategy_id': selected, 'idempotency_key': approve_key}, approve_key)
    duplicate_approval = api.post(f'/farm-workflow/proposals/{proposal["id"]}/approve-actions', {
        'proposal_id': proposal['id'], 'proposal_revision': applied['proposal_revision'],
        'selected_strategy_id': selected, 'idempotency_key': approve_key}, approve_key)
    tasks = approved.get('tasks', [])
    checks['approval_idempotent_with_tasks'] = bool(tasks) and hashed(duplicate_approval) == hashed(approved)
    task = next((row for row in tasks if row.get('unit') == 'kg'), tasks[0] if tasks else None)
    if not task: raise RuntimeError('approved strategy created no actions')
    result = api.post(f'/farm-workflow/tasks/{task["id"]}/result', {
        'expected_status': task['status'], 'result_status': 'completed',
        'actual_quantity': task.get('planned_quantity') if task.get('unit') else None,
        'unit': task.get('unit'), 'photo_reference': None,
        'checklist_completed': task['checklist'], 'note': 'Acceptance trial user-reported result'})
    correction_key = 'correction-' + uuid.uuid4().hex
    correction = api.post(f'/farm-workflow/tasks/{task["id"]}/corrections', {
        'expected_event_revision': result['event_revision'], 'field': 'result_note',
        'corrected_value': 'Acceptance trial corrected report', 'reason': 'Verify auditable correction',
        'idempotency_key': correction_key}, correction_key)
    checks['result_recorded'] = result['status'] == 'completed' and result.get('forecast_feedback', {}).get('basis') == 'farmer_reported_unverified'
    checks['correction_audited'] = correction['event_revision'] == result['event_revision'] + 1
    state = api.get('/farm-workflow'); replay_hash = hashed(state)
    checks['workflow_replay_identical'] = hashed(api.get('/farm-workflow')) == replay_hash
    checks['operations_disabled'] = state.get('real_operations_enabled') is False and all(not row.get('real_operations_enabled') for row in tasks)

    outsider = API(api.base, api.private)
    try:
        outsider_state = outsider.get('/farm-workflow')
        owned = {proposal['id'], task['id']}
        visible = {row.get('id') for row in outsider_state.get('proposals', []) + outsider_state.get('tasks', [])}
        checks['tenant_isolation'] = owned.isdisjoint(visible)
    finally:
        outsider.close()
    checks['main_farm_unchanged'] = hashed(api.get('/bootstrap')['farm']) == farm_before
    return {'status': 'PASS' if all(checks.values()) else 'FAIL', 'checks': checks,
            'session_id': session['id'], 'proposal_id': proposal['id'], 'task_id': task['id'],
            'calculation_seconds': calculation_seconds, 'recalculation_seconds': recalculation_seconds,
            'council_seconds': council_seconds, 'council': council,
            'workflow_revision': state.get('revision')}


def capacity(v12_base, v11_base, private):
    results = []
    for trial in range(1, 4):
        v12 = API(v12_base, private); v11 = API(v11_base, private)
        try:
            before12 = hashed(v12.get('/bootstrap')['farm']); before11 = hashed(v11.get('/bootstrap')['farm'])
            s12 = v12.post('/planning-sessions', {'name': f'V12 capacity trial {trial}', 'workflow': True})
            s11 = v11.post('/planning-sessions', {'name': f'V11 retained capacity trial {trial}'})
            started = time.monotonic()
            v12.post(f'/planning-sessions/{s12["id"]}/calculate', {'revision': s12['revision']})
            v11.post(f'/planning-sessions/{s11["id"]}/calculate', {'revision': s11['revision']})
            timings = []; errors = []; done12 = done11 = False
            while time.monotonic() - started < 180 and not (done12 and done11):
                for api in (v12, v11):
                    moment = time.monotonic()
                    try: api.get('/bootstrap')
                    except Exception as exc: errors.append(str(exc))
                    timings.append(time.monotonic() - moment)
                if not done12:
                    value12 = v12.get('/planning-sessions/' + s12['id']); done12 = value12['status'] not in ('QUEUED', 'RUNNING')
                    if done12: seconds12 = time.monotonic() - started
                if not done11:
                    value11 = v11.get('/planning-sessions/' + s11['id']); done11 = value11['status'] not in ('QUEUED', 'RUNNING')
                    if done11: seconds11 = time.monotonic() - started
                if not (done12 and done11): time.sleep(1)
            p95 = sorted(timings)[max(0, math.ceil(.95 * len(timings)) - 1)] if timings else None
            checks = {'browse_p95_under_5s': p95 is not None and p95 < 5,
                'v12_completed_under_180s': done12 and value12['status'] == 'COMPLETED' and seconds12 < 180,
                'v11_completed_under_180s': done11 and value11['status'] == 'COMPLETED' and seconds11 < 180,
                'farms_unchanged': hashed(v12.get('/bootstrap')['farm']) == before12 and hashed(v11.get('/bootstrap')['farm']) == before11,
                'all_browse_successful': not errors}
            for api, value, sid in ((v12, value12, s12['id']), (v11, value11, s11['id'])):
                if value['status'] in ('QUEUED', 'RUNNING'):
                    api.post(f'/planning-sessions/{sid}/cancel', {'revision': value['revision']})
            results.append({'trial': trial, 'status': 'PASS' if all(checks.values()) else 'FAIL',
                'checks': checks, 'browse_p95_seconds': p95, 'browse_samples': len(timings),
                'v12_seconds': seconds12 if done12 else None, 'v11_seconds': seconds11 if done11 else None,
                'errors': errors, 'inference_requests': 0})
        except Exception as exc:
            results.append({'trial': trial, 'status': 'FAIL', 'error': str(exc), 'inference_requests': 0})
        finally:
            v12.close(); v11.close()
    return {'status': 'PASS' if all(row['status'] == 'PASS' for row in results) else 'FAIL', 'trials': results,
            'protocol': 'Three paired V11/V12 numerical jobs; browse p95<5s and both terminal under 180s; zero inference.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:8092')
    parser.add_argument('--old-base-url', default='http://127.0.0.1:8091')
    parser.add_argument('--private-gateway', action='store_true')
    parser.add_argument('--review', action='store_true')
    parser.add_argument('--capacity', action='store_true')
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args(argv); started = datetime.now(timezone.utc).isoformat()
    try:
        if args.capacity:
            if args.review: raise ValueError('Capacity probes must make zero inference calls')
            report = capacity(args.base_url, args.old_base_url, args.private_gateway)
        else:
            api = API(args.base_url, args.private_gateway)
            try: report = journey(api, args.review)
            finally: api.close()
    except Exception as exc:
        report = {'status': 'FAIL', 'error': str(exc)}
    report.update(started_at=started, completed_at=datetime.now(timezone.utc).isoformat(),
                  base_url=args.base_url, old_base_url=args.old_base_url,
                  private_gateway=args.private_gateway, review_requested=args.review)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n'); args.report.chmod(0o600)
    print(json.dumps({key: report[key] for key in ('status', 'error', 'checks', 'trials') if key in report}))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
