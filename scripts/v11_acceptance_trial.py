"""Bounded V11 candidate acceptance, run locally or by authenticated Fly operator.

Private mode uses the existing gateway credential in memory. It never exports
cookies, credentials or request headers. No inference unless --review is explicit.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta, datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import time
import uuid
import httpx


def hashed(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

class API:
    def __init__(self,base,private=False):
        self.base=base.rstrip('/');headers={}
        if private:
            if self.base not in ('http://127.0.0.1:8090','http://127.0.0.1:8091'):raise ValueError('Only fixed V10/V11 candidate ports are admitted')
            headers={'host':'farmtact.fly.dev','origin':'https://farmtact.fly.dev','x-farmtact-gateway':os.environ['FARMTACT_CONTROL_SECRET'],'x-farmtact-client-ip':'198.18.0.11'}
        self.client=httpx.Client(headers=headers,timeout=20)
        self.private=private
    def call(self,method,path,body=None):
        response=self.client.request(method,self.base+'/api/v1'+path,json=body,headers={'Idempotency-Key':uuid.uuid4().hex} if method=='POST' else {})
        if self.private:
            token=self.client.cookies.get('farmtact_session')
            if token:self.client.headers['cookie']='farmtact_session='+token
        if response.status_code>=400:raise RuntimeError(f'{method} {path}: HTTP {response.status_code}: {response.text[:300]}')
        return response.json()
    def get(self,path):return self.call('GET',path)
    def post(self,path,body=None):return self.call('POST',path,body)
    def close(self):self.client.close()


def wait(api,path,deadline=180):
    start=time.monotonic();last=None
    while time.monotonic()-start<deadline:
        last=api.get(path)
        if last.get('status') not in ('DRAFT','QUEUED','RUNNING','CREATED'):
            return last,round(time.monotonic()-start,4)
        time.sleep(.8)
    raise TimeoutError(f'{path} exceeded {deadline}s; last status {last.get("status") if last else None}')


def journey(api,review=False):
    initial=api.get('/bootstrap');before=hashed(initial['farm'])
    s=api.post('/planning-sessions',{'name':'Organizer brief acceptance mission'})
    path='/planning-sessions/'+s['id']
    api.post(path+'/calculate',{'revision':s['revision']});s,elapsed=wait(api,path)
    checks={'initial_calculation':s['status']=='COMPLETED' and len(s['result']['strategies'])==3,'selected_feasible':bool(s.get('selected_strategy_id'))}
    first_result=s['result'];history=deepcopy_json(s['farm']['history'])
    s=api.post(path+'/advance',{'revision':s['revision'],'days':7})
    recorded=deepcopy_json(s['simulation']);checks['seven_days_recorded']=recorded['days_executed']==7
    start=str(date.fromisoformat(recorded['clock_date'])+timedelta(days=1));end=recorded['end_date']
    assumptions={'future_demand':[{'crop_id':'caixin','start_date':start,'end_date':end,'percent':130}],
      'seasonal':[{'crop_id':'caixin','system':'sheltered_hydroponic','start_date':start,'end_date':end,'yield_percent':85,'delay_days':3,'reason':'Declared seasonal production sensitivity, not a fitted weather forecast','provenance':'synthetic_assumption'}],
      'order_changes':[{'operation':'add','order_id':'acceptance-extra-order','crop_id':'lettuce','due_date':str(date.fromisoformat(start)+timedelta(days=21)),'quantity_kg':12,'price_sgd_per_kg':8}]}
    api.post(path+'/disrupt',{'revision':s['revision'],'assumptions':assumptions});s,replan_seconds=wait(api,path)
    checks.update(replan_completed=s['status']=='COMPLETED',history_unchanged=s['farm']['history']==history,retained_evaluated_without_optimization=s['result']['retained_strategy']['evaluated_without_optimization'],same_condition_comparisons=len(s['result']['comparisons'])==3,completed_days_preserved=s['simulation']['days_executed']==7)
    checks['initial_plan_preserved']=api.get(path)['history'][0]['result_id']!=s['result_id']
    for row in s['result']['comparisons']:
        checks['same_bookings_'+row['policy']]=row['baseline_metrics']['booked_requested_kg']==row['scenario_metrics']['booked_requested_kg']
    numerical=s['result'];live=None
    if review:
        api.post(path+'/review',{'revision':s['revision']});s,review_seconds=wait(api,path,330);live=s['review']
        live['elapsed_seconds']=review_seconds
        checks['actual_council_complete']=live['status']=='completed'
        checks['all_active_findings_valid']=all(row['status'] in ('validated','unavailable') for row in live.get('findings',[]))
        checks['actual_calls_within_reserved_ceiling']=0<live.get('request_count',0)<=7
        checks['absence_not_counted_as_inference']=sum(row.get('inference_origin')=='deterministic' for row in live.get('findings',[]))==2
        replay=api.get(path)['review'];checks['review_replay_identical']=hashed(replay)==hashed({k:v for k,v in live.items() if k!='elapsed_seconds'})
    s=api.post(path+'/advance',{'revision':s['revision'],'days':7})
    checks['advance_after_replan']=s['simulation']['days_executed']==14
    checks['main_farm_unchanged']=hashed(api.get('/bootstrap')['farm'])==before
    checks['operations_disabled']=s['simulation']['real_operations_enabled'] is False
    return dict(status='PASS' if all(checks.values()) else 'FAIL',checks=checks,session_id=s['id'],initial_seconds=elapsed,replan_seconds=replan_seconds,initial_result=first_result,numerical_result=numerical,council=live,simulation=s['simulation'])


def deepcopy_json(value):return json.loads(json.dumps(value))


def capacity(candidate_base,old_base,private):
    results=[]
    for trial in range(1,4):
        new=API(candidate_base,private);old=API(old_base,private)
        try:
            before_new=hashed(new.get('/bootstrap')['farm']);before_old=hashed(old.get('/bootstrap')['farm'])
            s=new.post('/planning-sessions',{'name':f'Capacity trial {trial}'})
            branch=old.post('/scenarios',{'name':f'V11 capacity retained V10 trial {trial}','controls':{'demand_crop_id':'caixin','demand_percent':130}})
            started=time.monotonic()
            new.post('/planning-sessions/'+s['id']+'/calculate',{'revision':s['revision']})
            old.post('/scenarios/'+branch['id']+'/run',{})
            timings=[];statuses=[];errors=[];done_new=False;done_old=False
            while time.monotonic()-started<180 and not(done_new and done_old):
                for api in (new,old):
                    moment=time.monotonic()
                    try:api.get('/bootstrap');statuses.append(200)
                    except Exception as exc:errors.append(str(exc));statuses.append(0)
                    timings.append(time.monotonic()-moment)
                if not done_new:
                    value=new.get('/planning-sessions/'+s['id']);done_new=value['status'] not in ('QUEUED','RUNNING')
                    if done_new:new_status=value['status'];new_elapsed=time.monotonic()-started
                if not done_old:
                    value=old.get('/scenarios/'+branch['id']);done_old=value['status'] not in ('QUEUED','RUNNING')
                    if done_old:old_status=value['status'];old_elapsed=time.monotonic()-started
                if not(done_new and done_old):time.sleep(1)
            p95=sorted(timings)[max(0,math.ceil(.95*len(timings))-1)] if timings else None
            checks={'browse_p95_under_5s':p95 is not None and p95<5,'v11_completed_under_180s':done_new and new_status=='COMPLETED' and new_elapsed<180,'v10_completed_under_180s':done_old and old_status=='COMPLETED' and old_elapsed<180,'farms_unchanged':hashed(new.get('/bootstrap')['farm'])==before_new and hashed(old.get('/bootstrap')['farm'])==before_old,'all_browse_successful':all(code==200 for code in statuses)}
            if not done_new:
                value=new.get('/planning-sessions/'+s['id'])
                if value['status'] in ('QUEUED','RUNNING'):new.post('/planning-sessions/'+s['id']+'/cancel',{'revision':value['revision']})
            if not done_old:
                value=old.get('/scenarios/'+branch['id'])
                if value['status'] in ('QUEUED','RUNNING'):old.post('/scenarios/'+branch['id']+'/cancel',{})
            results.append(dict(trial=trial,status='PASS' if all(checks.values()) else 'FAIL',checks=checks,browse_p95_seconds=p95,browse_samples=len(timings),v11_seconds=new_elapsed if done_new else None,v10_seconds=old_elapsed if done_old else None,errors=errors,inference_requests=0))
        except Exception as exc:
            results.append(dict(trial=trial,status='FAIL',error=str(exc),inference_requests=0))
        finally:new.close();old.close()
    return dict(status='PASS' if all(row['status']=='PASS' for row in results) else 'FAIL',trials=results,protocol='Three prescribed V11/V10 paired jobs; no other submitted numerical or provider work; browse p95<5s and terminal jobs<180s. Operator-private loopback transport excludes public network latency.')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--base-url',default='http://127.0.0.1:8080/v11');parser.add_argument('--old-base-url',default='https://farmtact.fly.dev/v10');parser.add_argument('--private-gateway',action='store_true');parser.add_argument('--review',action='store_true');parser.add_argument('--capacity',action='store_true');parser.add_argument('--report',required=True)
    args=parser.parse_args();started=datetime.now(timezone.utc).isoformat()
    try:
        if args.capacity:
            if args.review:raise ValueError('Capacity probes must make zero inference calls')
            report=capacity(args.base_url,args.old_base_url,args.private_gateway)
        else:
            api=API(args.base_url,args.private_gateway)
            try:report=journey(api,args.review)
            finally:api.close()
    except Exception as exc:report=dict(status='FAIL',error=str(exc))
    report.update(started_at=started,completed_at=datetime.now(timezone.utc).isoformat(),base_url=args.base_url,private_gateway=args.private_gateway)
    path=Path(args.report);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(report,indent=2)+'\n');path.chmod(0o600)
    print(json.dumps({key:report[key] for key in ('status','error','checks','trials') if key in report}))
    return 0 if report['status']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
