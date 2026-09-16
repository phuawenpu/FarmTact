from datetime import datetime, timezone
from decimal import Decimal
from io import BytesIO
from zipfile import ZipFile

import pytest

from packages.ingestion.financial import FinancialDataConnector, FinancialDataError


def test_csv_is_candidate_with_row_provenance_until_explicit_confirmation():
    raw = (b"Date,Type,Invoice,Description,Qty,Unit,Amount,Crop\n"
           b"2026-09-01,invoice,INV-7,Caixin delivery,12.5,kg,S$ 100.25,caixin\n")
    connector = FinancialDataConnector()
    candidate = connector.parse(tenant_id="farm-a", source_name="ledger.csv", payload=raw,
                                media_type="text/csv", created_at=datetime(2026, 9, 2, tzinfo=timezone.utc))
    assert candidate.status == "candidate"
    assert not candidate.planning_eligible
    assert candidate.rows[0].amount_sgd == Decimal("100.25")
    assert candidate.rows[0].provenance["row_number"] == 2
    confirmed = connector.confirm(candidate, reviewed_by="farmer")
    assert confirmed.planning_eligible
    assert candidate.status == "candidate"


def test_negative_quantity_requires_explicit_correction_record():
    rows = [{"date": "2026-09-01", "type": "sale", "amount": "10", "qty": "-2"}]
    with pytest.raises(FinancialDataError, match="negative quantity"):
        FinancialDataConnector().from_rows(tenant_id="t", source_name="manual", rows=rows)
    rows[0]["type"] = "correction"
    candidate = FinancialDataConnector().from_rows(tenant_id="t", source_name="manual", rows=rows,
                                                    import_kind="correction")
    assert candidate.rows[0].kind == "correction"


def test_rejects_unknown_schema_and_nonfinite_values():
    with pytest.raises(FinancialDataError, match="missing required columns"):
        FinancialDataConnector().from_rows(tenant_id="t", source_name="bad", rows=[{"foo": "bar"}])
    with pytest.raises(FinancialDataError, match="non-finite"):
        FinancialDataConnector().from_rows(tenant_id="t", source_name="bad", rows=[
            {"date": "2026-09-01", "kind": "expense", "amount": "NaN"}
        ])
    with pytest.raises(FinancialDataError, match="unsupported currency"):
        FinancialDataConnector().from_rows(tenant_id="t", source_name="foreign", import_kind="accounting_export", rows=[
            {"date": "2026-09-01", "kind": "expense", "amount": "10", "currency": "USD"}
        ])


def test_undeclared_accounting_currency_is_flagged_for_review():
    candidate = FinancialDataConnector().from_rows(tenant_id="t", source_name="export", import_kind="accounting_export", rows=[
        {"date": "2026-09-01", "kind": "sale", "amount": "$10"}
    ])
    assert candidate.warnings == ("currency_not_declared: values are candidate SGD only and require explicit review",)


def test_xlsx_rejects_formula_cells_instead_of_accepting_cached_values():
    output = BytesIO()
    with ZipFile(output, "w") as archive:
        archive.writestr("xl/worksheets/sheet1.xml", """<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1"><f>1+1</f><v>2</v></c></row></sheetData></worksheet>""")
    with pytest.raises(FinancialDataError, match="formulas are not accepted"):
        FinancialDataConnector().parse(tenant_id="t", source_name="unsafe.xlsx", payload=output.getvalue(),
                                       media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
