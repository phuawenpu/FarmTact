"""Curated public release metadata, separate from private routing configuration."""
import json
import os
import re
from urllib.parse import urlsplit
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EDITION = re.compile(r'v[1-9][0-9]*\Z')


def registry():
    path = Path(os.environ.get('FARMTACT_RELEASE_REGISTRY', '/data/releases/registry.json'))
    if not path.is_file():
        path = ROOT / 'config/releases/registry.json'
    data = json.loads(path.read_text())
    ids = [item['id'] for item in data['editions']]
    if len(set(ids)) != len(ids) or any(not EDITION.fullmatch(item) for item in ids):
        raise ValueError('Invalid release registry')
    return data


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
