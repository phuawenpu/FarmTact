"""Reproducible held-out synthetic evaluation, not evidence of farm-model validity."""
from pathlib import Path
import json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from packages.fixtures import GENERATOR_VERSION,GeneratorSettings,synthetic_farm
from packages.contracts import content_hash
from packages.planner import plan
from packages.planner.engine import baseline,candidates,allocations_existing,simulate
from packages.models import MODEL_VERSION,ForecastSettings,forecast,scenarios

def main():
    farm=synthetic_farm();forecast_report=[]
    for crop in sorted({r.crop_id for r in farm.recipes}):
        values=[float(h.ordered_kg) for h in sorted(farm.history,key=lambda h:h.week) if h.crop_id==crop]
        pred=[]
        for cutoff in range(6,len(values)):
            ewma=values[0]
            for v in values[1:cutoff]:ewma=.35*v+.65*ewma
            pred.append((values[cutoff],ewma,values[cutoff-1]))
        def metric(index):return dict(mae=sum(abs(r[0]-r[index]) for r in pred)/len(pred),wape=sum(abs(r[0]-r[index]) for r in pred)/sum(r[0] for r in pred))
        forecast_report.append(dict(crop_id=crop,held_out_periods=len(pred),ewma=metric(1),last_week_naive=metric(2)))
    output=plan(farm);f=forecast(farm)
    b=baseline(farm,candidates(farm),allocations_existing(farm),f['demand'])
    reference=[simulate(farm,b,f['demand'],s) for s in scenarios()]
    report=dict(status='PASS' if all(not s['violations'] for s in output['strategies']) else 'FAIL',mode='synthetic_demo',validation_status='demo_only',fixture_hash=content_hash(farm),dataset_name='Original generated dataset',generator_version=GENERATOR_VERSION,generator_settings=GeneratorSettings().model_dump(mode='json'),forecast_version=MODEL_VERSION,forecast_settings=ForecastSettings().model_dump(mode='json'),cutoff=farm.cutoff.isoformat(),forecast_evaluation=forecast_report,planner_version='daily-bed-cpsat-v1',strategies=[{k:s[k] for k in ('name','metrics','risk','solver','violations','policy_parameters','scenario_set_id','scenario_results')} for s in output['strategies']],baseline=[dict(scenario_id=s['scenario_id'],metrics=s['metrics']) for s in reference],limitations=['Synthetic-only outcomes and recipes; no real-farm forecast promotion.','Scenario weights are declared simulation weights; no calibrated intervals.','Whole-bed allocations may create surplus; no unsupported fractional beds or partner purchases.'])
    path=Path('reports/numerical_evaluation.json');path.write_text(json.dumps(report,indent=2)+'\n');print(path)
if __name__=='__main__':main()
