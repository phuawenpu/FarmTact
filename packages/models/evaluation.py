"""Leakage-aware synthetic benchmarks and model-promotion gates.

These utilities exercise an evaluation pipeline.  They are deliberately unable
to promote a model because their targets are generated, not observed on farms.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime,time,timezone
import math
import random
from statistics import mean
from typing import Any,Literal

from pydantic import BaseModel,ConfigDict,Field,model_validator

from packages.contracts import content_hash
from packages.fixtures import (
    CropCycleBundle,
    CropCycleOutcome,
    SyntheticDemandBundle,
    SyntheticDemandOrder,
    benchmark_manifest,
)


EVALUATION_SCHEMA_VERSION='farmtact-synthetic-evaluation-2.0.0'
DEMAND_EVALUATOR_VERSION='rolling-origin-demand-v3'
CROP_CYCLE_EVALUATOR_VERSION='whole-batch-cycle-v1'
PROMOTION_POLICY_VERSION='farmtact-model-promotion-v1'
HORIZONS=(1,2,4)
SEASONAL_PERIOD_WEEKS=13


class PromotionGate(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True,allow_inf_nan=False,validate_default=True)
    gate_id: str
    required: bool
    status: Literal['passed','failed','blocked','not_applicable']
    observed: str
    requirement: str


class PromotionDecision(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True,allow_inf_nan=False,validate_default=True)
    policy_version: Literal['farmtact-model-promotion-v1']=PROMOTION_POLICY_VERSION
    eligible_for_production: Literal[False]=False
    status: Literal['blocked']='blocked'
    candidate_scope: Literal['synthetic_benchmark_only']='synthetic_benchmark_only'
    gates: list[PromotionGate]

    @model_validator(mode='after')
    def required_gates_prevent_promotion(self):
        if not any(g.required and g.status in {'failed','blocked'} for g in self.gates):
            raise ValueError('synthetic evaluation must retain a blocking production gate')
        return self


class SyntheticEvaluationReport(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True,allow_inf_nan=False,validate_default=True)
    schema_version: Literal['farmtact-synthetic-evaluation-2.0.0']=EVALUATION_SCHEMA_VERSION
    report_id: str
    generated_at: datetime
    mode: Literal['synthetic_benchmark']='synthetic_benchmark'
    validation_status: Literal['synthetic_only']='synthetic_only'
    demand_evaluator_version: str
    crop_cycle_evaluator_version: str
    demand_training_manifest: dict[str,Any]
    demand_evaluation_manifest: dict[str,Any]
    crop_cycle_training_manifest: dict[str,Any]
    crop_cycle_evaluation_manifest: dict[str,Any]
    split_checks: dict[str,Any]
    demand_evaluation: dict[str,Any]
    crop_cycle_evaluation: dict[str,Any]
    promotion: PromotionDecision
    conclusions: list[str]=Field(min_length=1)
    limitations: list[str]=Field(min_length=1)


def _known_order_value(row:SyntheticDemandOrder,origin:datetime)->float:
    if row.booked_at>origin:
        return 0.0
    cancelled=row.cancelled_kg if row.cancellation_available_at is not None and row.cancellation_available_at<=origin else 0.0
    return row.gross_ordered_kg-cancelled


def _ewma(values:list[float],alpha:float)->float:
    if not values:
        return 0.0
    estimate=values[0]
    for value in values[1:]:
        estimate=alpha*value+(1-alpha)*estimate
    return estimate


def _actual_by_week(rows:list[SyntheticDemandOrder])->dict:
    totals=defaultdict(float)
    for row in rows:
        totals[row.due_week]+=row.net_ordered_kg
    return dict(totals)


def _series(bundle:SyntheticDemandBundle,key_kind:Literal['farm','buyer'])->dict[tuple,list[SyntheticDemandOrder]]:
    grouped=defaultdict(list)
    for row in bundle.records:
        identity=row.farm_id if key_kind=='farm' else row.buyer_id
        grouped[(identity,row.crop_id)].append(row)
    return dict(grouped)


def _tune_alpha(training:SyntheticDemandBundle)->dict[str,Any]:
    candidates=(.1,.2,.35,.5,.65,.8,.9)
    scores={alpha:[] for alpha in candidates}
    excluded=0
    for rows in _series(training,'farm').values():
        totals=_actual_by_week(rows)
        availability={week:max(row.outcome_available_at for row in rows if row.due_week==week) for week in totals}
        weeks=sorted(totals)
        for index in range(16,len(weeks)):
            origin=datetime.combine(weeks[index],time(hour=12),timezone.utc)
            history=[totals[week] for week in weeks[:index] if availability[week]<=origin]
            excluded+=sum(availability[week]>origin for week in weeks[:index])
            if not history:continue
            target=totals[weeks[index]]
            for alpha in candidates:
                scores[alpha].append(abs(target-_ewma(history,alpha)))
    mean_mae={alpha:mean(errors) for alpha,errors in scores.items()}
    selected=min(candidates,key=lambda alpha:(mean_mae[alpha],alpha))
    return {'selected_alpha':selected,'selection_metric':'one_step_mae',
        'candidate_alphas':list(candidates),'training_scores':{str(k):round(v,6) for k,v in mean_mae.items()},
        'evaluation_partition_used_for_selection':False,'unavailable_history_weeks_excluded':excluded,
        'availability_rule':'Every historical target dependency is available at its training forecast origin.'}


def _rolling_predictions(bundle:SyntheticDemandBundle,key_kind:Literal['farm','buyer'],alpha:float)->tuple[list[dict],dict]:
    predictions=[]
    leakage_violations=0
    excluded_history=0; unavailable_seasonal=0
    cancellation_records=sum(1 for row in bundle.records if row.cancelled_kg>0)
    for series_key,rows in _series(bundle,key_kind).items():
        totals=_actual_by_week(rows)
        weeks=sorted(totals)
        week_rows=defaultdict(list)
        for row in rows:
            week_rows[row.due_week].append(row)
        for origin_index in range(20,len(weeks)-max(HORIZONS)+1):
            origin_week=weeks[origin_index]
            origin=datetime.combine(origin_week,time(hour=12),timezone.utc)
            available_weeks=[]
            available_values=[]
            for historical_week in weeks[:origin_index]:
                dependencies=week_rows[historical_week]
                if all(row.outcome_available_at<=origin for row in dependencies):
                    available_weeks.append(historical_week)
                    available_values.append(totals[historical_week])
                    leakage_violations+=sum(row.outcome_available_at>origin for row in dependencies)
                else:excluded_history+=1
            if not available_values:
                continue
            for horizon in HORIZONS:
                target_week=weeks[origin_index+horizon-1]
                target=totals[target_week]
                confirmed=sum(_known_order_value(row,origin) for row in week_rows[target_week])
                seasonal_week=target_week.fromordinal(target_week.toordinal()-7*SEASONAL_PERIOD_WEEKS)
                # A calendar match alone does not make the seasonal target available.
                seasonal_known=seasonal_week in available_weeks
                seasonal=totals[seasonal_week] if seasonal_known else available_values[-1]
                if seasonal_week in totals and not seasonal_known:unavailable_seasonal+=1
                raw={
                    'last_week':available_values[-1],
                    'seasonal_naive':seasonal,
                    'ewma_alpha_0_35':_ewma(available_values,.35),
                    'tuned_ewma':_ewma(available_values,alpha),
                }
                for model,prediction in raw.items():
                    predictions.append({'series_id':series_key[0],'crop_id':series_key[1],
                        'horizon_weeks':horizon,'origin_week':origin_week.isoformat(),
                        'target_week':target_week.isoformat(),'model':model,'actual':target,
                        'prediction':max(confirmed,prediction),'confirmed_as_of_origin':confirmed})
    return predictions,{'leakage_violations':leakage_violations,'cancellation_records':cancellation_records,
        'unavailable_history_weeks_excluded':excluded_history,'unavailable_seasonal_fallbacks':unavailable_seasonal,
        'availability_rule':'Training values require every order outcome_available_at <= forecast origin; future bookings/cancellations contribute only after their own availability timestamps.'}


def _percentile(values:list[float],fraction:float)->float:
    if not values:
        return 0.0
    ordered=sorted(values)
    position=(len(ordered)-1)*fraction
    lower=int(math.floor(position));upper=int(math.ceil(position))
    if lower==upper:
        return ordered[lower]
    return ordered[lower]*(upper-position)+ordered[upper]*(position-lower)


def _metrics(rows:list[dict])->dict[str,float]:
    errors=[row['prediction']-row['actual'] for row in rows]
    absolute=[abs(value) for value in errors]
    denominator=sum(row['actual'] for row in rows)
    return {'n':len(rows),'mae':round(mean(absolute),6),'rmse':round(math.sqrt(mean([value*value for value in errors])),6),
        'wape':round(sum(absolute)/denominator,6) if denominator else 0.0,'bias_kg':round(mean(errors),6)}


def _mae_interval(rows:list[dict],seed:int)->dict[str,float]:
    by_series=defaultdict(list)
    for row in rows:
        by_series[row['series_id']].append(abs(row['prediction']-row['actual']))
    series_mae=[mean(values) for values in by_series.values()]
    if not series_mae:
        return {'low':0.0,'high':0.0,'confidence':.95,'method':'deterministic_series_bootstrap'}
    rng=random.Random(seed)
    samples=[]
    for _ in range(500):
        samples.append(mean(rng.choice(series_mae) for _ in series_mae))
    return {'low':round(_percentile(samples,.025),6),'high':round(_percentile(samples,.975),6),
        'confidence':.95,'method':'deterministic_series_bootstrap_500_replicates'}


def evaluate_demand(training:SyntheticDemandBundle,evaluation:SyntheticDemandBundle)->dict[str,Any]:
    tuning=_tune_alpha(training)
    output={'tuning':tuning,'horizons_weeks':list(HORIZONS),'seasonal_period_weeks':SEASONAL_PERIOD_WEEKS,
        'target':'final_net_ordered_kg_after_cancellations','cohorts':{},'leakage':{}}
    for kind in ('farm','buyer'):
        predictions,checks=_rolling_predictions(evaluation,kind,tuning['selected_alpha'])
        output['leakage'][kind]=checks
        summaries=[]
        for horizon in HORIZONS:
            for model in ('last_week','seasonal_naive','ewma_alpha_0_35','tuned_ewma'):
                rows=[row for row in predictions if row['horizon_weeks']==horizon and row['model']==model]
                summaries.append({'horizon_weeks':horizon,'model':model,**_metrics(rows),
                    'mae_95_interval':_mae_interval(rows,982451+horizon*100+len(model)+len(kind))})
        output['cohorts'][kind]={'series_count':len(_series(evaluation,kind)),'metrics':summaries}
    output['public_features_used']=[]
    output['feature_exclusion']='No public weather, News or trade feature enters a forecast because exposure and predictive value are unvalidated.'
    return output


def _cycle_metric(rows:list[tuple[float,float]])->dict[str,float]:
    errors=[prediction-actual for actual,prediction in rows]
    absolute=[abs(value) for value in errors]
    return {'n':len(rows),'mae':round(mean(absolute),6),'rmse':round(math.sqrt(mean([value*value for value in errors])),6),
        'bias':round(mean(errors),6)}


def evaluate_crop_cycles(training:CropCycleBundle,evaluation:CropCycleBundle)->dict[str,Any]:
    residuals=defaultdict(lambda:{'days':[],'yield':[]})
    for row in training.outcomes:
        planned_days=(row.planned_harvest_date-row.planned_sow_date).days
        baseline_yield=row.area_m2*row.recipe_marketable_kg_per_m2
        residuals[row.crop_id]['days'].append(row.observed_cycle_days-planned_days)
        residuals[row.crop_id]['yield'].append(row.observed_marketable_kg-baseline_yield)
    predictions={'recipe_baseline':{'maturity_days':[],'marketable_kg':[]},
        'crop_residual_mean':{'maturity_days':[],'marketable_kg':[]}}
    interval_hits={'maturity_days':0,'marketable_kg':0};interval_total=0
    for row in evaluation.outcomes:
        planned_days=(row.planned_harvest_date-row.planned_sow_date).days
        baseline_yield=row.area_m2*row.recipe_marketable_kg_per_m2
        crop=residuals[row.crop_id]
        candidate_days=planned_days+mean(crop['days'])
        candidate_yield=max(0,baseline_yield+mean(crop['yield']))
        predictions['recipe_baseline']['maturity_days'].append((row.observed_cycle_days,planned_days))
        predictions['recipe_baseline']['marketable_kg'].append((row.observed_marketable_kg,baseline_yield))
        predictions['crop_residual_mean']['maturity_days'].append((row.observed_cycle_days,candidate_days))
        predictions['crop_residual_mean']['marketable_kg'].append((row.observed_marketable_kg,candidate_yield))
        day_low=planned_days+_percentile(crop['days'],.1);day_high=planned_days+_percentile(crop['days'],.9)
        yield_low=max(0,baseline_yield+_percentile(crop['yield'],.1));yield_high=max(0,baseline_yield+_percentile(crop['yield'],.9))
        interval_hits['maturity_days']+=day_low<=row.observed_cycle_days<=day_high
        interval_hits['marketable_kg']+=yield_low<=row.observed_marketable_kg<=yield_high
        interval_total+=1
    return {'evaluation_unit':'whole_batch_temporal_and_farm_holdout','feature_set':['crop_id','recipe_cycle_days','recipe_marketable_kg_per_m2','area_m2'],
        'excluded_features':evaluation.excluded_features,'models':{model:{target:_cycle_metric(rows) for target,rows in targets.items()} for model,targets in predictions.items()},
        'candidate_interval_coverage':{key:round(value/interval_total,6) for key,value in interval_hits.items()},
        'interval_definition':'Training residual 10th to 90th percentiles; synthetic descriptive interval, not calibrated uncertainty.',
        'training_outcome_count':len(training.outcomes),'evaluation_outcome_count':len(evaluation.outcomes)}


def build_synthetic_evaluation(training_demand:SyntheticDemandBundle,evaluation_demand:SyntheticDemandBundle,
    training_cycles:CropCycleBundle,evaluation_cycles:CropCycleBundle)->SyntheticEvaluationReport:
    train_farms={row.farm_id for row in training_demand.records};eval_farms={row.farm_id for row in evaluation_demand.records}
    train_buyers={row.buyer_id for row in training_demand.records};eval_buyers={row.buyer_id for row in evaluation_demand.records}
    train_batches={row.batch_id for row in training_cycles.outcomes};eval_batches={row.batch_id for row in evaluation_cycles.outcomes}
    train_cycle_farms={row.farm_id for row in training_cycles.outcomes};eval_cycle_farms={row.farm_id for row in evaluation_cycles.outcomes}
    split_checks={'farm_ids_disjoint':train_farms.isdisjoint(eval_farms),'buyer_ids_disjoint':train_buyers.isdisjoint(eval_buyers),
        'batch_ids_disjoint':train_batches.isdisjoint(eval_batches),'dates_non_overlapping':max(row.due_week for row in training_demand.records)<min(row.due_week for row in evaluation_demand.records),
        'separate_generator_versions':training_demand.generator_version!=evaluation_demand.generator_version and training_cycles.generator_version!=evaluation_cycles.generator_version,
        'crop_cycle_farms_disjoint':train_cycle_farms.isdisjoint(eval_cycle_farms),
        'crop_training_outcomes_available_before_evaluation':max(row.outcome_available_at for row in training_cycles.outcomes)<min(row.input_available_at for row in evaluation_cycles.outcomes),
        'demand_training_outcomes_available_before_first_evaluation_week':max(row.outcome_available_at for row in training_demand.records)<datetime.combine(min(row.due_week for row in evaluation_demand.records),time(hour=12),timezone.utc)}
    demand=evaluate_demand(training_demand,evaluation_demand)
    cycles=evaluate_crop_cycles(training_cycles,evaluation_cycles)
    leakage=sum(check['leakage_violations'] for check in demand['leakage'].values())
    gates=[
        PromotionGate(gate_id='schema_and_split_integrity',required=True,status='passed' if all(split_checks.values()) else 'failed',
            observed=str(split_checks),requirement='Validated records and disjoint train/evaluation identities, dates and generator versions.'),
        PromotionGate(gate_id='point_in_time_leakage',required=True,status='passed' if leakage==0 else 'failed',
            observed=f'{leakage} detected dependency violations',requirement='Every feature dependency must be available at or before forecast origin.'),
        PromotionGate(gate_id='real_farm_temporal_validation',required=True,status='blocked',
            observed='No real farm/customer outcome dataset supplied.',requirement='Pass pre-registered temporal holdout evaluation on authorized real net orders and whole-batch outcomes.'),
        PromotionGate(gate_id='external_farm_validation',required=True,status='blocked',
            observed='No independent external farm cohort supplied.',requirement='Validate performance and interval behavior on farms absent from model development.'),
        PromotionGate(gate_id='operational_monitoring',required=True,status='blocked',
            observed='No production model, drift reference or rollback trial exists.',requirement='Define monitoring, alert, rollback and retraining controls before operational promotion.'),
    ]
    generated_at=datetime.now(timezone.utc)
    identity={'schema_version':EVALUATION_SCHEMA_VERSION,'demand_evaluator_version':DEMAND_EVALUATOR_VERSION,'crop_evaluator_version':CROP_CYCLE_EVALUATOR_VERSION,'promotion_policy_version':PROMOTION_POLICY_VERSION,
        'demand_train':content_hash(training_demand),'demand_eval':content_hash(evaluation_demand),
        'cycle_train':content_hash(training_cycles),'cycle_eval':content_hash(evaluation_cycles)}
    return SyntheticEvaluationReport(report_id=content_hash(identity),generated_at=generated_at,
        demand_evaluator_version=DEMAND_EVALUATOR_VERSION,crop_cycle_evaluator_version=CROP_CYCLE_EVALUATOR_VERSION,
        demand_training_manifest=benchmark_manifest(training_demand),demand_evaluation_manifest=benchmark_manifest(evaluation_demand),
        crop_cycle_training_manifest=benchmark_manifest(training_cycles),crop_cycle_evaluation_manifest=benchmark_manifest(evaluation_cycles),
        split_checks=split_checks,demand_evaluation=demand,crop_cycle_evaluation=cycles,
        promotion=PromotionDecision(gates=gates),
        conclusions=['The evaluation pipeline is deterministic and exercises disjoint synthetic cohorts, rolling origins, multiple horizons, cancellations and whole-batch crop outcomes.',
            'Synthetic metrics can compare implementations but cannot establish real-farm accuracy or authorize model promotion.'],
        limitations=['Every target was generated by declared code; shared design choices can favor models that resemble the generator.',
            'No public weather, News or trade variable is used and no weather causal coefficient is asserted.',
            'Intervals are descriptive residual ranges, not calibrated probability statements.',
            'A future real-data evaluation needs farm/buyer sampling, availability audit, stockout censoring policy and frozen acceptance thresholds.'])
