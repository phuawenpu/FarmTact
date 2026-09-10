"""Bounded explicit DeepSeek interpretation of a frozen research result.

One direct request reserves at most five provider calls including repairs. An
operator ledger retains that worst-case reservation if the trial is interrupted;
all invocations combined are capped at sixteen. No cookies enter reports.
"""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import time
import uuid
import httpx


def run(url,report_path,ledger_path):
    ledger=json.loads(ledger_path.read_text()) if ledger_path.exists() else {'maximum':16,'attempts':[]}
    if sum(a['charged'] for a in ledger['attempts'])+5>16:raise RuntimeError('Research experiment request ceiling reached')
    attempt={'id':uuid.uuid4().hex,'charged':5,'status':'RESERVED','started_at':datetime.now(timezone.utc).isoformat()}
    ledger['attempts'].append(attempt);ledger_path.parent.mkdir(parents=True,exist_ok=True);ledger_path.write_text(json.dumps(ledger,indent=2)+'\n')
    report={'status':'RUNNING','url':url,'maximum_provider_calls_this_attempt':5,'purpose':'Explicit interpretation of a frozen numerical research result; no farm mutation.'}
    with httpx.Client(timeout=20,follow_redirects=True) as c:
        base=url.rstrip('/')+'/api/v1'
        def get(path):
            response=c.get(base+path);response.raise_for_status();return response.json()
        def post(path,body):
            response=c.post(base+path,json=body,headers={'Idempotency-Key':uuid.uuid4().hex});response.raise_for_status();return response.json()
        paid_started=False
        try:
            before=get('/bootstrap')['farm']
            if url.startswith('http://127.0.0.1:'):
                for cookie in c.cookies.jar:cookie.secure=False
            study=post('/council-research',{})
            def act(kind,**kw):return post(f"/council-research/{study['id']}/actions",dict(action=kind,revision=study['revision'],**kw))
            study=act('propose',operation='reserve_bed',bed_id='bed-04',start_date='2026-09-17',end_date='2026-11-02');study=act('apply');study=act('propose',operation='order_status',order_id='research-extra-order',confirmed=False);study=act('apply');study=act('run')
            deadline=time.monotonic()+180
            while not any(r['version']==study['input_version'] and r['status'] in {'COMPLETED','FAILED'} for r in study['results']):
                if time.monotonic()>deadline:raise TimeoutError('Numerical worker did not complete')
                time.sleep(2);study=get('/council-research/'+study['id'])
            result=next(r for r in study['results'] if r['version']==study['input_version']);assert result['status']=='COMPLETED'
            conversation=post('/conversations',dict(advisor='asha',snapshot_kind='research',snapshot_id=study['id'],research_version=study['input_version'],selected_bed_id='bed-04'))
            path='/conversations/'+conversation['id']
            paid_started=True
            created=post(path+'/messages',dict(content='Explain the reserved bed and unconfirmed order in this frozen research result. Cite research:inputs and relevant numerical tool references. Do not claim to have changed any inputs or real farm operations.'))
            deadline=time.monotonic()+330
            while True:
                conversation=get(path)
                if conversation['last_request_status'] in {'COMPLETED','PARTIAL','FAILED','BLOCKED','INTERRUPTED'}:break
                if time.monotonic()>deadline:raise TimeoutError('Advisor request did not terminate')
                time.sleep(2)
            events=get(path+'/events')['events'];calls=sum(e['event_type']=='inference_request_reserved' for e in events);assert calls<=5
            attempt.update(charged=calls,status=conversation['last_request_status'])
            replay=get(path+'/replay');assert replay['inference_triggered'] is False
            assert before==get('/bootstrap')['farm']
            assert conversation['snapshot_ref']['hash']==result['input_hash']
            assert conversation['snapshot_ref']['version']==study['input_version']
            assert conversation['tool_results']['research:version']==study['input_version']
            replies=[m for m in conversation['messages'] if m.get('speaker')=='advisor']
            report['references_verified']=bool(replies) and all(m.get('validation_status')=='references_verified' for m in replies)
            report['pass_scope']='Provider boundary, frozen context, main-farm preservation and replay; interpretation quality is reported separately.'
            report.update(status='PASS' if conversation['last_request_status']=='COMPLETED' and replies else conversation['last_request_status'],actual_provider_calls=calls,research_session_id=study['id'],research_version=study['input_version'],input_hash=result['input_hash'],conversation_id=conversation['id'],request_id=conversation['last_request_id'],frozen_context_match=True,main_farm_unchanged=True,replay_inference_triggered=False,advisor_messages=replies,events=events)
        except Exception as error:
            if not paid_started:attempt.update(charged=0,status='FAILED_BEFORE_PROVIDER_SUBMISSION')
            report.update(status='FAILED',error=type(error).__name__)
            raise
        finally:
            ledger_path.write_text(json.dumps(ledger,indent=2)+'\n');report_path.parent.mkdir(parents=True,exist_ok=True);report_path.write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'], 'provider requests:',report.get('actual_provider_calls','unknown; worst-case retained'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--url',required=True);p.add_argument('--report',required=True);p.add_argument('--ledger',default='reports/v7/advisor_experiment_budget.json');p.add_argument('--live',action='store_true');a=p.parse_args()
    if not a.live:raise SystemExit('Explicit --live required: this invokes DeepSeek through the application')
    run(a.url,Path(a.report),Path(a.ledger))
