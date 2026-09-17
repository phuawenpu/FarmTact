from contextlib import contextmanager
from types import SimpleNamespace
from dataclasses import dataclass
from io import BytesIO
from unittest.mock import Mock
import pytest
from fastapi import HTTPException
from PIL import Image
from services.api import document_extraction as extraction

@dataclass
class Audit:
    request_count: int = 1

@pytest.fixture
def boundary(monkeypatch):
    store=Mock()
    store.reserve_calls.return_value=True
    calls=[]
    @contextmanager
    def factory(*args,**kwargs):
        class Gateway:
            def normalize_image(self,raw,asset_id):
                Image.open(BytesIO(raw)).verify()
                return SimpleNamespace(source_sha256='hash')
            def vision_json(self,**fields):
                calls.append(fields)
                kwargs['budget'].request_count+=1
                data=extraction.PhotoObservation(visible_findings=['Visible green leaves'],uncertainty='No calibrated measurement') if fields['role']=='visual_observer' else extraction.DocumentRecords(rows=[],warnings=['No explicit accounting rows'])
                return SimpleNamespace(data=data,audit=Audit())
        yield Gateway()
    monkeypatch.setattr(extraction.DeepSeekGateway,'from_config',factory)
    return store,calls

def picture():
    out=BytesIO();Image.new('RGB',(16,16),'green').save(out,format='PNG');return out.getvalue()

def test_photo_and_document_authority_are_separate_and_budgeted(boundary):
    store,calls=boundary
    photo=extraction.extract_document(store,'tenant',picture(),'crop.png','photo_observation')
    document=extraction.extract_document(store,'tenant',picture(),'invoice.png','document_extraction')
    assert [c['role'] for c in calls]==['visual_observer','document_vision']
    assert 'visible_findings MUST be a JSON array' in calls[0]['prompt']
    assert 'uncertainty MUST be one non-empty string' in calls[0]['prompt']
    assert '"rows":[' in calls[1]['prompt'] and '"warnings":[' in calls[1]['prompt']
    assert photo['provenance']['yield_authority'] is False
    assert document['provenance']['review_required'] is True
    assert photo['rows'][0]['uncertainty']
    assert store.reserve_calls.call_count==2
    assert [c.args[0] for c in store.release_unused_calls.call_args_list]==[0,0]

def test_invalid_image_needs_no_reservation_or_inference(boundary):
    store,calls=boundary
    with pytest.raises(Exception):extraction.extract_document(store,'tenant',b'not-image','bad.png','document_extraction')
    assert not calls
    store.reserve_calls.assert_not_called()
    store.release_unused_calls.assert_not_called()

def test_upload_size_and_budget_are_enforced_before_provider(boundary):
    store,calls=boundary
    with pytest.raises(HTTPException) as exc:extraction.extract_document(store,'tenant',b'x'*700001,'large','photo_observation')
    assert exc.value.status_code==413
    store.reserve_calls.assert_not_called()
    store.reserve_calls.return_value=False
    with pytest.raises(HTTPException) as exc:extraction.extract_document(store,'tenant',picture(),'photo.png','photo_observation')
    assert exc.value.status_code==429
    assert not calls


def test_gateway_failure_logs_only_bounded_safe_diagnostics(monkeypatch, caplog):
    from contextlib import contextmanager
    from runtime.deepseek_gateway import DeepSeekBlockedError
    store=Mock();store.reserve_calls.return_value=True
    @contextmanager
    def factory(*args,**kwargs):
        class Gateway:
            def normalize_image(self,*args,**kwargs): return SimpleNamespace(source_sha256='hash')
            def vision_json(self,**kwargs): raise DeepSeekBlockedError('DeepSeek request blocked with HTTP 503',status_code=503)
        yield Gateway()
    monkeypatch.setattr(extraction.DeepSeekGateway,'from_config',factory)
    with caplog.at_level('WARNING'),pytest.raises(HTTPException) as exc:
        extraction.extract_document(store,'tenant',picture(),'photo.png','photo_observation')
    assert exc.value.status_code==503
    assert 'type=DeepSeekBlockedError status=503' in caplog.text
    assert 'DeepSeek request blocked with HTTP 503' in caplog.text
