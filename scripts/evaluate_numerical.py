"""Versioned synthetic numerical evaluation, not evidence of farm-model validity."""
from __future__ import annotations

import argparse
from datetime import datetime,timezone
from pathlib import Path
import json,subprocess,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from packages.fixtures import GENERATOR_VERSION,GeneratorSettings,synthetic_farm
from packages.contracts import content_hash
from packages.ingestion.storage import write_json_atomic
from packages.planner import plan
from packages.planner.engine import VERSION as PLANNER_VERSION,baseline,candidates,allocations_existing,simulate
from packages.models import FORECAST_CONTRACT_VERSION,MODEL_VERSION,ForecastSettings,forecast,scenarios
from packages.models.reporting import NumericalEvaluationReport

def _source_revision():
    try:
        head=subprocess.run(['git','rev-parse','HEAD'],check=True,capture_output=True,text=True).stdout.strip()
        dirty=bool(subprocess.run(['git','status','--porcelain'],check=True,capture_output=True,text=True).stdout.strip())
        return {'git_head':head,'working_tree_dirty_at_generation':dirty}
    except (OSError,subprocess.CalledProcessError):
        return {'git_head':None,'working_tree_dirty_at_generation':None}


def build_report(*,time_limit:float=0,generated_at:datetime|None=None)->NumericalEvaluationReport:
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
    output=plan(farm,time_limit=time_limit);f=forecast(farm)
    scenario_set=output.get('scenario_set',scenarios())
    b=baseline(farm,candidates(farm),allocations_existing(farm),f['demand'],scenario_set=scenario_set)
    reference=[simulate(farm,b,f['demand'],s) for s in scenario_set]
    identity={'fixture_hash':content_hash(farm),'generator_version':GENERATOR_VERSION,'forecast_version':MODEL_VERSION,
        'forecast_settings':ForecastSettings().model_dump(mode='json'),'planner_version':PLANNER_VERSION,
        'time_limit_seconds':time_limit,'scenario_set':scenario_set}
    report=dict(report_id=content_hash(identity),generated_at=generated_at or datetime.now(timezone.utc),
        status='PASS' if all(not s['violations'] for s in output['strategies']) else 'FAIL',mode='synthetic_demo',
        validation_status='demo_only',fixture_hash=content_hash(farm),dataset_name='Original generated dataset',
        generator_version=GENERATOR_VERSION,generator_settings=GeneratorSettings().model_dump(mode='json'),
        forecast_version=MODEL_VERSION,forecast_contract_version=FORECAST_CONTRACT_VERSION,
        forecast_settings=ForecastSettings().model_dump(mode='json'),cutoff=farm.cutoff,
        source_revision=_source_revision(),
        evaluation_scope={'cohort':'one original deterministic fixture farm; four crop series','origin_count':24,
            'origins_per_crop':6,'horizons':[1],'target':'weekly synthetic ordered_kg','synthetic_only':True,
            'comparison_models':['ewma_alpha_0_35','last_week_naive']},
        forecast_evaluation=forecast_report,planner_version=PLANNER_VERSION,
        planner_configuration={'time_limit_seconds':time_limit,'scenario_set':scenario_set,'scenario_seed':None},
        strategies=[{k:s[k] for k in ('name','metrics','risk','solver','violations','policy_parameters','scenario_set_id','scenario_results')} for s in output['strategies']],
        baseline=[dict(scenario_id=s['scenario_id'],metrics=s['metrics']) for s in reference],
        solver_reproducibility={'single_worker':True,'deterministic_fallback_requested':time_limit==0,
            'runtime_bounded_search_may_vary':time_limit>0,
            'note':'CP-SAT bounded-search wall time, objective and best bound may vary by runtime/solver build; calculations and independent validators remain local.'},
        public_features_used=[],promotion_status='not_eligible_synthetic_only',
        limitations=['Synthetic-only outcomes and recipes; no real-farm forecast or crop-model promotion.',
            'The one-step legacy check is preserved for comparison; the separate v8 synthetic benchmark covers independent cohorts and 1/2/4-week horizons.',
            'Scenario weights are declared simulation weights; no calibrated intervals.',
            'Whole-bed allocations may create surplus; no unsupported fractional beds or partner purchases.',
            'Public weather, News and trade sources have no automatic numerical effect.'])
    return NumericalEvaluationReport.model_validate(report)


def parse_args():
    parser=argparse.ArgumentParser(description='Generate or validate the versioned numerical report')
    parser.add_argument('--output',type=Path,default=Path('reports/numerical_evaluation.json'))
    parser.add_argument('--v8-copy',type=Path,default=Path('reports/v8/numerical_evaluation.json'))
    parser.add_argument('--archive',type=Path,default=Path('reports/v8/archive/numerical_evaluation.pre-v8.json'))
    parser.add_argument('--time-limit',type=float,default=0)
    parser.add_argument('--check',action='store_true')
    return parser.parse_args()


def main():
    args=parse_args()
    if args.check:
        NumericalEvaluationReport.model_validate_json(args.output.read_text(encoding='utf-8'))
        print(json.dumps({'status':'passed','report':str(args.output)},sort_keys=True));return 0
    if args.output.exists() and not args.archive.exists():
        args.archive.parent.mkdir(parents=True,exist_ok=True)
        args.archive.write_bytes(args.output.read_bytes())
    report=build_report(time_limit=args.time_limit)
    payload=report.model_dump(mode='json')
    write_json_atomic(args.output,payload);write_json_atomic(args.v8_copy,payload)
    print(json.dumps({'status':report.status,'report':str(args.output),'archive':str(args.archive),'report_id':report.report_id},sort_keys=True))
    return 0 if report.status=='PASS' else 2


if __name__=='__main__':
    raise SystemExit(main())
