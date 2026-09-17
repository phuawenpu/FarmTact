"""Bounded V15 sandbox trial; operator authentication never leaves loopback.

This exercises real numerical and stored workflow consequences without any AI
submission. Browser/card acceptance is a separate release gate.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time
from uuid import uuid4

import httpx


def run(base: str, operator: bool = False, output: Path | None = None) -> dict:
    if operator and base != 'http://127.0.0.1:8095':
        raise ValueError('Operator trial permits only the fixed V15 candidate port')
    headers = {}
    if operator:
        headers = {'host': 'farmtact.fly.dev', 'origin': 'https://farmtact.fly.dev',
                   'x-farmtact-gateway': os.environ['FARMTACT_CONTROL_SECRET'],
                   'x-farmtact-client-ip': '127.0.0.1'}
    report = {'status': 'RUNNING', 'checks': [], 'mutations': [], 'provider_submissions': 0}

    def save():
        if output:
            output.write_text(json.dumps(report, indent=2) + '\n')

    def check(name, condition):
        report['checks'].append({'name': name, 'pass': bool(condition)})
        save()
        if not condition:
            raise AssertionError(name)

    with httpx.Client(base_url=base, headers=headers, timeout=45, trust_env=False) as client:
        def request(method, path, body=None, key=None):
            if method == 'POST':
                report['mutations'].append(path)
            response = client.request(method, '/api/v1' + path, json=body,
                                      headers={'Idempotency-Key': key or uuid4().hex} if method == 'POST' else {})
            if response.status_code == 429:
                raise RuntimeError('Admission wait required; Retry-After=' + response.headers.get('Retry-After', 'unspecified'))
            response.raise_for_status()
            if operator and path == '/bootstrap':
                token = client.cookies.get('farmtact_session')
                if not token:
                    raise AssertionError('Candidate did not issue its operator trial cookie')
                client.headers['cookie'] = 'farmtact_session=' + token
            return response.json()

        get = lambda path: request('GET', path)
        post = lambda path, body, key=None: request('POST', path, body, key)

        def ready(session_id):
            deadline = time.monotonic() + 240
            while time.monotonic() < deadline:
                value = get('/planning-sessions/' + session_id)
                if value['status'] not in ('QUEUED', 'RUNNING'):
                    check('Local numerical job completed', value['status'] == 'COMPLETED')
                    return value
                time.sleep(1)
            raise TimeoutError('Candidate local calculation exceeded 240 seconds')

        def proposal(session, assumptions):
            key = uuid4().hex
            body = {'session_id': session['id'], 'base_revision': session['revision'],
                    'selected_strategy_id': session['selected_strategy_id'],
                    'changes': [{'kind': 'planning_assumptions', 'assumptions': assumptions}],
                    'idempotency_key': key}
            draft = post('/farm-workflow/proposals', body, key)
            check('Proposal creation is idempotent', post('/farm-workflow/proposals', body, key)['id'] == draft['id'])
            key = uuid4().hex
            post('/farm-workflow/proposals/' + draft['id'] + '/apply',
                 {'proposal_id': draft['id'], 'expected_base_revision': draft['base_revision'], 'idempotency_key': key}, key)
            return draft['id'], ready(session['id'])

        try:
            bootstrap = get('/bootstrap')
            farm = bootstrap['farm']
            check('Ordinary general demo farm retained', len(farm['beds']) > 4 and len(farm['orders']) > 1)
            session = post('/planning-sessions', {'name': 'V15 private acceptance', 'workflow': True})
            report['session_id'] = session['id']; save()
            path = '/planning-sessions/' + session['id']
            original_revision = session['revision']
            planning_farm = session['farm']
            check('Workflow retains every ordinary farm entity', {b['id'] for b in planning_farm['beds']} == {b['id'] for b in farm['beds']} and {o['id'] for o in planning_farm['orders']} == {o['id'] for o in farm['orders']})
            for skipped in (True, False):
                session = post(path + '/guidance', {'revision': session['guidance']['revision'], 'step': 'inspect', 'skipped': skipped})
                check('Guidance preserves the farm and planner revision', session['revision'] == original_revision and session['farm'] == planning_farm)
            session = post(path + '/calculate', {'revision': session['revision']})
            session = ready(session['id'])
            original_result = session['result_id']
            check('All strategies and demand remain available', {s['name'] for s in session['result']['strategies']} == {'Lean', 'Balanced', 'Resilient'} and session['farm']['orders'] == planning_farm['orders'])
            grow = session['tactical_context']['grow_space']
            reservation = {'bed_id': grow['id'], **grow['reservation_window']}
            proposal_id, session = proposal(session, {'reservations': [reservation]})
            saved = next(p for p in get('/farm-workflow')['proposals'] if p['id'] == proposal_id)
            explanation = saved['explanation']
            check('Saved explanation binds both results and affected beds', explanation['evidence']['before_result_id'] == original_result and explanation['evidence']['after_result_id'] == session['result_id'] and bool(explanation['affected_bed_ids']))
            check('Exact inverse is eligible before dependent work', saved['undo']['available'])
            key = uuid4().hex
            inverse = post('/farm-workflow/proposals/' + proposal_id + '/inverse',
                           {'proposal_id': proposal_id, 'proposal_revision': saved['proposal_revision'], 'expected_session_revision': session['revision'], 'idempotency_key': key}, key)
            session = ready(session['id'])
            check('Inverse is an append-only compensating proposal', inverse['inverse_of_proposal_id'] == proposal_id and not session['assumptions'].get('reservations'))
            approved_id, session = proposal(session, {})
            saved = next(p for p in get('/farm-workflow')['proposals'] if p['id'] == approved_id)
            check('Server permits current sandbox approval', saved['approval']['available'])
            key = uuid4().hex
            body = {'proposal_id': approved_id, 'proposal_revision': saved['proposal_revision'],
                    'selected_strategy_id': saved['approval']['strategy_id'], 'idempotency_key': key}
            approved = post('/farm-workflow/proposals/' + approved_id + '/approve-actions', body, key)
            replay = post('/farm-workflow/proposals/' + approved_id + '/approve-actions', body, key)
            check('Approval creates sandbox tasks exactly once', bool(approved['tasks']) and replay == approved and all(t['real_operations_enabled'] is False for t in approved['tasks']))
            session = get(path)
            session = post(path + '/advance', {'revision': session['revision'], 'days': 7})
            world = session['simulation']
            check('Clock advance records authoritative scene facts', world['days_executed'] == 7 and world['scene_transition']['outcome_basis'] == 'recorded_simulation' and bool(world['scene_transition']['event_id']))
            task = next(t for t in approved['tasks'] if t['action'] == 'delivery')
            result = post('/farm-workflow/tasks/' + task['id'] + '/result',
                          {'expected_status': task['status'], 'result_status': 'completed',
                           'actual_quantity': task['planned_quantity'], 'rejected_quantity': 0,
                           'unit': 'kg', 'checklist_completed': task['checklist'], 'note': 'Operator trial: synthetic report'})
            key = uuid4().hex
            correction = post('/farm-workflow/tasks/' + task['id'] + '/corrections',
                              {'expected_event_revision': result['event_revision'], 'field': 'note',
                               'corrected_value': 'Operator trial: corrected synthetic report',
                               'reason': 'Verify append-only correction', 'idempotency_key': key}, key)
            check('Delivery report and correction retain separate revisions', correction['event_revision'] == result['event_revision'] + 1)
            frozen = get(path + '/results/' + original_result)
            check('Original result still replays read-only', frozen['result_id'] == original_result and frozen['replay'] and frozen['inference_triggered'] is False)
            check('Bootstrap farm remains unchanged', get('/bootstrap')['farm'] == farm)
            report['status'] = 'PASS'
        except Exception as error:
            report.update(status='FAIL', error=str(error))
        finally:
            save()
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', default='http://127.0.0.1:4194')
    parser.add_argument('--operator', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = run(args.base_url.rstrip('/'), args.operator, args.output)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['status'] == 'PASS' else 1)
