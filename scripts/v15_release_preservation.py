#!/usr/bin/env python3
"""Read-only V15 cutover preservation capture/check for the shared Fly host.

Raw database rows, counter principals, cookies and credentials never leave the
Machine. Identifiers are salted and hashed. The script performs no Fly writes.
Use --storage-container only with an already-running operator container whose
/persist mount is visible; absence is reported rather than inferred.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import shlex
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = ROOT / "config/hosting/shared.json"


class PreservationError(RuntimeError):
    pass


def _private_write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".next")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as output:
        output.write(json.dumps(value, indent=2) + "\n")
    os.replace(temporary, path)
    path.chmod(0o600)


def _run(container: str | None, code: str) -> dict:
    settings = json.loads(SETTINGS.read_text())
    command = ["fly", "ssh", "console", "--app", settings["app"], "--machine", settings["machine_id"]]
    command += (["--container", container, "--command", "gosu farmtact python -c " + shlex.quote(code)]
                if container else ["--no-container", "--command", "python3 -c " + shlex.quote(code)])
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=120)
    if result.returncode:
        raise PreservationError(f"Read-only probe failed in {container}")
    start = result.stdout.find("{")
    if start < 0:
        raise PreservationError(f"Read-only probe returned no JSON in {container}")
    try:
        value = json.loads(result.stdout[start:])
    except json.JSONDecodeError as error:
        raise PreservationError(f"Read-only probe returned invalid JSON in {container}") from error
    if not isinstance(value, dict):
        raise PreservationError("Read-only probe result must be an object")
    return value


def capture_gateway(salt: str) -> dict:
    code = r'''
import hashlib,json
from pathlib import Path
import psycopg
salt=''' + repr(salt) + r'''
def token(value):return hashlib.sha256((salt+'\0'+str(value)).encode()).hexdigest()
bundle=json.loads(Path('/data/releases/public.json').read_text())
identities=[{'id':r['id'],'source_commit':r['source_commit'],'image_digest':r['image_digest']} for r in bundle['history']['editions']]
tables={}
with psycopg.connect(host='/tmp/farmtact-pg',user='farmtact',dbname='farmtact_control',options='-c statement_timeout=15000') as c:
 existing={r[0] for r in c.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")}
 if 'edition_control_reservations' in existing:
  rows=c.execute('SELECT edition_id,reservation_id,day,requested_calls,accepted,released_calls FROM edition_control_reservations').fetchall()
  tables['reservations']=[{'key':token(r[0]+':'+r[1]),'day':r[2],'requested':r[3],'accepted':r[4],'released':r[5]} for r in rows]
 if 'edition_control_releases' in existing:
  rows=c.execute('SELECT edition_id,release_id,reservation_id,released_calls FROM edition_control_releases').fetchall()
  tables['releases']=[{'key':token(r[0]+':'+r[1]),'reservation':token(r[0]+':'+r[2]),'released':r[3]} for r in rows]
 if 'inference_budget' in existing:
  tables['budget']=[{'key':token(r[0]),'day':r[0],'reserved':r[1]} for r in c.execute('SELECT id,reserved_calls FROM inference_budget')]
 if 'abuse_security_settings' in existing:
  tables['security']=[token(r[0]+':'+r[1]) for r in c.execute('SELECT key,value FROM abuse_security_settings')]
 if 'abuse_rate_counters' in existing:
  tables['rate']=[{'key':token(r[0]),'count':r[1],'expires':r[2]} for r in c.execute('SELECT key,count,expires FROM abuse_rate_counters')]
print(json.dumps({'history':identities,'active':bundle['active'],'tables':tables},sort_keys=True))
'''
    return _run("gateway", code)


def capture_storage(container: str | None, active: str) -> dict:
    settings = json.loads(SETTINGS.read_text())
    root = "/persist" if container else "$(awk '$5 ~ /^\\/mnt\\/drives\\/.*farmtact_shared_data/ {print $5}' /proc/self/mountinfo)"
    script = f'''set -eu
root={root}
[ -n "$root" ] && [ -d "$root" ]
for p in "$root"/v[1-9]*; do
  [ -e "$p" ] || continue
  id=$(basename "$p")
  case "$id" in v*[!0-9]*|v) continue;; esac
  if [ -L "$p" ] || [ ! -d "$p" ]; then printf 'ROW\\t%s\\tfalse\\ttrue\\t0\\t0\\t-\\n' "$id"; continue; fi
  files=$(find "$p" -type f | wc -l)
  [ "$files" -le 100000 ]
  bytes=$(find "$p" -type f -printf '%s\\n' | awk '{{s+=$1}} END {{print s+0}}')
  digest=-
  if [ "$id" != {shlex.quote(active)} ]; then
    digest=$(cd "$p" && find . -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum | cut -d' ' -f1)
  fi
  printf 'ROW\\t%s\\ttrue\\tfalse\\t%s\\t%s\\t%s\\n' "$id" "$files" "$bytes" "$digest"
done'''
    command = ["fly", "ssh", "console", "--app", settings["app"], "--machine", settings["machine_id"]]
    command += ["--container", container] if container else ["--no-container"]
    command += ["--command", "/bin/sh -c " + shlex.quote(script)]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=180)
    if result.returncode:
        raise PreservationError("Read-only retained-storage probe failed")
    rows = []
    for line in result.stdout.splitlines():
        if not line.startswith("ROW\t"):
            continue
        _, edition, directory, symlink, files, size, digest = line.split("\t")
        row = {"id": edition, "directory": directory == "true", "symlink": symlink == "true",
               "files": int(files), "bytes": int(size)}
        if digest != "-": row["tree_sha256"] = digest
        rows.append(row)
    if not rows:
        raise PreservationError("Read-only retained-storage probe found no edition subtrees")
    return {"editions": rows}


def compare(before: dict, after: dict) -> tuple[bool, dict]:
    old_gateway, new_gateway = before["gateway"], after["gateway"]
    old_history, new_history = old_gateway["history"], new_gateway["history"]
    history_preserved = new_history[:len(old_history)] == old_history
    old_tables, new_tables = old_gateway["tables"], new_gateway["tables"]
    exact = {}
    for name in ("releases", "security"):
        exact[name] = not bool(Counter(map(lambda row: json.dumps(row, sort_keys=True), old_tables.get(name, []))) -
                               Counter(map(lambda row: json.dumps(row, sort_keys=True), new_tables.get(name, []))))
    new_reservations = {row["key"]: row for row in new_tables.get("reservations", [])}
    exact["reservations"] = all(
        row["key"] in new_reservations
        and all(new_reservations[row["key"]][field] == row[field] for field in ("day", "requested", "accepted"))
        and new_reservations[row["key"]]["released"] >= row["released"]
        for row in old_tables.get("reservations", [])
    )
    def budget_delta_reconciles() -> bool:
        old_rows = {row["key"]: row for row in old_tables.get("reservations", [])}
        expected = {}
        for row in new_tables.get("reservations", []):
            previous = old_rows.get(row["key"])
            if row["accepted"] and previous is None:
                expected[row["day"]] = expected.get(row["day"], 0) + row["requested"] - row["released"]
            elif row["accepted"] and previous is not None:
                expected[row["day"]] = expected.get(row["day"], 0) - (row["released"] - previous["released"])
        old_budget = {row["day"]: row["reserved"] for row in old_tables.get("budget", [])}
        new_budget = {row["day"]: row["reserved"] for row in new_tables.get("budget", [])}
        days = set(old_budget) | set(new_budget) | set(expected)
        return all(new_budget.get(day, 0) - old_budget.get(day, 0) == expected.get(day, 0) for day in days)
    # Historical pre-receipt budget rows may have no reconstructable origin.
    # Compare the cutover delta, which must be fully explained by newly durable
    # reservations and release increments captured during the interval.
    exact["budget_change_matches_receipts"] = budget_delta_reconciles()
    checked_at = after["captured_at_epoch"]
    current_rate = {row["key"]: row for row in new_tables.get("rate", [])}
    active_old = [row for row in old_tables.get("rate", []) if row["expires"] > checked_at]
    rate_preserved = all(row["key"] in current_rate and current_rate[row["key"]]["count"] >= row["count"] for row in active_old)
    storage_before, storage_after = before.get("storage"), after.get("storage")
    storage_checked = storage_before is not None and storage_after is not None
    old_rows = {row["id"]: row for row in (storage_before or {}).get("editions", [])}
    new_rows = {row["id"]: row for row in (storage_after or {}).get("editions", [])}
    old_dirs = {key for key, row in old_rows.items() if row["directory"] and not row["symlink"]}
    new_dirs = {key for key, row in new_rows.items() if row["directory"] and not row["symlink"] and row["files"] > 0}
    storage_preserved = storage_checked and old_dirs <= new_dirs
    after_active = new_gateway.get("active", {}).get("latest")
    stable_hashes = storage_checked and all(
        key == after_active or not row.get("tree_sha256")
        or new_rows.get(key, {}).get("tree_sha256") == row["tree_sha256"]
        for key, row in old_rows.items()
    )
    checks = {"immutable_history_prefix": history_preserved, **exact,
              "unexpired_abuse_counters_not_reset": rate_preserved,
              "retained_storage_checked": storage_checked,
              "retained_edition_subtrees_present": storage_preserved,
              "stable_retired_subtree_hashes": stable_hashes}
    return all(checks.values()), checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--storage-container", help="Optional existing operator container; default uses read-only machine-level volume access")
    args = parser.parse_args()
    if args.report and not args.before.exists():
        raise PreservationError("Before capture is required for comparison")
    salt = json.loads(args.before.read_text())["salt"] if args.report else secrets.token_hex(32)
    current = {"version": "v15-release-preservation-v1", "captured_at": datetime.now(timezone.utc).isoformat(),
               "captured_at_epoch": datetime.now(timezone.utc).timestamp(), "salt": salt,
               "gateway": capture_gateway(salt)}
    current["storage"] = capture_storage(args.storage_container, current["gateway"]["active"]["latest"])
    if not args.report:
        _private_write(args.before, current)
        print("Captured salted shared-control and immutable-release fingerprints.")
        return 0
    previous = json.loads(args.before.read_text())
    passed, checks = compare(previous, current)
    output = {"status": "PASS" if passed else "FAIL", "checks": checks,
              "scope": "No raw rows, principals, cookies or credentials exported; added durable records are allowed."}
    _private_write(args.report, output)
    print(output["status"])
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
