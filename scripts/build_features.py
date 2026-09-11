"""Versioned availability-aware demand features; external context cannot create target labels."""
from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pyarrow as pa
import pyarrow.parquet as pq
from packages.contracts import Farm,content_hash
from packages.fixtures import synthetic_farm
from packages.models import FORECAST_CONTRACT_VERSION,forecast

def build(farm=None,destination=Path('data')):
    farm=farm or synthetic_farm();f=forecast(farm);rows=[]
    for d in f['demand']:
        dependency_ids=[o.id for o in farm.orders if o.crop_id==d['crop_id'] and str(o.due_date)==d['date'] and o.booked_at<=farm.cutoff]
        dependency_ids += ['history:'+content_hash(h) for h in farm.history if h.crop_id==d['crop_id'] and h.available_at<=farm.cutoff and h.week<farm.planning_date]
        rows.append(dict(**d,cutoff=farm.cutoff.isoformat(),input_hash=content_hash(farm),model_version=f['model_version'],data_mode='synthetic_demo',dependency_ids=dependency_ids))
    path=destination/'normalized/features.parquet';path.parent.mkdir(parents=True,exist_ok=True);pq.write_table(pa.Table.from_pylist(rows),path)
    snapshot_path=destination/'normalized/private_snapshot.json';snapshot_path.write_text(farm.model_dump_json(indent=2)+'\n')
    price_status_counts={status:sum(row['price_status']==status for row in rows) for status in sorted({row['price_status'] for row in rows})}
    manifest=dict(schema_version='1.1',build_version='point-in-time-demand-v1',forecast_contract_version=FORECAST_CONTRACT_VERSION,
        input_hash=content_hash(farm),cutoff=farm.cutoff.isoformat(),origin='synthetic',feature_count=len(rows),
        file=str(path.relative_to(destination)),sha256=__import__('hashlib').sha256(path.read_bytes()).hexdigest(),
        private_snapshot_sha256=__import__('hashlib').sha256(snapshot_path.read_bytes()).hexdigest(),
        dependency_rule='Every private dependency available_at/booked_at <= cutoff; no public observation is a private target',
        price_status_counts=price_status_counts,public_features_used=[],
        public_context_exclusion='No public weather, News or trade value is coupled to demand/yield. Availability, exposure mapping and predictive benefit remain unvalidated.')
    out=destination/'manifests/feature_manifest.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(manifest,indent=2)+'\n');return manifest
if __name__=='__main__':print(json.dumps(build(),indent=2))
