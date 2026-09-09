"""Build a secret-free exact-image multi-container Fly Machine configuration."""
from __future__ import annotations
import argparse
import base64
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
GATEWAY_IMAGE = 'registry.fly.io/farmtact@sha256:6dcd86da3a282935c6fc595e36ca8ac140050b23d5ba9480903759d38f8c750b'
IMAGE = re.compile(r'registry\.fly\.io/farmtact(?:-edition-v[1-9][0-9]*)?@sha256:[0-9a-f]{64}\Z')


def machine_config(registry, volume, *, public=False, origin='https://farmtact.fly.dev'):
    ids = [entry['id'] for entry in registry['editions']]
    if ids != [f'v{i}' for i in range(1, len(ids)+1)] or not 1 <= len(ids) <= 99 or registry['latest'] != ids[-1]:
        raise ValueError('A contiguous bounded immutable registry is required')
    if not re.fullmatch(r'vol_[a-z0-9]+', volume):
        raise ValueError('A Fly volume ID is required')
    if origin not in ('https://farmtact.fly.dev', 'http://127.0.0.1:8088'):
        raise ValueError('Unapproved deployment origin')
    images = {e['id']: e['image_digest'] for e in registry['editions']}
    if any(not IMAGE.fullmatch(image) for image in images.values()):
        raise ValueError('Only exact published image digests are allowed')
    upstreams = {name: f'http://farmtact-local-{name}.flycast:{8080+int(name[1:])}' for name in ids}
    adapter = base64.b64encode((ROOT/'scripts/shared_container_entrypoint.py').read_bytes()).decode()
    containers = []
    for name, image in [('gateway', GATEWAY_IMAGE), *images.items()]:
        gateway = name == 'gateway'; port = 8080 if gateway else 8080+int(name[1:])
        env = dict(FARMTACT_CONTAINER=name, FARMTACT_PORT=str(port),
                   FARMTACT_EXECUTION_MODE='test', FARMTACT_SECURE_COOKIES='true',
                   FARMTACT_PUBLIC_ORIGIN=origin, FARMTACT_TRUST_FLY_PROXY='true',
                   FARMTACT_DATA_MODE='synthetic_demo', FARMTACT_LOCAL_EDITIONS='true',
                   FARMTACT_DATABASE_URL='postgresql+psycopg://farmtact@/'+('farmtact_control' if gateway else 'farmtact')+'?host=/tmp/farmtact-pg',
                   PYTHONUNBUFFERED='1')
        if gateway: env.update(FARMTACT_ROLE='gateway', FARMTACT_EDITION_UPSTREAMS=json.dumps(upstreams))
        else: env.update(FARMTACT_EDITION=name, FARMTACT_CONTROL_URL='http://farmtact-local-control.flycast:8080')
        containers.append(dict(name=name,image=image,env=env,
            secrets=[dict(env_var=key,name=key) for key in (['FARMTACT_CONTROL_SECRET'] if gateway else ['FARMTACT_CONTROL_SECRET','DEEPSEEK_API_KEY'])],
            entrypoint=['python','/opt/farmtact-shared-entrypoint.py'],
            files=[dict(guest_path='/opt/farmtact-shared-entrypoint.py',raw_value=adapter),dict(guest_path='/opt/farmtact-shared-registry.json',raw_value=base64.b64encode(json.dumps(registry).encode()).decode())],
            restart=dict(policy='on-failure',max_retries=5),
            stop=dict(signal='SIGTERM',timeout='30s'),
            healthchecks=[dict(name=name+'-ready',http=dict(port=port,method='GET',path='/api/v1/health'),interval=15,timeout=5,grace_period=60,success_threshold=1,failure_threshold=3)],
            **({} if gateway else {'depends_on':[dict(name='gateway',condition='healthy')]})))
    config=dict(guest=dict(cpu_kind='shared',cpus=4,memory_mb=4096),containers=containers,
                mounts=[dict(volume=volume,path='/persist')],
                restart=dict(policy='on-failure',max_retries=5),
                stop_config=dict(signal='SIGTERM',timeout='1m30s'),
                metadata={'farmtact_hosting':'shared-exact-images-v1'})
    if public:
        config['services']=[dict(protocol='tcp',internal_port=8080,autostart=True,autostop='off',min_machines_running=1,
            ports=[dict(port=80,handlers=['http'],force_https=True),dict(port=443,handlers=['http','tls'])],
            checks=[dict(type='http',interval='30s',timeout='5s',grace_period='1m0s',method='GET',path='/api/v1/health')])]
    return config


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--registry',type=Path,default=ROOT/'config/releases/registry.json');p.add_argument('--volume',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--public',action='store_true');p.add_argument('--local-probe',action='store_true');a=p.parse_args()
    c=machine_config(json.loads(a.registry.read_text()),a.volume,public=a.public,origin='http://127.0.0.1:8088' if a.local_probe else 'https://farmtact.fly.dev')
    a.output.write_text(json.dumps(c,indent=2)+'\n')
