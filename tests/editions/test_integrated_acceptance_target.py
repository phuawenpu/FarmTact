"""Operator acceptance credentials must never be sent beyond the exact candidate loopback."""
import pytest
from scripts.v15_acceptance_trial import run


@pytest.mark.parametrize("edition,base", [
    ("v16", "https://example.invalid"),
    ("v16", "http://127.0.0.1:8095"),
    ("v15", "http://127.0.0.1:8096"),
    ("v16", "http://localhost:8096"),
    ("v16", "http://127.0.0.1:8096@evil.invalid"),
    ("v0", "http://127.0.0.1:8080"),
    ("v16/../../x", "http://127.0.0.1:8096"),
])
def test_operator_trial_rejects_wrong_target_before_credentials(monkeypatch, edition, base):
    monkeypatch.delenv("FARMTACT_CONTROL_SECRET", raising=False)
    with pytest.raises(ValueError):
        run(base, operator=True, edition=edition)
