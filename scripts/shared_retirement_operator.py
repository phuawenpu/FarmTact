#!/usr/bin/env python3
"""Run bounded retirement inside the service-less shared-volume operator."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from scripts.retire_editions import main as retire


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('/persist'))
    parser.add_argument('--history-relative', type=Path, default=Path('gateway/releases/registry.json'))
    parser.add_argument('--active-relative', type=Path, default=Path('gateway/releases/active.json'))
    parser.add_argument('--public-relative', type=Path, default=Path('gateway/releases/public.json'))
    parser.add_argument('--staged')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--snapshot-id')
    parser.add_argument('--runtime-config', type=Path)
    args = parser.parse_args(argv)
    if os.geteuid() != 0:
        raise RuntimeError('shared-volume inventory requires a root operator container')
    root = args.root.resolve()
    if root != Path('/persist') or not root.is_mount():
        raise RuntimeError('operator requires the shared volume mounted at /persist')
    if (args.history_relative.is_absolute() or args.active_relative.is_absolute()
            or args.public_relative.is_absolute() or '..' in args.history_relative.parts
            or '..' in args.active_relative.parts or '..' in args.public_relative.parts):
        raise RuntimeError('manifest paths must stay within the shared volume')
    forwarded = ['--root', str(root), '--history', str(root / args.history_relative),
                 '--active', str(root / args.active_relative),
                 '--public-bundle', str(root / args.public_relative), '--output', str(args.output)]
    if args.staged: forwarded += ['--staged', args.staged]
    if args.apply:
        if args.runtime_config is None:
            raise RuntimeError('--runtime-config is required for apply')
        forwarded += ['--apply', '--snapshot-id', args.snapshot_id or '',
                      '--runtime-config', str(args.runtime_config)]
    return retire(forwarded)


if __name__ == '__main__':
    raise SystemExit(main())
