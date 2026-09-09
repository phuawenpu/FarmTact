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
    if manifest.exists():
        info = manifest.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise RuntimeError('Release registry must be protected and root-owned')
        previous = json.loads(manifest.read_text())
        if incoming['editions'][:len(previous['editions'])] != previous['editions']:
            raise RuntimeError('Published edition history cannot be replaced')
    pending = manifest.with_suffix('.next')
    fd = os.open(pending, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
    with os.fdopen(fd, 'w') as output:
        output.write(json.dumps(incoming, indent=2) + '\n')
        output.flush()
        os.fsync(output.fileno())
    pending.replace(manifest)
    fd = os.open(releases, os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    # Deployment aliases preserve old images' private-host allowlists and keep
    # edition/control traffic on localhost. Names and ports are not user input.
    aliases = ['farmtact-local-control.flycast'] + [f'farmtact-local-v{i}.flycast' for i in range(1, 100)]
    with open('/etc/hosts', 'a') as output:
        output.write('\n127.0.0.1 ' + ' '.join(aliases) + '\n')
    os.execv('/app/scripts/fly_entrypoint.sh', ['/app/scripts/fly_entrypoint.sh'])


if __name__ == '__main__':
    prepare(os.environ['FARMTACT_CONTAINER'])
