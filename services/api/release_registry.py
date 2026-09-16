"""Immutable release history and the small, mutable public edition set."""
import json
import os
import re
from urllib.parse import urlsplit
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EDITION = re.compile(r'v[1-9][0-9]*\Z')


def _public_bundle():
    path = Path(os.environ.get('FARMTACT_PUBLIC_RELEASES', '/data/releases/public.json'))
    if not path.is_file():
        return None
    data = json.loads(path.read_text())
    if set(data) != {'history', 'active'} or not isinstance(data['history'], dict) or not isinstance(data['active'], dict):
        raise ValueError('Invalid public release bundle')
    return data


def history_registry():
    bundle = _public_bundle()
    if bundle is not None:
        data = bundle['history']
        ids = [item['id'] for item in data['editions']]
        if len(set(ids)) != len(ids) or any(not EDITION.fullmatch(item) for item in ids):
            raise ValueError('Invalid release registry')
        return data
    path = Path(os.environ.get('FARMTACT_RELEASE_REGISTRY', '/data/releases/registry.json'))
    if not path.is_file():
        path = ROOT / 'config/releases/registry.json'
    data = json.loads(path.read_text())
    ids = [item['id'] for item in data['editions']]
    if len(set(ids)) != len(ids) or any(not EDITION.fullmatch(item) for item in ids):
        raise ValueError('Invalid release registry')
    return data


def registry():
    """Backward-compatible name for immutable publication history."""
    return history_registry()


def active_manifest(history=None):
    history = history or history_registry()
    bundle = _public_bundle()
    if bundle is not None:
        data = bundle['active']
    else:
        path = Path(os.environ.get('FARMTACT_ACTIVE_EDITIONS', '/data/releases/active.json'))
        if not path.is_file():
            path = ROOT / 'config/releases/active.json'
        # A missing active file fails safely to the newest published edition only.
        data = json.loads(path.read_text()) if path.is_file() else {
            'previous': None, 'latest': history['latest'],
        }
    if set(data) != {'previous', 'latest'}:
        raise ValueError('Invalid active-edition manifest')
    ids = [item['id'] for item in history['editions']]
    previous, latest = data['previous'], data['latest']
    if latest not in ids or (previous is not None and previous not in ids):
        raise ValueError('Active edition is absent from release history')
    if previous == latest:
        raise ValueError('Active editions must be distinct')
    if previous is not None and int(latest[1:]) != int(previous[1:]) + 1:
        raise ValueError('Active editions must be consecutive')
    return data


def active_registry():
    bundle = _public_bundle()
    if bundle is not None:
        history, active = bundle['history'], bundle['active']
        ids = [item['id'] for item in history.get('editions', [])]
        if len(set(ids)) != len(ids) or any(not EDITION.fullmatch(item) for item in ids):
            raise ValueError('Invalid release registry')
        if set(active) != {'previous', 'latest'} or active['latest'] not in ids:
            raise ValueError('Invalid active-edition manifest')
        if active['previous'] is not None and (active['previous'] not in ids or int(active['latest'][1:]) != int(active['previous'][1:]) + 1):
            raise ValueError('Invalid active-edition manifest')
    else:
        history = history_registry()
        active = active_manifest(history)
    wanted = {value for value in active.values() if value is not None}
    return {
        **active,
        'editions': [item for item in history['editions'] if item['id'] in wanted],
    }


def active_ids():
    active = active_registry()
    return frozenset(value for value in (active['previous'], active['latest']) if value is not None)


def upstream(edition):
    if not EDITION.fullmatch(edition):
        raise ValueError('Unknown edition')
    # Deployment-owned mapping only. Request parameters never become upstream URLs.
    overrides = json.loads(os.environ.get('FARMTACT_EDITION_UPSTREAMS', '{}'))
    value = overrides.get(edition, f'http://farmtact-edition-{edition}.flycast')
    parsed = urlsplit(value)
    if parsed.scheme != 'http' or not parsed.hostname or not parsed.hostname.endswith('.flycast') or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('', '/'):
        raise ValueError('Edition upstream must be a private Fly service')
    return value
