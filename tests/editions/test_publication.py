import json
from pathlib import Path
import subprocess
import sys

import pytest

import scripts.publish_edition as publication


def test_file_entrypoint_resolves_shared_host_helper_outside_repo(tmp_path):
    script = str(publication.ROOT / "scripts/publish_edition.py")
    code = (
        "import runpy; runpy.run_path(" + repr(script) + "); "
        "from scripts.shared_host_config import machine_config; "
        "assert callable(machine_config)"
    )
    subprocess.run([sys.executable, "-I", "-c", code], cwd=tmp_path, check=True)


def registry(count=2):
    editions = [{"id": f"v{i}", "title": f"Edition {i}"} for i in range(1, count + 1)]
    return {"latest": f"v{count}", "editions": editions}


def notes():
    return {"title": "Third edition", "summary": "A frozen release.", "changes": [{"title": "Change", "description": "Bounded change.", "feedback_ids": [], "evidence": []}]}


def test_registry_append_is_strictly_immutable():
    old = registry()
    new = {"latest": "v3", "editions": [*old["editions"], {"id": "v3", "title": "Third"}]}
    publication.append_only(old, new)
    changed = json.loads(json.dumps(new)); changed["editions"][0]["title"] = "Rewritten"
    with pytest.raises(publication.PublicationError, match="immutable"):
        publication.append_only(old, changed)
    with pytest.raises(publication.PublicationError):
        publication.validate_registry({"latest": "v3", "editions": [{"id": "v1"}, {"id": "v3"}]})


def test_failed_local_reservation_cannot_change_identity(tmp_path):
    state = tmp_path / "state.json"
    commit = "a" * 40; image = "registry.fly.io/farmtact@sha256:" + "b" * 64
    value = publication.reserve_number(state, "v3", commit, image)
    value["reservations"]["v3"]["stage"] = "failed"; publication.save_state(state, value)
    assert publication.reserve_number(state, "v3", commit, image)["reservations"]["v3"]["stage"] == "failed"
    with pytest.raises(publication.PublicationError, match="different inputs"):
        publication.reserve_number(state, "v3", "c" * 40, image)
    value["reservations"]["v3"]["stage"] = "published"; publication.save_state(state, value)
    with pytest.raises(publication.PublicationError, match="cannot be reused"):
        publication.reserve_number(state, "v3", commit, image)


def test_notes_and_image_are_bounded_and_pinned():
    publication.validate_notes(notes())
    with pytest.raises(publication.PublicationError): publication.validate_notes({**notes(), "extra": True})
    assert publication.IMAGE.fullmatch("registry.fly.io/farmtact@sha256:" + "0" * 64)
    assert not publication.IMAGE.fullmatch("registry.fly.io/farmtact:latest")


def test_deploy_uses_fixed_app_private_probe_and_exact_digest(tmp_path, monkeypatch):
    calls = []
    def fake(args, **kwargs):
        calls.append((args, kwargs))
        is_first_status = args[:2] == ["fly", "status"] and len(calls) == 1
        output = "[]" if args[:3] in (["fly", "volumes", "list"], ["fly", "ips", "list"]) else ""
        return type("Result", (), {"returncode": 1 if is_first_status else 0, "stdout": output, "stderr": ""})()
    monkeypatch.setattr(publication, "command", fake)
    monkeypatch.setenv("FARMTACT_CONTROL_SECRET", "control-value")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "provider-value")
    image = "registry.fly.io/farmtact@sha256:" + "d" * 64
    publication.deploy("v3", image, tmp_path / "fly-v3.toml")
    flattened = [item for call, _kwargs in calls for item in call]
    assert image in flattened
    assert "farmtact-edition-v3" in flattened
    assert ["fly", "volumes", "list", "--app", "farmtact-edition-v3", "--json"] in [call for call, _ in calls]
    assert any(call[:3] == ["fly", "volumes", "create"] for call, _ in calls)
    assert ["fly", "apps", "create", "farmtact-edition-v3"] in [call for call, _ in calls]
    assert any(call[:3] == ["fly", "ips", "allocate-v6"] and "--private" in call for call, _ in calls)
    assert any(call[:2] == ["fly", "deploy"] and "--no-public-ips" in call for call, _ in calls)
    assert any("farmtact-edition-v3.flycast/api/v1/health" in item for call, _ in calls for item in call)
    assert any("r.get('source_commit')" in item for call, _ in calls for item in call)
    assert all("control-value" not in item and "provider-value" not in item for item in flattened)
    secret_call = next((call, kwargs) for call, kwargs in calls if call[:3] == ["fly", "secrets", "import"])
    assert secret_call[1]["input_bytes"] == b"FARMTACT_CONTROL_SECRET=control-value\nDEEPSEEK_API_KEY=provider-value\n"


def test_new_app_fails_before_provision_without_runtime_credentials(tmp_path, monkeypatch):
    calls = []
    def fake(args, **kwargs):
        calls.append(args)
        return type("Result", (), {"returncode": 1, "stdout": "", "stderr": ""})()
    monkeypatch.setattr(publication, "command", fake)
    monkeypatch.delenv("FARMTACT_CONTROL_SECRET", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(publication.PublicationError, match="requires control and DeepSeek"):
        publication.deploy("v3", "registry.fly.io/farmtact@sha256:" + "e" * 64, tmp_path / "fly.toml")
    assert calls == [["fly", "status", "--app", "farmtact-edition-v3"]]


def test_build_path_returns_only_reported_pinned_digest(monkeypatch):
    digest = "registry.fly.io/farmtact@sha256:" + "f" * 64
    reported = "registry.fly.io/farmtact:edition-v3-aaaaaaaaaaaa@sha256:" + "f" * 64
    calls = []
    def fake(args, **kwargs):
        calls.append(args)
        return type("Result", (), {"returncode": 0, "stdout": f"pushed {reported}\n", "stderr": ""})()
    monkeypatch.setattr(publication, "command", fake)
    commit = "a" * 40
    assert publication.build_image("v3", commit) == digest
    assert calls == [[
        "fly", "deploy", "--app", "farmtact", "--config", "config/releases/fly-gateway.toml",
        "--build-only", "--push", "--remote-only", "--image-label", "edition-v3-aaaaaaaaaaaa",
        "--build-arg", f"SOURCE_COMMIT={commit}",
    ]]


def test_public_ip_inventory_stops_before_deploy(tmp_path, monkeypatch):
    calls = []
    def fake(args, **kwargs):
        calls.append(args)
        output = '[{"Type":"public_v6","Address":"2a09:dead::1"}]' if args[:3] == ["fly", "ips", "list"] else '[]'
        return type("Result", (), {"returncode": 0, "stdout": output, "stderr": ""})()
    monkeypatch.setattr(publication, "command", fake)
    with pytest.raises(publication.PublicationError, match="public or unrecognized IP"):
        publication.deploy("v3", "registry.fly.io/farmtact@sha256:" + "d" * 64, tmp_path / "fly.toml")
    assert not any(call[:2] == ["fly", "deploy"] for call in calls)


def test_remote_publish_uploads_temp_then_runs_fixed_validator(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(publication, "command", lambda args, **kwargs: calls.append((args, kwargs)) or type("Result", (), {"returncode": 0})())
    publication.publish_remote(registry(3), {'previous':'v2','latest':'v3'}, tmp_path / "next.json")
    assert calls[0][0][:4] == ["fly", "ssh", "sftp", "shell"]
    assert "/data/releases/public.json.next" in calls[0][1]["input_text"]
    assert calls[1][0][:4] == ["fly", "ssh", "console", "--app"]
    assert "os.replace(n,u)" in calls[1][0][-1]
    assert "p+'.previous'" in calls[1][0][-1]
    assert "q+'.previous'" in calls[1][0][-1]


def test_fly_manifest_has_isolated_app_volume_and_control():
    text = publication.fly_config("v7")
    assert 'app = "farmtact-edition-v7"' in text
    assert 'FARMTACT_EDITION = "v7"' in text
    assert 'FARMTACT_CONTROL_URL = "http://farmtact.flycast"' in text
    assert 'source = "farmtact_data"' in text
    assert "DEEPSEEK_API_KEY" not in text and "FARMTACT_CONTROL_SECRET" not in text
