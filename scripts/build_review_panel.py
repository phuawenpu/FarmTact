"""Curate only the ten approved persona reports and explicit PNG evidence for publication."""
import json, re, shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CRITERIA=['Goal & Scope Definition','Architecture & Reasoning Loop','Tool Use & Integration','Autonomy & Human-in-the-Loop','Safety, Security & Guardrails','Observability & Evaluation','Platform & Tooling Usage']
KEYS=['id','persona','reviewer_type','disclosure','reviewed_at','build','rubric_status','rubric_source','rubric_scores','usability_score','summary','strengths','findings','journeys','evidence','limitations','priority_improvements','retest']


def curate(raw, reviewer_id):
    assert raw['id']==reviewer_id
    assert raw['reviewer_type'] in ('judge','end_user') and raw['rubric_status']=='read'
    assert '13' in str(raw['rubric_source'])
    assert {s['criterion'] for s in raw['rubric_scores']}==set(CRITERIA)
    assert len(raw['rubric_scores'])==7
    for score in raw['rubric_scores']:
        assert score['score'] is None or (isinstance(score['score'],(float,int)) and 0<=score['score']<=5)
    assert any('mobile' in j['device'].lower() or ('touch' in j['device'].lower() and re.match(r'(360|390|430)(?:x|×)',str(j.get('viewport','')))) for j in raw['journeys'])
    assert any('desktop' in j['device'].lower() for j in raw['journeys'])
    assert raw['limitations'] and raw['findings'] and raw['strengths']
    assert all(f['severity'] in ('high','medium','low') for f in raw['findings'])
    assert raw.get('usability_score') is None or 0<=raw['usability_score']<=10
    result={k:raw[k] for k in KEYS if k in raw}
    result['reviewer_agent']=f'/root/{reviewer_id} · gpt-5.6-sol'
    for field,allowed_keys in {'evidence':['id','type','path','description'],'rubric_scores':['criterion','score','rationale','evidence_ids'],'findings':['severity','title','observation','impact','recommendation','evidence_ids'],'journeys':['id','device','viewport','steps','outcome','observations']}.items():
        result[field]=[{k:item[k] for k in allowed_keys if k in item} for item in raw[field]]
    ids={e['id'] for e in raw['evidence']}
    assert len(ids)==len(raw['evidence'])
    for item in [*raw['findings'],*raw['rubric_scores']]:
        assert set(item.get('evidence_ids',[]))<=ids, f'{reviewer_id}: dangling evidence'
    for e in result['evidence']:
        if e['type']=='screenshot':
            source=(ROOT/e['path']).resolve()
            allowed=(ROOT/'apps/web/screenshots/panel'/reviewer_id).resolve()
            assert source.is_relative_to(allowed) and source.suffix=='.png'
            assert source.read_bytes()[:8]==b'\x89PNG\r\n\x1a\n'
            assert re.fullmatch(r'[A-Za-z0-9_.-]+\.png',source.name)
            target=ROOT/'apps/web/public/review-evidence'/reviewer_id/source.name
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
            e['path']=f'/review-evidence/{reviewer_id}/{source.name}'
        else:
            e['path']='' # Never expose private logs or filesystem paths as public download targets.
    # Deny credential-bearing fields accidentally added to otherwise public prose.
    encoded=json.dumps(result)
    assert not re.search(r'(?:Bearer\s+[A-Za-z0-9_-]{15}|(?:sk-|ghp_)[A-Za-z0-9_-]{20}|farmtact_session\s*[=:]\s*[A-Za-z0-9_-]{16})',encoded)
    return result


def main():
    from PIL import Image
    reports=[json.loads((ROOT/f'reports/panel/review{i:02}.json').read_text()) for i in range(1,11)]
    for report in reports:
        widths=[]
        for evidence in report['evidence']:
            if evidence['type']=='screenshot':
                with Image.open(ROOT/evidence['path']) as screenshot:widths.append(screenshot.width)
        assert any(320<=w<=700 for w in widths) and any(w>=1000 for w in widths), f"{report['id']}: actual mobile and desktop screenshots required"
    reviews=[curate(report,f'review{i:02}') for i,report in enumerate(reports,1)]
    data={'title':'FarmTact independent AI review panel','published_at':datetime.now(timezone.utc).isoformat(),
      'release_notes':['Mobile pages scroll normally until Move farm is selected. Direct dragging works across beds and empty ground, and deliberate taps still inspect records.','Map arrows, keyboard navigation and larger previous/next preview-day controls provide alternatives to dragging. Map position is bounded, cancelled gestures release cleanly, and mouse-wheel scrolling is no longer captured.','The mobile navigation changes are verified separately from the independent persona reviews; browser emulation does not replace physical-device testing.'],
      'methodology':['Ten distinct Codex reviewer agents independently adopted user or judge personas and interacted with the real application on mobile and desktop browsers.','All reviewers read the judging rubric on page 13 of the user-supplied briefing. Its other deployment or platform instructions were not used.','Mobile tests use browser touch emulation, not physical devices. Browser observations, supplemental source inspection and untested capabilities are distinguished in each report.','Reviewers used bounded synthetic numerical experiments and optional explicit DeepSeek advisor messages. Browsing this public page performs no inference and loads no farm session.','Baseline findings are retained. Any release retest is shown separately, with its tested build and observations. No claim of a fix relies only on intent.'],
      'rubric':{'source_url':'https://github.com/phuawenpu/FarmTact/blob/main/ShowMeYourAgent_Hackathon_Briefing_release-1.pdf','page':13,'git_blob':'b5a05dc8e0b849d9f8b1566cbd865151984a1730','criteria':CRITERIA,'scoring':'The supplied rubric defines no weights or scale. This AI panel uses an unofficial 0–5 evidence scale: 0 absent, 1 weak, 2 partial, 3 competent, 4 strong, 5 exceptional; null means untested. Usability /10 is a separate subjective persona assessment.'},'reviews':reviews}
    (ROOT/'config/review_panel.json').write_text(json.dumps(data,indent=2)+'\n')
    print(f'Curated {len(reviews)} independent reviews and {sum(len(r["evidence"]) for r in reviews)} evidence references.')

if __name__=='__main__':main()
