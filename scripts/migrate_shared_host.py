"""Operator-only transfer orchestration for the authorized FarmTact shared host.

All locations/apps are fixed or enumerated. No HTTP endpoints, secret output or
unrelated Fly resources. Destructive cleanup is a separate post-verification step.
"""
from concurrent.futures import ThreadPoolExecutor
import argparse
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
PRIVATE=Path('/tmp/farmtact-v6-transfer')
CANDIDATE='2871575b4544d8'
ORIGINAL={'gateway':('farmtact','d8d2060c074438'),'v1':('farmtact-edition-v1','2873455c446528'),'v2':('farmtact-edition-v2','683e037ad33908'),'v3':('farmtact-edition-v3','2870e9ea3e4e28'),'v4':('farmtact-edition-v4','78475e3cde1298'),'v5':('farmtact-edition-v5','6836952f050738')}
ARTIFACTS=('database.dump','fingerprint.json','cache.tar.gz')


def run(args,stdin=None):
    r=subprocess.run(args,input=stdin,text=True,capture_output=True,timeout=180)
    if r.returncode:
        # Commands contain only fixed paths and IDs, no credentials/data.
        raise RuntimeError('Operator command failed: '+str(args[:5])+' '+r.stderr[-1500:])
    return r.stdout


def flags(name,target):
    if name not in ORIGINAL:raise ValueError('Unknown owned edition')
    if target=='candidate':return ['--app','farmtact','--machine',CANDIDATE,'--container',name]
    app,machine=ORIGINAL[name]
    return ['--app',app,'--machine',machine]


def ssh(name,target,command):
    return run(['fly','ssh','console',*flags(name,target),'--command',command])


def sftp(name,target,commands):
    output=run(['fly','ssh','sftp','shell',*flags(name,target)],'\n'.join(commands)+'\nquit\n')
    if any(word in output.lower() for word in ('error:', 'failed to', 'file exists')):raise RuntimeError('SFTP operation did not complete')
    return output


def prepare(name,target):
    ssh(name,target,'install -d -m 0700 -o farmtact -g farmtact /data/shared-transfer')
    ssh(name,target,'rm -f /opt/farmtact-shared-transfer.py')
    sftp(name,target,[f'put {ROOT}/scripts/shared_host_transfer.py /opt/farmtact-shared-transfer.py'])
    ssh(name,target,'chmod 0644 /opt/farmtact-shared-transfer.py')
    print('Prepared',target,name,flush=True)


def action(name,target,operation):
    if operation not in ('freeze','export','restore','verify','resume'):raise ValueError('Unknown operation')
    result=ssh(name,target,'gosu farmtact python /opt/farmtact-shared-transfer.py '+operation)
    print(target,name,operation,result.strip(),flush=True)


def transfer(name):
    local=PRIVATE/name;local.mkdir(mode=0o700,exist_ok=True)
    for file in ARTIFACTS:(local/file).unlink(missing_ok=True)
    sftp(name,'original',[f'get /data/shared-transfer/{file} {local}/{file}' for file in ARTIFACTS])
    for file in ARTIFACTS:(local/file).chmod(0o600)
    ssh(name,'candidate','rm -f /data/shared-transfer/database.dump /data/shared-transfer/fingerprint.json /data/shared-transfer/cache.tar.gz')
    sftp(name,'candidate',[f'put {local}/{file} /data/shared-transfer/{file}' for file in ARTIFACTS])
    ssh(name,'candidate','chown farmtact:farmtact /data/shared-transfer/database.dump /data/shared-transfer/fingerprint.json /data/shared-transfer/cache.tar.gz')
    print('Copied private artifacts',name,flush=True)


def parallel(function,names):
    with ThreadPoolExecutor(max_workers=3) as pool:
        for result in pool.map(function,names):pass


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('operation',choices=['prepare','freeze-export','copy','freeze-restore','verify','resume']);p.add_argument('--target',choices=['original','candidate'],default='original');p.add_argument('--edition',choices=list(ORIGINAL));a=p.parse_args()
    os.umask(0o077);PRIVATE.mkdir(mode=0o700,exist_ok=True)
    names=[a.edition] if a.edition else list(ORIGINAL)
    if a.operation=='prepare':parallel(lambda name:prepare(name,a.target),names)
    elif a.operation=='copy':parallel(transfer,names)
    elif a.operation=='freeze-export':
        # Freeze editions before the gateway so active-job recovery can still
        # finish its operational requests if a preflight finds unfinished work.
        editions=[name for name in names if name!='gateway']
        parallel(lambda name:action(name,'original','freeze'),editions)
        if 'gateway' in names:
            action('gateway','original','freeze')
            run(['fly','machine','cordon',ORIGINAL['gateway'][1],'--app','farmtact'])
        parallel(lambda name:action(name,'original','export'),names)
    elif a.operation=='freeze-restore':
        for name in sorted(names,key=lambda n:n=='gateway'):action(name,'candidate','freeze')
        parallel(lambda name:action(name,'candidate','restore'),names)
    else:parallel(lambda name:action(name,a.target,a.operation),names)
