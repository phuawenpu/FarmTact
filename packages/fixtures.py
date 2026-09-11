"""Deterministic fictional data: engineering fixtures, never agronomic evidence."""
from datetime import date,datetime,time,timedelta,timezone
from decimal import Decimal
import math
import random
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from packages.contracts import Farm,content_hash

GENERATOR_VERSION='synthetic-farm-v1'
DEMAND_TRAIN_GENERATOR_VERSION='synthetic-demand-train-v2'
DEMAND_EVALUATION_GENERATOR_VERSION='synthetic-demand-evaluation-v2'
CROP_CYCLE_TRAIN_GENERATOR_VERSION='synthetic-crop-cycle-train-v1'
CROP_CYCLE_EVALUATION_GENERATOR_VERSION='synthetic-crop-cycle-evaluation-v1'

class GeneratorSettings(BaseModel):
    """Bounded controls for deterministic Data Explorer fixture variants."""

    model_config=ConfigDict(extra='forbid',strict=True,allow_inf_nan=False,validate_default=True)
    history_multiplier: float=Field(default=1,ge=.5,le=1.5)
    history_trend: float=Field(default=0,ge=-.3,le=.3)
    pattern_amplitude: float=Field(default=1,ge=0,le=2)
    orders_multiplier: float=Field(default=1,ge=.5,le=1.5)
    price_multiplier: float=Field(default=1,ge=.5,le=1.5)

def _decimal(value: float) -> Decimal:
    return Decimal(str(value))

def synthetic_farm(cutoff=None,settings=None):
    settings=GeneratorSettings.model_validate(settings or GeneratorSettings())
    cutoff=cutoff or datetime(2026,9,8,0,tzinfo=timezone.utc)
    from zoneinfo import ZoneInfo
    day=cutoff.astimezone(ZoneInfo('Asia/Singapore')).date()
    recipes=[]
    for crop,nursery,grow,yield_kg,cost in [('caixin',7,21,'2.2','2.0'),('pak_choi',7,28,'2.6','2.5'),('kailan',10,32,'2.4','2.8'),('lettuce',10,25,'2.3','3.0')]:
        recipes.append(dict(id=f'{crop}-demo-v1',crop_id=crop,nursery_days=nursery,grow_days=grow,density_per_m2=16,marketable_kg_per_m2=yield_kg,cost_sgd_per_m2=cost,sow_labour_hours_per_m2='0.08',harvest_labour_hours_per_kg='0.07',shelf_life_days=4))
    beds=[dict(id=f'bed-{i+1:02}',name=f'{chr(65+i//4)}{i%4+1}',area_m2='20') for i in range(16)]
    batches=[]
    for i in range(8):
        r=recipes[i%4]; harvest=day+timedelta(days=(i//4)*14+6)
        batches.append(dict(id=f'batch-{i+1:02}',bed_id=beds[i]['id'],recipe_id=r['id'],sow_date=harvest-timedelta(days=r['nursery_days']+r['grow_days']),transplant_date=harvest-timedelta(days=r['grow_days']),harvest_date=harvest,expected_marketable_kg=str(float(r['marketable_kg_per_m2'])*20)))
    orders=[]; history=[]
    for ci,r in enumerate(recipes):
        for w in range(8):
            order_quantity=22+(ci%2)*4+(w%3)*2
            order_price=6+ci
            if settings.orders_multiplier!=1:
                order_quantity=_decimal(order_quantity)*_decimal(settings.orders_multiplier)
            if settings.price_multiplier!=1:
                order_price=_decimal(order_price)*_decimal(settings.price_multiplier)
            orders.append(dict(id=f'order-{ci}-{w}',crop_id=r['crop_id'],booked_at=cutoff-timedelta(days=7),due_date=day+timedelta(days=w*7+6),quantity_kg=str(order_quantity),price_sgd_per_kg=str(order_price)))
        for w in range(12):
            end=day-timedelta(days=7*(12-w))
            if (settings.history_multiplier,settings.history_trend,settings.pattern_amplitude)==(1,0,1):
                ordered_kg=str(27+ci*2+(w%4)*2)
            else:
                base=Decimal(27+ci*2)+Decimal(w%4)*Decimal(2)*_decimal(settings.pattern_amplitude)
                trend=Decimal(1)+_decimal(settings.history_trend)*Decimal(w)/Decimal(11)
                ordered_kg=str(base*_decimal(settings.history_multiplier)*trend)
            history.append(dict(crop_id=r['crop_id'],week=end,available_at=datetime.combine(end,datetime.min.time(),timezone.utc)+timedelta(days=1),ordered_kg=ordered_kg))
    return Farm.model_validate(dict(name='Little Plot Collective',location='Lim Chu Kang, Singapore',cutoff=cutoff,recipes=recipes,beds=beds,batches=batches,orders=orders,history=history,resources=dict(nursery_sites=2560,labour_hours_per_week='32',cash_sgd='2200'),inventory=[dict(id='opening-caixin',crop_id='caixin',quantity_kg='5',harvested_date=day-timedelta(days=1),expires_date=day+timedelta(days=2))]))


class SyntheticDemandOrder(BaseModel):
    """Order-level benchmark record with point-in-time availability fields."""

    model_config=ConfigDict(extra='forbid',strict=True,allow_inf_nan=False,validate_default=True)
    order_id: str
    partition: Literal['training','evaluation']
    farm_id: str
    buyer_id: str
    buyer_segment: Literal['wholesale','restaurant','retail']
    crop_id: Literal['caixin','pak_choi','kailan','lettuce']
    due_week: date
    booked_at: datetime
    gross_ordered_kg: float=Field(ge=0,le=10000)
    cancelled_kg: float=Field(ge=0,le=10000)
    cancellation_available_at: datetime|None=None
    outcome_available_at: datetime
    regime: Literal['stable','growth','compression']
    shock: Literal['none','demand_surge','demand_drop']
    origin: Literal['synthetic_benchmark']='synthetic_benchmark'

    @property
    def net_ordered_kg(self)->float:
        return round(self.gross_ordered_kg-self.cancelled_kg,3)

    @model_validator(mode='after')
    def validate_availability(self):
        timestamps=[self.booked_at,self.outcome_available_at]
        if self.cancellation_available_at is not None:
            timestamps.append(self.cancellation_available_at)
        if any(value.tzinfo is None for value in timestamps):
            raise ValueError('benchmark availability timestamps must be timezone-aware')
        if self.cancelled_kg>self.gross_ordered_kg:
            raise ValueError('cancelled demand exceeds gross demand')
        if self.cancellation_available_at is None and self.cancelled_kg:
            raise ValueError('cancelled demand requires an availability timestamp')
        if self.booked_at>=self.outcome_available_at:
            raise ValueError('outcome must become available after booking')
        return self


class SyntheticDemandBundle(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True,allow_inf_nan=False,validate_default=True)
    schema_version: Literal['1.0.0']='1.0.0'
    generator_version: str
    partition: Literal['training','evaluation']
    seed: int
    start_week: date
    week_count: int=Field(ge=16,le=260)
    generation_scope: str
    public_features_used: list[str]=Field(default_factory=list,max_length=0)
    records: list[SyntheticDemandOrder]

    @model_validator(mode='after')
    def validate_partition(self):
        if any(row.partition!=self.partition for row in self.records):
            raise ValueError('record partition does not match bundle partition')
        ids=[row.order_id for row in self.records]
        if len(ids)!=len(set(ids)):
            raise ValueError('duplicate synthetic demand order ID')
        return self


class CropCycleOutcome(BaseModel):
    """Whole-batch crop-cycle outcome with timing and measurement provenance."""

    model_config=ConfigDict(extra='forbid',strict=True,allow_inf_nan=False,validate_default=True)
    batch_id: str
    partition: Literal['training','evaluation']
    farm_id: str
    crop_id: Literal['caixin','pak_choi','kailan','lettuce']
    recipe_version: str
    planned_sow_date: date
    planned_harvest_date: date
    actual_sow_date: date
    actual_harvest_date: date
    area_m2: float=Field(gt=0,le=1000)
    recipe_marketable_kg_per_m2: float=Field(gt=0,le=30)
    observed_marketable_kg: float=Field(ge=0,le=10000)
    input_available_at: datetime
    outcome_available_at: datetime
    regime: Literal['stable','process_improvement','capacity_pressure']
    shock: Literal['none','operational_delay','quality_loss']
    endpoint: Literal['fresh_marketable_kg']='fresh_marketable_kg'
    measurement_method: Literal['synthetic_scale_record']='synthetic_scale_record'
    origin: Literal['synthetic_benchmark']='synthetic_benchmark'

    @property
    def observed_cycle_days(self)->int:
        return (self.actual_harvest_date-self.actual_sow_date).days

    @model_validator(mode='after')
    def validate_cycle(self):
        if self.planned_harvest_date<=self.planned_sow_date or self.actual_harvest_date<=self.actual_sow_date:
            raise ValueError('harvest must follow sowing')
        if self.input_available_at.tzinfo is None or self.outcome_available_at.tzinfo is None:
            raise ValueError('crop-cycle timestamps must be timezone-aware')
        if self.input_available_at.date()>self.actual_sow_date:
            raise ValueError('input features must be available by sowing')
        if self.outcome_available_at.date()<self.actual_harvest_date:
            raise ValueError('outcome cannot be available before harvest')
        return self


class CropCycleBundle(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True,allow_inf_nan=False,validate_default=True)
    schema_version: Literal['1.0.0']='1.0.0'
    generator_version: str
    partition: Literal['training','evaluation']
    seed: int
    generation_scope: str
    excluded_features: list[str]
    outcomes: list[CropCycleOutcome]

    @model_validator(mode='after')
    def validate_partition(self):
        if any(row.partition!=self.partition for row in self.outcomes):
            raise ValueError('outcome partition does not match bundle partition')
        ids=[row.batch_id for row in self.outcomes]
        if len(ids)!=len(set(ids)):
            raise ValueError('duplicate crop-cycle batch ID')
        return self


def _demand_profile(partition: Literal['training','evaluation']):
    if partition=='training':
        return DEMAND_TRAIN_GENERATOR_VERSION,731104,date(2023,1,2),104,6,'tr'
    return DEMAND_EVALUATION_GENERATOR_VERSION,982451,date(2025,1,6),64,4,'ev'


def synthetic_demand_benchmark(partition: Literal['training','evaluation'],seed: int|None=None)->SyntheticDemandBundle:
    """Generate distinct train/evaluation cohorts with regimes, shocks and cancellations.

    The two partitions use separate generator versions, default seeds, farm IDs,
    buyer IDs and non-overlapping dates.  Public weather, News and trade records
    are intentionally absent because no causal or predictive relationship has
    been established.
    """

    version,default_seed,start,weeks,farm_count,prefix=_demand_profile(partition)
    selected_seed=default_seed if seed is None else seed
    rng=random.Random(selected_seed)
    crops=('caixin','pak_choi','kailan','lettuce')
    segments=('wholesale','restaurant','retail')
    records=[]
    for farm_index in range(farm_count):
        farm_id=f'{prefix}-farm-{farm_index+1:02}'
        regime=('stable','growth','compression')[farm_index%3]
        farm_factor=.82+.09*farm_index+rng.uniform(-.025,.025)
        for week_index in range(weeks):
            due=start+timedelta(days=7*week_index)
            phase=(week_index%13)/13
            seasonal=1+.12*math.sin(2*math.pi*phase)
            progress=week_index/max(1,weeks-1)
            regime_factor=1 if regime=='stable' else (1+.24*progress if regime=='growth' else 1-.18*progress)
            shock='demand_surge' if weeks//3<=week_index<weeks//3+4 else ('demand_drop' if 2*weeks//3<=week_index<2*weeks//3+3 else 'none')
            shock_factor=1.32 if shock=='demand_surge' else (.72 if shock=='demand_drop' else 1)
            for crop_index,crop_id in enumerate(crops):
                crop_factor=1+.08*crop_index
                for buyer_index,segment in enumerate(segments):
                    buyer_id=f'{prefix}-buyer-{farm_index+1:02}-{buyer_index+1:02}'
                    buyer_factor=(1.18,.74,.92)[buyer_index]
                    noise=1+rng.uniform(-.12,.12)
                    gross=max(0,10.5*farm_factor*crop_factor*buyer_factor*seasonal*regime_factor*shock_factor*noise)
                    cancellation_rate=0
                    if rng.random()<(.16 if segment=='restaurant' else .09):
                        cancellation_rate=rng.uniform(.08,.42)
                    cancelled=gross*cancellation_rate
                    lead_days=rng.randint(2,18)
                    booked_at=datetime.combine(due-timedelta(days=lead_days),time(hour=3),timezone.utc)
                    cancellation_available_at=None
                    if cancelled:
                        cancellation_available_at=datetime.combine(due-timedelta(days=rng.randint(0,min(lead_days-1,4))),time(hour=4),timezone.utc)
                    records.append(SyntheticDemandOrder(
                        order_id=f'{prefix}-o-{farm_index:02}-{week_index:03}-{crop_index}-{buyer_index}',
                        partition=partition,farm_id=farm_id,buyer_id=buyer_id,buyer_segment=segment,crop_id=crop_id,
                        due_week=due,booked_at=booked_at,gross_ordered_kg=round(gross,3),
                        cancelled_kg=round(cancelled,3),cancellation_available_at=cancellation_available_at,
                        outcome_available_at=datetime.combine(due+timedelta(days=7),time(hour=2),timezone.utc),
                        regime=regime,shock=shock))
    return SyntheticDemandBundle(generator_version=version,partition=partition,seed=selected_seed,
        start_week=start,week_count=weeks,
        generation_scope='Synthetic order-level benchmark with distinct farms/buyers, 13-week seasonality, trend regimes, declared shocks, booking lead times and cancellations.',
        records=records)


def _cycle_profile(partition: Literal['training','evaluation']):
    if partition=='training':
        return CROP_CYCLE_TRAIN_GENERATOR_VERSION,445901,date(2023,2,1),6,24,'tr'
    return CROP_CYCLE_EVALUATION_GENERATOR_VERSION,771283,date(2025,2,1),4,16,'ev'


def synthetic_crop_cycle_benchmark(partition: Literal['training','evaluation'],seed: int|None=None)->CropCycleBundle:
    """Generate independent whole-batch outcomes without fabricated weather effects."""

    version,default_seed,start,farm_count,cycles,prefix=_cycle_profile(partition)
    selected_seed=default_seed if seed is None else seed
    rng=random.Random(selected_seed)
    recipes=(('caixin',28,2.2),('pak_choi',35,2.6),('kailan',42,2.4),('lettuce',35,2.3))
    outcomes=[]
    for farm_index in range(farm_count):
        farm_id=f'{prefix}-cycle-farm-{farm_index+1:02}'
        regime=('stable','process_improvement','capacity_pressure')[farm_index%3]
        farm_yield_factor=.91+.045*farm_index+rng.uniform(-.02,.02)
        for cycle_index in range(cycles):
            for crop_index,(crop_id,cycle_days,yield_per_m2) in enumerate(recipes):
                planned_sow=start+timedelta(days=10*cycle_index+crop_index)
                actual_sow=planned_sow+timedelta(days=1 if regime=='capacity_pressure' and cycle_index%5==0 else 0)
                shock='operational_delay' if cycle_index in {cycles//3,cycles//3+1} else ('quality_loss' if cycle_index==2*cycles//3 else 'none')
                regime_delay=-1 if regime=='process_improvement' and cycle_index>cycles//2 else (1 if regime=='capacity_pressure' else 0)
                shock_delay=3 if shock=='operational_delay' else 0
                actual_days=max(10,cycle_days+regime_delay+shock_delay+rng.choice((-1,0,0,0,1)))
                area=20.0
                yield_factor=farm_yield_factor*(1+.025*cycle_index/max(1,cycles-1) if regime=='process_improvement' else 1)
                if regime=='capacity_pressure':
                    yield_factor*=.96
                if shock=='quality_loss':
                    yield_factor*=.76
                yield_factor*=1+rng.uniform(-.075,.075)
                actual_harvest=actual_sow+timedelta(days=actual_days)
                observed=max(0,area*yield_per_m2*yield_factor)
                outcomes.append(CropCycleOutcome(
                    batch_id=f'{prefix}-b-{farm_index:02}-{cycle_index:03}-{crop_index}',partition=partition,
                    farm_id=farm_id,crop_id=crop_id,recipe_version=f'{crop_id}-demo-v1',
                    planned_sow_date=planned_sow,planned_harvest_date=planned_sow+timedelta(days=cycle_days),
                    actual_sow_date=actual_sow,actual_harvest_date=actual_harvest,area_m2=area,
                    recipe_marketable_kg_per_m2=yield_per_m2,observed_marketable_kg=round(observed,3),
                    input_available_at=datetime.combine(planned_sow-timedelta(days=1),time(hour=2),timezone.utc),
                    outcome_available_at=datetime.combine(actual_harvest+timedelta(days=1),time(hour=2),timezone.utc),
                    regime=regime,shock=shock))
    return CropCycleBundle(generator_version=version,partition=partition,seed=selected_seed,
        generation_scope='Synthetic independent whole-batch timing and fresh-marketable-mass observations with operational regimes and declared non-weather shocks.',
        excluded_features=['public_weather','news','trade','causal_weather_coefficients'],outcomes=outcomes)


def benchmark_manifest(bundle: SyntheticDemandBundle|CropCycleBundle)->dict:
    """Return a compact deterministic manifest without embedding benchmark records."""

    payload=bundle.model_dump(mode='json')
    rows=payload.pop('records',payload.pop('outcomes',[]))
    return {**payload,'row_count':len(rows),'content_sha256':content_hash(bundle)}

if __name__=='__main__':
    from pathlib import Path
    p=Path('data/fixtures/synthetic_farm.json'); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(synthetic_farm().model_dump_json(indent=2)+'\n')
    Path('packages/contracts.schema.json').write_text(__import__('json').dumps(Farm.model_json_schema(),indent=2)+'\n')
