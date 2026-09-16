"""One-call private V12 native-text PDF extraction acceptance trial."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

import httpx
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from scripts.v12_upload_trial import valid_actual_audit


def synthetic_invoice_pdf() -> bytes:
    writer = PdfWriter(); page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"),
                             NameObject("/BaseFont"): NameObject("/Helvetica")})
    font_ref = writer._add_object(font)
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})})
    lines = ["SYNTHETIC FARM INVOICE - TEST DATA", "Date: 2026-09-03", "Reference: INV-V12-PDF",
             "Item: caixin", "Quantity: 12 kg", "Amount: SGD 96.00", "NOT A REAL SALE"]
    commands = ["BT", "/F1 20 Tf", "50 730 Td"]
    for index, line in enumerate(lines):
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        if index: commands.append("0 -45 Td")
        commands.append(f"({escaped}) Tj")
    commands.append("ET")
    stream = DecodedStreamObject(); stream.set_data("\n".join(commands).encode("ascii")); page[NameObject("/Contents")] = writer._add_object(stream)
    from io import BytesIO
    output = BytesIO(); writer.write(output); return output.getvalue()


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8092")
    parser.add_argument("--auth-state", type=Path, default=Path("/tmp/v12-private-replay-state.json"))
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv); started = datetime.now(timezone.utc).isoformat()
    report = {"status": "FAIL"}; client = None
    try:
        if args.base_url.rstrip("/") != "http://127.0.0.1:8092": raise ValueError("trial admits only private localhost:8092")
        state = json.loads(args.auth_state.read_text()); cookie = state.get("cookie")
        if not isinstance(cookie, str) or not cookie: raise ValueError("private replay cookie unavailable")
        headers = {"cookie": "farmtact_session=" + cookie, "host": "farmtact.fly.dev", "origin": "https://farmtact.fly.dev",
                   "x-farmtact-gateway": os.environ['FARMTACT_CONTROL_SECRET'],
                   "x-farmtact-client-ip": "198.18.0.24"}
        client = httpx.Client(base_url=args.base_url, headers=headers, timeout=120, follow_redirects=False)
        before_response = client.get("/api/v1/bootstrap")
        if before_response.status_code != 200: raise RuntimeError(f"bootstrap HTTP {before_response.status_code}")
        before = digest(before_response.json()["farm"]); raw = synthetic_invoice_pdf()
        rejected = client.post("/api/v1/farm-workflow/imports/upload?filename=synthetic-invoice.pdf&source_kind=photo_observation",
                               content=raw, headers={"content-type": "application/pdf"})
        if rejected.status_code != 422: raise RuntimeError(f"PDF photo boundary expected 422, got {rejected.status_code}")
        endpoint = "/api/v1/farm-workflow/imports/upload?filename=synthetic-invoice.pdf&source_kind=document_extraction"
        response = client.post(endpoint, content=raw, headers={"content-type": "application/pdf"})
        if response.status_code != 201: raise RuntimeError(f"PDF extraction HTTP {response.status_code}: {response.text[:200]}")
        candidate = response.json(); rows = candidate.get("rows", [])
        if not rows: raise RuntimeError("PDF extraction returned zero rows")
        row = rows[0]; audit = candidate.get("provenance", {}).get("audit")
        checks = {"photo_boundary_preprovider": True,
            "authored_truth": str(row.get("reference")) == "INV-V12-PDF" and str(row.get("occurred_on") or row.get("date")) == "2026-09-03"
                              and float(row.get("quantity", -1)) == 12 and row.get("unit") == "kg" and float(row.get("amount_sgd", row.get("amount", -1))) == 96,
            "actual_audit": valid_actual_audit(audit)}
        review = client.post(f'/api/v1/farm-workflow/imports/{candidate["candidate_id"]}/review',
                             json={"decision": "confirm", "reviewer": "v12-pdf-trial"})
        checks["explicit_review"] = review.status_code == 200 and review.json().get("status") == "confirmed"
        source = client.get(f'/api/v1/farm-workflow/imports/{candidate["candidate_id"]}/source')
        checks["source_bytes_exact"] = source.status_code == 200 and source.content == raw
        replay = client.post(endpoint, content=raw, headers={"content-type": "application/pdf"})
        checks["replay_exact_without_new_inference"] = replay.status_code == 201 and replay.json().get("candidate_id") == candidate["candidate_id"] \
            and replay.json().get("provenance", {}).get("audit") == audit
        after = client.get("/api/v1/bootstrap")
        checks["main_farm_unchanged"] = after.status_code == 200 and digest(after.json()["farm"]) == before
        report = {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks,
                  "provider_requests_expected": 1, "candidate_id": candidate["candidate_id"], "rows": rows,
                  "warnings": candidate.get("warnings"), "audit": audit, "request_id_present": bool((audit or {}).get("request_id"))}
    except Exception as exc:
        report = {**report, "status": "FAIL", "error": f"{type(exc).__name__}: {exc}"}
    finally:
        if client: client.close()
    report.update(started_at=started, completed_at=datetime.now(timezone.utc).isoformat(), base_url=args.base_url)
    args.report.parent.mkdir(parents=True, exist_ok=True); args.report.write_text(json.dumps(report, indent=2) + "\n"); args.report.chmod(0o600)
    print(json.dumps({key: report[key] for key in ("status", "error", "checks") if key in report}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__": raise SystemExit(main())
