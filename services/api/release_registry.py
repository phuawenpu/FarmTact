"""Immutable release history and the small, mutable public edition set."""
import json
import os
import re
from urllib.parse import urlsplit
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EDITION = re.compile(r'v[1-9][0-9]*\Z')
LATEST_ONLY_FROM = 14


def edition_number(edition: str) -> int:
    if not EDITION.fullmatch(edition):
        raise ValueError('Invalid edition identifier')
    return int(edition[1:])


def latest_only_policy(active: dict) -> bool:
    """Whether the published application has switched to one public runtime."""
    latest = active.get('latest') if isinstance(active, dict) else None
    return isinstance(latest, str) and EDITION.fullmatch(latest) is not None and edition_number(latest) >= LATEST_ONLY_FROM


def _validate_active(data: dict, ids: list[str]) -> dict:
    if set(data) != {'previous', 'latest'}:
        raise ValueError('Invalid active-edition manifest')
    previous, latest = data['previous'], data['latest']
    if latest not in ids or (previous is not None and previous not in ids):
        raise ValueError('Active edition is absent from release history')
    if previous == latest:
        raise ValueError('Active editions must be distinct')
    if edition_number(latest) >= LATEST_ONLY_FROM:
        if previous is not None:
            raise ValueError('V14 and later expose only the latest public edition')
    elif previous is not None and edition_number(latest) != edition_number(previous) + 1:
        raise ValueError('Active editions must be consecutive')
    return data


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
    ids = [item['id'] for item in history['editions']]
    return _validate_active(data, ids)


def active_registry():
    bundle = _public_bundle()
    if bundle is not None:
        history, active = bundle['history'], bundle['active']
        ids = [item['id'] for item in history.get('editions', [])]
        if len(set(ids)) != len(ids) or any(not EDITION.fullmatch(item) for item in ids):
            raise ValueError('Invalid release registry')
        _validate_active(active, ids)
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
