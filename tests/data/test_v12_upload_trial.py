from scripts.v12_upload_trial import merge_terminal_report, valid_actual_audit


def test_actual_audit_does_not_require_optional_provider_request_id():
    audit = {"provider": "deepseek", "inference_origin": "deepseek_api",
             "returned_model": "deepseek-chat", "input_sha256": "a" * 64,
             "latency_ms": 120, "usage": {"prompt_tokens": 10}, "request_id": None}
    assert valid_actual_audit(audit)
    assert not valid_actual_audit({**audit, "inference_origin": "fixture"})
    assert not valid_actual_audit({**audit, "input_sha256": "short"})
    assert not valid_actual_audit({**audit, "usage": {}})
    assert not valid_actual_audit({**audit, "usage": {"total_tokens": 0}})


def test_terminal_report_retains_incremental_paid_call_evidence():
    snapshot = {"status": "IN_PROGRESS", "invoice_evidence": {"audit": {"request_id": None}},
                "photo_evidence": {"rows": [{"visible_findings": ["label"]}]}}
    terminal = {"status": "PASS", "checks": {"photo_no_yield_authority": True}}
    merged = merge_terminal_report(snapshot, terminal)
    assert merged["status"] == "PASS" and merged["checks"] == terminal["checks"]
    assert merged["invoice_evidence"] == snapshot["invoice_evidence"]
    assert merged["photo_evidence"] == snapshot["photo_evidence"]
