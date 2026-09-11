#!/usr/bin/env python3
"""Reproduce FarmTact's bounded offline data path in a clean temporary directory."""
from __future__ import annotations

from datetime import datetime,timezone
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

REPOSITORY_ROOT=Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0,str(REPOSITORY_ROOT))

from packages.contracts import content_hash
from packages.fixtures import synthetic_farm
from packages.ingestion import install_fixture_bundle,rebuild,validate_fixture_bundle
from packages.ingestion.storage import write_json_atomic
from scripts.build_features import build as build_features


SCHEMA_VERSION='farmtact-data-pipeline-verification-1.0.0'


def verify()->dict:
    bundle_path=REPOSITORY_ROOT/'data/fixtures/public_context_v1'
    bundle=validate_fixture_bundle(bundle_path)
    farm=synthetic_farm()
    with TemporaryDirectory(prefix='farmtact-data-verification-') as directory:
        destination=Path(directory)
        first=install_fixture_bundle(bundle_path,destination)
        first_manifest=json.loads((destination/'manifests/dataset_manifest.json').read_text())
        feature_manifest=build_features(farm,destination)
        second=rebuild(destination)
        second_manifest=json.loads((destination/'manifests/dataset_manifest.json').read_text())
    checks={
        'fixture_source_hashes_verified':True,
        'normalized_dataset_id_stable':first_manifest['dataset_id']==second_manifest['dataset_id'],
        'normalized_artifact_hashes_stable':first_manifest['artifacts']==second_manifest['artifacts'],
        'normalized_row_counts_stable':first.quality['row_counts']==second.quality['row_counts'],
        'registry_counts_current':first.quality['coverage']['catalogue_profiles']==12 and first.quality['coverage']['scientific_evidence_documents']==24,
        'original_private_fixture_hash_preserved':content_hash(farm)=='00286779541fa9ed1245ea2aff65d08c1a05241cdc6a399706aa6601fdbc3f76',
        'public_context_excluded_from_numerical_features':feature_manifest['public_features_used']==[],
    }
    return {
        'schema_version':SCHEMA_VERSION,'generated_at':datetime.now(timezone.utc).isoformat(),
        'status':'PASS' if all(checks.values()) else 'FAIL','mode':'offline_synthetic_contract_fixture',
        'checks':checks,'bundle':{'bundle_id':bundle['bundle_id'],'licence':bundle['licence'],
            'notice':bundle['notice'],'source_count':len(bundle['files']),
            'source_hashes':{key:value['sha256'] for key,value in sorted(bundle['files'].items())}},
        'normalized':{'dataset_id':first_manifest['dataset_id'],'row_counts':first.quality['row_counts'],
            'artifact_hashes':{key:value['sha256'] for key,value in sorted(first_manifest['artifacts'].items())},
            'registry_coverage':first.quality['coverage']},
        'private_features':feature_manifest,
        'limitations':['The public bundle contains project-authored synthetic contract values, not current public observations.',
            'The historical September 2026 real-public manifest remains an archive; its ignored raw snapshots are not reconstructed or redistributed.',
            'No public context value enters demand or harvest calculations.'],
        'rebuild_commands':['python scripts/verify_data_pipeline.py',
            'python scripts/build_dataset.py --fixture-bundle data/fixtures/public_context_v1 --data-dir <destination>',
            'python scripts/build_dataset.py --offline --data-dir <destination>'],
    }


def main()->int:
    output=REPOSITORY_ROOT/'reports/v8/data_pipeline_verification.json'
    report=verify();write_json_atomic(output,report)
    print(json.dumps({'status':report['status'],'report':str(output)},sort_keys=True))
    return 0 if report['status']=='PASS' else 2


if __name__=='__main__':
    raise SystemExit(main())
