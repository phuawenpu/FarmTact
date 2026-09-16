from contextlib import contextmanager
from dataclasses import dataclass
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pypdf import PdfReader

from scripts.v12_pdf_trial import synthetic_invoice_pdf
from services.api import document_extraction as extraction


@dataclass
class Audit:
    provider: str = "deepseek"


def test_native_pdf_contains_authored_text_and_enters_text_extraction(monkeypatch):
    raw = synthetic_invoice_pdf(); text = PdfReader(__import__("io").BytesIO(raw)).pages[0].extract_text()
    assert all(value in text for value in ("2026-09-03", "INV-V12-PDF", "12 kg", "SGD 96.00"))
    captured = {}
    @contextmanager
    def factory(*args, **kwargs):
        class Gateway:
            def chat_json(self, role, messages, output_model, **fields):
                captured["text"] = messages[1]["content"]
                kwargs["budget"].request_count += 1
                data = output_model.model_validate({"rows": [{"date": "2026-09-03", "kind": "sale", "reference": "INV-V12-PDF",
                    "description": "caixin", "quantity": 12, "unit": "kg", "amount": 96, "crop_id": "caixin"}], "warnings": []})
                return SimpleNamespace(data=data, audit=Audit())
        yield Gateway()
    monkeypatch.setattr(extraction.DeepSeekGateway, "from_config", factory)
    store = SimpleNamespace(reserve_calls=lambda *args: True, release_unused_calls=lambda *args: None)
    result = extraction.extract_document(store, "tenant", raw, "invoice.pdf", "document_extraction")
    assert "INV-V12-PDF" in captured["text"] and result["rows"][0]["quantity"] == "12"


def test_pdf_photo_observation_is_rejected_before_budget_or_provider():
    class Store:
        def reserve_calls(self, *args): raise AssertionError("provider budget must not be touched")
    with pytest.raises(HTTPException) as exc:
        extraction.extract_document(Store(), "tenant", synthetic_invoice_pdf(), "invoice.pdf", "photo_observation")
    assert exc.value.status_code == 422
