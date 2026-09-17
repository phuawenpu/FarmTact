"""Independent invariants for the exact-image shared-host deployment."""
import copy
import json
from pathlib import Path

import pytest

import scripts.publish_edition as publication
from scripts import shared_container_entrypoint as entrypoint
from scripts.shared_host_config import GATEWAY_IMAGE, machine_config


ROOT = Path(__file__).resolve().parents[2]


def registry():
    return json.loads((ROOT / "config/releases/registry.json").read_text())


def active(source=None):
    source = source or registry()
    return {'previous': None, 'latest': source['latest']}


def test_config_retains_registry_images_and_bounds_one_machine():
    source = registry()
    config = machine_config(source, "vol_review123", active=active(source), public=True)
    containers = {row["name"]: row for row in config["containers"]}

    assert config["guest"] == {"cpu_kind": "shared", "cpus": 4, "memory_mb": 4096}
    assert config["mounts"] == [{"volume": "vol_review123", "path": "/persist"}]
    assert config["services"][0]["internal_port"] == 8080
    expected_gateway = source['editions'][-1]['image_digest'] if int(source['latest'][1:]) >= 11 else GATEWAY_IMAGE
    assert containers["gateway"]["image"] == expected_gateway
    assert {name: row["image"] for name, row in containers.items() if name != "gateway"} == {
        source['latest']: source['editions'][-1]['image_digest']
    }
    assert len(containers) == 2
    assert all(row["entrypoint"] == ["python", "/opt/farmtact-shared-entrypoint.py"] for row in containers.values())
    assert all(row["files"][0]["guest_path"] == "/opt/farmtact-shared-entrypoint.py" for row in containers.values())


def test_v14_config_runs_latest_only_without_historical_upstreams():
    source = copy.deepcopy(registry())
    source['editions'] = source['editions'][:13]
    source['latest'] = 'v13'
    candidate = copy.deepcopy(source['editions'][-1])
    candidate.update(id='v14', image_digest='registry.fly.io/farmtact@sha256:' + 'e' * 64)
    source['editions'].append(candidate); source['latest'] = 'v14'
    config = machine_config(source, 'vol_review123', active={'previous': None, 'latest': 'v14'}, public=True)
    rows = {row['name']: row for row in config['containers']}
    assert set(rows) == {'gateway', 'v14'}
    upstreams = json.loads(rows['gateway']['env']['FARMTACT_EDITION_UPSTREAMS'])
    assert set(upstreams) == {'v14'}
    assert rows['gateway']['healthchecks'][0]['tcp'] == {'port':8080}
    assert 'http' not in rows['gateway']['healthchecks'][0]
    assert rows['v14']['healthchecks'][0]['http']['path'] == '/api/v1/health'
    assert config['services'][0]['checks'][0]['headers'] == [{'name':'Fly-Client-IP','values':['127.0.0.1']}]
    with pytest.raises(ValueError, match='only the latest'):
        machine_config(source, 'vol_review123', active={'previous': 'v13', 'latest': 'v14'}, public=True)


def test_private_probe_relay_is_service_less_and_never_enters_public_config():
    private = machine_config(registry(), "vol_review123", active=active(), public=False, origin="http://127.0.0.1:8088")
    public = machine_config(registry(), "vol_review123", active=active(), public=True)
    private_rows = {row["name"]: row for row in private["containers"]}

    assert "services" not in private
    assert "private-relay" in private_rows
    assert all(row.get("env", {}).get("FARMTACT_TRUST_FLY_PROXY") == "false" for name, row in private_rows.items() if name != "private-relay")
    assert private_rows["private-relay"]["entrypoint"] == ["python", "/opt/farmtact-probe-relay.py"]
    assert private_rows["private-relay"]["depends_on"] == [{"name": "gateway", "condition": "healthy"}]
    assert "private-relay" not in {row["name"] for row in public["containers"]}
    assert len(public["containers"]) == 2
    assert all(row["env"]["FARMTACT_TRUST_FLY_PROXY"] == "true" for row in public["containers"])

    relay_source = (ROOT / "scripts/shared_probe_relay.py").read_text()
    assert "subprocess.run(['umount','/persist'],check=True)" in relay_source
    assert "any(Path('/persist').iterdir())" in relay_source
    assert "os.setgroups([]);os.setgid(account.pw_gid);os.setuid(account.pw_uid)" in relay_source
    assert "Server(('fly-local-6pn',8080), Handler)" in relay_source
    assert "socket.IPV6_V6ONLY" in relay_source


def test_retirement_operator_is_explicit_service_less_and_secret_free():
    source = registry()
    config = machine_config(source, 'vol_review123', active=active(source),
                            retirement_operator=True, public=True)
    row = next(item for item in config['containers'] if item['name'] == 'retirement-operator')
    assert row['entrypoint'] == ['sleep', 'infinity']
    assert 'secrets' not in row and 'env' not in row and 'healthchecks' not in row
    assert all(service['internal_port'] == 8080 for service in config['services'])


def test_ports_aliases_and_local_control_are_fixed_by_edition():
    source = registry(); current = source['latest']
    config = machine_config(source, "vol_review123", active=active(source))
    containers = {row["name"]: row for row in config["containers"]}
    upstreams = json.loads(containers["gateway"]["env"]["FARMTACT_EDITION_UPSTREAMS"])

    assert containers["gateway"]["env"]["FARMTACT_PORT"] == "8080"
    for index in (int(current[1:]),):
        name = f"v{index}"
        assert containers[name]["env"]["FARMTACT_PORT"] == str(8080 + index)
        assert upstreams[name] == f"http://farmtact-local-{name}.flycast:{8080 + index}"
        assert containers[name]["env"]["FARMTACT_CONTROL_URL"] == "http://farmtact-local-control.flycast:8080"
        assert containers[name]["depends_on"] == [{"name": "gateway", "condition": "healthy"}]


@pytest.mark.parametrize("bad_id", ["v0", "v01", "v100", "../../data", "gateway"])
def test_registry_namespace_is_contiguous_and_bounded(bad_id):
    source = registry()
    source["editions"][0]["id"] = bad_id
    with pytest.raises(ValueError, match="contiguous bounded"):
        machine_config(source, "vol_review123")


@pytest.mark.parametrize(
    "image",
    [
        "registry.fly.io/farmtact:latest",
        "registry.fly.io/farmtact@sha256:" + "A" * 64,
        "registry.fly.io/other@sha256:" + "a" * 64,
        "registry.fly.io/farmtact@sha256:" + "a" * 63,
    ],
)
def test_mutable_or_out_of_scope_images_fail_closed(image):
    source = copy.deepcopy(registry())
    source["editions"][0]["image_digest"] = image
    with pytest.raises(ValueError, match="exact published image digests"):
        machine_config(source, "vol_review123")


def test_public_service_exposes_only_gateway_port_and_config_contains_no_secret_values():
    config = machine_config(registry(), "vol_review123", public=True)
    assert len(config["services"]) == 1
    assert config["services"][0]["internal_port"] == 8080
    assert config["services"][0]["ports"][0] == {
        "port": 80, "handlers": ["http"], "force_https": True,
    }
    containers = {row["name"]: row for row in config["containers"]}
    assert containers["gateway"]["secrets"] == [
        {"env_var": "FARMTACT_CONTROL_SECRET", "name": "FARMTACT_CONTROL_SECRET"}
    ]
    for name, row in containers.items():
        assert not set(row["env"]) & {"DEEPSEEK_API_KEY", "FARMTACT_CONTROL_SECRET"}
        if name != "gateway":
            assert row["secrets"] == [
                {"env_var": "FARMTACT_CONTROL_SECRET", "name": "FARMTACT_CONTROL_SECRET"},
                {"env_var": "DEEPSEEK_API_KEY", "name": "DEEPSEEK_API_KEY"},
            ]


def test_adapter_uses_fixed_absolute_handoff_and_hides_common_parent():
    source = (ROOT / "scripts/shared_container_entrypoint.py").read_text()
    assert "re.fullmatch(r'v[1-9][0-9]?', name)" in source
    assert "subprocess.run(['mount', '--bind', str(target), '/data'], check=True)" in source
    assert "subprocess.run(['umount', '/persist'], check=True)" in source
    assert "os.execv('/app/scripts/fly_entrypoint.sh', ['/app/scripts/fly_entrypoint.sh'])" in source
    assert "shell=True" not in source
    assert "os.O_EXCL | os.O_NOFOLLOW" in source
    assert "os.fsync(output.fileno())" in source
    assert "os.fsync(fd)" in source


def test_transfer_preflights_candidate_artifacts_before_destructive_restore():
    source = (ROOT / "scripts/shared_host_transfer.py").read_text()
    restore = source[source.index("def restore():"):source.index("\ndef verify():")]
    preflight = restore.index("with tarfile.open(DIRECTORY/'cache.tar.gz') as archive:")
    database_restore = restore.index("subprocess.run(['pg_restore'")
    cache_delete = restore.index("for child in Path('/data/public-data').iterdir():")

    assert preflight < database_restore < cache_delete
    assert "expected['dump_sha256']" in restore
    assert "'..' in Path(m.name).parts" in restore
    assert "not (m.isfile() or m.isdir())" in restore
    assert "filter='data'" in restore


def test_transfer_requires_current_stopped_owned_processes_and_has_timeouts():
    source = (ROOT / "scripts/shared_host_transfer.py").read_text()
    assert "def require_frozen():" in source
    assert "state.split()[1]!='T'" in source
    assert "record['database']!=database()" in source
    assert "connect_timeout=5" in source
    assert "statement_timeout=15000" in source
    assert "lock_timeout=3000" in source
    assert "timeout=60" in source
    assert "timeout=90" in source
    assert "expected['identity']!=identity()" in source
    assert "expected['metadata_sha256']!=metadata_hash()" in source
    assert "source_commit=Path('/app/config/build-source.txt').read_text().strip()" in source
    assert "pg_get_userbyid(c.relowner)" in source
    assert "pg_get_functiondef(oid)" in source


def test_shared_publisher_updates_exact_machine_then_probes_new_local_port(monkeypatch):
    source = registry()
    new = copy.deepcopy(source)
    number = len(new["editions"]) + 1
    commit = "c" * 40
    image = "registry.fly.io/farmtact@sha256:" + "d" * 64
    new["editions"].append({
        "id": f"v{number}", "source_commit": commit, "image_digest": image,
        "title": "Next", "status": "published",
    })
    new["latest"] = f"v{number}"
    calls = []

    monkeypatch.setattr(publication, "shared_settings", lambda: {
        "app": "farmtact", "machine_id": "1234567890abcd", "volume_id": "vol_review123",
    })

    def fake_command(args, **kwargs):
        if args[:3] == ["fly", "machine", "update"]:
            generated = json.loads(Path(args[args.index("--machine-config") + 1]).read_text())
            rows = {row["name"]: row for row in generated["containers"]}
            assert generated["services"][0]["internal_port"] == 8080
            assert "private-relay" not in rows
            assert rows[f"v{number}"]["image"] == image
        calls.append(args)
        return type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(publication, "command", fake_command)
    publication.deploy_shared(new, {'previous': None, 'latest': new['latest']})

    assert calls[0][:5] == ["fly", "machine", "update", "1234567890abcd", "--app"]
    assert calls[0][5] == "farmtact"
    probe = calls[1]
    assert probe[:8] == [
        "fly", "ssh", "console", "--app", "farmtact", "--machine", "1234567890abcd", "--container",
    ]
    assert probe[8] == "gateway"
    assert f"127.0.0.1:{8080 + number}/api/v1/health" in probe[-1]
    assert commit in probe[-1]
    assert "r.get(" in probe[-1] and "status" in probe[-1] and "ok" in probe[-1]
    assert "edition" in probe[-1] and f"v{number}" in probe[-1]


def test_shared_settings_reject_ignored_fields(tmp_path, monkeypatch):
    hosting = tmp_path / "config" / "hosting"
    hosting.mkdir(parents=True)
    path = hosting / "shared.json"
    base = {"app": "farmtact", "machine_id": "1234567890abcd", "volume_id": "vol_review123"}
    path.write_text(json.dumps(base))
    monkeypatch.setattr(publication, "ROOT", tmp_path)
    assert publication.shared_settings() == base
    path.write_text(json.dumps({**base, "unexpected": "ignored"}))
    with pytest.raises(publication.PublicationError, match="Invalid deployment-owned"):
        publication.shared_settings()


def test_shared_registry_gateway_preserves_precutover_history():
    incoming = registry()
    previous = {"latest": incoming["editions"][-2]["id"], "editions": incoming["editions"][:-1]}
    assert entrypoint._validated_registry_action(previous, incoming, "gateway") == "preserve"


def test_shared_registry_edition_appends_verified_incoming_history(tmp_path):
    incoming = registry()
    previous = {"latest": incoming["editions"][-2]["id"], "editions": incoming["editions"][:-1]}
    local = entrypoint._registry_for_container(incoming, {"previous": previous["latest"], "latest": incoming["latest"]}, incoming["latest"])
    manifest = tmp_path / "registry.json"
    manifest.write_text(json.dumps(previous))
    assert entrypoint._validated_registry_action(previous, local, incoming["latest"]) == "write"
    entrypoint._atomic_json(manifest, local)
    assert json.loads(manifest.read_text()) == incoming


def test_future_candidate_restage_does_not_pin_unpublished_identity():
    published = registry()
    staged = copy.deepcopy(published)
    candidate = copy.deepcopy(staged["editions"][-1])
    candidate.update(id=f"v{len(staged['editions']) + 1}", title="candidate first identity")
    staged["editions"].append(candidate); staged["latest"] = candidate["id"]
    active = {"previous": published["editions"][-2]["id"], "latest": published["latest"]}
    first = entrypoint._registry_for_container(staged, active, candidate["id"])
    staged["editions"][-1]["title"] = "candidate restaged identity"
    second = entrypoint._registry_for_container(staged, active, candidate["id"])
    assert first == second == published
    assert entrypoint._validated_registry_action(published, second, candidate["id"]) == "preserve"


def test_shared_registry_rejects_history_rewrite_for_gateway_and_edition():
    incoming = registry()
    previous = copy.deepcopy(incoming)
    previous["editions"][0]["title"] = "rewritten published title"
    for name in ("gateway", incoming["latest"]):
        with pytest.raises(RuntimeError, match="history cannot be replaced"):
            entrypoint._validated_registry_action(previous, incoming, name)


def test_shared_atomic_publish_targets_pinned_gateway_container(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(publication, "shared_settings", lambda: {
        "app": "farmtact", "machine_id": "1234567890abcd", "volume_id": "vol_review123",
    })
    monkeypatch.setattr(
        publication, "command",
        lambda args, **kwargs: calls.append((args, kwargs)) or type("Result", (), {"returncode": 0})(),
    )
    source = registry()
    new = copy.deepcopy(source); number = len(source['editions']) + 1
    new['editions'].append({'id':f'v{number}'}); new['latest'] = f'v{number}'
    publication.publish_remote(new, {'previous':None,'latest':new['latest']}, tmp_path / "registry.json")

    pinned = ["--machine", "1234567890abcd", "--container", "gateway"]
    assert all(all(item in args for item in pinned) for args, _ in calls)
    assert "/data/releases/public.json.next" in calls[0][1]["input_text"]
    validator = calls[1][0][-1]
    assert "b['editions'][:-1]==a['editions']" in validator
    assert "len(b['editions'])==len(a['editions'])+1" in validator
    assert "os.replace(n,u)" in validator
    assert "os.replace(t,q)" in validator
