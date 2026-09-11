"""Bounded local numerical subprocess. No caller-selectable code or filesystem paths."""
from collections import OrderedDict
from copy import deepcopy
import multiprocessing
import threading
import time
from packages.contracts import Farm, content_hash

DEADLINE_SECONDS = 150
_GATE = threading.Lock()
_CACHE = OrderedDict()


def _child(connection, operation, payload):
    try:
        if operation == 'plan':
            from packages.planner import plan
            value = plan(Farm.model_validate(payload['farm']), **payload['kwargs'])
        elif operation == 'research':
            from packages.planner.research import calculate_research
            value=calculate_research(Farm.model_validate(payload['farm']),**payload['kwargs'])
        elif operation == 'session':
            from packages.planning_numerics import calculate_session
            from packages.planner.engine import simulate
            value = calculate_session(payload['farm'], **payload['kwargs'])
            chosen = next((s for s in value['strategies'] if s['name']=='Balanced' and s['status']=='FEASIBLE'), None)
            chosen = chosen or next((s for s in value['strategies'] if s['status']=='FEASIBLE'), None)
            value['selected_strategy_id'] = chosen['id'] if chosen else None
            if chosen:
                farm=Farm.model_validate(value.get('input_snapshot',payload['farm']))
                value['_execution_trace']=simulate(farm,chosen['allocations'],value['forecast']['demand'],dict(id='execution-central',yield_factor=1.,demand_factor=1.,weight=1.))
        else:
            raise ValueError('Unknown numerical operation')
        connection.send(('ok',value))
    except Exception as exc:
        # Only local validation/solver failures, no environment or transport objects.
        connection.send(('error',type(exc).__name__,str(exc)[:400]))
    finally:
        connection.close()


def calculate(operation, payload, *, cache_scope=None, cancelled=lambda: False, progress=lambda stage: None, deadline=DEADLINE_SECONDS):
    started=time.monotonic()
    key=content_hash(dict(operation=operation,payload=payload,scope=cache_scope)) if cache_scope else None
    progress('waiting_for_numerical_worker')
    while not _GATE.acquire(timeout=.1):
        if cancelled(): raise InterruptedError('Calculation cancelled before execution')
        if time.monotonic()-started>=deadline: raise TimeoutError('Numerical admission deadline exceeded')
    process=None
    receiver=None
    try:
        if cancelled(): raise InterruptedError('Calculation cancelled')
        if key in _CACHE:
            _CACHE.move_to_end(key)
            value=deepcopy(_CACHE[key]);value['worker_timing']={'cache_hit':True,'queue_seconds':round(time.monotonic()-started,4),'elapsed_seconds':round(time.monotonic()-started,4)}
            return value
        queued=time.monotonic()-started
        progress('calculating_schedules_and_inventory')
        context=multiprocessing.get_context('spawn')
        receiver,sender=context.Pipe(duplex=False)
        process=context.Process(target=_child,args=(sender,operation,payload),daemon=True,name='farmtact-numerical-job')
        process.start();sender.close()
        # Receive on a bounded auxiliary thread: poll readiness alone does not
        # guarantee an entire large result frame has arrived.
        received=[];receive_errors=[];received_event=threading.Event()
        def receive():
            try:received.append(receiver.recv())
            except Exception as exc:receive_errors.append(type(exc).__name__)
            finally:received_event.set()
        reader=threading.Thread(target=receive,daemon=True,name='farmtact-result-reader')
        reader.start()
        while not received_event.wait(.1):
            if cancelled(): raise InterruptedError('Calculation cancelled')
            if time.monotonic()-started>=deadline: raise TimeoutError('Numerical job exceeded its end-to-end deadline')
            if not process.is_alive() and not received_event.wait(.2): raise RuntimeError('Numerical worker exited without a result')
        if receive_errors:raise RuntimeError('Numerical result transport failed')
        response=received[0]
        if cancelled(): raise InterruptedError('Calculation cancelled before result acceptance')
        if response[0]!='ok': raise ValueError(f'{response[1]}: {response[2]}')
        value=response[1]
        value['worker_timing']={'cache_hit':False,'queue_seconds':round(queued,4),'execution_seconds':round(time.monotonic()-started-queued,4),'elapsed_seconds':round(time.monotonic()-started,4)}
        if key:
            _CACHE[key]=deepcopy(value)
            while len(_CACHE)>8:_CACHE.popitem(last=False)
        return value
    finally:
        if process:
            process.join(timeout=.2)
            if process.is_alive():process.terminate();process.join(timeout=1)
            if process.is_alive():process.kill();process.join(timeout=1)
            process.close()
        if receiver:receiver.close()
        _GATE.release()


def plan(farm, **kwargs):
    """Existing API calculations share the same per-process admission boundary."""
    # The public test-mode API retains historical result shapes; guided sessions
    # expose worker timings separately. No shared cross-tenant cache here.
    result=calculate('plan',{'farm':farm.model_dump(mode='json'),'kwargs':kwargs})
    result.pop('worker_timing',None)
    return result


def calculate_research(farm, **kwargs):
    result=calculate('research',{'farm':farm.model_dump(mode='json'),'kwargs':kwargs})
    result.pop('worker_timing',None)
    return result
