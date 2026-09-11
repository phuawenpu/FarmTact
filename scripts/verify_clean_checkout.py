"""Reproduce the staged source tree in an isolated directory/database; no LLM calls.

Stage intended files first. This checks the index, never copies ignored secrets,
raw downloads, node_modules, or the developer virtual environment into the tree.
"""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,tempfile,time,uuid

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'reports/clean_checkout.json'
report={'status':'RUNNING','inference_calls':0,'steps':[]}

def run(command,cwd,env=None,timeout=240):
    started=time.monotonic()
    result=subprocess.run(command,cwd=cwd,env=env,capture_output=True,text=True,timeout=timeout)
    report['steps'].append({'command':command,'exit_code':result.returncode,'seconds':round(time.monotonic()-started,2)})
    if result.returncode:
        # Package managers may include authenticated URLs in diagnostics; retain
        # only the exit code. Reproduction commands identify the failed step.
        raise RuntimeError('Clean-checkout command failed: '+command[0])
    return result.stdout

def main():
    dbname='farmtact_clean_'+uuid.uuid4().hex[:12]
    database_created=False
    with tempfile.TemporaryDirectory(prefix='farmtact-clean-') as directory:
        checkout=Path(directory)/'checkout';checkout.mkdir()
        env=os.environ.copy()
        for name in ('DEEPSEEK_API_KEY','GH_TOKEN','GITHUB_TOKEN','FLY_API_TOKEN','FLY_ACCESS_TOKEN','MOONSHOT_API_KEY','MINIMAX_API_KEY'):
            env.pop(name,None)
        env['FARMTACT_DATABASE_URL']=f'postgresql+psycopg://sprite@/{dbname}?host=/tmp/farmtact-pg'
        try:
            report['staged_tree']=run(['git','write-tree'],ROOT).strip()
            run(['git','checkout-index','--all',f'--prefix={checkout}/'],ROOT)
            source_files=sorted(p for p in checkout.rglob('*') if p.is_file() and p.suffix in ('.py','.ts','.tsx','.json','.css') and p.parts[len(checkout.parts)] in ('packages','runtime','services','config','apps'))
            report['source_digest']=hashlib.sha256(b''.join(str(p.relative_to(checkout)).encode()+b'\0'+p.read_bytes() for p in source_files)).hexdigest()
            run([sys.executable,'-m','venv',str(checkout/'.venv')],checkout,env)
            python=str(checkout/'.venv/bin/python')
            run([python,'-m','pip','install','-r','requirements.lock.txt'],checkout,env)
            run(['npm','ci','--prefix','apps/web'],checkout,env)
            run(['npm','run','build','--prefix','apps/web'],checkout,env)
            run(['createdb','-h','/tmp/farmtact-pg',dbname],checkout,env);database_created=True
            run([python,'scripts/initialize_database.py'],checkout,env)
            run([python,'-m','packages.fixtures'],checkout,env)
            run([python,'scripts/build_dataset.py','--fixture-bundle','data/fixtures/public_context_v1'],checkout,env)
            run([python,'scripts/build_features.py'],checkout,env)
            quality=json.loads((checkout/'data/reports/data_quality.json').read_text())
            report['public_data_quality']=quality
            assert quality['status']=='passed' and quality['row_counts']['traceable_rows']>0
            smoke="""
import json,time
from fastapi.testclient import TestClient
from services.api.app import create_app
from packages.ingestion.validation import registry_coverage

def wait(c,id):
    deadline=time.monotonic()+90
    while time.monotonic()<deadline:
        run=c.get('/api/v1/planning-runs/'+id).json()
        if run['status'] not in ('CREATED','RUNNING'):return run
        time.sleep(.2)
    raise AssertionError('mission timeout')
with TestClient(create_app()) as c:
    b=c.get('/api/v1/bootstrap'); assert b.status_code==200 and len(b.json()['crops'])==registry_coverage()['catalogue_profiles']
    assert c.get('/').status_code==200
    imported=c.post('/api/v1/imports',json={'fixture':'synthetic_demo'},headers={'Idempotency-Key':'clean-import'}); assert imported.status_code==201
    r=c.post('/api/v1/planning-runs',json={'council':False},headers={'Idempotency-Key':'clean-plan'}); assert r.status_code==202
    run=wait(c,r.json()['id']); assert run['status']=='ACCEPTED_FOR_SIMULATION' and len(run['strategies'])==3 and run['claims']==[]
    replay=c.get('/api/v1/planning-runs/'+run['id']+'/replay').json(); assert replay['execution_mode']=='replay' and replay['strategies']==run['strategies']
    assert c.get('/api/v1/planning-runs/'+run['id']+'/worklist.csv').status_code==200
    changed=c.post('/api/v1/planning-runs/'+run['id']+'/replan',json={'council':False},headers={'Idempotency-Key':'clean-replan'}); assert changed.status_code==202
    replanned=wait(c,changed.json()['id']); assert replanned['status']=='ACCEPTED_FOR_SIMULATION' and replanned['input_version']==3
    assert c.get('/api/v1/planning-runs/'+run['id']+'/worklist.csv').status_code==409
    print(json.dumps({'status':'PASS','crop_count':len(b.json()['crops']),'strategy_count':3,'initial_version':run['input_version'],'replan_version':replanned['input_version'],'inference_calls':0}))
"""
            report['workflow']=json.loads(run([python,'-c',smoke],checkout,env).strip())
            report['status']='PASS'
        except Exception as error:
            report['status']='FAIL';report['error_type']=type(error).__name__
            raise
        finally:
            if database_created:run(['dropdb','-h','/tmp/farmtact-pg',dbname],ROOT,env)
            REPORT.write_text(json.dumps(report,indent=2)+'\n')
    print('Clean checkout PASS: isolated dependencies, synthetic source-contract fixture, PostgreSQL workflow; no inference calls')

if __name__=='__main__':main()
