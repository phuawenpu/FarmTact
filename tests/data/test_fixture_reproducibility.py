import json
import shutil

import pytest

from packages.ingestion import get_public_context,install_fixture_bundle,rebuild,validate_fixture_bundle
from packages.ingestion.validation import registry_coverage


def test_registry_coverage_is_derived_versioned_and_contradictions_fail():
    coverage=registry_coverage()
    assert coverage['catalogue_profiles']==12
    assert coverage['scientific_evidence_documents']==24
    assert coverage['catalogue_version']=='2026-09-09.v2'
    assert len(coverage['catalogue_sha256'])==64
    contradictory={**coverage,'catalogue_profiles':10,'scientific_evidence_documents':20}
    with pytest.raises(ValueError,match='contradicts validated registries'):
        registry_coverage(declared=contradictory)


def test_project_authored_public_fixture_is_self_contained_and_offline_rebuildable(tmp_path):
    bundle='data/fixtures/public_context_v1'
    manifest=validate_fixture_bundle(bundle)
    assert manifest['licence']=='CC0-1.0'
    context=install_fixture_bundle(bundle,tmp_path)
    assert context.execution_mode=='offline_public_contract_fixture'
    assert context.quality['coverage']['catalogue_profiles']==12
    assert context.quality['coverage']['scientific_evidence_documents']==24
    assert context.quality['row_counts']['traceable_rows']==24
    assert all(row['data_mode']=='synthetic_contract_fixture' for row in context.sources)
    rebuilt=rebuild(tmp_path)
    assert rebuilt.execution_mode=='offline_fixture_snapshot_rebuild'
    assert rebuilt.quality['row_counts']==context.quality['row_counts']
    loaded=get_public_context(tmp_path)
    assert {row['freshness'] for row in loaded.sources}=={'not_applicable_fixture'}
    persisted=json.loads((tmp_path/'manifests/dataset_manifest.json').read_text())
    assert persisted['data_mode']=='synthetic_contract_fixture'
    assert persisted['rebuild_command'].endswith('--data-dir /tmp/farmtact-public-fixture')


def test_fixture_bundle_rejects_tampered_source_bytes(tmp_path):
    bundle=tmp_path/'bundle'
    shutil.copytree('data/fixtures/public_context_v1',bundle)
    path=bundle/'d01.json'
    path.write_text(path.read_text()+' ')
    with pytest.raises(ValueError,match='integrity mismatch'):
        validate_fixture_bundle(bundle)
