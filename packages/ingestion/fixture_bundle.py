"""Integrity-checked, project-authored public-source contract fixture installer."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from .context import _persist_context,refresh
from .http import HttpResponse
from .validation import validate_context


FIXTURE_SCHEMA_VERSION='farmtact-public-contract-fixture-1.0.0'
FIXTURE_LICENCE='CC0-1.0_project_authored_synthetic_fixture'
REQUIRED_SOURCES={'D01','D02','D03','D04','D05','D06'}


def validate_fixture_bundle(bundle_dir:Path|str)->dict[str,Any]:
    root=Path(bundle_dir)
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('schema_version')!=FIXTURE_SCHEMA_VERSION:
        raise ValueError('unsupported public contract fixture schema')
    if manifest.get('data_mode')!='synthetic_contract_fixture' or manifest.get('licence')!='CC0-1.0':
        raise ValueError('fixture bundle must be explicitly synthetic and redistributable')
    files=manifest.get('files')
    if not isinstance(files,dict) or set(files)!=REQUIRED_SOURCES:
        raise ValueError(f'fixture bundle requires exactly {sorted(REQUIRED_SOURCES)}')
    for source_id,descriptor in files.items():
        relative=Path(str(descriptor.get('path','')))
        if relative.is_absolute() or '..' in relative.parts or len(relative.parts)!=1:
            raise ValueError(f'unsafe fixture path for {source_id}')
        path=root/relative
        body=path.read_bytes()
        if len(body)!=descriptor.get('byte_count') or hashlib.sha256(body).hexdigest()!=descriptor.get('sha256'):
            raise ValueError(f'fixture integrity mismatch for {source_id}')
        payload=json.loads(body)
        if not isinstance(payload,dict) or 'Project-authored synthetic' not in str(payload.get('fixture_notice')):
            raise ValueError(f'fixture notice missing for {source_id}')
    build_time=datetime.fromisoformat(manifest['fixed_build_time'])
    if build_time.tzinfo is None:
        raise ValueError('fixture build time must be timezone-aware')
    return manifest


class FixtureBundleTransport:
    def __init__(self,bundle_dir:Path|str,manifest:dict[str,Any]):
        self.root=Path(bundle_dir);self.manifest=manifest

    def get(self,url:str,query:dict[str,str],timeout:float)->HttpResponse:
        if url.endswith('/rainfall'): source_id='D01'
        elif url.endswith('/air-temperature'): source_id='D02'
        elif url.endswith('/relative-humidity'): source_id='D03'
        elif url.endswith('/twenty-four-hr-forecast'): source_id='D04'
        elif url.endswith('/four-day-outlook'): source_id='D05'
        elif url.endswith('/T010002'): source_id='D06'
        else: raise ValueError(f'fixture bundle has no route for {url}')
        body=(self.root/self.manifest['files'][source_id]['path']).read_bytes()
        return HttpResponse(200,body,{'content-type':'application/json','date':'Fri, 11 Sep 2026 00:05:00 GMT'},url)


def install_fixture_bundle(bundle_dir:Path|str,destination:Path|str):
    """Normalize a self-contained fixture without network access.

    The normal production transforms are reused, then all source/snapshot labels
    are changed to synthetic fixture mode before the final artifacts are stored.
    """

    manifest=validate_fixture_bundle(bundle_dir)
    built_at=datetime.fromisoformat(manifest['fixed_build_time'])
    context=refresh(destination,include_singstat=True,include_power=False,now=built_at,
        transport=FixtureBundleTransport(bundle_dir,manifest))
    context.execution_mode='offline_public_contract_fixture'
    context.snapshots=[replace(snapshot,licence_state=FIXTURE_LICENCE) for snapshot in context.snapshots]
    for source in context.sources:
        source['data_mode']='synthetic_contract_fixture'
        source['status']='validated_contract_fixture'
        source['licence_state']=FIXTURE_LICENCE
        source['provider']=f"{source['provider']} contract shape (synthetic values)"
        source['freshness']='not_applicable_fixture'
        source['freshness_age_minutes']=None
    context.freshness=[{key:source.get(key) for key in ('source_id','source_time','retrieved_at','freshness','freshness_age_minutes')}
        for source in context.sources]
    context.quality=validate_context(context)
    context.quality['fixture_bundle']={
        'bundle_id':manifest['bundle_id'],'schema_version':manifest['schema_version'],
        'data_mode':manifest['data_mode'],'licence':manifest['licence'],'notice':manifest['notice'],
        'source_file_hashes':{key:value['sha256'] for key,value in sorted(manifest['files'].items())},
    }
    _persist_context(Path(destination),context)
    return context
