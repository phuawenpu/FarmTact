#!/usr/bin/env python3
"""Publish one immutable FarmTact edition.

The command deliberately accepts an already-built digest.  Builds and release
verification happen before this command; publication never resolves a mutable
tag while deploying.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "config/releases/registry.json"
STATE_NAME = "farmtact-publications.json"
EDITION = re.compile(r"v([1-9][0-9]*)\Z")
COMMIT = re.compile(r"[0-9a-f]{40}\Z")
IMAGE = re.compile(r"registry\.fly\.io/farmtact(?:-edition-v[1-9][0-9]*)?(?::[a-z0-9][a-z0-9._-]{0,127})?@sha256:[0-9a-f]{64}\Z")


class PublicationError(RuntimeError):
    pass


def command(args: list[str], *, input_text: str | None = None, input_bytes: bytes | None = None, check: bool = True) -> subprocess.CompletedProcess:
    if input_text is not None and input_bytes is not None:
        raise ValueError("Only one subprocess input form is allowed")
    return subprocess.run(
        args, cwd=ROOT, input=input_bytes if input_bytes is not None else input_text,
        text=input_bytes is None, capture_output=True, check=check,
    )


def git(*args: str) -> str:
    return command(["git", *args]).stdout.strip()


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise PublicationError(f"Invalid JSON file: {path}") from error
    if not isinstance(value, dict):
        raise PublicationError(f"JSON object required: {path}")
    return value


def validate_notes(notes: dict) -> None:
    if set(notes) != {"title", "summary", "changes"}:
        raise PublicationError("Notes require exactly title, summary and changes")
    if not all(isinstance(notes[key], str) and 1 <= len(notes[key]) <= limit for key, limit in (("title", 100), ("summary", 400))):
        raise PublicationError("Edition title or summary is invalid")
    changes = notes["changes"]
    if not isinstance(changes, list) or not 1 <= len(changes) <= 20:
        raise PublicationError("Edition changes must be a nonempty bounded list")
    for change in changes:
        if not isinstance(change, dict) or set(change) != {"title", "description", "feedback_ids", "evidence"}:
            raise PublicationError("Each change requires title, description, feedback_ids and evidence")
        if not isinstance(change["title"], str) or not 1 <= len(change["title"]) <= 120:
            raise PublicationError("Invalid change title")
        if not isinstance(change["description"], str) or not 1 <= len(change["description"]) <= 600:
            raise PublicationError("Invalid change description")
        for key in ("feedback_ids", "evidence"):
            if not isinstance(change[key], list) or len(change[key]) > 50 or not all(isinstance(item, str) and len(item) <= 300 for item in change[key]):
                raise PublicationError(f"Invalid change {key}")


def validate_registry(registry: dict) -> None:
    if set(registry) != {"latest", "editions"} or not isinstance(registry["editions"], list):
        raise PublicationError("Invalid release registry shape")
    ids = [item.get("id") for item in registry["editions"] if isinstance(item, dict)]
    if len(ids) != len(registry["editions"]) or len(ids) != len(set(ids)) or any(not isinstance(item, str) or not EDITION.fullmatch(item) for item in ids):
        raise PublicationError("Invalid release edition identifiers")
    numbers = [int(EDITION.fullmatch(item).group(1)) for item in ids]
    if numbers != list(range(1, len(numbers) + 1)) or registry["latest"] != (ids[-1] if ids else None):
        raise PublicationError("Release registry must be contiguous and ordered")


def append_only(old: dict, new: dict) -> None:
    validate_registry(old); validate_registry(new)
    if new["editions"][:len(old["editions"])] != old["editions"] or len(new["editions"]) != len(old["editions"]) + 1:
        raise PublicationError("Published registry history is immutable")


def remote_registry(origin: str) -> dict:
    if origin != "https://farmtact.fly.dev":
        raise PublicationError("Publication origin is fixed")
    request = Request(origin + "/api/releases", headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=10) as response:
            if response.status != 200 or int(response.headers.get("Content-Length", "0") or 0) > 1_000_000:
                raise PublicationError("Remote registry unavailable")
            body = response.read(1_000_001)
    except PublicationError:
        raise
    except Exception as error:
        raise PublicationError("Remote registry unavailable") from error
    if len(body) > 1_000_000:
        raise PublicationError("Remote registry response too large")
    try: result = json.loads(body)
    except json.JSONDecodeError as error: raise PublicationError("Remote registry is not JSON") from error
    validate_registry(result)
    return result


def state_path() -> Path:
    git_dir = Path(git("rev-parse", "--git-dir"))
    if not git_dir.is_absolute(): git_dir = ROOT / git_dir
    return git_dir / STATE_NAME


def load_state(path: Path) -> dict:
    if not path.exists(): return {"reservations": {}}
    state = load_json(path)
    if set(state) != {"reservations"} or not isinstance(state["reservations"], dict):
        raise PublicationError("Invalid local publication state")
    return state


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, sort_keys=True, indent=2) + "\n")
    os.replace(temporary, path)


def reserve_number(path: Path, edition: str, source_commit: str, image: str) -> dict:
    state = load_state(path); reservations = state["reservations"]
    existing = reservations.get(edition)
    identity = {"source_commit": source_commit, "image": image}
    if existing:
        if any(existing.get(key) != value for key, value in identity.items()):
            raise PublicationError("Edition number is already reserved with different inputs")
        if existing.get("stage") == "published":
            raise PublicationError("Published edition numbers cannot be reused")
        return state
    reservations[edition] = {**identity, "stage": "reserved", "reserved_at": datetime.now(timezone.utc).isoformat()}
    save_state(path, state)
    return state


def source_url(commit: str) -> str:
    remote = git("remote", "get-url", "origin")
    match = re.fullmatch(r"(?:https://github\.com/|git@github\.com:)([^/]+/[^/]+?)(?:\.git)?", remote)
    if not match: raise PublicationError("Origin must be a GitHub repository")
    return f"https://github.com/{match.group(1)}/commit/{commit}"


def make_entry(edition: str, notes: dict, image: str, commit: str, previous: dict) -> dict:
    prior = previous["editions"][-1] if previous["editions"] else None
    base = source_url(commit)
    prior_commit = prior.get("source_commit") if prior else None
    compare = ""
    if isinstance(prior_commit, str) and COMMIT.fullmatch(prior_commit):
        compare = base.rsplit("/commit/", 1)[0] + f"/compare/{prior_commit}...{commit}"
    return {
        "id": edition, "title": notes["title"], "published_at": datetime.now(timezone.utc).date().isoformat(),
        "summary": notes["summary"], "status": "published", "source_commit": commit,
        "source_url": base, "compare_url": compare, "image_digest": image,
        "review_url": f"/{edition}/review", "play_url": f"/{edition}/",
        "changes": [{**change, "status": "implemented"} for change in notes["changes"]],
    }


def fly_config(edition: str) -> str:
    return f'''app = "farmtact-edition-{edition}"
primary_region = "sin"
kill_signal = "SIGTERM"
kill_timeout = 90

[env]
  FARMTACT_EDITION = "{edition}"
  FARMTACT_CONTROL_URL = "http://farmtact.flycast"
  FARMTACT_EXECUTION_MODE = "test"
  FARMTACT_SECURE_COOKIES = "true"
  FARMTACT_PUBLIC_ORIGIN = "https://farmtact.fly.dev"
  FARMTACT_TRUST_FLY_PROXY = "true"
  FARMTACT_DATA_MODE = "synthetic_demo"
  FARMTACT_DATABASE_URL = "postgresql+psycopg://farmtact@/farmtact?host=/tmp/farmtact-pg"
  PYTHONUNBUFFERED = "1"

[[mounts]]
  source = "farmtact_data"
  destination = "/data"
  snapshot_retention = 7

[http_service]
  internal_port = 8080
  force_https = false
  auto_stop_machines = "off"
  auto_start_machines = true
  min_machines_running = 1

  [[http_service.checks]]
    interval = "30s"
    timeout = "5s"
    grace_period = "60s"
    method = "GET"
    path = "/api/v1/health"

[[vm]]
  cpu_kind = "shared"
  cpus = 1
  memory = "2gb"
'''


def deploy(edition: str, image: str, config: Path) -> None:
    app = f"farmtact-edition-{edition}"
    status = command(["fly", "status", "--app", app], check=False)
    creating = status.returncode != 0
    control_secret = os.environ.get("FARMTACT_CONTROL_SECRET")
    deepseek_secret = os.environ.get("DEEPSEEK_API_KEY")
    if creating and (not control_secret or not deepseek_secret):
        raise PublicationError("A new edition requires control and DeepSeek credentials in the publishing process")
    if creating:
        command(["fly", "apps", "create", app])
    staged = {key: value for key, value in (
        ("FARMTACT_CONTROL_SECRET", control_secret), ("DEEPSEEK_API_KEY", deepseek_secret),
    ) if value}
    if staged:
        # Secret material exists only in subprocess stdin. It never enters argv,
        # command output, the generated manifest, or publication records.
        payload = "".join(f"{key}={value}\n" for key, value in staged.items()).encode()
        command(["fly", "secrets", "import", "--stage", "--app", app], input_bytes=payload)
    ips = command(["fly", "ips", "list", "--app", app, "--json"])
    try:
        ip_rows = json.loads(ips.stdout)
    except json.JSONDecodeError as error:
        raise PublicationError("Fly IP inventory is invalid") from error
    if not isinstance(ip_rows, list):
        raise PublicationError("Fly IP inventory is invalid")
    parsed_ips = []
    for row in ip_rows:
        if not isinstance(row, dict):
            raise PublicationError("Fly IP inventory is invalid")
        address = row.get("Address")
        try: parsed_ips.append((row.get("Type"), ipaddress.ip_address(address)))
        except ValueError as error: raise PublicationError("Fly IP inventory is invalid") from error
    if any(not address.is_private or kind != "private_v6" for kind, address in parsed_ips):
        raise PublicationError("Edition app has a public or unrecognized IP allocation")
    if not any(kind == "private_v6" and address.version == 6 for kind, address in parsed_ips):
        command(["fly", "ips", "allocate-v6", "--private", "--app", app])
    volumes = command(["fly", "volumes", "list", "--app", app, "--json"])
    try:
        volume_rows = json.loads(volumes.stdout)
    except json.JSONDecodeError as error:
        raise PublicationError("Fly volume inventory is invalid") from error
    if not isinstance(volume_rows, list):
        raise PublicationError("Fly volume inventory is invalid")
    if not any(row.get("name") == "farmtact_data" and row.get("region") == "sin" for row in volume_rows if isinstance(row, dict)):
        command(["fly", "volumes", "create", "farmtact_data", "--app", app, "--region", "sin", "--size", "3", "--snapshot-retention", "7", "--yes"])
    command(["fly", "deploy", "--app", app, "--config", str(config), "--image", image, "--ha=false", "--no-public-ips", "--yes"])
    command(["fly", "status", "--app", app])
    source_commit = git("rev-parse", "HEAD")
    probe = "import json,urllib.request;u='http://" + app + ".flycast/api/v1/health';r=json.load(urllib.request.urlopen(u,timeout=10));assert r.get('status')=='ok' and r.get('source_commit')=='" + source_commit + "'"
    command(["fly", "ssh", "console", "--app", "farmtact", "--command", f"python -c \"{probe}\""])


def build_image(edition: str, source_commit: str) -> str:
    label = f"edition-{edition}-{source_commit[:12]}"
    result = command([
        "fly", "deploy", "--app", "farmtact", "--config", "config/releases/fly-gateway.toml",
        "--build-only", "--push", "--remote-only", "--image-label", label,
        "--build-arg", f"SOURCE_COMMIT={source_commit}",
    ])
    output = (result.stdout or "") + "\n" + (result.stderr or "")
    matches = re.findall(r"registry\.fly\.io/farmtact(?::[a-z0-9][a-z0-9._-]{0,127})?@(sha256:[0-9a-f]{64})", output)
    if len(set(matches)) != 1:
        raise PublicationError("Fly build did not report one pinned image digest")
    return "registry.fly.io/farmtact@" + matches[0]


def publish_remote(registry: dict, temporary: Path) -> None:
    temporary.write_text(json.dumps(registry, sort_keys=False, indent=2) + "\n")
    remote_tmp = "/data/releases/registry.json.next"
    command(["fly", "ssh", "sftp", "shell", "--app", "farmtact"], input_text=f"put {temporary} {remote_tmp}\nquit\n")
    code = (
        "import json,os,shutil; p='/data/releases/registry.json'; n=p+'.next'; "
        "a=json.load(open(p)); b=json.load(open(n)); "
        "assert b['editions'][:-1]==a['editions'] and len(b['editions'])==len(a['editions'])+1; "
        "assert b['latest']==b['editions'][-1]['id']; shutil.copy2(p,p+'.previous'); os.replace(n,p)"
    )
    command(["fly", "ssh", "console", "--app", "farmtact", "--command", f"python -c \"{code}\""])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edition", required=True)
    parser.add_argument("--notes", required=True, type=Path)
    parser.add_argument("--image")
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        match = EDITION.fullmatch(args.edition)
        if not match or not COMMIT.fullmatch(args.source_commit) or (args.image is not None and not IMAGE.fullmatch(args.image)):
            raise PublicationError("Edition, source commit or pinned image digest is invalid")
        if git("status", "--porcelain"):
            raise PublicationError("Publication requires a clean committed source tree")
        if git("rev-parse", "HEAD") != args.source_commit:
            raise PublicationError("Source commit must equal HEAD")
        notes = load_json(args.notes); validate_notes(notes)
        remote = remote_registry("https://farmtact.fly.dev")
        expected = len(remote["editions"]) + 1
        if int(match.group(1)) != expected:
            raise PublicationError(f"Next edition must be v{expected}")
        if REGISTRY.exists() and load_json(REGISTRY) != remote:
            raise PublicationError("Local registry must exactly match the published registry")
        if args.dry_run:
            print(f"Validated publication {args.edition}; no local, Fly or registry mutation performed.")
            return 0
        image = args.image or build_image(args.edition, args.source_commit)
        state_file = state_path()
        state = reserve_number(state_file, args.edition, args.source_commit, image)
        entry = make_entry(args.edition, notes, image, args.source_commit, remote)
        updated = {"latest": args.edition, "editions": [*remote["editions"], entry]}
        append_only(remote, updated)
        config = ROOT / f"config/releases/fly-{args.edition}.toml"
        expected_config = fly_config(args.edition)
        if config.exists() and config.read_text() != expected_config:
            raise PublicationError("Edition Fly manifest exists with different contents")
        if not config.exists(): config.write_text(expected_config)
        try:
            deploy(args.edition, image, config)
            with tempfile.TemporaryDirectory(prefix="farmtact-publish-") as directory:
                publish_remote(updated, Path(directory) / "registry.json")
            REGISTRY.write_text(json.dumps(updated, indent=2) + "\n")
            manifest = ROOT / f"config/releases/{args.edition}.json"
            manifest.write_text(json.dumps(entry, indent=2) + "\n")
            git("add", str(REGISTRY.relative_to(ROOT)), str(config.relative_to(ROOT)), str(manifest.relative_to(ROOT)))
            git("commit", "-m", f"Publish immutable FarmTact {args.edition}")
            git("tag", "-a", f"farmtact-{args.edition}", args.source_commit, "-m", f"FarmTact {args.edition} source")
            git("push", "origin", "HEAD", f"refs/tags/farmtact-{args.edition}")
        except Exception:
            state["reservations"][args.edition]["stage"] = "failed"
            save_state(state_file, state)
            raise
        state["reservations"][args.edition]["stage"] = "published"
        save_state(state_file, state)
        print(f"Published {args.edition} from the pinned source and image digest.")
        return 0
    except (PublicationError, subprocess.CalledProcessError) as error:
        print(f"Publication stopped: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
