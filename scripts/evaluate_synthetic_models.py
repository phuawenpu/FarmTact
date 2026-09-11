#!/usr/bin/env python3
"""Build deterministic synthetic-only demand and crop-cycle evaluation evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPOSITORY_ROOT=Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0,str(REPOSITORY_ROOT))

from packages.fixtures import benchmark_manifest,synthetic_crop_cycle_benchmark,synthetic_demand_benchmark
from packages.ingestion.storage import write_json_atomic
from packages.models.evaluation import SyntheticEvaluationReport,build_synthetic_evaluation


def build_report()->SyntheticEvaluationReport:
    return build_synthetic_evaluation(
        synthetic_demand_benchmark('training'),synthetic_demand_benchmark('evaluation'),
        synthetic_crop_cycle_benchmark('training'),synthetic_crop_cycle_benchmark('evaluation'))


def parse_args()->argparse.Namespace:
    parser=argparse.ArgumentParser(description='Evaluate deterministic synthetic demand and crop-cycle benchmarks')
    parser.add_argument('--output',type=Path,default=Path('reports/v8/synthetic_model_evaluation.json'))
    parser.add_argument('--manifest-output',type=Path,default=Path('data/manifests/synthetic_benchmark_manifest.json'))
    parser.add_argument('--check',action='store_true',help='validate the existing report instead of rewriting it')
    return parser.parse_args()


def main()->int:
    args=parse_args()
    if args.check:
        SyntheticEvaluationReport.model_validate_json(args.output.read_text(encoding='utf-8'))
        print(json.dumps({'status':'passed','report':str(args.output)},sort_keys=True))
        return 0
    report=build_report()
    write_json_atomic(args.output,report.model_dump(mode='json'))
    write_json_atomic(args.manifest_output,{
        'schema_version':'1.0.0','mode':'synthetic_benchmark','report_id':report.report_id,
        'public_features_used':[],
        'bundles':{
            'demand_training':report.demand_training_manifest,
            'demand_evaluation':report.demand_evaluation_manifest,
            'crop_cycle_training':report.crop_cycle_training_manifest,
            'crop_cycle_evaluation':report.crop_cycle_evaluation_manifest,
        },
        'rebuild_command':'python scripts/evaluate_synthetic_models.py',
        'claim_boundary':'Synthetic-only pipeline validation; not evidence of real-farm model validity.',
    })
    print(json.dumps({'status':'passed','report':str(args.output),'report_id':report.report_id},sort_keys=True))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
