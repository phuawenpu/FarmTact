"""Verify the deployed application and retired workspace HTTP service."""
import json
from pathlib import Path
import socket
import subprocess

import httpx


def main() -> None:
    services = json.loads(subprocess.check_output(["sprite-env", "services", "list"]))
    report = {
        "status": "PASS",
        "public_url": "https://farmtact.fly.dev",
        "sprite_web_registration_removed": not any(
            item["name"] == "farmtact-web" for item in services
        ),
        "development_database_preserved": any(
            item["name"] == "farmtact-db" for item in services
        ),
    }
    with socket.socket() as probe:
        probe.settimeout(2)
        report["development_http_port_closed"] = probe.connect_ex(("127.0.0.1", 8080)) != 0
    with httpx.Client(timeout=20, follow_redirects=True) as client:
        fly = client.get(report["public_url"])
        report["fly_http_status"] = fly.status_code
        report["fly_application_served"] = fly.status_code == 200 and "FarmTact" in fly.text
        health = client.get(report["public_url"] + "/api/v1/health")
        report["fly_health_status"] = health.status_code
        try:
            sprite = client.get("https://farm001-bqddl.sprites.app/", follow_redirects=False)
            report["sprite_http_status"] = sprite.status_code
            report["sprite_application_not_served"] = sprite.status_code != 200 and "<title>FarmTact" not in sprite.text
        except httpx.RequestError:
            report["sprite_http_status"] = "unavailable"
            report["sprite_application_not_served"] = report["development_http_port_closed"]
    passed = all(report[key] for key in (
        "sprite_web_registration_removed", "development_database_preserved",
        "development_http_port_closed", "fly_application_served", "sprite_application_not_served",
    )) and report["fly_health_status"] == 200
    report["status"] = "PASS" if passed else "FAIL"
    Path("reports/gameplay_hosting.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
