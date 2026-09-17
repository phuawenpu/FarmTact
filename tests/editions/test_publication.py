import json
from pathlib import Path
import subprocess
import sys

import pytest

import scripts.publish_edition as publication


def test_file_entrypoint_resolves_shared_host_helper_outside_repo(tmp_path):
    script = str(publication.ROOT / "scripts/publish_edition.py")
    code = (
        "import runpy; runpy.run_path(" + repr(script) + "); "
        "from scripts.shared_host_config import machine_config; "
        "assert callable(machine_config)"
    )
    subprocess.run([sys.executable, "-I", "-c", code], cwd=tmp_path, check=True)


def registry(count=2):
    editions = [{"id": f"v{i}", "title": f"Edition {i}"} for i in range(1, count + 1)]
    return {"latest": f"v{count}", "editions": editions}


def notes():
    return {"title": "Third edition", "summary": "A frozen release.", "changes": [{"title": "Change", "description": "Bounded change.", "feedback_ids": [], "evidence": []}]}


def snapshot_row(snapshot_id, status='created', *, created_at='2026-09-16T15:12:22Z', size=123):
    return {'id': snapshot_id, 'status': status, 'size': size,
            'digest': 'a' * 64 if size else '', 'created_at': created_at}


def test_registry_append_is_strictly_immutable():
    old = registry()
    new = {"latest": "v3", "editions": [*old["editions"], {"id": "v3", "title": "Third"}]}
    publication.append_only(old, new)
    changed = json.loads(json.dumps(new)); changed["editions"][0]["title"] = "Rewritten"
    with pytest.raises(publication.PublicationError, match="immutable"):
        publication.append_only(old, changed)
    with pytest.raises(publication.PublicationError):
        publication.validate_registry({"latest": "v3", "editions": [{"id": "v1"}, {"id": "v3"}]})


def test_failed_local_reservation_cannot_change_identity(tmp_path):
    state = tmp_path / "state.json"
    commit = "a" * 40; image = "registry.fly.io/farmtact@sha256:" + "b" * 64
    value = publication.reserve_number(state, "v3", commit, image)
    value["reservations"]["v3"]["stage"] = "failed"; publication.save_state(state, value)
    assert publication.reserve_number(state, "v3", commit, image)["reservations"]["v3"]["stage"] == "failed"
    with pytest.raises(publication.PublicationError, match="different inputs"):
        publication.reserve_number(state, "v3", "c" * 40, image)
    value["reservations"]["v3"]["stage"] = "published"; publication.save_state(state, value)
    with pytest.raises(publication.PublicationError, match="cannot be reused"):
        publication.reserve_number(state, "v3", commit, image)


def test_notes_and_image_are_bounded_and_pinned():
    publication.validate_notes(notes())
    with pytest.raises(publication.PublicationError): publication.validate_notes({**notes(), "extra": True})
    assert publication.IMAGE.fullmatch("registry.fly.io/farmtact@sha256:" + "0" * 64)
    assert not publication.IMAGE.fullmatch("registry.fly.io/farmtact:latest")


def test_deploy_uses_fixed_app_private_probe_and_exact_digest(tmp_path, monkeypatch):
    calls = []
    def fake(args, **kwargs):
        calls.append((args, kwargs))
        is_first_status = args[:2] == ["fly", "status"] and len(calls) == 1
        output = "[]" if args[:3] in (["fly", "volumes", "list"], ["fly", "ips", "list"]) else ""
        return type("Result", (), {"returncode": 1 if is_first_status else 0, "stdout": output, "stderr": ""})()
    monkeypatch.setattr(publication, "command", fake)
    monkeypatch.setenv("FARMTACT_CONTROL_SECRET", "control-value")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "provider-value")
    image = "registry.fly.io/farmtact@sha256:" + "d" * 64
    publication.deploy("v3", image, tmp_path / "fly-v3.toml")
    flattened = [item for call, _kwargs in calls for item in call]
    assert image in flattened
    assert "farmtact-edition-v3" in flattened
    assert ["fly", "volumes", "list", "--app", "farmtact-edition-v3", "--json"] in [call for call, _ in calls]
    assert any(call[:3] == ["fly", "volumes", "create"] for call, _ in calls)
    assert ["fly", "apps", "create", "farmtact-edition-v3"] in [call for call, _ in calls]
    assert any(call[:3] == ["fly", "ips", "allocate-v6"] and "--private" in call for call, _ in calls)
    assert any(call[:2] == ["fly", "deploy"] and "--no-public-ips" in call for call, _ in calls)
    assert any("farmtact-edition-v3.flycast/api/v1/health" in item for call, _ in calls for item in call)
    assert any("r.get('source_commit')" in item for call, _ in calls for item in call)
    assert all("control-value" not in item and "provider-value" not in item for item in flattened)
    secret_call = next((call, kwargs) for call, kwargs in calls if call[:3] == ["fly", "secrets", "import"])
    assert secret_call[1]["input_bytes"] == b"FARMTACT_CONTROL_SECRET=control-value\nDEEPSEEK_API_KEY=provider-value\n"


def test_new_app_fails_before_provision_without_runtime_credentials(tmp_path, monkeypatch):
    calls = []
    def fake(args, **kwargs):
        calls.append(args)
        return type("Result", (), {"returncode": 1, "stdout": "", "stderr": ""})()
    monkeypatch.setattr(publication, "command", fake)
    monkeypatch.delenv("FARMTACT_CONTROL_SECRET", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(publication.PublicationError, match="requires control and DeepSeek"):
        publication.deploy("v3", "registry.fly.io/farmtact@sha256:" + "e" * 64, tmp_path / "fly.toml")
    assert calls == [["fly", "status", "--app", "farmtact-edition-v3"]]


def test_build_path_returns_only_reported_pinned_digest(monkeypatch):
    digest = "registry.fly.io/farmtact@sha256:" + "f" * 64
    reported = "registry.fly.io/farmtact:edition-v3-aaaaaaaaaaaa@sha256:" + "f" * 64
    calls = []
    def fake(args, **kwargs):
        calls.append(args)
        return type("Result", (), {"returncode": 0, "stdout": f"pushed {reported}\n", "stderr": ""})()
    monkeypatch.setattr(publication, "command", fake)
    commit = "a" * 40
    assert publication.build_image("v3", commit) == digest
    assert calls == [[
        "fly", "deploy", "--app", "farmtact", "--config", "config/releases/fly-gateway.toml",
        "--build-only", "--push", "--remote-only", "--image-label", "edition-v3-aaaaaaaaaaaa",
        "--build-arg", f"SOURCE_COMMIT={commit}",
    ]]


def test_public_ip_inventory_stops_before_deploy(tmp_path, monkeypatch):
    calls = []
    def fake(args, **kwargs):
        calls.append(args)
        output = '[{"Type":"public_v6","Address":"2a09:dead::1"}]' if args[:3] == ["fly", "ips", "list"] else '[]'
        return type("Result", (), {"returncode": 0, "stdout": output, "stderr": ""})()
    monkeypatch.setattr(publication, "command", fake)
    with pytest.raises(publication.PublicationError, match="public or unrecognized IP"):
        publication.deploy("v3", "registry.fly.io/farmtact@sha256:" + "d" * 64, tmp_path / "fly.toml")
    assert not any(call[:2] == ["fly", "deploy"] for call in calls)


def test_remote_publish_uploads_temp_then_runs_fixed_validator(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(publication, "command", lambda args, **kwargs: calls.append((args, kwargs)) or type("Result", (), {"returncode": 0})())
    publication.publish_remote(registry(3), {'previous':'v2','latest':'v3'}, tmp_path / "next.json")
    assert calls[0][0][:4] == ["fly", "ssh", "sftp", "shell"]
    assert "/data/releases/public.json.next" in calls[0][1]["input_text"]
    assert calls[1][0][:4] == ["fly", "ssh", "console", "--app"]
    assert "os.replace(n,u)" in calls[1][0][-1]
    assert "p+'.previous'" in calls[1][0][-1]
    assert "q+'.previous'" in calls[1][0][-1]


def test_fly_manifest_has_isolated_app_volume_and_control():
    text = publication.fly_config("v7")
    assert 'app = "farmtact-edition-v7"' in text
    assert 'FARMTACT_EDITION = "v7"' in text
    assert 'FARMTACT_CONTROL_URL = "http://farmtact.flycast"' in text
    assert 'source = "farmtact_data"' in text
    assert "DEEPSEEK_API_KEY" not in text and "FARMTACT_CONTROL_SECRET" not in text


def test_pre_retention_gateway_history_fallback_is_404_only(monkeypatch):
    from io import BytesIO
    from urllib.error import HTTPError
    class Response(BytesIO):
        status=200
        headers={}
    calls=[]
    def legacy(request,timeout):
        calls.append(request.full_url)
        if request.full_url.endswith('/history'):
            raise HTTPError(request.full_url,404,'Not Found',{},None)
        return Response(json.dumps(registry()).encode())
    monkeypatch.setattr(publication,'urlopen',legacy)
    assert publication.remote_registry('https://farmtact.fly.dev')==registry()
    assert calls==['https://farmtact.fly.dev/api/releases/history','https://farmtact.fly.dev/api/releases']
    def unavailable(request,timeout):raise HTTPError(request.full_url,503,'Unavailable',{},None)
    monkeypatch.setattr(publication,'urlopen',unavailable)
    with pytest.raises(publication.PublicationError):publication.remote_registry('https://farmtact.fly.dev')


def test_legacy_active_migrates_latest_only_and_rejects_truncated_history():
    assert publication.active_from_public(registry(11))=={'previous':None,'latest':'v11'}
    with pytest.raises(publication.PublicationError):
        publication.active_from_public({'latest':'v11','editions':[{'id':'v11'}]})


def test_v14_active_policy_is_latest_only_while_v13_pair_remains_valid():
    publication.validate_active({'previous': 'v12', 'latest': 'v13'}, registry(13))
    publication.validate_active({'previous': None, 'latest': 'v14'}, registry(14))
    with pytest.raises(publication.PublicationError, match='only the latest'):
        publication.validate_active({'previous': 'v13', 'latest': 'v14'}, registry(14))
    assert publication.next_active_manifest('v13', 'v12') == {'previous': 'v12', 'latest': 'v13'}
    assert publication.next_active_manifest('v14', 'v13') == {'previous': None, 'latest': 'v14'}


def test_hidden_public_release_endpoints_fall_back_to_private_bundle(monkeypatch):
    from urllib.error import HTTPError
    bundle = {'history': registry(14), 'active': {'previous': None, 'latest': 'v14'}}
    monkeypatch.setattr(publication, 'urlopen', lambda request, timeout:
                        (_ for _ in ()).throw(HTTPError(request.full_url, 404, 'Not Found', {}, None)))
    calls = []
    monkeypatch.setattr(publication, 'private_release_bundle', lambda: calls.append(True) or bundle)
    assert publication.remote_registry('https://farmtact.fly.dev') == bundle['history']
    assert publication.remote_active('https://farmtact.fly.dev') == bundle['active']
    assert calls == [True, True]


def test_v14_cleanup_archives_and_stops_workers_without_deletion_operator(monkeypatch):
    history = registry(14)
    for entry in history['editions']:
        entry['image_digest'] = 'registry.fly.io/farmtact@sha256:' + entry['id'][1:].zfill(64)
        entry['source_commit'] = 'a' * 40
    active = {'previous': None, 'latest': 'v14'}
    settings = {'app': 'farmtact', 'machine_id': '1234567890abcd', 'volume_id': 'vol_review123'}
    runtime = {'config': {'containers': [
        {'name': 'gateway', 'env': {}}, {'name': 'v12', 'env': {}},
        {'name': 'v13', 'env': {}}, {'name': 'v14', 'env': {}},
    ]}}
    events = []
    monkeypatch.setattr(publication, 'shared_settings', lambda: settings)
    monkeypatch.setattr(publication, 'guard_shared_cleanup_runtime', lambda *_args: runtime)
    monkeypatch.setattr(publication, 'create_recovery_snapshot', lambda *_args: events.append('snapshot') or 'snapshot-v14-archive')
    monkeypatch.setattr(publication, 'deploy_shared', lambda *_args: events.append('stop-workers'))
    monkeypatch.setattr(publication, 'command', lambda args, **kwargs:
                        events.append((args, kwargs)) or type('Result', (), {'stdout': ''})())
    result = publication.retire_oldest_shared(history, active)
    flattened = ' '.join(str(item) for event in events if isinstance(event, tuple) for item in event[0])
    assert events[1:3] == ['snapshot', 'stop-workers']
    assert 'shared_retirement_operator' not in flattened and 'retirement-operator' not in flattened
    assert result['status'] == 'archived'
    assert result['protected_editions'] == [f'v{i}' for i in range(1, 14)]
    assert result['workers_stopped'] == ['v12', 'v13']
    assert result['snapshot_id'] == 'snapshot-v14-archive'


def test_rolling_retirement_stops_oldest_then_snapshots_and_applies(tmp_path, monkeypatch):
    history = registry(13)
    for entry in history['editions']:
        entry['image_digest'] = 'registry.fly.io/farmtact@sha256:' + entry['id'][1:].zfill(64)
        entry['source_commit'] = 'a' * 40
    active = {'previous': 'v12', 'latest': 'v13'}
    settings = {'app': 'farmtact', 'machine_id': '1234567890abcd', 'volume_id': 'vol_review123'}
    events = []
    monkeypatch.setattr(publication, 'shared_settings', lambda: settings)
    monkeypatch.setattr(publication, 'guard_shared_cleanup_runtime', lambda *_args: {})
    monkeypatch.setattr(publication, 'update_shared_machine',
                        lambda _settings, config: events.append(('update', [r['name'] for r in config['containers']])))
    monkeypatch.setattr(publication, 'create_recovery_snapshot',
                        lambda _settings: events.append(('snapshot', None)) or 'snapshot-rolling-13')
    actual_runtime = {'id': settings['machine_id'], 'config': {'containers': [
        {'name': name, 'env': {}} for name in ('gateway', 'v12', 'v13', 'retirement-operator')
    ]}}
    monkeypatch.setattr(publication, 'readback_shared_runtime',
                        lambda _settings, _config: events.append(('readback', None)) or actual_runtime)
    monkeypatch.setattr(publication, 'deploy_shared',
                        lambda _history, _active: events.append(('finalize', None)))

    def fake_command(args, **kwargs):
        if args[:4] == ['fly', 'ssh', 'sftp', 'shell']:
            assert kwargs['input_text'].endswith('/tmp/farmtact-runtime.json\n')
            assert 'quit' not in kwargs['input_text']
            events.append(('runtime', kwargs['input_text']))
        elif '--container' in args and args[args.index('--container') + 1] == 'retirement-operator':
            assert args[-2] == '--command'
            assert args[-1].startswith("sh -c '")
            assert 'cd /app && python -m scripts.shared_retirement_operator' in args[-1]
            events.append(('apply', args[-1]))
        return type('Result', (), {'returncode': 0, 'stdout': '', 'stderr': ''})()

    monkeypatch.setattr(publication, 'command', fake_command)
    result = publication.retire_oldest_shared(history, active)

    assert [event[0] for event in events] == ['update', 'snapshot', 'readback', 'runtime', 'apply', 'finalize']
    assert set(events[0][1]) == {'gateway', 'v12', 'v13', 'retirement-operator'}
    assert 'v11' not in events[0][1]
    assert '--snapshot-id snapshot-rolling-13' in events[4][1]
    assert result['status'] == 'retired'


def test_rolling_retirement_failure_leaves_operator_for_safe_resume(monkeypatch):
    history = registry(3)
    for entry in history['editions']:
        entry['image_digest'] = 'registry.fly.io/farmtact@sha256:' + entry['id'][1:].zfill(64)
    settings = {'app': 'farmtact', 'machine_id': '1234567890abcd', 'volume_id': 'vol_review123'}
    finalized = []
    monkeypatch.setattr(publication, 'shared_settings', lambda: settings)
    monkeypatch.setattr(publication, 'guard_shared_cleanup_runtime', lambda *_args: {})
    monkeypatch.setattr(publication, 'update_shared_machine', lambda *_args: None)
    monkeypatch.setattr(publication, 'create_recovery_snapshot', lambda *_args: 'snapshot-rolling-03')
    monkeypatch.setattr(publication, 'readback_shared_runtime', lambda *_args: {
        'id': settings['machine_id'], 'config': {'containers': []},
    })
    monkeypatch.setattr(publication, 'deploy_shared', lambda *_args: finalized.append(True))
    calls = 0

    def fail_apply(args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise subprocess.CalledProcessError(1, args)
        return type('Result', (), {'returncode': 0, 'stdout': '', 'stderr': ''})()

    monkeypatch.setattr(publication, 'command', fail_apply)
    with pytest.raises(subprocess.CalledProcessError):
        publication.retire_oldest_shared(history, {'previous': 'v2', 'latest': 'v3'})
    assert finalized == []


def test_snapshot_creation_requires_valid_recorded_identifier(monkeypatch):
    calls = 0
    def ready(args, **_kwargs):
        nonlocal calls
        calls += 1
        if 'list' in args:
            payload = [] if calls == 1 else [snapshot_row('snapshot-good-123')]
        else:
            payload = {'id': 'snapshot-good-123'}
        return type('Result', (), {'stdout': json.dumps(payload)})()
    monkeypatch.setattr(publication, 'command', ready)
    monkeypatch.setattr(publication, 'datetime', type('Clock', (), {
        'now': staticmethod(lambda _tz: __import__('datetime').datetime(2026, 9, 16, 15, 12, tzinfo=__import__('datetime').timezone.utc)),
        'fromisoformat': staticmethod(__import__('datetime').datetime.fromisoformat),
    }))
    assert publication.create_recovery_snapshot({'volume_id': 'vol_x', 'app': 'farmtact'}) == 'snapshot-good-123'
    responses = iter([json.dumps([]), 'unexpected output'])
    monkeypatch.setattr(publication, 'command', lambda *_args, **_kwargs:
                        type('Result', (), {'stdout': next(responses)})())
    with pytest.raises(publication.PublicationError, match='exact scheduling acknowledgement'):
        publication.create_recovery_snapshot({'volume_id': 'vol_x', 'app': 'farmtact'})


def test_snapshot_pending_then_created_is_bounded(monkeypatch):
    inventories = iter([
        [snapshot_row('snapshot-wait-123', 'running', created_at='0001-01-01T00:00:00Z', size=0)],
        [snapshot_row('snapshot-wait-123')],
    ])
    sleeps = []
    monkeypatch.setattr(publication, 'command', lambda *_args, **_kwargs:
                        type('Result', (), {'stdout': json.dumps(next(inventories))})())
    monkeypatch.setattr(publication.time, 'sleep', lambda seconds: sleeps.append(seconds))
    publication.wait_for_snapshot({'volume_id': 'vol_x', 'app': 'farmtact'},
                                  'snapshot-wait-123', attempts=2, interval=.25)
    assert sleeps == [.25]


def test_plain_scheduled_ack_discovers_only_new_recent_completed_snapshot(monkeypatch):
    old = snapshot_row('snapshot-old-123', created_at='2026-09-15T12:00:00Z')
    running = snapshot_row('snapshot-new-123', 'running', created_at='0001-01-01T00:00:00Z', size=0)
    completed = snapshot_row('snapshot-new-123', created_at='2026-09-16T15:12:22Z', size=279218627)
    inventories = iter([[old], [running, old], [running, old, completed]])
    sleeps = []

    def cli(args, **_kwargs):
        if 'create' in args:
            return type('Result', (), {'stdout': 'Scheduled to snapshot volume vol_x\n'})()
        return type('Result', (), {'stdout': json.dumps(next(inventories))})()

    monkeypatch.setattr(publication, 'command', cli)
    monkeypatch.setattr(publication.time, 'sleep', lambda seconds: sleeps.append(seconds))
    monkeypatch.setattr(publication, 'datetime', type('Clock', (), {
        'now': staticmethod(lambda _tz: __import__('datetime').datetime(2026, 9, 16, 15, 12, tzinfo=__import__('datetime').timezone.utc)),
        'fromisoformat': staticmethod(__import__('datetime').datetime.fromisoformat),
    }))
    assert publication.create_recovery_snapshot({'volume_id': 'vol_x', 'app': 'farmtact'}) == 'snapshot-new-123'
    assert sleeps == [2]


def test_scheduled_ack_never_selects_old_empty_or_ambiguous_snapshot(monkeypatch):
    old = snapshot_row('snapshot-old-123', created_at='2026-09-15T12:00:00Z')
    recent_a = snapshot_row('snapshot-new-a', created_at='2026-09-16T15:12:22Z')
    recent_b = snapshot_row('snapshot-new-b', created_at='2026-09-16T15:12:23Z')
    inventories = iter([[old], [old, recent_a, recent_b]])

    def cli(args, **_kwargs):
        if 'create' in args:
            return type('Result', (), {'stdout': 'Scheduled to snapshot volume vol_x\n'})()
        return type('Result', (), {'stdout': json.dumps(next(inventories))})()

    monkeypatch.setattr(publication, 'command', cli)
    monkeypatch.setattr(publication, 'datetime', type('Clock', (), {
        'now': staticmethod(lambda _tz: __import__('datetime').datetime(2026, 9, 16, 15, 12, tzinfo=__import__('datetime').timezone.utc)),
        'fromisoformat': staticmethod(__import__('datetime').datetime.fromisoformat),
    }))
    with pytest.raises(publication.PublicationError, match='ambiguous completed'):
        publication.create_recovery_snapshot({'volume_id': 'vol_x', 'app': 'farmtact'})


@pytest.mark.parametrize('inventories, message', [
    ([[snapshot_row('snapshot-bad-123', 'failed', size=0)]], 'failed with status'),
    ([[snapshot_row('snapshot-bad-123', 'running', created_at='0001-01-01T00:00:00Z', size=0)],
      [snapshot_row('snapshot-bad-123', 'running', created_at='0001-01-01T00:00:00Z', size=0)]], 'before timeout'),
])
def test_unusable_snapshot_prevents_retirement_apply(monkeypatch, inventories, message):
    history = registry(3)
    for entry in history['editions']:
        entry['image_digest'] = 'registry.fly.io/farmtact@sha256:' + entry['id'][1:].zfill(64)
    settings = {'app': 'farmtact', 'machine_id': '1234567890abcd', 'volume_id': 'vol_review123'}
    inventory = iter(inventories); list_calls = 0
    applied = []
    monkeypatch.setattr(publication, 'shared_settings', lambda: settings)
    monkeypatch.setattr(publication, 'guard_shared_cleanup_runtime', lambda *_args: {})
    monkeypatch.setattr(publication, 'update_shared_machine', lambda *_args: None)
    monkeypatch.setattr(publication.time, 'sleep', lambda *_args: None)

    def commands(args, **_kwargs):
        nonlocal list_calls
        if 'create' in args:
            return type('Result', (), {'stdout': json.dumps({'id': 'snapshot-bad-123'})})()
        if 'list' in args:
            list_calls += 1
            if list_calls == 1:
                return type('Result', (), {'stdout': '[]'})()
            try: payload = next(inventory)
            except StopIteration: payload = inventories[-1]
            return type('Result', (), {'stdout': json.dumps(payload)})()
        applied.append(args)
        return type('Result', (), {'stdout': ''})()

    monkeypatch.setattr(publication, 'command', commands)
    with pytest.raises(publication.PublicationError, match=message):
        publication.retire_oldest_shared(history, {'previous': 'v2', 'latest': 'v3'})
    assert applied == []


@pytest.mark.parametrize('candidate_source', ['container', 'staged_env'])
def test_cleanup_refuses_future_staged_candidate_before_machine_update(monkeypatch, candidate_source):
    history = registry(13)
    active = {'previous': 'v12', 'latest': 'v13'}
    containers = [{'name': 'gateway', 'env': {}}, {'name': 'v12', 'env': {}}, {'name': 'v13', 'env': {}}]
    if candidate_source == 'container':
        containers.append({'name': 'v14', 'env': {'FARMTACT_STAGED_EDITION': 'v14'}})
    else:
        containers[0]['env']['FARMTACT_STAGED_EDITION'] = 'v14'
    calls = []

    def runtime(args, **_kwargs):
        calls.append(args)
        return type('Result', (), {'stdout': json.dumps([{
            'id': '1234567890abcd', 'config': {'containers': containers},
        }])})()

    monkeypatch.setattr(publication, 'command', runtime)
    settings = {'app': 'farmtact', 'machine_id': '1234567890abcd', 'volume_id': 'vol_review123'}
    monkeypatch.setattr(publication, 'shared_settings', lambda: settings)
    with pytest.raises(publication.PublicationError, match='unpublished candidate'):
        publication.retire_oldest_shared(history, active)
    assert len(calls) == 1 and calls[0] == ['fly', 'machine', 'list', '--app', 'farmtact', '--json']


def test_cleanup_allows_post_cutover_staged_marker_equal_to_latest(monkeypatch):
    history = registry(13)
    active = {'previous': 'v12', 'latest': 'v13'}
    runtime = {'id': '1234567890abcd', 'config': {'containers': [
        {'name': 'gateway', 'env': {'FARMTACT_STAGED_EDITION': 'v13'}},
        {'name': 'v12', 'env': {'FARMTACT_STAGED_EDITION': 'v13'}},
        {'name': 'v13', 'env': {'FARMTACT_STAGED_EDITION': 'v13'}},
    ]}}
    monkeypatch.setattr(publication, 'command', lambda *_args, **_kwargs:
                        type('Result', (), {'stdout': json.dumps([runtime])})())
    assert publication.guard_shared_cleanup_runtime(
        {'app': 'farmtact', 'machine_id': '1234567890abcd'}, history, active,
    ) == runtime


@pytest.mark.parametrize('drift', ['retired_worker', 'future_candidate', 'staged_marker'])
def test_post_snapshot_machine_readback_rejects_actual_runtime_drift(monkeypatch, drift):
    settings = {'app': 'farmtact', 'machine_id': '1234567890abcd'}
    expected = {'containers': [
        {'name': 'gateway', 'env': {}}, {'name': 'v12', 'env': {}},
        {'name': 'v13', 'env': {}}, {'name': 'retirement-operator'},
    ]}
    actual = json.loads(json.dumps(expected))
    if drift == 'retired_worker':
        actual['containers'].append({'name': 'v11', 'env': {}})
    elif drift == 'future_candidate':
        actual['containers'].append({'name': 'v14', 'env': {'FARMTACT_STAGED_EDITION': 'v14'}})
    else:
        actual['containers'][0]['env']['FARMTACT_STAGED_EDITION'] = 'v14'
    calls = []
    monkeypatch.setattr(publication, 'command', lambda args, **_kwargs:
                        calls.append(args) or type('Result', (), {'stdout': json.dumps([{
                            'id': settings['machine_id'], 'config': actual,
                        }])})())
    with pytest.raises(publication.PublicationError, match='containers differ|unexpected candidate'):
        publication.readback_shared_runtime(settings, expected)
    assert len(calls) == 1 and calls[0] == ['fly', 'machine', 'list', '--app', 'farmtact', '--json']


@pytest.mark.parametrize('inventory', [[], [
    {'id': '1234567890abcd', 'config': {'containers': []}},
    {'id': '1234567890abcd', 'config': {'containers': []}},
]])
def test_post_snapshot_machine_readback_requires_one_exact_machine(monkeypatch, inventory):
    settings = {'app': 'farmtact', 'machine_id': '1234567890abcd'}
    expected = {'containers': [{'name': 'gateway', 'env': {}}]}
    monkeypatch.setattr(publication, 'command', lambda *_args, **_kwargs:
                        type('Result', (), {'stdout': json.dumps(inventory)})())
    with pytest.raises(publication.PublicationError, match='missing or duplicated'):
        publication.readback_shared_runtime(settings, expected)


def test_shared_probe_retries_transient_ssh_transport_then_preserves_exact_predicate(monkeypatch):
    calls = []; sleeps = []
    entry = {'id': 'v12', 'source_commit': 'a' * 40}
    settings = {'machine_id': '1234567890abcd'}

    def transient(args, **_kwargs):
        calls.append(args)
        if len(calls) == 1:
            raise subprocess.CalledProcessError(1, args)
        return type('Result', (), {'returncode': 0, 'stdout': '', 'stderr': ''})()

    monkeypatch.setattr(publication, 'command', transient)
    monkeypatch.setattr(publication.time, 'sleep', lambda seconds: sleeps.append(seconds))
    publication.probe_shared_edition(settings, entry)
    assert len(calls) == 2 and calls[0] == calls[1]
    assert sleeps == [2]
    probe = calls[0][-1]
    assert '127.0.0.1:8092/api/v1/health' in probe
    assert 'edition' in probe and 'v12' in probe
    assert 'source_commit' in probe and 'a' * 40 in probe
    assert 'status' in probe and 'ok' in probe


def test_shared_probe_raises_after_three_ssh_transport_failures(monkeypatch):
    calls = []; sleeps = []

    def unavailable(args, **_kwargs):
        calls.append(args)
        raise subprocess.CalledProcessError(1, args)

    monkeypatch.setattr(publication, 'command', unavailable)
    monkeypatch.setattr(publication.time, 'sleep', lambda seconds: sleeps.append(seconds))
    with pytest.raises(subprocess.CalledProcessError):
        publication.probe_shared_edition(
            {'machine_id': '1234567890abcd'},
            {'id': 'v12', 'source_commit': 'b' * 40},
        )
    assert len(calls) == 3
    assert sleeps == [2, 2]
