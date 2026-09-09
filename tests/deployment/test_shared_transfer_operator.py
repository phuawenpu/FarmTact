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


def test_namespace_control_uses_only_pinned_host_ssh_without_container(monkeypatch):
    calls=[]
    monkeypatch.setattr(transfer,'run',lambda args,stdin=None:calls.append(args) or 'verified')
    transfer.namespace_control('STOP')
    command=calls[0]
    assert command[:8]==[
        'fly','ssh','console','--app','farmtact','--machine',transfer.CANDIDATE,'--no-container',
    ]
    assert '--container' not in command
    assert command[-2]=='--command'
    assert command[-1].endswith(' namespace-control STOP')
    with pytest.raises(ValueError):transfer.namespace_control('KILL')


def test_namespace_script_never_reads_environment_and_validates_fixed_identity():
    source=(transfer.ROOT/'scripts/shared_namespace_control.sh').read_text()
    assert 'record=/run/farmtact-v6-namespace-freeze' in source
    assert '/environ' not in source
    assert 'NSpid:' in source and '$NF==1' in source
    assert 'awk \'$5=="/data" {print $4}\'' in source
    assert '/gateway|/v1|/v2|/v3|/v4|/v5' in source
    assert "grep -qx '/app/scripts/fly_boot.py'" in source
    assert 'sort -u | wc -l' in source
    assert 'kill -"$operation" "$pid"' in source
    assert "trap 'while read -r name pid started namespace; do kill -CONT" in source
    discovery=source[source.index('(set -C; : > "$record.next")'):source.index('test -f "$record"')]
    assert "trap 'rm -f \"$record.next\"' EXIT" in discovery
    assert discovery.index("trap 'rm -f") < discovery.index('mv "$record.next" "$record"')
    assert discovery.index('mv "$record.next" "$record"') < discovery.index('trap - EXIT')


def test_orchestrator_reports_recovery_without_auto_resuming_partial_restore():
    source=(transfer.ROOT/'scripts/migrate_shared_host.py').read_text()
    restore=source[source.index("elif a.operation=='freeze-restore':"):source.index("    else:",source.index("elif a.operation=='freeze-restore':"))]
    export=source[source.index("elif a.operation=='freeze-export':"):source.index("elif a.operation=='freeze-restore':")]
    assert 'PARTIAL RESTORE MAY HAVE OCCURRED; candidate remains frozen for inspection.' in restore
    assert 'python scripts/migrate_shared_host.py resume --target candidate' in restore
    assert "namespace_control('CONT')" not in restore
    assert 'RECOVERY REQUIRED: resume each selected original edition that froze' in export
    assert 'fly machine uncordon d8d2060c074438 --app farmtact' in export
    assert "for name in names:" in export
    assert "resume --target original --edition '+name" in export
