"""Capture and verify an owned release session without logging authentication material."""
import argparse,hashlib,json,os,secrets,sys,time
from pathlib import Path
import httpx

parser=argparse.ArgumentParser()
parser.add_argument('--url',default='https://farmtact.fly.dev')
parser.add_argument('--state',default='/tmp/farmtact-gameplay-release.json')
parser.add_argument('--phase',choices=['capture','verify','capture-gameplay','verify-gameplay'],required=True)
parser.add_argument('--report',default='reports/gameplay_persistence.json')
args=parser.parse_args();path=Path(args.state)
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
def checked(response):response.raise_for_status();return response.json()
def preserved(before, after):
    if isinstance(before,dict):return isinstance(after,dict) and all(k in after and preserved(v,after[k]) for k,v in before.items())
    if isinstance(before,list):return isinstance(after,list) and len(before)==len(after) and all(preserved(a,b) for a,b in zip(before,after))
    return before==after
with httpx.Client(base_url=args.url,timeout=30) as client:
    if args.phase=='capture':
        workspace=checked(client.get('/api/v1/bootstrap'))
        created=checked(client.post('/api/v1/planning-runs',json={'council':False},headers={'Idempotency-Key':secrets.token_hex(16)}))
        deadline=time.monotonic()+150
        while True:
            run=checked(client.get('/api/v1/planning-runs/'+created['id']))
            if run['status'] not in ('CREATED','RUNNING'):break
            if time.monotonic()>deadline:raise RuntimeError('Numerical probe timeout')
            time.sleep(1)
        if not run['strategies']:raise RuntimeError('Probe did not compute strategies')
        state=dict(url=args.url,cookie=client.cookies.get('farmtact_session'),farm=workspace['farm'],run_id=run['id'],strategies_hash=digest(run['strategies']))
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
        with os.fdopen(fd,'w') as f:json.dump(state,f)
        print('Captured private release session with completed numerical run; no credentials printed.')
    else:
        state=json.loads(path.read_text());client.cookies.set('farmtact_session',state['cookie'])
        workspace=checked(client.get('/api/v1/bootstrap'))
        run=checked(client.get('/api/v1/planning-runs/'+state['run_id']))
        assert preserved(state['farm'],workspace['farm']),'Farm changed during release'
        assert digest(run['strategies'])==state['strategies_hash'],'Recorded planning results changed'
        if args.phase=='capture-gameplay':
            scenario=checked(client.post('/api/v1/scenarios',json={'name':'Release persistence lesson','controls':{'cash_percent':75},'quest_id':'tight_budget'},headers={'Idempotency-Key':secrets.token_hex(16)}))
            checked(client.post('/api/v1/scenarios/'+scenario['id']+'/run',headers={'Idempotency-Key':'release-run'}))
            deadline=time.monotonic()+150
            while True:
                scenario=checked(client.get('/api/v1/scenarios/'+scenario['id']))
                if scenario['status'] not in ('QUEUED','RUNNING'):break
                if time.monotonic()>deadline:raise RuntimeError('Scenario timeout')
                time.sleep(1)
            assert scenario['status']=='COMPLETED'
            progress=checked(client.post('/api/v1/quests/tight_budget/inspect',json={'scenario_id':scenario['id']}))
            conversation=checked(client.post('/api/v1/conversations',json={'advisor':'mei','snapshot_kind':'scenario','snapshot_id':scenario['id']},headers={'Idempotency-Key':secrets.token_hex(16)}))
            state.update(scenario_id=scenario['id'],scenario_result_hash=digest(scenario['result']),conversation_id=conversation['id'],quest_progress=progress)
            path.write_text(json.dumps(state))
            print('Captured persistent branch, completed quest, and empty conversation; no inference requested.')
        else:
            report=dict(status='PASS',base_url=args.url,phase=args.phase,main_farm_preserved=True,recorded_run_preserved=True,secrets_printed=False)
            if args.phase=='verify-gameplay':
                scenario=checked(client.get('/api/v1/scenarios/'+state['scenario_id']))
                assert digest(scenario['result'])==state['scenario_result_hash']
                conversation=checked(client.get('/api/v1/conversations/'+state['conversation_id']))
                assert conversation['id']==state['conversation_id']
                if state.get('conversation_messages_hash'):
                    actual=hashlib.sha256(json.dumps(conversation['messages'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
                    assert actual==state['conversation_messages_hash'],'Recorded advisor messages changed during release'
                    report['advisor_messages_preserved']=len(conversation['messages'])
                if state.get('prior_partial_conversation_id'):
                    partial=checked(client.get('/api/v1/conversations/'+state['prior_partial_conversation_id']))
                    partial_hash=hashlib.sha256(json.dumps(partial['messages'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
                    assert partial_hash==state['prior_partial_messages_hash'],'Earlier partial dialogue changed during release'
                    report['partial_dialogue_messages_preserved']=len(partial['messages'])
                quests=checked(client.get('/api/v1/quests'))['quests']
                assert next(q for q in quests if q['id']=='tight_budget')['status']=='completed'
                report.update(branch_result_preserved=True,conversation_preserved=True,quest_progress_preserved=True)
            Path(args.report).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
