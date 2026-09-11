"""Process-boundary checks for the bounded V11 numerical worker."""
from __future__ import annotations

import multiprocessing
import time

import pytest

from packages.fixtures import synthetic_farm
from services.api import numerical_worker as worker


def _send_payload(connection, operation, payload):
    connection.send(('ok',{'value':payload.get('value'),'blob':'x'*payload.get('size',0)}))
    connection.close()


def _sleep_without_result(connection, operation, payload):
    time.sleep(float(payload.get('seconds',5)))
    connection.close()


def _close_without_result(connection, operation, payload):
    connection.close()


@pytest.fixture(autouse=True)
def clean_worker_cache_and_gate():
    worker._CACHE.clear()
    assert not worker._GATE.locked()
    yield
    worker._CACHE.clear()
    acquired=worker._GATE.acquire(blocking=False)
    assert acquired, 'numerical worker gate leaked in the locked state'
    worker._GATE.release()
    time.sleep(.05)
    assert not [child for child in multiprocessing.active_children() if child.name=='farmtact-numerical-job']


def test_actual_spawned_tiny_session_returns_a_complete_result():
    farm=synthetic_farm();farm.horizon_days=7;farm.beds=farm.beds[:1]
    farm.batches=[];farm.orders=[];farm.history=[];farm.inventory=[]

    result=worker.calculate('session',{'farm':farm.model_dump(mode='json'),'kwargs':{}},deadline=20)

    assert [strategy['name'] for strategy in result['strategies']]==['Lean','Balanced','Resilient']
    assert result['selected_strategy_id']
    assert result['_execution_trace']['scenario_id']=='execution-central'
    assert result['worker_timing']['cache_hit'] is False
    assert result['worker_timing']['elapsed_seconds']<20


def test_large_result_frame_is_read_completely(monkeypatch):
    monkeypatch.setattr(worker,'_child',_send_payload)

    result=worker.calculate('test',{'value':'large','size':4_000_000},deadline=5)

    assert result['value']=='large'
    assert len(result['blob'])==4_000_000
    assert result['worker_timing']['cache_hit'] is False


def test_cache_is_deep_copied_and_isolated_by_scope(monkeypatch):
    monkeypatch.setattr(worker,'_child',_send_payload)
    payload={'value':{'count':1}}

    first=worker.calculate('test',payload,cache_scope='tenant-a',deadline=5)
    first['value']['count']=999
    same_scope=worker.calculate('test',payload,cache_scope='tenant-a',deadline=5)
    other_scope=worker.calculate('test',payload,cache_scope='tenant-b',deadline=5)

    assert first['worker_timing']['cache_hit'] is False
    assert same_scope['worker_timing']['cache_hit'] is True
    assert same_scope['value']=={'count':1}
    assert other_scope['worker_timing']['cache_hit'] is False


def test_cancellation_terminates_child_and_releases_gate(monkeypatch):
    monkeypatch.setattr(worker,'_child',_sleep_without_result)
    started=time.monotonic()

    with pytest.raises(InterruptedError,match='cancelled'):
        worker.calculate('test',{'seconds':5},cancelled=lambda:time.monotonic()-started>.2,deadline=5)

    assert time.monotonic()-started<2
    monkeypatch.setattr(worker,'_child',_send_payload)
    assert worker.calculate('test',{'value':'after-cancel'},deadline=5)['value']=='after-cancel'


def test_deadline_terminates_child_and_releases_gate(monkeypatch):
    monkeypatch.setattr(worker,'_child',_sleep_without_result)
    started=time.monotonic()

    with pytest.raises(TimeoutError,match='end-to-end deadline'):
        worker.calculate('test',{'seconds':5},deadline=.25)

    assert time.monotonic()-started<2
    monkeypatch.setattr(worker,'_child',_send_payload)
    assert worker.calculate('test',{'value':'after-timeout'},deadline=5)['value']=='after-timeout'


def test_child_exit_without_result_is_bounded_and_gate_recovers(monkeypatch):
    monkeypatch.setattr(worker,'_child',_close_without_result)

    with pytest.raises(RuntimeError,match='result'):
        worker.calculate('test',{},deadline=2)

    monkeypatch.setattr(worker,'_child',_send_payload)
    assert worker.calculate('test',{'value':'after-exit'},deadline=5)['value']=='after-exit'

