"""Generate isolated UI-test response fixtures; never exports browser cookies."""
import json
from pathlib import Path
from fastapi.testclient import TestClient
from services.api.app import create_app
from services.api.store import Store

def build():
    with TestClient(create_app(Store('sqlite://'),start_worker=False)) as client:
        bootstrap=client.get('/api/v1/bootstrap').json()
        response=client.post('/api/v1/planning-sessions',json={'name':'V22 UI fixture','workflow':True},headers={'Idempotency-Key':'v22-ui-fixture'})
        response.raise_for_status()
        return {'bootstrap':bootstrap,'session':response.json(),'workflow':client.get('/api/v1/farm-workflow').json()}
if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    args.output.write_text(json.dumps(build())+'\n');args.output.chmod(0o600)
