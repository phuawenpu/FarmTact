"""Bounded first-season acceptance against a running application.

Operator mode runs inside the private gateway container. It authenticates only
the fixed local candidate worker and never prints credentials, cookies or headers.
"""
import argparse
import json
import os
import time
from uuid import uuid4

import httpx


def run(base: str, operator: bool = False) -> dict:
    if operator and base != 'http://127.0.0.1:8094':
        raise ValueError('Operator trial permits only the fixed V14 candidate port')
    headers = {}
    if operator:
        headers = {'host': 'farmtact.fly.dev', 'x-farmtact-gateway': os.environ['FARMTACT_CONTROL_SECRET'],
                   'x-farmtact-client-ip': '127.0.0.1'}
    report = {'status': 'RUNNING', 'checks': [], 'attempts': []}

    def check(name, condition):
        report['checks'].append({'name': name, 'pass': bool(condition)})
        if not condition:
            raise AssertionError(name)

    with httpx.Client(base_url=base, headers=headers, timeout=40, trust_env=False) as client:
        def request(method, path, body=None):
            key = uuid4().hex
            for _ in range(3):
                response = client.request(method, '/api/v1' + path, json=body,
                    headers={'Idempotency-Key': key} if method == 'POST' else {})
                if response.status_code != 429:
                    response.raise_for_status()
                    return response.json()
                time.sleep(min(60, max(1, int(response.headers.get('Retry-After', '5')))))
            raise AssertionError('Trial admission remained limited')

        bootstrap = request('GET', '/bootstrap')
        # The backend correctly marks production cookies Secure. Only this local
        # operator client relays that acquired cookie over private loopback.
        if operator:
            token = client.cookies.get('farmtact_session')
            if not token:
                raise AssertionError('Candidate did not create an operator trial session')
            client.headers['cookie'] = 'farmtact_session=' + token
        original_farm = bootstrap['farm']
        for lesson in ('first_delivery', 'two_orders'):
            current = request('POST', '/beginner-journeys', {'lesson_id': lesson})
            stages, revisions = [], []
            for _ in range(45):
                deadline = time.monotonic() + 180
                while current['planning_session']['status'] in ('QUEUED', 'RUNNING'):
                    if time.monotonic() > deadline:
                        raise AssertionError('Candidate calculation deadline exceeded')
                    time.sleep(2)
                    current = request('GET', '/beginner-journeys/' + current['id'])
                stages.append(current['stage'])
                revisions.append(current['revision'])
                if current['stage'] == 'COMPLETE':
                    break
                action = current['next_action']
                check(f'{lesson}: {current["stage"]} has an eligible next action', action and action['eligible'])
                body = {'revision': current['revision'], 'action_id': action['id']}
                if action.get('requires_option'):
                    choices = [item for item in current['choices'] if item['eligible']]
                    check(f'{lesson}: eligible calculated choice exists', bool(choices))
                    body['option_id'] = choices[-1]['id']
                previous = current['revision']
                current = request('POST', '/beginner-journeys/' + current['id'] + '/actions', body)
                check(f'{lesson}: action advances revision', current['revision'] > previous)
            check(f'{lesson}: reaches debrief', current['stage'] == 'COMPLETE')
            check(f'{lesson}: order objective met', current['debrief']['objective_met'])
            check(f'{lesson}: recorded event history exists', bool(current['timeline']))
            check(f'{lesson}: operations stay simulated', current['real_operations_enabled'] is False)
            report['attempts'].append({'lesson': lesson, 'stages': stages, 'revisions': revisions,
                                       'metrics': current['metrics'], 'debrief': current['debrief']})
        check('main farm unchanged', request('GET', '/bootstrap')['farm'] == original_farm)
        report['status'] = 'PASS'
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', default='http://127.0.0.1:4190')
    parser.add_argument('--operator', action='store_true')
    arguments = parser.parse_args()
    print(json.dumps(run(arguments.base_url.rstrip('/'), arguments.operator), indent=2))
