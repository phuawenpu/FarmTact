import pytest

import scripts.shared_retirement_operator as operator


def test_operator_rejects_non_shared_mount(tmp_path, monkeypatch):
    monkeypatch.setattr(operator.os, 'geteuid', lambda: 0)
    with pytest.raises(RuntimeError, match='mounted at /persist'):
        operator.main(['--root', str(tmp_path), '--output', str(tmp_path/'out')])


def test_operator_requires_root(tmp_path, monkeypatch):
    monkeypatch.setattr(operator.os, 'geteuid', lambda: 10001)
    with pytest.raises(RuntimeError, match='root operator'):
        operator.main(['--output', str(tmp_path/'out')])
