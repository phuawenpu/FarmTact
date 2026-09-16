"""Bounded accounting-record ingestion for the Farm Data Inbox.

Parsing creates candidates only.  A caller must explicitly review a candidate before
its rows may become planning inputs.  Images and documents are deliberately outside
this connector: observations extracted from them never acquire financial or yield
authority through this module.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import csv
import hashlib
import io
import re
from typing import Any, Iterable, Literal
from zipfile import BadZipFile, ZipFile
from xml.etree import ElementTree as ET


ImportKind = Literal["accounting_export", "manual", "correction"]
RowKind = Literal["sale", "expense", "inventory", "correction"]
_MAX_BYTES = 8 * 1024 * 1024
_MAX_ROWS = 10_000
_MAX_XLSX_MEMBERS = 200
_MAX_XLSX_EXPANDED = 20 * 1024 * 1024
_MAX_COLUMNS = 64
_MAX_CELL_CHARS = 4_000
_PLANNING_CROPS = {"caixin", "pak_choi", "kailan", "lettuce"}
_HEADERS = {
    "date": ("date", "transaction_date", "invoice_date", "posting_date"),
    "kind": ("kind", "type", "transaction_type", "record_type"),
    "reference": ("reference", "reference_id", "invoice", "invoice_no", "id"),
    "description": ("description", "memo", "item", "product"),
    "quantity": ("quantity", "qty", "quantity_kg"),
    "unit": ("unit", "uom"),
    "amount": ("amount", "total", "amount_sgd", "net_amount"),
    "crop_id": ("crop_id", "crop", "product_code"),
    "currency": ("currency", "currency_code", "ccy"),
}


@dataclass(frozen=True)
class FinancialRow:
    row_number: int
    occurred_on: date
    kind: RowKind
    reference: str
    description: str
    quantity: Decimal | None
    unit: str | None
    amount_sgd: Decimal
    crop_id: str | None = None
    corrects_reference: str | None = None
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FinancialImport:
    candidate_id: str
    tenant_id: str
    source_name: str
    source_sha256: str
    media_type: str
    import_kind: ImportKind
    created_at: datetime
    rows: tuple[FinancialRow, ...]
    warnings: tuple[str, ...] = ()
    status: Literal["candidate", "confirmed", "rejected"] = "candidate"
    reviewed_at: datetime | None = None
    reviewed_by: str | None = None

    @property
    def planning_eligible(self) -> bool:
        return self.status == "confirmed"


class FinancialDataError(ValueError):
    pass


def _header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _mapping(headers: Iterable[str]) -> dict[str, str]:
    actual = {_header(h): h for h in headers if h is not None}
    result = {}
    for canonical, aliases in _HEADERS.items():
        match = next((actual[a] for a in aliases if a in actual), None)
        if match:
            result[canonical] = match
    missing = {"date", "kind", "amount"} - set(result)
    if missing:
        raise FinancialDataError(f"missing required columns: {', '.join(sorted(missing))}")
    return result


def _decimal(value: Any, *, optional: bool = False) -> Decimal | None:
    text = str(value or "").strip().replace(",", "")
    if optional and not text:
        return None
    if text.startswith("(") and text.endswith(")"):
        text = "-" + text[1:-1]
    text = re.sub(r"^(?:SGD|S\$|\$)\s*", "", text, flags=re.I)
    try:
        result = Decimal(text)
    except InvalidOperation as exc:
        raise FinancialDataError(f"invalid decimal {value!r}") from exc
    if not result.is_finite():
        raise FinancialDataError("non-finite decimal")
    return result


def _date(value: Any) -> date:
    text = str(value or "").strip()
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        pass
    numeric = re.fullmatch(r"(\d{1,2})([/\-])(\d{1,2})\2(\d{4})", text)
    if numeric:
        first, second, year = int(numeric.group(1)), int(numeric.group(3)), int(numeric.group(4))
        if first <= 12 and second <= 12 and first != second:
            raise FinancialDataError(f"ambiguous date {value!r}; use YYYY-MM-DD")
        fmt = "%d/%m/%Y" if numeric.group(2) == "/" and first > 12 else "%m/%d/%Y" if numeric.group(2) == "/" else "%d-%m-%Y" if first > 12 else "%m-%d-%Y"
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    raise FinancialDataError(f"invalid date {value!r}; use YYYY-MM-DD")


def _rows_from_csv(payload: bytes) -> list[dict[str, str]]:
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise FinancialDataError("CSV must be UTF-8") from exc
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise FinancialDataError("CSV has no header")
    rows = []
    for row in reader:
        if len(rows) >= _MAX_ROWS: raise FinancialDataError("row limit exceeded")
        if any(len(str(value or "")) > _MAX_CELL_CHARS for value in row.values()):
            raise FinancialDataError("CSV cell length limit exceeded")
        rows.append(row)
    return rows


def _rows_from_xlsx(payload: bytes) -> list[dict[str, str]]:
    """Read the first XLSX worksheet using stdlib, without formulas/macros."""
    try:
        archive = ZipFile(io.BytesIO(payload))
        infos = archive.infolist()
        if len(infos) > _MAX_XLSX_MEMBERS or sum(info.file_size for info in infos) > _MAX_XLSX_EXPANDED:
            raise FinancialDataError("XLSX archive expansion limit exceeded")
        if any(info.filename.lower().endswith(("vbaproject.bin", ".xlsm")) for info in infos):
            raise FinancialDataError("XLSX macros are not accepted")
        shared: list[str] = []
        excel_epoch = date(1899, 12, 30)
        minimum_serial = 1
        if "xl/workbook.xml" in archive.namelist():
            workbook = ET.fromstring(archive.read("xl/workbook.xml"))
            ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
            properties = workbook.find(ns + "workbookPr")
            if properties is not None and properties.attrib.get("date1904", "").lower() in {"1", "true"}:
                excel_epoch = date(1904, 1, 1)
                minimum_serial = 0
        date_styles: set[int] = set()
        if "xl/styles.xml" in archive.namelist():
            styles = ET.fromstring(archive.read("xl/styles.xml"))
            ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
            custom = {int(node.attrib["numFmtId"]): node.attrib.get("formatCode", "").lower()
                      for node in styles.iter(ns + "numFmt") if "numFmtId" in node.attrib}
            cell_xfs = styles.find(ns + "cellXfs")
            if cell_xfs is not None:
                for style_index, xf in enumerate(cell_xfs.findall(ns + "xf")):
                    number_format = int(xf.attrib.get("numFmtId", 0))
                    code = custom.get(number_format, "")
                    if number_format in set(range(14, 23)) | {45, 46, 47} or any(token in code for token in ("yy", "dd", "mm")):
                        date_styles.add(style_index)
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = ["".join(node.itertext()) for node in root]
        sheet_names = sorted(n for n in archive.namelist() if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n))
        if not sheet_names:
            raise FinancialDataError("XLSX has no worksheet")
        root = ET.fromstring(archive.read(sheet_names[0]))
    except (BadZipFile, ET.ParseError, KeyError) as exc:
        raise FinancialDataError("invalid XLSX file") from exc
    matrix: list[list[str]] = []
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    for row in root.iter(ns + "row"):
        cells: dict[int, str] = {}
        for cell in row.findall(ns + "c"):
            if cell.find(ns + "f") is not None:
                raise FinancialDataError("XLSX formulas are not accepted; export values as CSV")
            ref = cell.attrib.get("r", "A1")
            letters = re.match(r"[A-Z]+", ref)
            index = 0
            for char in (letters.group(0) if letters else "A"):
                index = index * 26 + ord(char) - 64
            if index < 1 or index > _MAX_COLUMNS:
                raise FinancialDataError("XLSX column limit exceeded")
            value = cell.find(ns + "v")
            inline = cell.find(ns + "is")
            text = "" if value is None else (value.text or "")
            if cell.attrib.get("t") == "s" and text:
                try:
                    shared_index = int(text)
                    if shared_index < 0: raise FinancialDataError("invalid XLSX shared string")
                    text = shared[shared_index]
                except (IndexError, ValueError):
                    raise FinancialDataError("invalid XLSX shared string")
            elif inline is not None:
                text = "".join(inline.itertext())
            elif text and cell.attrib.get("t", "n") == "n" and int(cell.attrib.get("s", 0)) in date_styles:
                try:
                    serial = Decimal(text)
                    if serial != serial.to_integral_value() or not minimum_serial <= serial <= 2_958_465:
                        raise ValueError
                    text = str(excel_epoch + timedelta(days=int(serial)))
                except (InvalidOperation, ValueError, OverflowError):
                    raise FinancialDataError("invalid XLSX date serial; export an ISO YYYY-MM-DD date")
            if len(text) > _MAX_CELL_CHARS:
                raise FinancialDataError("XLSX cell length limit exceeded")
            cells[index - 1] = text
        if cells:
            matrix.append([cells.get(i, "") for i in range(max(cells) + 1)])
        if len(matrix) > _MAX_ROWS + 1:
            raise FinancialDataError("row limit exceeded")
    if not matrix:
        raise FinancialDataError("XLSX worksheet is empty")
    headers = matrix[0]
    return [{headers[i]: row[i] if i < len(row) else "" for i in range(len(headers))} for row in matrix[1:]]


class FinancialDataConnector:
    """Converts CSV/XLSX/manual records to immutable review candidates."""

    def parse(self, *, tenant_id: str, source_name: str, payload: bytes,
              media_type: str, import_kind: ImportKind = "accounting_export",
              created_at: datetime | None = None) -> FinancialImport:
        if not tenant_id.strip():
            raise FinancialDataError("tenant_id is required")
        if not payload or len(payload) > _MAX_BYTES:
            raise FinancialDataError("file is empty or exceeds 8 MiB")
        digest = hashlib.sha256(payload).hexdigest()
        lowered = source_name.lower()
        raw = _rows_from_xlsx(payload) if lowered.endswith(".xlsx") or "spreadsheet" in media_type else _rows_from_csv(payload)
        return self.from_rows(tenant_id=tenant_id, source_name=source_name, rows=raw,
                              import_kind=import_kind, source_sha256=digest,
                              media_type=media_type, created_at=created_at)

    def from_rows(self, *, tenant_id: str, source_name: str, rows: Iterable[dict[str, Any]],
                  import_kind: ImportKind = "manual", source_sha256: str | None = None,
                  media_type: str = "application/json", created_at: datetime | None = None) -> FinancialImport:
        raw = list(rows)
        if not raw or len(raw) > _MAX_ROWS:
            raise FinancialDataError("records are empty or exceed row limit")
        mapping = _mapping(raw[0].keys())
        parsed: list[FinancialRow] = []
        warnings: set[str] = set()
        for number, item in enumerate(raw, 2):
            currency = str(item.get(mapping.get("currency", ""), "")).strip().upper()
            if currency and currency not in {"SGD", "S$"}:
                raise FinancialDataError(f"row {number}: unsupported currency {currency!r}; no conversion is performed")
            amount_text = str(item.get(mapping["amount"], "")).strip()
            if not currency and (import_kind == "accounting_export" or amount_text.startswith("$")):
                warnings.add("currency_not_declared: values are candidate SGD only and require explicit review")
            kind_text = str(item.get(mapping["kind"], "")).strip().lower().replace(" ", "_")
            aliases = {"income": "sale", "invoice": "sale", "purchase": "expense", "bill": "expense", "adjustment": "correction"}
            kind = aliases.get(kind_text, kind_text)
            if kind not in {"sale", "expense", "inventory", "correction"}:
                raise FinancialDataError(f"row {number}: unsupported kind {kind_text!r}")
            reference = str(item.get(mapping.get("reference", ""), "")).strip() or f"row-{number}"
            crop_id = str(item.get(mapping.get("crop_id", ""), "")).strip() or None
            if crop_id and crop_id not in _PLANNING_CROPS:
                warnings.add(f"unsupported_crop:{crop_id}")
            quantity = _decimal(item.get(mapping.get("quantity", "")), optional=True)
            if quantity is not None and quantity < 0 and kind != "correction":
                raise FinancialDataError(f"row {number}: negative quantity requires correction kind")
            parsed.append(FinancialRow(
                row_number=number, occurred_on=_date(item.get(mapping["date"])), kind=kind, reference=reference,
                description=str(item.get(mapping.get("description", ""), "")).strip()[:500], quantity=quantity,
                unit=(str(item.get(mapping.get("unit", ""), "")).strip() or None),
                amount_sgd=_decimal(item.get(mapping["amount"])),
                crop_id=crop_id,
                corrects_reference=reference if kind == "correction" else None,
                provenance={"source_name": source_name, "source_sha256": source_sha256, "row_number": number},
            ))
        now = created_at or datetime.now(timezone.utc)
        if now.tzinfo is None:
            raise FinancialDataError("created_at must be timezone-aware")
        canonical = source_sha256 or hashlib.sha256(repr(raw).encode()).hexdigest()
        candidate_id = "fin-" + hashlib.sha256(f"{tenant_id}:{canonical}:{import_kind}".encode()).hexdigest()[:24]
        return FinancialImport(candidate_id, tenant_id, source_name, canonical, media_type, import_kind, now, tuple(parsed), tuple(sorted(warnings)))

    @staticmethod
    def confirm(candidate: FinancialImport, *, reviewed_by: str, reviewed_at: datetime | None = None) -> FinancialImport:
        if candidate.status != "candidate":
            raise FinancialDataError("only candidates can be confirmed")
        when = reviewed_at or datetime.now(timezone.utc)
        if when.tzinfo is None or not reviewed_by.strip():
            raise FinancialDataError("aware reviewed_at and reviewed_by are required")
        return replace(candidate, status="confirmed", reviewed_at=when, reviewed_by=reviewed_by)

    @staticmethod
    def reject(candidate: FinancialImport, *, reviewed_by: str, reviewed_at: datetime | None = None) -> FinancialImport:
        confirmed = FinancialDataConnector.confirm(candidate, reviewed_by=reviewed_by, reviewed_at=reviewed_at)
        return replace(confirmed, status="rejected")
