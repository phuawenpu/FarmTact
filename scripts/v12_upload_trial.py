"""Strict V12 Farm Inbox and optional two-call DeepSeek upload trial."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from io import BytesIO
import json
import os
from pathlib import Path
import time
import uuid
from zipfile import ZipFile

import httpx


class TrialFailure(RuntimeError): pass


class API:
    def __init__(self, base: str, private: bool):
        base = base.rstrip("/")
        if private and base != "http://127.0.0.1:8092": raise TrialFailure("private trial admits only localhost:8092")
        headers = ({"host": "farmtact.fly.dev", "origin": "https://farmtact.fly.dev",
                    "x-farmtact-gateway": os.environ["FARMTACT_CONTROL_SECRET"],
                    "x-farmtact-client-ip": "198.18.0.22"} if private else {})
        self.base = base; self.private = private; self.client = httpx.Client(headers=headers, timeout=120)

    def request(self, method, path, *, body=None, content=None, media=None, expected=(200, 201, 202)):
        headers = {"Idempotency-Key": uuid.uuid4().hex} if method == "POST" else {}
        if media: headers["content-type"] = media
        kwargs = {"headers": headers}
        if body is not None: kwargs["json"] = body
        if content is not None: kwargs["content"] = content
        response = self.client.request(method, self.base + "/api/v1" + path, **kwargs)
        if self.private:
            token = self.client.cookies.get("farmtact_session")
            if token: self.client.headers["cookie"] = "farmtact_session=" + token
        if response.status_code not in expected:
            raise TrialFailure(f"{method} {path}: HTTP {response.status_code}: {response.text[:300]}")
        return response

    def json(self, method, path, **kwargs): return self.request(method, path, **kwargs).json()
    def close(self): self.client.close()


def xlsx_bytes() -> bytes:
    rows = [["date", "kind", "reference", "description", "quantity", "unit", "amount", "currency"],
            ["2026-09-02", "expense", "BILL-X1", "Nutrient input", "2", "items", "24.50", "SGD"]]
    xml_rows = []
    for row_number, values in enumerate(rows, 1):
        cells = []
        for index, value in enumerate(values):
            column = chr(65 + index)
            cells.append(f'<c r="{column}{row_number}" t="inlineStr"><is><t>{value}</t></is></c>')
        xml_rows.append(f'<row r="{row_number}">{"".join(cells)}</row>')
    output = BytesIO()
    with ZipFile(output, "w") as archive:
        archive.writestr("xl/worksheets/sheet1.xml",
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
            + "".join(xml_rows) + "</sheetData></worksheet>")
    return output.getvalue()


def png_fixture(kind: str) -> bytes:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc: raise TrialFailure("Pillow is required to author synthetic PNG trial fixtures") from exc
    image = Image.new("RGB", (1200, 720), "white"); draw = ImageDraw.Draw(image)
    try:
        heading = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
        body = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 38)
    except OSError:
        heading = body = ImageFont.load_default()
    if kind == "invoice":
        lines = ["SYNTHETIC FARM INVOICE", "Invoice: INV-V12-001", "Date: 2026-09-03",
                 "Item: caixin", "Quantity: 12 kg", "Amount: SGD 96.00", "TEST DATA - NOT A REAL SALE"]
    else:
        lines = ["SYNTHETIC CROP LABEL", "Batch: BATCH-V12-PHOTO", "Crop: caixin",
                 "Visual observation only", "NO YIELD VALUE", "TEST IMAGE"]
        draw.rectangle((820, 120, 1120, 620), fill="#5d9e55", outline="#204f2b", width=10)
    for index, line in enumerate(lines):
        draw.text((50, 45 + index * 82), line, fill="black", font=heading if index == 0 else body)
    output = BytesIO(); image.save(output, format="PNG"); return output.getvalue()


def upload(api: API, filename: str, kind: str, raw: bytes, media: str):
    return api.json("POST", f"/farm-workflow/imports/upload?filename={filename}&source_kind={kind}", content=raw, media=media)


def review(api: API, candidate: dict):
    return api.json("POST", f'/farm-workflow/imports/{candidate["candidate_id"]}/review',
                    body={"decision": "confirm", "reviewer": "v12-upload-trial"})


def wait_session(api: API, session_id: str):
    deadline = time.monotonic() + 240
    while time.monotonic() < deadline:
        value = api.json("GET", "/planning-sessions/" + session_id)
        if value.get("status") not in {"QUEUED", "RUNNING", "DRAFT", "CREATED"}: return value
        time.sleep(.8)
    raise TrialFailure("planning calculation timed out")


def run(api: API, vision: bool, on_snapshot=lambda evidence: None) -> dict:
    checks = {}; api.json("GET", "/bootstrap")
    manual = api.json("POST", "/farm-workflow/imports", body={"source_name": "manual-sgd", "rows": [
        {"date": "2026-09-01", "kind": "sale", "reference": "SALE-M1", "description": "caixin", "quantity": "5", "unit": "kg", "amount": "40", "currency": "SGD"}]})
    manual = review(api, manual)
    csv_raw = b"date,kind,reference,description,quantity,unit,amount,currency\n2026-09-02,sale,SALE-C1,pak choi,8,kg,72,SGD\n"
    csv_candidate = upload(api, "synthetic.csv", "accounting_export", csv_raw, "text/csv")
    csv_candidate = review(api, csv_candidate)
    xlsx_raw = xlsx_bytes()
    xlsx_candidate = review(api, upload(api, "synthetic.xlsx", "accounting_export", xlsx_raw,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))
    correction = api.json("POST", "/farm-workflow/imports", body={"source_name": "correction", "import_kind": "correction", "rows": [
        {"date": "2026-09-02", "kind": "correction", "reference": "SALE-C1", "description": "price correction", "amount": "-2", "currency": "SGD"}]})
    correction = review(api, correction)
    checks["manual_csv_xlsx_reviewed"] = all(row.get("status") == "confirmed" for row in (manual, csv_candidate, xlsx_candidate, correction))
    checks["reconciliation_exact"] = (csv_candidate["reconciliation"]["revenue_sgd"] == "72" and
        xlsx_candidate["reconciliation"]["expense_sgd"] == "24.50" and correction["reconciliation"]["correction_row_count"] == 1)
    source = api.request("GET", f'/farm-workflow/imports/{csv_candidate["candidate_id"]}/source')
    xlsx_source = api.request("GET", f'/farm-workflow/imports/{xlsx_candidate["candidate_id"]}/source/download')
    checks["source_preview_exact"] = (source.content == csv_raw and xlsx_source.content == xlsx_raw
        and source.headers.get("x-content-type-options") == "nosniff")
    duplicate = upload(api, "synthetic.csv", "accounting_export", csv_raw, "text/csv")
    checks["upload_replay_exact"] = duplicate["candidate_id"] == csv_candidate["candidate_id"]

    session = api.json("POST", "/planning-sessions", body={"name": "V12 upload trial", "workflow": True})
    api.json("POST", f'/planning-sessions/{session["id"]}/calculate', body={"revision": session["revision"]})
    session = wait_session(api, session["id"])
    changes = [{"kind": "planning_assumptions", "assumptions": {}}]
    tentative = api.json("POST", "/farm-workflow/imports", body={"source_name": "tentative", "rows": [
        {"date": "2026-09-04", "kind": "sale", "reference": "T-1", "amount": "8", "currency": "SGD"}]})
    rejected = api.request("POST", "/farm-workflow/proposals", body={"session_id": session["id"], "base_revision": session["revision"],
        "changes": changes, "source_candidate_ids": [tentative["candidate_id"]], "idempotency_key": uuid.uuid4().hex}, expected=(409, 422))
    checks["tentative_link_withheld"] = rejected.status_code in {409, 422}
    proposal = api.json("POST", "/farm-workflow/proposals", body={"session_id": session["id"], "base_revision": session["revision"],
        "changes": changes, "source_candidate_ids": [csv_candidate["candidate_id"], xlsx_candidate["candidate_id"]],
        "idempotency_key": uuid.uuid4().hex})
    checks["confirmed_provenance_linked"] = len(proposal.get("source_candidates", [])) == 2

    provider_calls = 0
    if vision:
        invoice_raw = png_fixture("invoice")
        invoice = upload(api, "synthetic-invoice.png", "document_extraction", invoice_raw, "image/png"); provider_calls += 1
        if not invoice.get("rows"): raise TrialFailure("invoice extraction returned zero rows")
        row = invoice["rows"][0]
        checks["invoice_truth_match"] = (str(row.get("reference")) == "INV-V12-001" and
            str(row.get("date") or row.get("occurred_on")) == "2026-09-03" and float(row.get("amount_sgd", row.get("amount", -1))) == 96.0)
        checks["invoice_actual_inference_audited"] = bool(invoice.get("provenance", {}).get("audit", {}).get("request_id"))
        invoice = review(api, invoice)
        on_snapshot({"status": "IN_PROGRESS", "stage": "invoice_completed", "checks": dict(checks),
            "provider_requests_observed": 1, "invoice_evidence": {"candidate_id": invoice.get("candidate_id"),
                "rows": invoice.get("rows"), "warnings": invoice.get("warnings"),
                "audit": invoice.get("provenance", {}).get("audit")}})
        photo_raw = png_fixture("photo")
        photo = upload(api, "synthetic-crop-label.png", "photo_observation", photo_raw, "image/png"); provider_calls += 1
        if not photo.get("rows") or not photo["rows"][0].get("visible_findings"): raise TrialFailure("photo observation returned no visible findings")
        checks["photo_actual_inference_audited"] = bool(photo.get("provenance", {}).get("audit", {}).get("request_id"))
        photo = review(api, photo)
        checks["photo_no_yield_authority"] = photo.get("yield_authority") is False and photo.get("planning_eligible") is False
        on_snapshot({"status": "IN_PROGRESS", "stage": "photo_completed", "checks": dict(checks),
            "provider_requests_observed": 2, "invoice_evidence": {"candidate_id": invoice.get("candidate_id"),
                "rows": invoice.get("rows"), "audit": invoice.get("provenance", {}).get("audit")},
            "photo_evidence": {"candidate_id": photo.get("candidate_id"), "rows": photo.get("rows"),
                "warnings": photo.get("warnings"), "audit": photo.get("provenance", {}).get("audit")}})
        checks["vision_replay_exact"] = (upload(api, "synthetic-invoice.png", "document_extraction", invoice_raw, "image/png")["candidate_id"] == invoice["candidate_id"] and
            upload(api, "synthetic-crop-label.png", "photo_observation", photo_raw, "image/png")["candidate_id"] == photo["candidate_id"])
    checks["provider_call_contract"] = provider_calls == (2 if vision else 0)

    outsider = API(api.base, api.private)
    try:
        outsider.json("GET", "/bootstrap")
        hidden = outsider.request("GET", f'/farm-workflow/imports/{csv_candidate["candidate_id"]}/source', expected=(404,))
        checks["cross_tenant_source_isolated"] = hidden.status_code == 404
    finally: outsider.close()
    state = api.json("GET", "/farm-workflow")
    checks["state_has_no_raw_blobs"] = "payload" not in json.dumps(state)
    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks,
            "provider_requests_expected": provider_calls, "vision_requested": vision,
            "candidate_ids": [manual["candidate_id"], csv_candidate["candidate_id"], xlsx_candidate["candidate_id"], correction["candidate_id"]],
            "session_id": session["id"], "proposal_id": proposal["id"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8092")
    parser.add_argument("--private-gateway", action="store_true")
    parser.add_argument("--vision", action="store_true", help="Make exactly two extraction calls through app endpoints")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv); started = datetime.now(timezone.utc).isoformat()
    api = None; last_snapshot = {}
    def persist_snapshot(evidence):
        nonlocal last_snapshot
        last_snapshot = dict(evidence, started_at=started, base_url=args.base_url,
            private_gateway=args.private_gateway, vision_requested=args.vision)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(last_snapshot, indent=2) + "\n"); args.report.chmod(0o600)
    try:
        api = API(args.base_url, args.private_gateway); report = run(api, args.vision, persist_snapshot)
    except Exception as exc: report = {**last_snapshot, "status": "FAIL", "error": f"{type(exc).__name__}: {exc}"}
    finally:
        if api: api.close()
    report.update(started_at=started, completed_at=datetime.now(timezone.utc).isoformat(), base_url=args.base_url,
                  private_gateway=args.private_gateway, vision_requested=args.vision)
    args.report.parent.mkdir(parents=True, exist_ok=True); args.report.write_text(json.dumps(report, indent=2) + "\n"); args.report.chmod(0o600)
    print(json.dumps({key: report[key] for key in ("status", "error", "checks") if key in report}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__": raise SystemExit(main())
