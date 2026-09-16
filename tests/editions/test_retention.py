import json

import pytest

from scripts.retire_editions import apply_plan, build_plan, load_public_manifests


def history(count=4):
    return {'latest': f'v{count}', 'editions': [{'id': f'v{i}'} for i in range(1, count + 1)]}


def test_inventory_protects_active_and_staged_and_counts_only_retired(tmp_path):
    for name in ('gateway', 'v1', 'v2', 'v3', 'v4'):
        path = tmp_path / name; path.mkdir(); (path / 'state').write_bytes(name.encode())
    plan = build_plan(tmp_path, history(), {'previous': 'v3', 'latest': 'v4'}, staged=None)
    actions = {row['edition']: row['action'] for row in plan['entries']}
    assert actions == {'v1': 'retire', 'v2': 'retire', 'v3': 'protect', 'v4': 'protect'}
    assert plan['reclaimable_bytes'] == len(b'v1') + len(b'v2')


def test_authoritative_public_bundle_is_required_and_loaded_atomically(tmp_path):
    bundle = tmp_path / 'public.json'
    history = {'latest': 'v2', 'editions': [{'id': 'v1'}, {'id': 'v2'}]}
    active = {'previous': 'v1', 'latest': 'v2'}
    bundle.write_text(json.dumps({'history': history, 'active': active}))
    assert load_public_manifests(bundle) == (history, active)
    bundle.write_text(json.dumps({'history': history, 'active': active, 'extra': True}))
    with pytest.raises(RuntimeError, match='invalid authoritative'):
        load_public_manifests(bundle)


def test_apply_requires_snapshot_and_rechecks_checksum(tmp_path):
    for name in ('v1', 'v2'):
        path = tmp_path / name; path.mkdir(); (path / 'state').write_text(name)
    plan = build_plan(tmp_path, history(2), {'previous': None, 'latest': 'v2'})
    runtime = {'containers': [{'name':'gateway'}, {'name':'v2'}]}
    with pytest.raises(RuntimeError, match='snapshot'):
        apply_plan(plan, tmp_path, '', active={'previous':None,'latest':'v2'}, staged=None, runtime=runtime)
    (tmp_path / 'v1' / 'state').write_text('changed')
    with pytest.raises(RuntimeError, match='changed'):
        apply_plan(plan, tmp_path, 'snapshot-1234', active={'previous':None,'latest':'v2'}, staged=None, runtime=runtime)
    assert (tmp_path / 'v1').exists() and (tmp_path / 'v2').exists()


def test_apply_never_deletes_active_storage(tmp_path):
    for name in ('v1', 'v2'):
        path = tmp_path / name; path.mkdir(); (path / 'state').write_text(name)
    plan = build_plan(tmp_path, history(2), {'previous': None, 'latest': 'v2'})
    assert apply_plan(plan, tmp_path, 'snapshot-1234', active={'previous':None,'latest':'v2'}, staged=None,
                      runtime={'containers':[{'name':'gateway'},{'name':'v2'}]}) == ['v1']
    assert not (tmp_path / 'v1').exists()
    assert (tmp_path / 'v2').exists()


def test_empty_active_manifest_cannot_create_or_apply_plan(tmp_path):
    (tmp_path/'v1').mkdir()
    with pytest.raises(RuntimeError, match='active-edition'):
        build_plan(tmp_path, history(1), {})


def test_stale_or_forged_plan_cannot_delete_current_active_or_running(tmp_path):
    for name in ('v1','v2'):
        path=tmp_path/name;path.mkdir();(path/'state').write_text(name)
    stale = build_plan(tmp_path, history(2), {'previous':None,'latest':'v2'})
    stale['entries'][0]['edition'] = 'v2'; stale['entries'][0]['path'] = str(tmp_path/'v2')
    with pytest.raises(RuntimeError, match='active, staged, or running'):
        apply_plan(stale,tmp_path,'snapshot-1234',active={'previous':None,'latest':'v2'},staged=None,
                   runtime={'containers':[{'name':'gateway'},{'name':'v2'}]})
    assert (tmp_path/'v2').exists()


def test_shared_image_digest_is_protected_when_retained_edition_uses_it(tmp_path):
    data=history(2); data['editions'][0]['image_digest']='same';data['editions'][1]['image_digest']='same'
    plan=build_plan(tmp_path,data,{'previous':None,'latest':'v2'})
    assert {row['action'] for row in plan['images']} == {'protect'}
