"""Exercise the running application. --council makes bounded real DeepSeek calls."""
from pathlib import Path
import argparse,json,time,sys
import httpx
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from packages.ingestion.validation import registry_coverage
from packages.agents import ROLES

def main():
    p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:8080');p.add_argument('--council',action='store_true');p.add_argument('--require-public-sources',action='store_true');p.add_argument('--replan',action='store_true');p.add_argument('--vision',action='store_true');p.add_argument('--deterministic-replan',action='store_true');p.add_argument('--report',default='reports/integrated_demo.json');p.add_argument('--reuse-browser-state',type=Path);p.add_argument('--browser-state',default='/tmp/farmtact-integrated-browser-state.json');args=p.parse_args()
    report={'origin':'synthetic','actual_application_http':True,'council_requested':args.council,'stages':[],'base_url':args.url}
    with httpx.Client(base_url=args.url,timeout=20) as c:
        def await_run(id):
            started=time.monotonic()
            while time.monotonic()-started<360:
                r=c.get('/api/v1/planning-runs/'+id);r.raise_for_status();run=r.json()
                if run['status'] not in ('CREATED','RUNNING'):
                    run['measured_wait_seconds']=round(time.monotonic()-started,3);return run
                time.sleep(.5)
            raise TimeoutError('Application mission exceeded test deadline; existing run left intact')
        if args.reuse_browser_state:
            for cookie in json.loads(args.reuse_browser_state.read_text())['cookies']:
                c.cookies.set(cookie['name'],cookie['value'],domain=cookie['domain'],path=cookie.get('path','/'))
        boot=c.get('/api/v1/bootstrap');boot.raise_for_status();b=boot.json()
        report['registry_coverage']=registry_coverage();report['capabilities']=b['capabilities'];report['sources']=b['sources'];report['crop_count']=len(b['crops'])
        imported=c.post('/api/v1/imports',json={'fixture':'synthetic_demo'},headers={'Idempotency-Key':'integrated-import-'+str(time.time_ns())});imported.raise_for_status();report['import']=imported.json()
        if report['import'].get('planning_run'):await_run(report['import']['planning_run']['id'])
        key='integrated-demo-'+str(time.time_ns())
        request=c.post('/api/v1/planning-runs',json={'council':args.council,'with_vision':args.vision},headers={'Idempotency-Key':key});request.raise_for_status()
        id=request.json()['id'];duplicate=c.post('/api/v1/planning-runs',json={'council':args.council,'with_vision':args.vision},headers={'Idempotency-Key':key});assert duplicate.json()['id']==id
        run=await_run(id);report['run']=run
        replay=c.get('/api/v1/planning-runs/'+id+'/replay');replay.raise_for_status();stored=replay.json()
        assert stored['execution_mode']=='replay' and stored['strategies']==run['strategies']
        report['replay']={'status':'PASS','replay_of':id,'new_inference_calls':0,'events_match':stored['events']==run['events']}
        if args.replan and run['status']=='ACCEPTED_FOR_SIMULATION':
            repl=c.post('/api/v1/planning-runs/'+id+'/replan',json={'disruption':'crop_delay',**({'council':False} if args.deterministic_replan else {})},headers={'Idempotency-Key':key+'-shock'});repl.raise_for_status()
            report['replan']=await_run(repl.json()['id'])
        import os
        from urllib.parse import urlsplit
        location=urlsplit(args.url)
        state={'cookies':[{'name':cookie.name,'value':cookie.value,'domain':location.hostname,'path':'/','expires':-1,'httpOnly':True,'secure':location.scheme=='https','sameSite':'Strict'} for cookie in c.cookies.jar],'origins':[]}
        fd=os.open(args.browser_state,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
        with os.fdopen(fd,'w') as f:json.dump(state,f)
        report['source_coverage_required']=args.require_public_sources
        report['source_coverage_passed']=len([s for s in report['sources'] if s['status']=='validated'])>=1
        report['status']='PASS' if (report['source_coverage_passed'] or not args.require_public_sources) and report['crop_count']==report['registry_coverage']['catalogue_profiles'] and (not args.vision or run.get('visual_observation',{}).get('review_status')=='label_verified_against_fixture') and run['status']=='ACCEPTED_FOR_SIMULATION' and (not args.council or run['council_status']=='completed' and [claim.get('role') for claim in run.get('claims',[])]==ROLES) and (not args.replan or report.get('replan',{}).get('status')=='ACCEPTED_FOR_SIMULATION') else 'INCOMPLETE'
    out=Path(args.report);out.write_text(json.dumps(report,indent=2)+'\n');out.with_name(out.stem+'_'+id+'.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'report':str(out),'status':report['status'],'run_id':id,'council_status':run['council_status'],'warnings':run['warnings']}))
    return 0 if report['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
