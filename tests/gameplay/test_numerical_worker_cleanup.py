"""Admission survives cleanup faults without overlapping numerical processes."""
import threading

import pytest

from services.api import numerical_worker as worker


class Receiver:
    def __init__(self, result=None, close_fails=False):
        self.result = result
        self.close_fails = close_fails
        self.closed = threading.Event()

    def recv(self):
        if self.result is not None:
            return ('ok', {'value': self.result})
        self.closed.wait(2)
        raise EOFError('closed test pipe')

    def close(self):
        self.closed.set()
        if self.close_fails:
            raise OSError('injected receiver close failure')


class Sender:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class Process:
    def __init__(self, *, stubborn=False, join_fails=False, close_fails=False):
        self.stubborn = stubborn
        self.join_fails = join_fails
        self.close_fails = close_fails
        self.alive = True
        self.starts = 0
        self.kills = 0
        self.closes = 0

    def start(self):
        self.starts += 1

    def join(self, timeout):
        assert timeout in (0, .2, 1)
        if self.join_fails:
            raise OSError('injected join failure')

    def is_alive(self):
        return self.alive

    def terminate(self):
        if not self.stubborn:
            self.alive = False

    def kill(self):
        self.kills += 1
        if not self.stubborn:
            self.alive = False

    def close(self):
        self.closes += 1
        if self.alive or self.close_fails:
            raise ValueError('injected process close failure')


class Context:
    def __init__(self, process, receiver):
        self.process, self.receiver, self.sender = process, receiver, Sender()

    def Pipe(self, duplex):
        assert duplex is False
        return self.receiver, self.sender

    def Process(self, **kwargs):
        return self.process


@pytest.fixture(autouse=True)
def isolated_worker(monkeypatch):
    monkeypatch.setattr(worker, '_GATE', threading.Lock())
    monkeypatch.setattr(worker, '_UNREAPED', [])
    monkeypatch.setattr(worker, '_CACHE', {})
    yield
    assert not worker._GATE.locked(), 'cleanup leaked worker admission lock'


def install(monkeypatch, context):
    monkeypatch.setattr(worker.multiprocessing, 'get_context', lambda method: context)


def assert_following_calculation_succeeds(monkeypatch):
    context = Context(Process(), Receiver(result='recovered'))
    install(monkeypatch, context)
    assert worker.calculate('test', {}, deadline=.5)['value'] == 'recovered'
    assert context.process.starts == 1
    assert context.receiver.closed.is_set()
    assert context.sender.closed


def test_live_after_kill_preserves_timeout_releases_gate_and_recovers(monkeypatch):
    process = Process(stubborn=True)
    context = Context(process, Receiver())
    install(monkeypatch, context)

    with pytest.raises(TimeoutError, match='end-to-end deadline'):
        worker.calculate('test', {}, deadline=.005)

    assert process.kills == 1
    assert process.closes == 0, 'a live process must not be closed'
    assert context.receiver.closed.is_set()
    assert context.sender.closed
    assert not worker._GATE.locked()
    assert worker._UNREAPED == [process]
    process.alive = False  # OS reap finishes after the bounded cleanup window.
    assert_following_calculation_succeeds(monkeypatch)
    assert not worker._UNREAPED
    assert process.closes == 1


def test_unreaped_child_blocks_new_spawn_with_existing_deadline(monkeypatch):
    previous = Process(stubborn=True)
    worker._UNREAPED.append(previous)
    context = Context(Process(), Receiver(result='must not run'))
    install(monkeypatch, context)

    with pytest.raises(TimeoutError, match='admission deadline'):
        worker.calculate('test', {}, deadline=.005)

    assert context.process.starts == 0
    assert worker._UNREAPED == [previous]
    assert not worker._GATE.locked()
    with pytest.raises(InterruptedError, match='before execution'):
        worker.calculate('test', {}, cancelled=lambda: True, deadline=.5)
    assert context.process.starts == 0
    previous.alive = False
    assert_following_calculation_succeeds(monkeypatch)


@pytest.mark.parametrize('fault', ['join', 'terminate', 'process_close', 'receiver_close'])
def test_cleanup_failure_does_not_mask_timeout_or_prevent_next_job(monkeypatch, fault):
    process = Process(join_fails=fault == 'join', close_fails=fault == 'process_close')
    if fault == 'terminate':
        def failed_terminate():
            raise OSError('injected terminate failure')
        monkeypatch.setattr(process, 'terminate', failed_terminate)
    context = Context(process, Receiver(close_fails=fault == 'receiver_close'))
    install(monkeypatch, context)

    with pytest.raises(TimeoutError, match='end-to-end deadline'):
        worker.calculate('test', {}, deadline=.005)

    assert not process.alive
    assert context.receiver.closed.is_set()
    assert context.sender.closed
    assert not worker._GATE.locked()
    assert not worker._UNREAPED
    assert_following_calculation_succeeds(monkeypatch)


def test_completed_result_is_not_replaced_by_cleanup_failure(monkeypatch):
    context = Context(Process(close_fails=True), Receiver(result='complete', close_fails=True))
    install(monkeypatch, context)

    assert worker.calculate('test', {}, deadline=.5)['value'] == 'complete'
    assert context.receiver.closed.is_set()
    assert context.sender.closed
    assert_following_calculation_succeeds(monkeypatch)
