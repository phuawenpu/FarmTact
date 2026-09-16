"""Deployment adapter for an exact-image container on the shared Fly Machine.

Only root sees the common volume. The original image entrypoint starts after its
own fixed data subtree is mounted and the common parent is removed. No app source
is patched. This file is injected by the deployment-owned Machine configuration.
"""
import json
import os
from pathlib import Path
import re
import stat
import subprocess


def _validate_registry(value: dict, label: str) -> None:
    if set(value) != {'latest', 'editions'} or not isinstance(value['editions'], list):
        raise RuntimeError(f'Invalid {label} release registry')
    ids = [row.get('id') for row in value['editions'] if isinstance(row, dict)]
    if (len(ids) != len(value['editions']) or len(set(ids)) != len(ids)
            or ids != [f'v{i}' for i in range(1, len(ids) + 1)]
            or value['latest'] != (ids[-1] if ids else None)):
        raise RuntimeError(f'Invalid {label} release registry')


def _validated_registry_action(previous: dict | None, incoming: dict, name: str) -> str:
    """Choose a registry write without allowing published history replacement."""
    _validate_registry(incoming, 'incoming')
    if previous is None:
        return 'write'
    _validate_registry(previous, 'existing')
    if (len(incoming['editions']) < len(previous['editions'])
            or incoming['editions'][:len(previous['editions'])] != previous['editions']):
        raise RuntimeError('Published edition history cannot be replaced')
    if len(incoming['editions']) == len(previous['editions']):
        if incoming != previous:
            raise RuntimeError('Published edition history cannot be replaced')
        return 'preserve'
    # The gateway owns atomic public cutover and must retain its current history
    # until publish_remote updates it. Edition containers need the verified full
    # history so their middleware can resolve the newly active edition on restart.
    return 'preserve' if name == 'gateway' else 'write'


def _registry_for_container(incoming: dict, incoming_active: dict, name: str) -> dict:
    """Exclude unpublished staged metadata from edition-local history."""
    if name == 'gateway':
        return incoming
    if set(incoming_active) != {'previous', 'latest'} or not re.fullmatch(r'v[1-9][0-9]?', str(incoming_active['latest'])):
        raise RuntimeError('Invalid active-edition manifest')
    ids = [row.get('id') for row in incoming.get('editions', []) if isinstance(row, dict)]
    try:
        cutoff = ids.index(incoming_active['latest']) + 1
    except ValueError as exc:
        raise RuntimeError('Active edition is absent from incoming release history') from exc
    editions = incoming['editions'][:cutoff]
    return {'latest': incoming_active['latest'], 'editions': editions}


def _atomic_json(path: Path, payload: dict) -> None:
    pending = path.with_suffix('.next')
    if pending.exists():
        pending.unlink()
    fd = os.open(pending, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
    with os.fdopen(fd, 'w') as output:
        output.write(json.dumps(payload, indent=2) + '\n')
        output.flush()
        os.fsync(output.fileno())
    pending.replace(path)
    fd = os.open(path.parent, os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def prepare(name: str):
    if os.geteuid() != 0:
        raise RuntimeError('Shared storage preparation requires root')
    if name != 'gateway' and not re.fullmatch(r'v[1-9][0-9]?', name):
        raise RuntimeError('Invalid fixed deployment container name')
    parent = Path('/persist')
    target = parent / name
    if not parent.is_mount():
        raise RuntimeError('Persistent Fly volume is not mounted')
    if target.is_symlink():
        raise RuntimeError('Edition storage must not be a symlink')
    target.mkdir(mode=0o700, exist_ok=True)
    info = target.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0:
        raise RuntimeError('Edition storage root must be owned by root')
    target.chmod(0o755)  # app may traverse its own root, not replace it
    data = Path('/data')
    if data.is_symlink() or data.is_mount():
        raise RuntimeError('Unexpected existing data mount')
    data.mkdir(exist_ok=True)
    subprocess.run(['mount', '--bind', str(target), '/data'], check=True)
    subprocess.run(['umount', '/persist'], check=True)
    if parent.is_mount() or any(parent.iterdir()) or not data.is_mount():
        raise RuntimeError('Shared storage parent remains visible')
    incoming = json.loads(Path('/opt/farmtact-shared-registry.json').read_text())
    incoming_active = json.loads(Path('/opt/farmtact-active.json').read_text())
    local_incoming = _registry_for_container(incoming, incoming_active, name)
    releases = data / 'releases'
    if releases.is_symlink():
        raise RuntimeError('Release directory must not be a symlink')
    releases.mkdir(mode=0o755, exist_ok=True)
    info = releases.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
        raise RuntimeError('Release directory must be protected and root-owned')
    manifest = releases / 'registry.json'
    if manifest.is_symlink():
        raise RuntimeError('Release registry must not be a symlink')
    previous = None
    if manifest.exists():
        info = manifest.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise RuntimeError('Release registry must be protected and root-owned')
        previous = json.loads(manifest.read_text())
    if _validated_registry_action(previous, local_incoming, name) == 'write':
        _atomic_json(manifest, local_incoming)
    active = releases / 'active.json'
    if not active.exists() or json.loads(active.read_text()) != incoming_active:
        _atomic_json(active, incoming_active)
    # Deployment aliases preserve old images' private-host allowlists and keep
    # edition/control traffic on localhost. Names and ports are not user input.
    aliases = ['farmtact-local-control.flycast'] + [f'farmtact-local-v{i}.flycast' for i in range(1, 100)]
    with open('/etc/hosts', 'a') as output:
        output.write('\n127.0.0.1 ' + ' '.join(aliases) + '\n')
    os.execv('/app/scripts/fly_entrypoint.sh', ['/app/scripts/fly_entrypoint.sh'])


if __name__ == '__main__':
    prepare(os.environ['FARMTACT_CONTAINER'])
