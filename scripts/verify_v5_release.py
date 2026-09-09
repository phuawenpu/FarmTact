"""Bounded synthetic v5 API smoke; --advisor permits one explicit paid request.

Persistent owner-only state makes reruns idempotent. Normal smoke uses no inference;
the optional direct advisor path can use at most two provider requests (one repair).
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

import httpx

p=argparse.ArgumentParser()
p.add_argument('--url',default='https://farmtact.fly.dev/v5/')
p.add_argument('--state',default='/tmp/farmtact-v5-live-state.json')
p.add_argument('--report',default='reports/v5/live_api.json')
p.add_argument('--advisor',action='store_true')
a=p.parse_args();state_path=Path(a.state)
state=json.loads(state_path.read_text()) if state_path.exists() else {}
checks=[]
def check(name,value):
    checks.append({'name':name,'pass':bool(value)})
    if not value:raise AssertionError(name)
def save():
    fd=os.open(state_path,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(fd,'w') as f:json.dump(state,f)
    state_path.chmod(0o600)
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def wait(read,terminal,seconds=180):
    until=time.monotonic()+seconds
    while time.monotonic()<until:
        value=read()
        if terminal(value):return value
        time.sleep(1)
    raise TimeoutError('Bounded release job did not complete')
report=dict(status='RUNNING',url=a.url,checks=checks,provider_calls=0)
try:
    with httpx.Client(base_url=a.url.rstrip('/')+'/',timeout=35) as c:
        if state.get('cookie'):c.headers['Cookie']='farmtact_v5_session='+state['cookie']
        def get(path):
            r=c.get('api/v1/'+path);r.raise_for_status();return r.json()
        def post(path,body,key):
            r=c.post('api/v1/'+path,json=body,headers={'Idempotency-Key':'v5-release-'+key});r.raise_for_status();return r.json()
        expected=json.loads(Path('config/releases/v5.json').read_text())['source_commit']
        check('exact immutable source',get('health')['source_commit']==expected)
        bootstrap=get('bootstrap')
        if not state.get('cookie'):
            state['cookie']=next(v.value for v in c.cookies.jar if v.name=='farmtact_v5_session');save()
        state.setdefault('farm_hash',digest(bootstrap['farm']));save()
        browser={'cookies':[dict(name='farmtact_v5_session',value=state['cookie'],domain=httpx.URL(a.url).host,path='/v5/',httpOnly=True,secure=a.url.startswith('https'),sameSite='Strict',expires=-1)],'origins':[]}
        path=state_path.with_name(state_path.stem+'-browser.json');fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
        with os.fdopen(fd,'w') as f:json.dump(browser,f)
        origin=str(httpx.URL(a.url).copy_with(path='/'))
        wrong=c.get(origin+'v4/api/v1/market-signals',headers={'Cookie':'farmtact_v4_session='+state['cookie']})
        check('edition cookie cannot read prior edition',wrong.status_code==401)
        check('seven council roles',len(get('conversations/advisors')['advisors'])==7)
        check('public numerical observations retained',sum(len(v) for v in get('data-explorer/public')['datasets'].values())==200)
        live_news=get('news');check('real cached News metadata',live_news['total']>0)
        check('news changes no numerical inputs',live_news['numerical_effect']=='none')
        dataset=post('data-explorer/snapshots',{'name':'V5 frozen release check','generator_settings':{'history_multiplier':1.1},'forecast_settings':{'alpha':.7}},'dataset')
        state['snapshot_id']=dataset['id'];save()
        scenario=post('scenarios',{'name':'V5 release decision','explorer_snapshot_id':dataset['id'],'controls':{'demand_crop_id':'pak_choi','demand_percent':120}},'scenario')
        state['scenario_id']=scenario['id'];save()
        if scenario['status']=='DRAFT':post('scenarios/'+scenario['id']+'/run',{},'scenario-run')
        scenario=wait(lambda:get('scenarios/'+state['scenario_id']),lambda v:v['status'] not in ('DRAFT','QUEUED','RUNNING'))
        check('real numerical worker completed',scenario['status']=='COMPLETED')
        check('saved alpha reaches strategy inputs',scenario['result']['forecast']['forecast_settings']=={'alpha':.7})
        check('same-policy alternatives retained',len(scenario['policy_comparisons'])==3)
        frozen=get('news?scenario_id='+scenario['id'])
        check('scenario freezes exact News context',frozen['frozen'] and frozen['content_hash']==scenario['news_context']['content_hash'])
        child=post('scenarios',{'parent_scenario_id':scenario['id'],'controls':{'labour_percent':90}},'child')
        check('continuation retains root and News',child['news_context']==scenario['news_context'] and child['comparison_root']==scenario['comparison_root'])
        check('sandbox leaves main farm unchanged',digest(get('bootstrap')['farm'])==state['farm_hash'])
        conversation=post('conversations',{'advisor':'idris','snapshot_kind':'scenario','snapshot_id':scenario['id']},'conversation')
        state['conversation_id']=conversation['id'];save()
        conversation=get('conversations/'+conversation['id'])
        check('advisor attached to selected frozen scenario',conversation['snapshot_ref']['id']==scenario['id'] and conversation['tool_results']['news:context_hash']==frozen['content_hash'])
        event_path='conversations/'+conversation['id']+'/events'
        def calls():return sum(e['event_type']=='inference_request_reserved' for e in get(event_path)['events'])
        before=calls()
        if a.advisor:
            title_ref=next(k for k in conversation['tool_results'] if k.startswith('news:news_') and k.endswith('.title'))
            body={'content':f'Using this frozen scenario, explain the relevance and limits of the source headline at tool reference {title_ref}. Cite that exact reference and news:context_hash. Distinguish publication time from our synthetic farm date, and explain why this headline alone cannot change demand. Do not propose a numerical change.'}
            request=post('conversations/'+conversation['id']+'/messages',body,'advisor-one')
            state['advisor_request_id']=request['id'];save()
            conversation=wait(lambda:get('conversations/'+conversation['id']),lambda v:v.get('last_request_id')==request['id'] and v.get('last_request_status') in ('COMPLETED','PARTIAL','FAILED','BLOCKED','INTERRUPTED'))
            report['provider_calls']=calls()
            report['new_provider_calls']=calls()-before
            check('explicit advisor completes through configured gateway',conversation['last_request_status']=='COMPLETED')
            messages=[m for m in conversation['messages'] if m.get('speaker')=='advisor' and m.get('request_id')==request['id']]
            check('advisor cites exact frozen News evidence',bool(messages) and any(title_ref in m.get('tool_refs',[]) for m in messages))
            check('direct request stays within two-call repair ceiling',calls()<=2)
        recorded=calls();replay=get('conversations/'+conversation['id']+'/replay')
        check('replay reuses frozen News without inference',replay['tool_results']['news:context_hash']==frozen['content_hash'] and calls()==recorded)
        report.update(status='PASS',provider_calls=calls(),new_provider_calls=calls()-before,scenario_id=scenario['id'],snapshot_id=dataset['id'],news_context_hash=frozen['content_hash'],news_records=live_news['total'],advisor_requested=a.advisor)
except Exception as e:
    report.update(status='FAIL',error=type(e).__name__+': '+str(e));raise
finally:
    Path(a.report).write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'],len(checks),'v5 API checks; private session state not displayed')
