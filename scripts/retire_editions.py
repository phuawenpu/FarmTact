#!/usr/bin/env python3
"""Inventory and optionally remove storage for historically published, inactive editions.

The default is a read-only JSON inventory. Applying a plan requires a separately
recorded recovery snapshot identifier and deletes only validated direct ``vN``
children of the configured shared-volume root.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat

EDITION = re.compile(r'v[1-9][0-9]*\Z')


def checksum_tree(path: Path) -> str:
    digest = hashlib.sha256()
    for item in sorted(path.rglob('*')):
        relative = item.relative_to(path).as_posix()
        info = item.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise RuntimeError(f'symlink is not allowed in edition storage: {relative}')
        digest.update(relative.encode() + b'\0')
        if item.is_file():
            with item.open('rb') as source:
                for block in iter(lambda: source.read(1024 * 1024), b''):
                    digest.update(block)
    return digest.hexdigest()


def build_plan(root: Path, history: dict, active: dict, staged: str | None = None) -> dict:
    if not root.is_absolute() or root == Path('/') or root.is_symlink():
        raise RuntimeError('storage root must be an absolute non-symlink directory')
    if set(active) != {'previous', 'latest'} or not active.get('latest'):
        raise RuntimeError('invalid active-edition manifest')
    published = {item['id'] for item in history['editions']}
    protected = {value for value in active.values() if value} | ({staged} if staged else set())
    if not protected <= published | ({staged} if staged else set()):
        raise RuntimeError('active manifest references unknown history')
    rows = []
    if root.exists():
        for path in sorted(root.iterdir()):
            if path.name in {'gateway', 'releases', 'credentials', 'budgets'}:
                continue
            if not EDITION.fullmatch(path.name) or path.name not in published:
                continue
            if path.is_symlink() or not path.is_dir():
                raise RuntimeError(f'unsafe edition storage: {path}')
            size = sum(item.stat().st_size for item in path.rglob('*') if item.is_file() and not item.is_symlink())
            action = 'protect' if path.name in protected else 'retire'
            rows.append({'edition': path.name, 'path': str(path), 'bytes': size,
                         'checksum': checksum_tree(path) if action == 'retire' else None, 'action': action})
    images = {item['id']: item.get('image_digest') for item in history['editions']}
    protected_digests = {images[edition] for edition in protected if edition in images}
    return {'schema': 'farmtact-retirement-plan-v1', 'root': str(root),
            'active': sorted(protected), 'entries': rows,
            'reclaimable_bytes': sum(row['bytes'] for row in rows if row['action'] == 'retire'),
            'images': [{'edition': edition, 'digest': digest,
                        'action': 'protect' if digest in protected_digests else 'candidate-if-unused'}
                       for edition, digest in images.items()]}


def resource_snapshot(root: Path) -> dict:
    usage = shutil.disk_usage(root if root.exists() else root.parent)
    memory = {}
    try:
        for line in Path('/proc/meminfo').read_text().splitlines():
            key, value = line.split(':', 1)
            if key in {'MemTotal', 'MemAvailable'}:
                memory[key] = value.strip()
    except OSError:
        pass
    try:
        load = Path('/proc/loadavg').read_text().split()[:3]
    except OSError:
        load = []
    try:
        processes = sum(1 for item in Path('/proc').iterdir() if item.name.isdigit())
    except OSError:
        processes = None
    return {'disk': {'total_bytes': usage.total, 'used_bytes': usage.used, 'free_bytes': usage.free},
            'memory': memory, 'load_1_5_15': load, 'process_count': processes}


def running_editions(runtime: dict) -> set[str]:
    containers = runtime.get('containers') if isinstance(runtime, dict) else None
    if containers is None and isinstance(runtime.get('config') if isinstance(runtime, dict) else None, dict):
        containers = runtime['config'].get('containers')
    if not isinstance(containers, list):
        raise RuntimeError('current runtime Machine configuration is required')
    names = {row.get('name') for row in containers if isinstance(row, dict)}
    return {name for name in names if isinstance(name, str) and EDITION.fullmatch(name)}


def apply_plan(plan: dict, root: Path, snapshot_id: str, *, active: dict, staged: str | None, runtime: dict) -> list[str]:
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{7,127}', snapshot_id):
        raise RuntimeError('a recorded recovery snapshot identifier is required')
    if set(active) != {'previous', 'latest'} or not active.get('latest'):
        raise RuntimeError('invalid current active-edition manifest')
    protected = {value for value in active.values() if value} | ({staged} if staged else set())
    running = running_editions(runtime)
    if not {value for value in active.values() if value} <= running:
        raise RuntimeError('active edition is missing from current runtime configuration')
    targets = {row['edition'] for row in plan.get('entries', []) if row.get('action') == 'retire'}
    if targets & (protected | running):
        raise RuntimeError('plan would remove an active, staged, or running edition')
    removed = []
    for row in plan['entries']:
        if row['action'] != 'retire':
            continue
        path = Path(row['path'])
        if path.parent != root or not EDITION.fullmatch(path.name) or path.is_symlink():
            raise RuntimeError('retirement target escaped the storage root')
        if not path.exists():
            continue
        if checksum_tree(path) != row['checksum']:
            raise RuntimeError(f'edition changed after inventory: {path.name}')
        shutil.rmtree(path)
        removed.append(path.name)
    return removed


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--history', type=Path, required=True)
    parser.add_argument('--active', type=Path, required=True)
    parser.add_argument('--staged')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--snapshot-id')
    parser.add_argument('--runtime-config', type=Path)
    args = parser.parse_args(argv)
    history = json.loads(args.history.read_text()); active = json.loads(args.active.read_text())
    plan = build_plan(args.root.resolve(), history, active, args.staged)
    result = {**plan, 'mode': 'dry-run', 'removed': [],
              'resources_before': resource_snapshot(args.root.resolve())}
    if args.apply:
        if args.runtime_config is None:
            raise RuntimeError('--runtime-config is required for apply')
        runtime = json.loads(args.runtime_config.read_text())
        # Re-read manifests at the mutation boundary rather than trusting inventory.
        current_active = json.loads(args.active.read_text())
        result.update(mode='applied', removed=apply_plan(plan, args.root.resolve(), args.snapshot_id or '',
                                                        active=current_active, staged=args.staged, runtime=runtime),
                      resources_after=resource_snapshot(args.root.resolve()))
    output = json.dumps(result, indent=2) + '\n'
    if args.output:
        pending = args.output.with_suffix(args.output.suffix + '.next')
        pending.write_text(output); os.replace(pending, args.output)
    else:
        print(output, end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
