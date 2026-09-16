#!/usr/bin/env python3
"""Publish one immutable FarmTact edition.

Accept a pinned digest or build the committed candidate before publication.
Publication never resolves a mutable tag while deploying.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError


ROOT = Path(__file__).resolve().parents[1]
# File-style execution puts scripts/, rather than the repository, on sys.path.
# Shared-host helpers must resolve identically for both supported entrypoints.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
REGISTRY = ROOT / "config/releases/registry.json"
ACTIVE = ROOT / "config/releases/active.json"
STATE_NAME = "farmtact-publications.json"
EDITION = re.compile(r"v([1-9][0-9]*)\Z")
COMMIT = re.compile(r"[0-9a-f]{40}\Z")
IMAGE = re.compile(r"registry\.fly\.io/farmtact(?:-edition-v[1-9][0-9]*)?(?::[a-z0-9][a-z0-9._-]{0,127})?@sha256:[0-9a-f]{64}\Z")


class PublicationError(RuntimeError):
    pass


def command(args: list[str], *, input_text: str | None = None, input_bytes: bytes | None = None, check: bool = True) -> subprocess.CompletedProcess:
    if input_text is not None and input_bytes is not None:
        raise ValueError("Only one subprocess input form is allowed")
    return subprocess.run(
        args, cwd=ROOT, input=input_bytes if input_bytes is not None else input_text,
        text=input_bytes is None, capture_output=True, check=check,
    )


def git(*args: str) -> str:
    return command(["git", *args]).stdout.strip()


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise PublicationError(f"Invalid JSON file: {path}") from error
    if not isinstance(value, dict):
        raise PublicationError(f"JSON object required: {path}")
    return value


def validate_notes(notes: dict) -> None:
    if set(notes) != {"title", "summary", "changes"}:
        raise PublicationError("Notes require exactly title, summary and changes")
    if not all(isinstance(notes[key], str) and 1 <= len(notes[key]) <= limit for key, limit in (("title", 100), ("summary", 400))):
        raise PublicationError("Edition title or summary is invalid")
    changes = notes["changes"]
    if not isinstance(changes, list) or not 1 <= len(changes) <= 20:
        raise PublicationError("Edition changes must be a nonempty bounded list")
    for change in changes:
        if not isinstance(change, dict) or set(change) != {"title", "description", "feedback_ids", "evidence"}:
            raise PublicationError("Each change requires title, description, feedback_ids and evidence")
        if not isinstance(change["title"], str) or not 1 <= len(change["title"]) <= 120:
            raise PublicationError("Invalid change title")
        if not isinstance(change["description"], str) or not 1 <= len(change["description"]) <= 600:
            raise PublicationError("Invalid change description")
        for key in ("feedback_ids", "evidence"):
            if not isinstance(change[key], list) or len(change[key]) > 50 or not all(isinstance(item, str) and len(item) <= 300 for item in change[key]):
                raise PublicationError(f"Invalid change {key}")


def validate_registry(registry: dict) -> None:
    if set(registry) != {"latest", "editions"} or not isinstance(registry["editions"], list):
        raise PublicationError("Invalid release registry shape")
    ids = [item.get("id") for item in registry["editions"] if isinstance(item, dict)]
    if len(ids) != len(registry["editions"]) or len(ids) != len(set(ids)) or any(not isinstance(item, str) or not EDITION.fullmatch(item) for item in ids):
        raise PublicationError("Invalid release edition identifiers")
    numbers = [int(EDITION.fullmatch(item).group(1)) for item in ids]
    if numbers != list(range(1, len(numbers) + 1)) or registry["latest"] != (ids[-1] if ids else None):
        raise PublicationError("Release registry must be contiguous and ordered")


def append_only(old: dict, new: dict) -> None:
    validate_registry(old); validate_registry(new)
    if new["editions"][:len(old["editions"])] != old["editions"] or len(new["editions"]) != len(old["editions"]) + 1:
        raise PublicationError("Published registry history is immutable")


def validate_active(active: dict, history: dict) -> None:
    if set(active) != {'previous', 'latest'}:
        raise PublicationError('Invalid active-edition manifest')
    ids = [item['id'] for item in history['editions']]
    if active['latest'] not in ids or (active['previous'] is not None and active['previous'] not in ids):
        raise PublicationError('Active edition is absent from release history')
    if active['previous'] is not None and int(active['latest'][1:]) != int(active['previous'][1:]) + 1:
        raise PublicationError('Active editions must be consecutive')


def active_from_public(payload: dict) -> dict:
    active = {'previous': payload.get('previous'), 'latest': payload.get('latest')}
    if not {'latest','editions'} <= set(payload):
        raise PublicationError('Remote active manifest unavailable')
    if 'previous' not in payload:
        validate_registry(payload)  # Legacy full history; migrate to newest-only.
    return active


def remote_registry(origin: str) -> dict:
    if origin != "https://farmtact.fly.dev":
        raise PublicationError("Publication origin is fixed")
    request = Request(origin + "/api/releases/history", headers={"Accept": "application/json"})
    try:
        try:
            response = urlopen(request, timeout=10)
        except HTTPError as error:
            if error.code != 404: raise
            # One-time V11 gateway migration: the old public endpoint IS history.
            # validate_registry below rejects a truncated active-edition response.
            response = urlopen(Request(origin + "/api/releases", headers={"Accept":"application/json"}), timeout=10)
        with response:
            if response.status != 200 or int(response.headers.get("Content-Length", "0") or 0) > 1_000_000:
                raise PublicationError("Remote registry unavailable")
            body = response.read(1_000_001)
    except PublicationError:
        raise
    except Exception as error:
        raise PublicationError("Remote registry unavailable") from error
    if len(body) > 1_000_000:
        raise PublicationError("Remote registry response too large")
    try: result = json.loads(body)
    except json.JSONDecodeError as error: raise PublicationError("Remote registry is not JSON") from error
    validate_registry(result)
    return result


def remote_active(origin: str) -> dict:
    if origin != 'https://farmtact.fly.dev':
        raise PublicationError('Publication origin is fixed')
    try:
        with urlopen(Request(origin + '/api/releases', headers={'Accept': 'application/json'}), timeout=10) as response:
            payload = json.loads(response.read(1_000_001))
    except Exception as error:
        raise PublicationError('Remote active manifest unavailable') from error
    active = active_from_public(payload)
    return active


def state_path() -> Path:
    git_dir = Path(git("rev-parse", "--git-dir"))
    if not git_dir.is_absolute(): git_dir = ROOT / git_dir
    return git_dir / STATE_NAME


def load_state(path: Path) -> dict:
    if not path.exists(): return {"reservations": {}}
    state = load_json(path)
    if set(state) != {"reservations"} or not isinstance(state["reservations"], dict):
        raise PublicationError("Invalid local publication state")
    return state


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, sort_keys=True, indent=2) + "\n")
    os.replace(temporary, path)


def reserve_number(path: Path, edition: str, source_commit: str, image: str) -> dict:
    state = load_state(path); reservations = state["reservations"]
    existing = reservations.get(edition)
    identity = {"source_commit": source_commit, "image": image}
    if existing:
        if any(existing.get(key) != value for key, value in identity.items()):
            raise PublicationError("Edition number is already reserved with different inputs")
        if existing.get("stage") == "published":
            raise PublicationError("Published edition numbers cannot be reused")
        return state
    reservations[edition] = {**identity, "stage": "reserved", "reserved_at": datetime.now(timezone.utc).isoformat()}
    save_state(path, state)
    return state


def source_url(commit: str) -> str:
    remote = git("remote", "get-url", "origin")
    match = re.fullmatch(r"(?:https://github\.com/|git@github\.com:)([^/]+/[^/]+?)(?:\.git)?", remote)
    if not match: raise PublicationError("Origin must be a GitHub repository")
    return f"https://github.com/{match.group(1)}/commit/{commit}"


def make_entry(edition: str, notes: dict, image: str, commit: str, previous: dict) -> dict:
    prior = previous["editions"][-1] if previous["editions"] else None
    base = source_url(commit)
    prior_commit = prior.get("source_commit") if prior else None
    compare = ""
    if isinstance(prior_commit, str) and COMMIT.fullmatch(prior_commit):
        compare = base.rsplit("/commit/", 1)[0] + f"/compare/{prior_commit}...{commit}"
    return {
        "id": edition, "title": notes["title"], "published_at": datetime.now(timezone.utc).date().isoformat(),
        "summary": notes["summary"], "status": "published", "source_commit": commit,
        "source_url": base, "compare_url": compare, "image_digest": image,
        "review_url": f"/{edition}/review", "play_url": f"/{edition}/",
        "changes": [{**change, "status": "implemented"} for change in notes["changes"]],
    }


def fly_config(edition: str) -> str:
    return f'''app = "farmtact-edition-{edition}"
primary_region = "sin"
kill_signal = "SIGTERM"
kill_timeout = 90

[env]
  FARMTACT_EDITION = "{edition}"
  FARMTACT_CONTROL_URL = "http://farmtact.flycast"
  FARMTACT_EXECUTION_MODE = "test"
  FARMTACT_SECURE_COOKIES = "true"
  FARMTACT_PUBLIC_ORIGIN = "https://farmtact.fly.dev"
  FARMTACT_TRUST_FLY_PROXY = "true"
  FARMTACT_DATA_MODE = "synthetic_demo"
  FARMTACT_DATABASE_URL = "postgresql+psycopg://farmtact@/farmtact?host=/tmp/farmtact-pg"
  PYTHONUNBUFFERED = "1"

[[mounts]]
  source = "farmtact_data"
  destination = "/data"
  snapshot_retention = 7

[http_service]
  internal_port = 8080
  force_https = false
  auto_stop_machines = "off"
  auto_start_machines = true
  min_machines_running = 1

  [[http_service.checks]]
    interval = "30s"
    timeout = "5s"
    grace_period = "60s"
    method = "GET"
    path = "/api/v1/health"

[[vm]]
  cpu_kind = "shared"
  cpus = 1
  memory = "2gb"
'''


def deploy(edition: str, image: str, config: Path) -> None:
    app = f"farmtact-edition-{edition}"
    status = command(["fly", "status", "--app", app], check=False)
    creating = status.returncode != 0
    control_secret = os.environ.get("FARMTACT_CONTROL_SECRET")
    deepseek_secret = os.environ.get("DEEPSEEK_API_KEY")
    if creating and (not control_secret or not deepseek_secret):
        raise PublicationError("A new edition requires control and DeepSeek credentials in the publishing process")
    if creating:
        command(["fly", "apps", "create", app])
    staged = {key: value for key, value in (
        ("FARMTACT_CONTROL_SECRET", control_secret), ("DEEPSEEK_API_KEY", deepseek_secret),
    ) if value}
    if staged:
        # Secret material exists only in subprocess stdin. It never enters argv,
        # command output, the generated manifest, or publication records.
        payload = "".join(f"{key}={value}\n" for key, value in staged.items()).encode()
        command(["fly", "secrets", "import", "--stage", "--app", app], input_bytes=payload)
    ips = command(["fly", "ips", "list", "--app", app, "--json"])
    try:
        ip_rows = json.loads(ips.stdout)
    except json.JSONDecodeError as error:
        raise PublicationError("Fly IP inventory is invalid") from error
    if not isinstance(ip_rows, list):
        raise PublicationError("Fly IP inventory is invalid")
    parsed_ips = []
    for row in ip_rows:
        if not isinstance(row, dict):
            raise PublicationError("Fly IP inventory is invalid")
        address = row.get("Address")
        try: parsed_ips.append((row.get("Type"), ipaddress.ip_address(address)))
        except ValueError as error: raise PublicationError("Fly IP inventory is invalid") from error
    if any(not address.is_private or kind != "private_v6" for kind, address in parsed_ips):
        raise PublicationError("Edition app has a public or unrecognized IP allocation")
    if not any(kind == "private_v6" and address.version == 6 for kind, address in parsed_ips):
        command(["fly", "ips", "allocate-v6", "--private", "--app", app])
    volumes = command(["fly", "volumes", "list", "--app", app, "--json"])
    try:
        volume_rows = json.loads(volumes.stdout)
    except json.JSONDecodeError as error:
        raise PublicationError("Fly volume inventory is invalid") from error
    if not isinstance(volume_rows, list):
        raise PublicationError("Fly volume inventory is invalid")
    if not any(row.get("name") == "farmtact_data" and row.get("region") == "sin" for row in volume_rows if isinstance(row, dict)):
        command(["fly", "volumes", "create", "farmtact_data", "--app", app, "--region", "sin", "--size", "3", "--snapshot-retention", "7", "--yes"])
    command(["fly", "deploy", "--app", app, "--config", str(config), "--image", image, "--ha=false", "--no-public-ips", "--yes"])
    command(["fly", "status", "--app", app])
    source_commit = git("rev-parse", "HEAD")
    probe = "import json,urllib.request;u='http://" + app + ".flycast/api/v1/health';r=json.load(urllib.request.urlopen(u,timeout=10));assert r.get('status')=='ok' and r.get('source_commit')=='" + source_commit + "'"
    command(["fly", "ssh", "console", "--app", "farmtact", "--command", f"python -c \"{probe}\""])


def build_image(edition: str, source_commit: str) -> str:
    label = f"edition-{edition}-{source_commit[:12]}"
    result = command([
        "fly", "deploy", "--app", "farmtact", "--config", "config/releases/fly-gateway.toml",
        "--build-only", "--push", "--remote-only", "--image-label", label,
        "--build-arg", f"SOURCE_COMMIT={source_commit}",
    ])
    output = (result.stdout or "") + "\n" + (result.stderr or "")
    matches = re.findall(r"registry\.fly\.io/farmtact(?::[a-z0-9][a-z0-9._-]{0,127})?@(sha256:[0-9a-f]{64})", output)
    if len(set(matches)) != 1:
        raise PublicationError("Fly build did not report one pinned image digest")
    return "registry.fly.io/farmtact@" + matches[0]


def shared_settings():
    path = ROOT / 'config/hosting/shared.json'
    if not path.exists(): return None
    settings = load_json(path)
    if set(settings) != {'app','machine_id','volume_id'} or settings.get('app') != 'farmtact' or not re.fullmatch(r'[0-9a-f]{14}', settings.get('machine_id','')) or not re.fullmatch(r'vol_[a-z0-9]+', settings.get('volume_id','')):
        raise PublicationError('Invalid deployment-owned shared host configuration')
    return settings


def shared_ssh_args():
    settings = shared_settings()
    return ['--machine', settings['machine_id'], '--container', 'gateway'] if settings else []


def deploy_shared(updated, active, *, staged=None):
    from scripts.shared_host_config import machine_config
    settings = shared_settings()
    if not settings: raise PublicationError('Shared host is not configured')
    validate_active(active, updated)
    config = machine_config(updated, settings['volume_id'], active=active, staged=staged, public=True)
    update_shared_machine(settings, config)
    entry = updated['editions'][-1]
    probe_shared_edition(settings, entry)


def update_shared_machine(settings: dict, config: dict) -> None:
    with tempfile.TemporaryDirectory(prefix='farmtact-shared-publish-') as directory:
        path = Path(directory) / 'machine.json'
        path.write_text(json.dumps(config))
        command(['fly','machine','update',settings['machine_id'],'--app','farmtact','--machine-config',str(path),'--yes'])


def probe_shared_edition(settings: dict, entry: dict) -> None:
    # The public registry is still the previous edition until this probe passes.
    # Pinned server health is read via authenticated operator SSH on localhost.
    port = 8080 + int(entry['id'][1:])
    probe = "import json,time,urllib.request; deadline=time.monotonic()+150\nwhile True:\n try:\n  r=json.load(urllib.request.urlopen('http://127.0.0.1:"+str(port)+"/api/v1/health',timeout=5)); assert r.get('status')=='ok' and r.get('edition')=='"+entry['id']+"' and r.get('source_commit')=='"+entry['source_commit']+"'; break\n except Exception:\n  assert time.monotonic()<deadline; time.sleep(2)"
    import shlex
    args = ['fly','ssh','console','--app','farmtact','--machine',settings['machine_id'],
            '--container','gateway','--command','python -c '+shlex.quote(probe)]
    for attempt in range(3):
        try:
            command(args)
            return
        except subprocess.CalledProcessError:
            if attempt == 2:
                raise
            time.sleep(2)


def create_recovery_snapshot(settings: dict) -> str:
    before = snapshot_inventory(settings)
    previous_completed = {row['id'] for row in before if snapshot_ready(row)}
    scheduled_at = datetime.now(timezone.utc)
    result = command(['fly', 'volumes', 'snapshots', 'create', settings['volume_id'],
                      '--app', settings['app'], '--json'])
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        payload = None
    snapshot_id = payload.get('id') if isinstance(payload, dict) else None
    if isinstance(snapshot_id, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{7,127}', snapshot_id):
        wait_for_snapshot(settings, snapshot_id, earliest=scheduled_at - timedelta(minutes=5))
        return snapshot_id
    acknowledgement = result.stdout.strip()
    expected = f"Scheduled to snapshot volume {settings['volume_id']}"
    if acknowledgement != expected:
        raise PublicationError('Fly recovery snapshot did not return an identifier or exact scheduling acknowledgement')
    return wait_for_new_snapshot(settings, previous_completed, earliest=scheduled_at - timedelta(minutes=5))


def snapshot_inventory(settings: dict) -> list[dict]:
    result = command(['fly', 'volumes', 'snapshots', 'list', settings['volume_id'],
                      '--app', settings['app'], '--json'])
    try:
        rows = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise PublicationError('Fly recovery snapshot inventory is invalid') from error
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise PublicationError('Fly recovery snapshot inventory is invalid')
    return rows


def snapshot_ready(row: dict, *, earliest: datetime | None = None) -> bool:
    if str(row.get('status', '')).lower() not in {'created', 'complete', 'completed'}:
        return False
    if not isinstance(row.get('size'), int) or row['size'] <= 0:
        return False
    if not isinstance(row.get('digest'), str) or not re.fullmatch(r'[0-9a-f]{64}', row['digest']):
        return False
    try:
        created = datetime.fromisoformat(str(row.get('created_at', '')).replace('Z', '+00:00'))
    except ValueError:
        return False
    if created.tzinfo is None or created.year <= 1:
        return False
    return earliest is None or created.astimezone(timezone.utc) >= earliest


def shared_machine_runtime(settings: dict) -> dict:
    """Select the exact configured host from the supported Fly Machine inventory."""
    result = command(['fly', 'machine', 'list', '--app', settings['app'], '--json'])
    try:
        inventory = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise PublicationError('Current shared Machine configuration is invalid') from error
    if not isinstance(inventory, list):
        raise PublicationError('Current shared Machine inventory is invalid')
    matches = [row for row in inventory if isinstance(row, dict) and row.get('id') == settings['machine_id']]
    if len(matches) != 1:
        raise PublicationError('Configured shared Machine is missing or duplicated in Fly inventory')
    return matches[0]


def guard_shared_cleanup_runtime(settings: dict, history: dict, active: dict) -> dict:
    """Refuse to replace a Machine configuration containing a future candidate."""
    runtime = shared_machine_runtime(settings)
    config = runtime.get('config') if isinstance(runtime, dict) else None
    containers = config.get('containers') if isinstance(config, dict) else None
    if not isinstance(containers, list):
        raise PublicationError('Current shared Machine container inventory is required')
    history_ids = {entry['id'] for entry in history['editions']}
    active_ids = {edition for edition in active.values() if edition}
    for row in containers:
        if not isinstance(row, dict):
            raise PublicationError('Current shared Machine container inventory is invalid')
        name = row.get('name')
        if isinstance(name, str) and EDITION.fullmatch(name) and name not in history_ids:
            raise PublicationError(f'Cleanup refused while unpublished candidate {name} is running')
        env = row.get('env', {})
        if not isinstance(env, dict):
            raise PublicationError('Current shared Machine container environment is invalid')
        staged = env.get('FARMTACT_STAGED_EDITION')
        if staged and staged not in active_ids:
            raise PublicationError(f'Cleanup refused while unpublished candidate {staged} is staged')
    return runtime


def readback_shared_runtime(settings: dict, expected_config: dict) -> dict:
    """Read and verify the applied Machine configuration immediately before cleanup."""
    runtime = shared_machine_runtime(settings)
    actual = runtime.get('config')
    actual_containers = actual.get('containers') if isinstance(actual, dict) else None
    expected_containers = expected_config.get('containers')
    if not isinstance(actual_containers, list) or not isinstance(expected_containers, list):
        raise PublicationError('Applied shared Machine container inventory is required')
    actual_names = [row.get('name') for row in actual_containers if isinstance(row, dict)]
    expected_names = [row.get('name') for row in expected_containers if isinstance(row, dict)]
    if (len(actual_names) != len(actual_containers) or len(set(actual_names)) != len(actual_names)
            or set(actual_names) != set(expected_names)):
        raise PublicationError('Applied shared Machine containers differ from the retirement configuration')
    expected_editions = {name for name in expected_names if isinstance(name, str) and EDITION.fullmatch(name)}
    for row in actual_containers:
        env = row.get('env', {})
        if not isinstance(env, dict):
            raise PublicationError('Applied shared Machine container environment is invalid')
        staged = env.get('FARMTACT_STAGED_EDITION')
        if staged and staged not in expected_editions:
            raise PublicationError(f'Cleanup refused while unexpected candidate {staged} is staged')
    return runtime


def wait_for_snapshot(settings: dict, snapshot_id: str, *, attempts: int = 30, interval: float = 2,
                      earliest: datetime | None = None) -> None:
    """Require Fly to report a usable recovery point before deletion can start."""
    pending = {'pending', 'queued', 'creating', 'processing', 'running'}
    for attempt in range(attempts):
        matches = [row for row in snapshot_inventory(settings)
                   if (row.get('id') or row.get('snapshot_id')) == snapshot_id]
        if any(snapshot_ready(row, earliest=earliest) for row in matches):
            return
        for row in matches:
            status = row.get('status')
            if not isinstance(status, str):
                raise PublicationError('Fly recovery snapshot status is invalid')
            normalized = status.lower()
            if normalized not in pending and normalized not in {'created', 'complete', 'completed'}:
                raise PublicationError(f'Fly recovery snapshot failed with status {normalized}')
        if attempt + 1 < attempts:
            time.sleep(interval)
    raise PublicationError('Fly recovery snapshot did not become ready before timeout')


def wait_for_new_snapshot(settings: dict, previous_completed: set[str], *, earliest: datetime,
                          attempts: int = 30, interval: float = 2) -> str:
    for attempt in range(attempts):
        ready = {row['id'] for row in snapshot_inventory(settings)
                 if isinstance(row.get('id'), str)
                 and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{7,127}', row['id'])
                 and row['id'] not in previous_completed
                 and snapshot_ready(row, earliest=earliest)}
        if len(ready) == 1:
            return ready.pop()
        if len(ready) > 1:
            raise PublicationError('Fly recovery snapshot scheduling produced ambiguous completed snapshots')
        if attempt + 1 < attempts:
            time.sleep(interval)
    raise PublicationError('Fly scheduled recovery snapshot did not become ready before timeout')


def retire_oldest_shared(history: dict, active: dict) -> dict:
    """Stop the displaced worker, snapshot, reclaim its storage, and remove the operator.

    The authoritative public bundle is read again inside the operator at the
    mutation boundary. A failed apply leaves the service-less operator present so
    the same snapshot-backed operation can be inspected and resumed safely.
    """
    from scripts.shared_host_config import machine_config
    settings = shared_settings()
    if not settings:
        return {'status': 'not_shared'}
    validate_active(active, history)
    guard_shared_cleanup_runtime(settings, history, active)
    if active['previous'] is None:
        deploy_shared(history, active)
        return {'status': 'nothing_to_retire'}
    operator_config = machine_config(
        history, settings['volume_id'], active=active,
        retirement_operator=True, public=True,
    )
    # Updating to the active pair first stops the displaced worker. No storage is
    # touched until Fly has recorded a recovery snapshot of the shared volume.
    update_shared_machine(settings, operator_config)
    snapshot_id = create_recovery_snapshot(settings)
    # Read Fly's applied state after the update and completed snapshot. This is
    # the runtime evidence consumed by apply_plan, rather than the desired local
    # JSON, and is fetched as close to deletion as the operator upload permits.
    applied_runtime = readback_shared_runtime(settings, operator_config)
    with tempfile.TemporaryDirectory(prefix='farmtact-retirement-') as directory:
        runtime_path = Path(directory) / 'runtime.json'
        runtime_path.write_text(json.dumps(applied_runtime))
        command(
            ['fly', 'ssh', 'sftp', 'shell', '--app', settings['app'], '--machine',
             settings['machine_id'], '--container', 'retirement-operator'],
            input_text=f'put {runtime_path} /tmp/farmtact-runtime.json\n',
        )
    import shlex
    report = f"/persist/gateway/releases/retirement-{active['latest']}.json"
    invocation = (
        'cd /app && python -m scripts.shared_retirement_operator '
        f'--output {shlex.quote(report)} --runtime-config /tmp/farmtact-runtime.json '
        f'--apply --snapshot-id {shlex.quote(snapshot_id)}'
    )
    command(
        ['fly', 'ssh', 'console', '--app', settings['app'], '--machine',
         settings['machine_id'], '--container', 'retirement-operator',
         '--command', 'sh -c ' + shlex.quote(invocation)]
    )
    # Successful cleanup is followed by an exact active-pair config, removing
    # the privileged operator and re-probing the published latest edition.
    deploy_shared(history, active)
    return {'status': 'retired', 'snapshot_id': snapshot_id, 'report': report}


def publish_remote(registry: dict, active: dict, temporary: Path) -> None:
    validate_active(active, registry)
    temporary.write_text(json.dumps({'history': registry, 'active': active}, sort_keys=False, indent=2) + "\n")
    remote_tmp = "/data/releases/public.json.next"
    command(["fly", "ssh", "sftp", "shell", "--app", "farmtact", *shared_ssh_args()], input_text=f"put {temporary} {remote_tmp}\nquit\n")
    code = (
        "import json,os,shutil; p='/data/releases/registry.json'; q='/data/releases/active.json'; u='/data/releases/public.json'; n=u+'.next'; "
        "x=json.load(open(n)); a=json.load(open(p)); b=x['history']; c=x['active']; "
        "assert b['editions'][:-1]==a['editions'] and len(b['editions'])==len(a['editions'])+1; "
        "assert b['latest']==b['editions'][-1]['id']; assert c=={'previous':a['latest'],'latest':b['latest']}; "
        "shutil.copy2(p,p+'.previous'); shutil.copy2(q,q+'.previous'); "
        "os.replace(n,u); t=p+'.next'; open(t,'w').write(json.dumps(b)); os.replace(t,p); "
        "t=q+'.next'; open(t,'w').write(json.dumps(c)); os.replace(t,q)"
    )
    command(["fly", "ssh", "console", "--app", "farmtact", *shared_ssh_args(), "--command", f"python -c \"{code}\""])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edition")
    parser.add_argument("--notes", type=Path)
    parser.add_argument("--image")
    parser.add_argument("--source-commit")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume-cleanup", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.resume_cleanup:
            if any((args.edition, args.notes, args.image, args.source_commit, args.dry_run)):
                raise PublicationError('--resume-cleanup does not accept publication arguments')
            history = remote_registry('https://farmtact.fly.dev')
            active = remote_active('https://farmtact.fly.dev')
            result = retire_oldest_shared(history, active)
            publication_state = load_state(state_path())
            reservation = publication_state['reservations'].get(active['latest'])
            if reservation and reservation.get('stage') == 'published_cleanup_pending':
                reservation['stage'] = 'published'
                save_state(state_path(), publication_state)
            print(f"Completed retirement cleanup for {active['latest']}: {result['status']}.")
            return 0
        if args.edition is None or args.notes is None or args.source_commit is None:
            raise PublicationError('Edition, notes and source commit are required')
        match = EDITION.fullmatch(args.edition)
        if not match or not COMMIT.fullmatch(args.source_commit) or (args.image is not None and not IMAGE.fullmatch(args.image)):
            raise PublicationError("Edition, source commit or pinned image digest is invalid")
        if git("status", "--porcelain"):
            raise PublicationError("Publication requires a clean committed source tree")
        if git("rev-parse", "HEAD") != args.source_commit:
            raise PublicationError("Source commit must equal HEAD")
        notes = load_json(args.notes); validate_notes(notes)
        remote = remote_registry("https://farmtact.fly.dev")
        current_active = remote_active("https://farmtact.fly.dev")
        validate_active(current_active, remote)
        expected = len(remote["editions"]) + 1
        if int(match.group(1)) != expected:
            raise PublicationError(f"Next edition must be v{expected}")
        if REGISTRY.exists() and load_json(REGISTRY) != remote:
            raise PublicationError("Local registry must exactly match the published registry")
        if args.dry_run:
            print(f"Validated publication {args.edition}; no local, Fly or registry mutation performed.")
            return 0
        image = args.image or build_image(args.edition, args.source_commit)
        state_file = state_path()
        state = reserve_number(state_file, args.edition, args.source_commit, image)
        entry = make_entry(args.edition, notes, image, args.source_commit, remote)
        updated = {"latest": args.edition, "editions": [*remote["editions"], entry]}
        append_only(remote, updated)
        shared = shared_settings()
        config = ROOT / ('config/hosting/shared.json' if shared else f'config/releases/fly-{args.edition}.toml')
        if not shared:
            expected_config = fly_config(args.edition)
            if config.exists() and config.read_text() != expected_config:
                raise PublicationError("Edition Fly manifest exists with different contents")
            if not config.exists(): config.write_text(expected_config)
        cutover_complete = False
        try:
            next_active = {'previous': remote['latest'], 'latest': args.edition}
            if shared: deploy_shared(updated, current_active, staged=args.edition)
            else: deploy(args.edition, image, config)
            with tempfile.TemporaryDirectory(prefix="farmtact-publish-") as directory:
                publish_remote(updated, next_active, Path(directory) / "registry.json")
            cutover_complete = True
            REGISTRY.write_text(json.dumps(updated, indent=2) + "\n")
            ACTIVE.write_text(json.dumps(next_active, indent=2) + "\n")
            manifest = ROOT / f"config/releases/{args.edition}.json"
            manifest.write_text(json.dumps(entry, indent=2) + "\n")
            git("add", str(REGISTRY.relative_to(ROOT)), str(ACTIVE.relative_to(ROOT)), str(config.relative_to(ROOT)), str(manifest.relative_to(ROOT)))
            git("commit", "-m", f"Publish immutable FarmTact {args.edition}")
            git("tag", "-a", f"farmtact-{args.edition}", args.source_commit, "-m", f"FarmTact {args.edition} source")
            git("push", "origin", "HEAD", f"refs/tags/farmtact-{args.edition}")
            if shared:
                retire_oldest_shared(updated, next_active)
        except Exception:
            state["reservations"][args.edition]["stage"] = (
                "published_cleanup_pending" if cutover_complete else "failed"
            )
            save_state(state_file, state)
            raise
        state["reservations"][args.edition]["stage"] = "published"
        save_state(state_file, state)
        print(f"Published {args.edition} from the pinned source and image digest.")
        return 0
    except (PublicationError, subprocess.CalledProcessError) as error:
        print(f"Publication stopped: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
