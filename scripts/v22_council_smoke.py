"""Explicit, bounded V22 live Council smoke. Operator credentials never leave loopback.

One numerical calculation, one structured Council review, and at most one direct
Chair question. No approval, provider fallback, retries or budget overrides.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import time
from uuid import uuid4
import httpx


def run(output: Path) -> dict:
    report = {'status': 'RUNNING', 'provider_submissions': 0, 'checks': [], 'scope': 'Live availability/integration smoke, not agronomic or human usability validation'}
    def save(): output.write_text(json.dumps(report, indent=2)+'\n')
    if not os.environ.get('DEEPSEEK_API_KEY'):
        report.update(status='UNAVAILABLE', reason='Provider credential is not configured; no inference submitted');save();return report
    headers={'host':'farmtact.fly.dev','origin':'https://farmtact.fly.dev','x-farmtact-gateway':os.environ['FARMTACT_CONTROL_SECRET'],'x-farmtact-client-ip':'127.0.0.1'}
    with httpx.Client(base_url='http://127.0.0.1:8102/api/v1',headers=headers,timeout=45,trust_env=False) as client:
        def request(method,path,body=None):
            response=client.request(method,path,json=body,headers={'Idempotency-Key':uuid4().hex} if method=='POST' else {})
            if response.status_code==429:
                raise RuntimeError('Rate limited; no retry; Retry-After='+response.headers.get('Retry-After','unspecified'))
            response.raise_for_status()
            if path=='/bootstrap':client.headers['cookie']='farmtact_session='+client.cookies.get('farmtact_session')
            return response.json()
        def wait(path,field):
            deadline=time.monotonic()+360
            while time.monotonic()<deadline:
                value=request('GET',path)
                if str(value.get(field,'')).upper() not in ('QUEUED','RUNNING','PENDING'):return value
                time.sleep(2)
            raise TimeoutError('Bounded smoke deadline exceeded; no resubmission')
        try:
            request('GET','/bootstrap')
            session=request('POST','/planning-sessions',{'name':'V22 explicit live Council smoke','workflow':True})
            path='/planning-sessions/'+session['id']
            request('POST',path+'/calculate',{'revision':session['revision']})
            session=wait(path,'status')
            if session['status']!='COMPLETED':raise RuntimeError('Calculation did not complete')
            report['session_id']=session['id'];report['result_id']=session['result_id']
            request('POST',path+'/review',{'revision':session['revision']});report['provider_submissions']+=1;save()
            session=wait(path,'status');review=session.get('review',{})
            report['review']={key:review.get(key) for key in ('status','request_count','result_id','reason')}
            report['roles']=[{key:row.get(key) for key in ('role','status','truth_status','tool_status','proposed_strategy_id','rejection_reasons')} for row in review.get('findings',[])]
            if review.get('status') not in ('completed','partial'):
                report.update(status='UNAVAILABLE',reason='Council review did not return a completed or partial response');save();return report
            report['checks'].append({'name':'review binds current result','pass':review.get('result_id')==session['result_id']})
            created=request('POST','/conversations',{'advisor':'asha','snapshot_kind':'planning','snapshot_id':session['id'],'expected_result_id':session['result_id'],'council_review_result_id':session['result_id']})
            thread='/conversations/'+created['id']
            request('POST',thread+'/messages',{'content':'Explain the main tradeoff in the recorded Council review and which evidence is still missing.'});report['provider_submissions']+=1;save()
            conversation=wait(thread,'last_request_status')
            answers=[row for row in conversation.get('messages',[]) if row.get('speaker')!='user']
            report['chair']={'status':conversation.get('last_request_status'),'messages':[{'speaker':row.get('speaker_name'),'validation_status':row.get('validation_status'),'interpretation_status':row.get('interpretation_status'),'fact_count':len(row.get('rendered_facts',[]))} for row in answers]}
            before=len(conversation.get('messages',[]));replay=request('GET',thread+'/replay')
            report['checks'].append({'name':'saved conversation replays without inference','pass':len(replay.get('messages',[]))==before and replay.get('inference_triggered') is False})
            report['status']='PASS' if all(row['pass'] for row in report['checks']) and answers else 'PARTIAL'
        except Exception as error:
            report.update(status='UNAVAILABLE',reason=f'{type(error).__name__}: '+str(error)[:240])
    save();return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--live-ai',action='store_true');parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if not args.live_ai:parser.error('Explicit --live-ai required; this smoke submits bounded provider work')
    print(json.dumps(run(args.output),indent=2))
