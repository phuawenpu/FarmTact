"""Exercise the running application. --council makes bounded real DeepSeek calls.

Mutation keys and resulting run IDs are persisted before and after requests so
an operator can explicitly resume a trial without creating another paid run.
"""
from pathlib import Path
import argparse
import json
import os
import secrets
import sys
import time
from urllib.parse import urlsplit

import httpx

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from packages.ingestion.validation import registry_coverage
from packages.agents import ROLES


STATE_VERSION='integrated-demo-resume-v1'


class TrialFailure(RuntimeError):
    def __init__(self,operation,message,*,status_code=None):
        super().__init__(message)
        self.operation=operation;self.message=message;self.status_code=status_code

    def public(self):
        result=dict(operation=self.operation,message=self.message)
        if self.status_code is not None:result['http_status']=self.status_code
        return result


def _write_private(path,payload):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(f'.{path.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp')
    flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL
    if hasattr(os,'O_NOFOLLOW'):flags|=os.O_NOFOLLOW
    fd=os.open(temporary,flags,0o600)
    try:
        with os.fdopen(fd,'w') as output:
            json.dump(payload,output,indent=2);output.write('\n');output.flush();os.fsync(output.fileno())
        temporary.replace(path);path.chmod(0o600)
    finally:
        if temporary.exists():temporary.unlink()


def _write_report(path,report,run_id=None):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    text=json.dumps(report,indent=2)+'\n';path.write_text(text)
    if run_id:path.with_name(path.stem+'_'+run_id+'.json').write_text(text)


def _settings(args):
    return dict(base_url=args.url.rstrip('/'),council=bool(args.council),with_vision=bool(args.vision),
                replan=bool(args.replan),deterministic_replan=bool(args.deterministic_replan),
                require_public_sources=bool(args.require_public_sources),fixture='synthetic_demo')


def _state(args):
    path=args.state or Path(str(args.browser_state)+'.trial.json')
    settings=_settings(args)
    if path.exists():
        try:saved=json.loads(path.read_text())
        except (OSError,json.JSONDecodeError) as exc:raise TrialFailure('load_state','Trial state is unreadable; preserve it for inspection and select a different --state path.') from exc
        if saved.get('schema_version')!=STATE_VERSION or saved.get('settings')!=settings:
            raise TrialFailure('load_state','Existing trial state belongs to different semantic settings; select a different --state path.')
        keys=saved.get('keys',{})
        if set(keys)!= {'import','mission','replan'} or any(not isinstance(value,str) or not value for value in keys.values()):
            raise TrialFailure('load_state','Existing trial state has invalid stable request keys.')
        path.chmod(0o600);saved.setdefault('ids',{});return path,saved,True
    saved=dict(schema_version=STATE_VERSION,settings=settings,
               keys={name:'integrated-'+name+'-'+secrets.token_hex(16) for name in ('import','mission','replan')},ids={})
    _write_private(path,saved)
    return path,saved,False


def _load_cookies(client,path):
    try:browser=json.loads(Path(path).read_text())
    except (OSError,json.JSONDecodeError,KeyError,TypeError) as exc:raise TrialFailure('load_browser_state','Browser state is unavailable or invalid; the saved tenant cannot be resumed safely.') from exc
    for cookie in browser.get('cookies',[]):
        client.cookies.set(cookie['name'],cookie['value'],domain=cookie['domain'],path=cookie.get('path','/'))


def _save_cookies(client,path,url):
    location=urlsplit(url)
    state={'cookies':[{'name':cookie.name,'value':cookie.value,'domain':location.hostname,'path':'/','expires':-1,
                      'httpOnly':True,'secure':location.scheme=='https','sameSite':'Strict'} for cookie in client.cookies.jar],
           'origins':[]}
    _write_private(path,state)


def _checked(response,operation):
    try:response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        message=f'{operation} returned HTTP {response.status_code}; no new key or automatic retry was generated.'
        raise TrialFailure(operation,message,status_code=response.status_code) from exc
    try:return response.json()
    except (json.JSONDecodeError,ValueError) as exc:raise TrialFailure(operation,f'{operation} returned a non-JSON success response; saved keys and IDs were retained for explicit resume.') from exc


def _post(client,path,body,key,operation):
    try:response=client.post(path,json=body,headers={'Idempotency-Key':key})
    except httpx.HTTPError as exc:raise TrialFailure(operation,f'{operation} transport failed; rerun with the same --state to query the same receipt.') from exc
    return _checked(response,operation)


def _get(client,path,operation):
    try:response=client.get(path)
    except httpx.HTTPError as exc:raise TrialFailure(operation,f'{operation} transport failed; no mutation was retried.') from exc
    return _checked(response,operation)


def _await_run(client,run_id):
    started=time.monotonic()
    while time.monotonic()-started<360:
        run=_get(client,'/api/v1/planning-runs/'+run_id,'read planning mission')
        if run['status'] not in ('CREATED','RUNNING'):
            run['measured_wait_seconds']=round(time.monotonic()-started,3);return run
        time.sleep(.5)
    raise TrialFailure('read planning mission','Application mission exceeded the test deadline; existing run and stable receipt were left intact.')


def _parse_args(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--url',default='http://127.0.0.1:8080')
    parser.add_argument('--council',action='store_true')
    parser.add_argument('--require-public-sources',action='store_true')
    parser.add_argument('--replan',action='store_true')
    parser.add_argument('--vision',action='store_true')
    parser.add_argument('--deterministic-replan',action='store_true')
    parser.add_argument('--report',default='reports/integrated_demo.json')
    parser.add_argument('--reuse-browser-state',type=Path)
    parser.add_argument('--browser-state',type=Path,default=Path('/tmp/farmtact-integrated-browser-state.json'))
    parser.add_argument('--state',type=Path,help='Private resume state; defaults to <browser-state>.trial.json')
    return parser.parse_args(argv)


def run(args,*,client_factory=None):
    report={'origin':'synthetic','actual_application_http':True,'council_requested':args.council,
            'stages':[],'base_url':args.url,'status':'INCOMPLETE'}
    state_path=None;saved=None;run_id=None;run_record=None;client_factory=client_factory or httpx.Client
    try:
        state_path,saved,resuming=_state(args)
        report['resume_state']=dict(schema_version=STATE_VERSION,path=str(state_path),resumed=resuming)
        with client_factory(base_url=args.url,timeout=20) as client:
            progressed=bool(saved.get('import_response') or saved.get('ids'))
            cookie_source=(args.browser_state if resuming and args.browser_state.exists() else
                           args.reuse_browser_state if not resuming or not progressed else None)
            if cookie_source:_load_cookies(client,cookie_source)
            elif resuming and progressed:raise TrialFailure('load_browser_state','Saved mutations require the matching private browser state; no request was made.')
            boot=_get(client,'/api/v1/bootstrap','bootstrap')
            _save_cookies(client,args.browser_state,args.url)
            report['registry_coverage']=registry_coverage();report['capabilities']=boot['capabilities'];report['sources']=boot['sources'];report['crop_count']=len(boot['crops'])

            imported=saved.get('import_response')
            if imported is None:
                imported=_post(client,'/api/v1/imports',{'fixture':'synthetic_demo'},saved['keys']['import'],'synthetic fixture import')
                saved['import_response']=imported
                if imported.get('planning_run'):saved['ids']['import_planning_run_id']=imported['planning_run']['id']
                _write_private(state_path,saved)
            report['import']=imported
            if saved['ids'].get('import_planning_run_id'):_await_run(client,saved['ids']['import_planning_run_id'])

            mission_body={'council':args.council,'with_vision':args.vision}
            run_id=saved['ids'].get('mission_run_id')
            if run_id is None:
                created=_post(client,'/api/v1/planning-runs',mission_body,saved['keys']['mission'],'planning mission creation')
                run_id=created['id'];saved['ids']['mission_run_id']=run_id;_write_private(state_path,saved)
                report['run_id']=run_id;_write_report(args.report,report,run_id)
                duplicate=_post(client,'/api/v1/planning-runs',mission_body,saved['keys']['mission'],'planning receipt verification')
                if duplicate.get('id')!=run_id:raise TrialFailure('planning receipt verification','Idempotent planning receipt returned a different mission ID.')
                saved['mission_receipt_verified']=True;_write_private(state_path,saved)
            report['run_id']=run_id
            run_record=_await_run(client,run_id);report['run']=run_record
            if not saved.get('mission_receipt_verified'):
                saved['mission_recovered_by_get']=True;_write_private(state_path,saved)
            replay=_get(client,'/api/v1/planning-runs/'+run_id+'/replay','planning replay')
            if replay.get('execution_mode')!='replay' or replay.get('strategies')!=run_record.get('strategies'):
                raise TrialFailure('planning replay','Stored replay does not match the completed mission.')
            report['replay']={'status':'PASS','replay_of':run_id,'new_inference_calls':0,'events_match':replay.get('events')==run_record.get('events')}

            if args.replan and run_record['status']=='ACCEPTED_FOR_SIMULATION':
                replan_id=saved['ids'].get('replan_run_id')
                if replan_id is None:
                    body={'disruption':'crop_delay',**({'council':False} if args.deterministic_replan else {})}
                    repl=_post(client,'/api/v1/planning-runs/'+run_id+'/replan',body,saved['keys']['replan'],'replan mission creation')
                    replan_id=repl['id'];saved['ids']['replan_run_id']=replan_id;_write_private(state_path,saved)
                    report['replan_run_id']=replan_id;_write_report(args.report,report,run_id)
                report['replan_run_id']=replan_id;report['replan']=_await_run(client,replan_id)

            _save_cookies(client,args.browser_state,args.url)
            report['source_coverage_required']=args.require_public_sources
            report['source_coverage_passed']=len([source for source in report['sources'] if source['status']=='validated'])>=1
            report['status']='PASS' if (report['source_coverage_passed'] or not args.require_public_sources) and report['crop_count']==report['registry_coverage']['catalogue_profiles'] and (not args.vision or run_record.get('visual_observation',{}).get('review_status')=='label_verified_against_fixture') and run_record['status']=='ACCEPTED_FOR_SIMULATION' and (not args.council or run_record['council_status']=='completed' and [claim.get('role') for claim in run_record.get('claims',[])]==ROLES) and (not args.replan or report.get('replan',{}).get('status')=='ACCEPTED_FOR_SIMULATION') else 'INCOMPLETE'
    except TrialFailure as exc:
        report['status']='ERROR';report['error']=exc.public()
    except Exception as exc:
        report['status']='ERROR';report['error']={'operation':'integrated_demo','message':f'Unexpected {type(exc).__name__}; partial report and private resume state were retained.'}
    _write_report(args.report,report,run_id)
    if report['status']=='PASS':
        print(json.dumps({'report':str(args.report),'status':report['status'],'run_id':run_id,'council_status':run_record['council_status'],'warnings':run_record['warnings']}))
        return 0
    print(json.dumps({'report':str(args.report),'status':report['status'],'run_id':run_id,'error':report.get('error')}),file=sys.stderr)
    return 1


def main(argv=None):return run(_parse_args(argv))


if __name__=='__main__':raise SystemExit(main())
