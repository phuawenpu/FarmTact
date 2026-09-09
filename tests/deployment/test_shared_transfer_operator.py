"""Guard the operator boundary; never call Fly from these tests."""
import pytest
from scripts import migrate_shared_host as transfer


def test_only_fixed_farmtact_apps_and_original_machines_are_transferable():
    assert set(transfer.ORIGINAL)=={'gateway','v1','v2','v3','v4','v5'}
    assert transfer.flags('gateway','original')==['--app','farmtact','--machine','d8d2060c074438']
    for edition in ['v1','v2','v3','v4','v5']:
        assert transfer.flags(edition,'original')[1]=='farmtact-edition-'+edition
    with pytest.raises(ValueError):transfer.flags('unrelated-app','original')


def test_candidate_transfers_cannot_accidentally_select_original_gateway():
    assert transfer.flags('v5','candidate')==['--app','farmtact','--machine',transfer.CANDIDATE,'--container','v5']
    assert transfer.CANDIDATE not in {machine for _,machine in transfer.ORIGINAL.values()}


def test_source_process_freeze_record_is_never_copied():
    assert transfer.ARTIFACTS==('database.dump','fingerprint.json','cache.tar.gz')
    assert 'frozen.json' not in transfer.ARTIFACTS


def test_sftp_errors_fail_even_when_cli_exit_code_is_zero(monkeypatch):
    monkeypatch.setattr(transfer,'run',lambda *args:'Error: file exists')
    with pytest.raises(RuntimeError,match='did not complete'):transfer.sftp('v1','candidate',['put fixed fixed'])
