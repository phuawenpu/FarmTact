"""Independent invariants for the exact-image shared-host deployment."""
import copy
import json
from pathlib import Path

import pytest

from scripts.shared_host_config import GATEWAY_IMAGE, machine_config


ROOT = Path(__file__).resolve().parents[2]


def registry():
    return json.loads((ROOT / "config/releases/registry.json").read_text())


def test_config_retains_registry_images_and_bounds_one_machine():
    source = registry()
    config = machine_config(source, "vol_review123")
    containers = {row["name"]: row for row in config["containers"]}

    assert config["guest"] == {"cpu_kind": "shared", "cpus": 4, "memory_mb": 4096}
    assert config["mounts"] == [{"volume": "vol_review123", "path": "/persist"}]
    assert "services" not in config
    assert containers["gateway"]["image"] == GATEWAY_IMAGE
    assert {name: row["image"] for name, row in containers.items() if name != "gateway"} == {
        row["id"]: row["image_digest"] for row in source["editions"]
    }
    assert len(containers) == len(source["editions"]) + 1
    assert all(row["entrypoint"] == ["python", "/opt/farmtact-shared-entrypoint.py"] for row in containers.values())
    assert all(row["files"][0]["guest_path"] == "/opt/farmtact-shared-entrypoint.py" for row in containers.values())


def test_ports_aliases_and_local_control_are_fixed_by_edition():
    config = machine_config(registry(), "vol_review123")
    containers = {row["name"]: row for row in config["containers"]}
    upstreams = json.loads(containers["gateway"]["env"]["FARMTACT_EDITION_UPSTREAMS"])

    assert containers["gateway"]["env"]["FARMTACT_PORT"] == "8080"
    for index in range(1, len(registry()["editions"]) + 1):
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
