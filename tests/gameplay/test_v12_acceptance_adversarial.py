"""Adversarial V12 acceptance through real HTTP routes and durable stores."""
from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from services.api import farm_workflow
from services.api.app import create_app
from services.api.planning_sessions import execute_job
from services.api.store import Store


DATABASE_URL = 'postgresql+psycopg://sprite@/farmtact_review?host=/tmp/farmtact-pg'


@pytest.fixture
def isolated_database_url():
    # Durable restart coverage needs PostgreSQL, but repeated acceptance runs must
    # not inherit earlier tenants or their durable abuse counters.
    schema = 'v12_acceptance_' + uuid4().hex
    engine = create_engine(DATABASE_URL)
    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA {schema}'))
    url = make_url(DATABASE_URL).update_query_dict({'options': f'-csearch_path={schema}'})
    try:
        yield url.render_as_string(hide_password=False)
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA {schema} CASCADE'))
        engine.dispose()


def post(client, path, body, key=None):
    return client.post('/api/v1' + path, json=body, headers={'Idempotency-Key': key or uuid4().hex})


def calculated_workflow(store, client):
    bootstrap = client.get('/api/v1/bootstrap')
    assert bootstrap.status_code == 200, bootstrap.text
    tenant = store.authenticate(client.cookies.get('farmtact_session'))
    created = post(client, '/planning-sessions', {'name': 'Adversarial acceptance', 'workflow': True})
    assert created.status_code == 201, created.text
    session = created.json(); path = '/planning-sessions/' + session['id']
    queued = post(client, path + '/calculate', {'revision': session['revision']})
    assert queued.status_code == 202, queued.text
    execute_job(store, tenant, queued.json()['job']['id'])
    session = client.get('/api/v1' + path).json()
    assert session['status'] == 'COMPLETED' and session['workflow'] is True
    return tenant, path, session


def proposal(client, session, key):
    body = {'session_id': session['id'], 'base_revision': session['revision'],
            'changes': [{'kind': 'planning_assumptions', 'assumptions': {}}],
            'selected_strategy_id': session['selected_strategy_id'], 'idempotency_key': key}
    response = post(client, '/farm-workflow/proposals', body, key)
    assert response.status_code == 201, response.text
    return response.json()


def apply_and_approve(store, client, tenant, session, draft):
    apply_key = 'apply-' + uuid4().hex
    response = post(client, f'/farm-workflow/proposals/{draft["id"]}/apply', {
        'proposal_id': draft['id'], 'expected_base_revision': draft['base_revision'],
        'idempotency_key': apply_key}, apply_key)
    assert response.status_code == 202, response.text
    applied = response.json(); execute_job(store, tenant, applied['recalculation_job']['id'])
    approve_key = 'approve-' + uuid4().hex
    body = {'proposal_id': draft['id'], 'proposal_revision': applied['proposal_revision'],
            'selected_strategy_id': draft['selected_strategy_id'], 'idempotency_key': approve_key}
    endpoint = f'/farm-workflow/proposals/{draft["id"]}/approve-actions'
    response = post(client, endpoint, body, approve_key)
    assert response.status_code == 200, response.text
    assert post(client, endpoint, body, approve_key).json() == response.json()
    return response.json()


def test_stale_approval_results_corrections_restart_and_tenant_isolation(isolated_database_url):
    store = Store(isolated_database_url)
    app = create_app(store, start_worker=False)
    with TestClient(app) as client:
        tenant, path, session = calculated_workflow(store, client)
        stale = proposal(client, session, 'stale-' + uuid4().hex)
        disrupted = post(client, path + '/disrupt', {'revision': session['revision'], 'assumptions': {
            'future_demand': [], 'seasonal': [], 'order_changes': [], 'reservations': []}})
        assert disrupted.status_code == 202, disrupted.text
        execute_job(store, tenant, disrupted.json()['job']['id'])
        response = post(client, f'/farm-workflow/proposals/{stale["id"]}/apply', {
            'proposal_id': stale['id'], 'expected_base_revision': stale['base_revision'],
            'idempotency_key': 'stale-apply-' + uuid4().hex})
        assert response.status_code == 409

        session = client.get('/api/v1' + path).json()
        approved = apply_and_approve(store, client, tenant, session,
                                     proposal(client, session, 'current-' + uuid4().hex))
        harvest = next(row for row in approved['tasks'] if row['action'] == 'harvest')
        quantity = max(0, float(harvest['planned_quantity']) - 1)
        result_body = {'expected_status': 'pending', 'result_status': 'completed',
            'actual_quantity': quantity, 'unit': 'kg', 'photo_reference': None,
            'checklist_completed': harvest['checklist'], 'note': 'Farmer reported'}
        response = post(client, f'/farm-workflow/tasks/{harvest["id"]}/result', result_body)
        assert response.status_code == 200, response.text
        completed = response.json()
        assert post(client, f'/farm-workflow/tasks/{harvest["id"]}/result', result_body).status_code == 409
        session_after = client.get('/api/v1' + path).json()
        forecast = session_after['reported_forecast']
        assert forecast['basis'] == 'user_reported_projection' and forecast['independently_verified'] is False
        assert forecast['recovery_required'] is True

        correction_key = 'correction-' + uuid4().hex
        correction_body = {'expected_event_revision': completed['event_revision'], 'field': 'actual_quantity',
            'corrected_value': quantity + .5, 'reason': 'Scale transcription', 'idempotency_key': correction_key}
        endpoint = f'/farm-workflow/tasks/{harvest["id"]}/corrections'
        corrected = post(client, endpoint, correction_body, correction_key)
        assert corrected.status_code == 200, corrected.text
        assert post(client, endpoint, correction_body, correction_key).json() == corrected.json()
        changed = dict(correction_body, corrected_value=quantity)
        assert post(client, endpoint, changed, correction_key).status_code == 409
        workflow = client.get('/api/v1/farm-workflow').json()
        assert any(row['id'] == harvest['id'] and row['event_revision'] == 2 for row in workflow['tasks'])

        token = client.cookies.get('farmtact_session')
        client.cookies.clear()
        client.get('/api/v1/bootstrap')
        other = client.get('/api/v1/farm-workflow').json()
        assert harvest['id'] not in {row['id'] for row in other['tasks']}
        assert stale['id'] not in {row['id'] for row in other['proposals']}

    restarted = Store(isolated_database_url)
    with TestClient(create_app(restarted, start_worker=False)) as client:
        client.cookies.set('farmtact_session', token)
        persisted = client.get('/api/v1/farm-workflow').json()
        assert any(row['id'] == harvest['id'] and row['event_revision'] == 2 for row in persisted['tasks'])
        replay_session = client.get('/api/v1' + path).json()
        assert replay_session['reported_forecast']['source_task_events']
    restarted.engine.dispose()
    store.engine.dispose()


def test_task_result_rolls_back_when_event_append_fails(monkeypatch):
    store = Store('sqlite://')
    with TestClient(create_app(store, start_worker=False), raise_server_exceptions=False) as client:
        tenant, _path, session = calculated_workflow(store, client)
        approved = apply_and_approve(store, client, tenant, session,
                                     proposal(client, session, 'rollback-' + uuid4().hex))
        task = next(row for row in approved['tasks'] if row['action'] == 'sow')
        original = farm_workflow.append_event
        monkeypatch.setattr(farm_workflow, 'append_event', lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError('event failure')))
        response = post(client, f'/farm-workflow/tasks/{task["id"]}/result', {
            'expected_status': 'pending', 'result_status': 'completed', 'actual_quantity': None,
            'unit': None, 'photo_reference': None, 'checklist_completed': task['checklist']})
        assert response.status_code == 500
        monkeypatch.setattr(farm_workflow, 'append_event', original)
        state = client.get('/api/v1/farm-workflow').json()
        saved = next(row for row in state['tasks'] if row['id'] == task['id'])
        assert saved['status'] == 'pending' and saved['event_revision'] == 0


def test_reviewed_import_boundary_and_document_failure_are_tenant_scoped():
    store = Store('sqlite://')
    with TestClient(create_app(store, start_worker=False)) as client:
        client.get('/api/v1/bootstrap')
        created = post(client, '/farm-workflow/imports', {'source_name': 'manual correction',
            'import_kind': 'correction', 'rows': [
                {'date': '2026-09-15', 'kind': 'sale', 'reference': 'invoice-1',
                 'amount': '25.00', 'currency': 'SGD'},
                {'date': '2026-09-16', 'kind': 'correction', 'reference': 'correction-1',
                 'corrects_reference': 'invoice-1', 'amount': '-2.50', 'currency': 'SGD'},
            ]})
        assert created.status_code == 201, created.text
        candidate = created.json()
        assert candidate['status'] == 'candidate'
        state = client.get('/api/v1/farm-workflow').json()
        assert state['phase'] == 'inbox_review'
        reviewed = post(client, f'/farm-workflow/imports/{candidate["candidate_id"]}/review', {
            'expected_status': 'candidate', 'decision': 'confirm', 'reviewer': 'acceptance farmer'})
        assert reviewed.status_code == 200 and reviewed.json()['planning_eligible'] is True
        bad = client.post('/api/v1/farm-workflow/imports/upload?filename=bad.png&source_kind=document_extraction',
                          content=b'not-an-image', headers={'Content-Type': 'image/png', 'Idempotency-Key': uuid4().hex})
        assert bad.status_code == 422
        client.cookies.clear(); client.get('/api/v1/bootstrap')
        response = post(client, f'/farm-workflow/imports/{candidate["candidate_id"]}/review', {
            'expected_status': 'candidate', 'decision': 'reject', 'reviewer': 'other tenant'})
        assert response.status_code == 404
