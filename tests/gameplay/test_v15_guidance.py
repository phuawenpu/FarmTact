from copy import deepcopy
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from services.api.app import create_app
from services.api.store import Store


def test_guidance_is_versioned_isolated_and_does_not_change_planning():
    store = Store('sqlite://')
    with TestClient(create_app(store, start_worker=False)) as client:
        client.get('/api/v1/bootstrap')
        def post(path, body, key=None):
            return client.post('/api/v1/planning-sessions' + path, json=body,
                               headers={'Idempotency-Key': key or uuid4().hex})
        session = post('', {'workflow': True}).json()
        baseline = deepcopy(session)
        path = '/' + session['id'] + '/guidance'
        body = {'revision': 0, 'step': 'compare', 'skipped': True}
        saved = post(path, body, 'skip-guidance')
        assert saved.status_code == 200, saved.text
        assert saved.json()['guidance']['revision'] == 1
        assert saved.json()['guidance']['skipped'] is True
        assert post(path, body, 'skip-guidance').json() == saved.json()
        assert post(path, body).status_code == 409
        for field in ['farm', 'revision', 'input_hash', 'result_id', 'history', 'simulation']:
            assert saved.json()[field] == baseline[field]
        assert post(path, {'revision': 1, 'step': 'compare', 'skipped': False}).json()['guidance']['skipped'] is False
        assert post(path, {'revision': 2, 'step': 'unrecognized'}).status_code == 422
        with TestClient(create_app(store, start_worker=False)) as other:
            other.get('/api/v1/bootstrap')
            assert other.post('/api/v1/planning-sessions'+path, json=body,
                             headers={'Idempotency-Key':uuid4().hex}).status_code == 404
