"""Capture/verify immutable explorer results across service restart or deployment."""
import argparse,hashlib,json,os,secrets,time
from pathlib import Path
import httpx

parser=argparse.ArgumentParser()
parser.add_argument('--url',default='http://127.0.0.1:8080')
parser.add_argument('--state',default='/tmp/farmtact-explorer-saved-release.json')
parser.add_argument('--phase',choices=['capture','verify'],required=True)
parser.add_argument('--report',default='reports/explorer_saved_persistence.json')
args=parser.parse_args()
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
def checked(response):response.raise_for_status();return response.json()
with httpx.Client(base_url=args.url,timeout=30) as client:
    if args.phase=='capture':
        workspace=checked(client.get('/api/v1/bootstrap'))
        data=checked(client.post('/api/v1/data-explorer/snapshots',json={'name':'Persistence: alpha 0.8','generator_settings':{'history_trend':.2},'forecast_settings':{'alpha':.8}},headers={'Idempotency-Key':secrets.token_hex(16)}))
        branch=checked(client.post('/api/v1/scenarios',json={'explorer_snapshot_id':data['id']},headers={'Idempotency-Key':secrets.token_hex(16)}))
        checked(client.post('/api/v1/scenarios/'+branch['id']+'/run',headers={'Idempotency-Key':'persist-run'}))
        deadline=time.monotonic()+180
        while True:
            branch=checked(client.get('/api/v1/scenarios/'+branch['id']))
            if branch['status'] not in ('QUEUED','RUNNING'):break
            if time.monotonic()>deadline:raise RuntimeError('Numerical probe timed out')
            time.sleep(1)
        assert branch['status']=='COMPLETED' and branch['result']['forecast']==data['forecast']
        state=dict(cookie=client.cookies.get('farmtact_session'),dataset_id=data['id'],dataset_hash=digest(data),scenario_id=branch['id'],result_hash=digest(branch),farm_hash=digest(workspace['farm']))
        fd=os.open(args.state,os.O_CREAT|os.O_TRUNC|os.O_WRONLY,0o600)
        with os.fdopen(fd,'w') as f:json.dump(state,f)
        print('Captured immutable explorer dataset and numerical result privately; no inference requested.')
    else:
        state=json.loads(Path(args.state).read_text());client.cookies.set('farmtact_session',state['cookie'])
        data=checked(client.get('/api/v1/data-explorer/snapshots/'+state['dataset_id']))
        branch=checked(client.get('/api/v1/scenarios/'+state['scenario_id']))
        workspace=checked(client.get('/api/v1/bootstrap'))
        assert digest(data)==state['dataset_hash']
        assert digest(branch)==state['result_hash']
        assert digest(workspace['farm'])==state['farm_hash']
        report=dict(status='PASS',url=args.url,immutable_dataset_preserved=True,forecast_alpha=data['forecast_settings']['alpha'],branch_result_preserved=True,main_farm_preserved=True,inference_calls=0)
        Path(args.report).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
