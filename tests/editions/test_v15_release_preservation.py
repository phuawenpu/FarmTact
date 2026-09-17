from scripts.v15_release_preservation import compare


def fixture():
    return {
        "captured_at_epoch": 100,
        "gateway": {
            "history": [{"id": "v14", "source_commit": "a" * 40, "image_digest": "image"}],
            "tables": {
                "reservations": [{"key": "r", "day": "2026-09-17", "requested": 2, "accepted": True, "released": 0}],
                "releases": [], "security": ["setting"], "budget": [{"key": "day", "day": "2026-09-17", "reserved": 2}],
                "rate": [{"key": "limit", "count": 4, "expires": 200}],
            },
        },
        "storage": {"editions": [{"id": "v14", "directory": True, "symlink": False, "files": 3, "bytes": 100}]},
    }


def test_allows_appended_history_records_and_increased_live_counter():
    before = fixture(); after = fixture(); after["captured_at_epoch"] = 110
    after["gateway"]["history"].append({"id": "v15", "source_commit": "b" * 40, "image_digest": "next"})
    after["gateway"]["tables"]["reservations"].append({"key": "new", "day": "2026-09-17", "requested": 1, "accepted": True, "released": 0})
    after["gateway"]["tables"]["rate"][0]["count"] = 5
    after["gateway"]["tables"]["budget"][0]["reserved"] = 3
    passed, checks = compare(before, after)
    assert passed
    assert all(checks.values())


def test_detects_reset_counter_changed_manifest_and_missing_retained_subtree():
    before = fixture(); after = fixture(); after["captured_at_epoch"] = 110
    after["gateway"]["history"][0]["source_commit"] = "b" * 40
    after["gateway"]["tables"]["rate"][0]["count"] = 0
    after["storage"]["editions"] = []
    passed, checks = compare(before, after)
    assert not passed
    assert not checks["immutable_history_prefix"]
    assert not checks["unexpired_abuse_counters_not_reset"]
    assert not checks["retained_edition_subtrees_present"]


def test_refuses_to_claim_retained_storage_without_operator_inventory():
    before = fixture(); after = fixture(); before["storage"] = after["storage"] = None
    passed, checks = compare(before, after)
    assert not passed
    assert checks["retained_storage_checked"] is False


def test_budget_change_must_equal_new_reservation_and_release_receipts():
    before = fixture(); after = fixture(); after["captured_at_epoch"] = 110
    after["gateway"]["tables"]["budget"][0]["reserved"] = 0
    passed, checks = compare(before, after)
    assert not passed
    assert checks["budget_change_matches_receipts"] is False


def test_newly_active_candidate_is_presence_checked_not_frozen_as_retired():
    before = fixture(); after = fixture(); after["captured_at_epoch"] = 110
    candidate = {"id": "v15", "directory": True, "symlink": False, "files": 4, "bytes": 120, "tree_sha256": "before"}
    before["storage"]["editions"].append(candidate)
    after["storage"]["editions"].append({**candidate, "tree_sha256": "after"})
    before["gateway"]["active"] = {"previous": None, "latest": "v14"}
    after["gateway"]["active"] = {"previous": None, "latest": "v15"}
    passed, checks = compare(before, after)
    assert passed
    assert checks["stable_retired_subtree_hashes"]
