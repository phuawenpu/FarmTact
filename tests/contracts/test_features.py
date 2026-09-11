import pyarrow.parquet as pq
from scripts.build_features import build
from packages.fixtures import synthetic_farm
from packages.contracts import content_hash

def test_features_have_rebuildable_cutoff_and_lineage(tmp_path):
    farm=synthetic_farm();one=build(farm,tmp_path);two=build(farm,tmp_path)
    assert one['sha256']==two['sha256']
    rows=pq.read_table(tmp_path/one['file']).to_pylist()
    assert len(rows)==32
    assert all(r['input_hash']==content_hash(farm) and r['dependency_ids'] for r in rows)
    assert one['public_features_used']==[]
    assert one['forecast_contract_version']=='2.0.0'
    assert sum(one['price_status_counts'].values())==32
    assert all(r['price_status'] in {'booked_weighted_average','unavailable_no_booked_price'} for r in rows)
