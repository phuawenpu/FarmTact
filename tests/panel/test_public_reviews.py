import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from services.api.app import create_app
from services.api.store import Store
from scripts import build_review_panel as builder


def test_public_reviews_need_no_session_and_never_bootstrap_a_farm(tmp_path,monkeypatch):
    import services.api.reviews as module
    monkeypatch.setattr(module,'ROOT',tmp_path)
    payload={'title':'Published independent reviews','reviews':[{'id':'review01','summary':'Observed, not invented'}]}
    (tmp_path/'config').mkdir();(tmp_path/'config/review_panel.json').write_text(json.dumps(payload))
    with TestClient(create_app(Store('sqlite://'),start_worker=False)) as c:
        r=c.get('/api/v1/reviews')
        assert r.status_code==200 and r.json()==payload
        assert 'set-cookie' not in r.headers and not c.cookies
        assert c.get('/api/v1/reviews?path=/etc/passwd').json()==payload
        assert c.post('/api/v1/reviews',json={}).status_code in (401,405)


def test_missing_public_panel_is_explicit_without_private_fallback(tmp_path,monkeypatch):
    import services.api.reviews as module
    monkeypatch.setattr(module,'ROOT',tmp_path)
    with TestClient(create_app(Store('sqlite://'),start_worker=False)) as c:
        r=c.get('/api/v1/reviews')
        assert r.status_code==503 and 'prepared' in r.json()['detail']


def base_review():
    return dict(id='review01',reviewer_type='end_user',rubric_status='read',rubric_source='page13',rubric_scores=[dict(criterion=c,score=None,rationale='Untested',evidence_ids=[]) for c in builder.CRITERIA],journeys=[dict(device='mobile'),dict(device='desktop')],limitations=['Emulation only'],findings=[dict(severity='medium',evidence_ids=['e1'])],strengths=['Observed'],evidence=[dict(id='e1',type='screenshot',path='apps/web/screenshots/panel/review01/proof.png')])


def test_publisher_only_copies_explicit_owned_images_and_drops_unknown_fields(tmp_path,monkeypatch):
    monkeypatch.setattr(builder,'ROOT',tmp_path)
    r=base_review();p=tmp_path/r['evidence'][0]['path'];p.parent.mkdir(parents=True);p.write_bytes(b'\x89PNG\r\n\x1a\n')
    r['private_session']='do-not-publish'
    out=builder.curate(r,'review01')
    assert 'private_session' not in out
    assert out['evidence'][0]['path']=='/review-evidence/review01/proof.png'
    assert (tmp_path/'apps/web/public/review-evidence/review01/proof.png').exists()
    r['evidence'][0]['path']='../../private.png'
    with pytest.raises(AssertionError):builder.curate(r,'review01')


@pytest.mark.parametrize('mutation',['missing_desktop','fake_grade','missing_evidence','rubric_not_read'])
def test_incomplete_or_misleading_review_is_rejected(tmp_path,monkeypatch,mutation):
    monkeypatch.setattr(builder,'ROOT',tmp_path);r=base_review()
    if mutation=='missing_desktop':r['journeys']=r['journeys'][:1]
    elif mutation=='fake_grade':r['rubric_scores'][0]['score']=10
    elif mutation=='missing_evidence':r['findings'][0]['evidence_ids']=['invented']
    else:r['rubric_status']='not_read'
    with pytest.raises(AssertionError):builder.curate(r,'review01')


def test_published_screenshots_use_static_asset_admission_without_weakening_probe_limit():
    with TestClient(create_app(Store('sqlite://'),start_worker=False)) as c:
        for _ in range(40):assert c.get('/review-evidence/missing.png').status_code==404
        for i in range(30):assert c.get(f'/unknown-{i}').status_code==404
        assert c.get('/unknown-over-limit').status_code==429
