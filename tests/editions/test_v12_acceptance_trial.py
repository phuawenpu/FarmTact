import pytest

import scripts.v12_acceptance_trial as acceptance
from scripts.v12_acceptance_trial import API, main


def test_private_acceptance_allows_only_fixed_retained_and_candidate_ports(monkeypatch):
    monkeypatch.setenv('FARMTACT_CONTROL_SECRET', 's' * 40)
    clients = []
    try:
        clients.extend([API('http://127.0.0.1:8091', True), API('http://127.0.0.1:8092', True)])
        with pytest.raises(ValueError, match='8091/8092'):
            API('http://127.0.0.1:8090', True)
        with pytest.raises(ValueError, match='8091/8092'):
            API('https://farmtact.fly.dev/v12', True)
    finally:
        for client in clients: client.close()


def test_capacity_and_review_are_mutually_exclusive_without_http(tmp_path):
    report = tmp_path / 'report.json'
    assert main(['--capacity', '--review', '--report', str(report)]) == 1
    value = __import__('json').loads(report.read_text())
    assert value['status'] == 'FAIL'
    assert 'zero inference' in value['error']


def test_publisher_starts_candidate_without_advancing_public_active_manifest():
    source = (__import__('pathlib').Path(__file__).parents[2] / 'scripts/publish_edition.py').read_text()
    assert 'deploy_shared(updated, current_active, staged=args.edition)' in source
    assert source.index('deploy_shared(updated, current_active, staged=args.edition)') < source.index('publish_remote(updated, next_active')


def test_late_failure_preserves_completed_council_evidence(tmp_path, monkeypatch):
    class FakeAPI:
        def __init__(self, *_args, **_kwargs): pass
        def close(self): pass

    evidence = {'status': 'completed', 'request_count': 7, 'roles': ['Plan Reviewer']}

    def fail_after_review(_api, _review, progress, checkpoint):
        progress.update(stage='council_reviewed', session_id='session-1',
                        council=evidence, council_seconds=12.5,
                        checks={'actual_council_completed': True})
        checkpoint()
        raise RuntimeError('later correction failed')

    monkeypatch.setattr(acceptance, 'API', FakeAPI)
    monkeypatch.setattr(acceptance, 'journey', fail_after_review)
    report = tmp_path / 'acceptance.json'
    assert acceptance.main(['--review', '--report', str(report)]) == 1
    value = __import__('json').loads(report.read_text())
    assert value['status'] == 'FAIL'
    assert value['stage'] == 'council_reviewed'
    assert value['council'] == evidence
    assert value['checks']['actual_council_completed'] is True
