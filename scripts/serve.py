"""Service entrypoint: load local protected secret delivery, then run the API.

No secret is accepted as a command-line argument or served by an HTTP endpoint.
Deployments may inject the environment directly instead of using this local file.
"""
import json,os,stat,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
secret_file=Path.home()/'.config/farmtact/server-secrets.json'
if 'DEEPSEEK_API_KEY' not in os.environ and secret_file.exists():
    info=secret_file.stat()
    if info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)&0o077:
        raise RuntimeError('Server secret delivery file has unsafe ownership or permissions')
    secret=json.loads(secret_file.read_text())
    if isinstance(secret.get('DEEPSEEK_API_KEY'),str):os.environ['DEEPSEEK_API_KEY']=secret['DEEPSEEK_API_KEY']
    del secret
os.environ.setdefault('FARMTACT_EXECUTION_MODE','test')
from services.api.egress import install
install()
import uvicorn
uvicorn.run('services.api.app:app',host='0.0.0.0',port=8080,access_log=False,proxy_headers=False,limit_concurrency=64,timeout_keep_alive=5)
