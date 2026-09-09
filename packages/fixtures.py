"""Deterministic fictional farm: coefficients are engineering fixtures, never agronomic evidence."""
from datetime import datetime,timedelta,timezone
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field
from packages.contracts import Farm

GENERATOR_VERSION='synthetic-farm-v1'

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

if __name__=='__main__':
    from pathlib import Path
    p=Path('data/fixtures/synthetic_farm.json'); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(synthetic_farm().model_dump_json(indent=2)+'\n')
    Path('packages/contracts.schema.json').write_text(__import__('json').dumps(Farm.model_json_schema(),indent=2)+'\n')
