"""Point-in-time baselines, deliberately labelled demo_only for this synthetic cohort."""
from collections import defaultdict
from datetime import timedelta
from pydantic import BaseModel,ConfigDict,Field
from packages.contracts import Farm,content_hash

MODEL_VERSION='recipe-ewma-v1'
class ForecastSettings(BaseModel):
    """Validated numerical configuration for the demand baseline."""

    model_config=ConfigDict(extra='forbid',strict=True,allow_inf_nan=False,validate_default=True)
    alpha: float=Field(default=.35,ge=.05,le=.95)

def forecast(farm: Farm,alpha=.35):
    settings=ForecastSettings(alpha=alpha)
    cutoff=farm.cutoff; day=farm.planning_date; weeks=(farm.horizon_days+6)//7
    history=defaultdict(list)
    for row in sorted(farm.history,key=lambda x:x.week):
        if row.available_at<=cutoff and row.week<day: history[row.crop_id].append(float(row.ordered_kg))
    result=[]
    for recipe in farm.recipes:
        values=history[recipe.crop_id]
        ewma=values[0] if values else 0
        for v in values[1:]: ewma=settings.alpha*v+(1-settings.alpha)*ewma
        for week in range(weeks):
            lines=[o for o in farm.orders if o.crop_id==recipe.crop_id and (o.due_date-day).days//7==week and o.booked_at<=cutoff]
            booked=sum(float(o.quantity_kg-o.cancelled_kg) for o in lines)
            residual=max(0,ewma-booked) if values else 0
            by_date=defaultdict(list)
            for line in lines:by_date[line.due_date].append(line)
            end=day+timedelta(days=min(7*week+6,farm.horizon_days-1))
            by_date.setdefault(end,[])
            for due,orders in sorted(by_date.items()):
                confirmed=sum(float(o.quantity_kg-o.cancelled_kg) for o in orders)
                extra=residual if due==end else 0
                price=sum(float(o.quantity_kg-o.cancelled_kg)*float(o.price_sgd_per_kg) for o in orders)/confirmed if confirmed else (float(lines[0].price_sgd_per_kg) if lines else 0)
                result.append(dict(crop_id=recipe.crop_id,week=week,date=str(due),confirmed_kg=round(confirmed,3),residual_kg=round(extra,3),expected_kg=round(confirmed+extra,3),price_sgd_per_kg=round(price,4),history_periods=len(values)))
    input_hash=content_hash(farm)
    forecast_settings=settings.model_dump(mode='json')
    configuration_hash=content_hash(dict(model_version=MODEL_VERSION,forecast_settings=forecast_settings))
    numerical_input_hash=content_hash(dict(input_hash=input_hash,configuration_hash=configuration_hash))
    return dict(model_version=MODEL_VERSION,validation_status='demo_only',cutoff=cutoff.isoformat(),input_hash=input_hash,numerical_input_hash=numerical_input_hash,configuration_hash=configuration_hash,forecast_settings=forecast_settings,demand=result,harvest=[dict(batch_id=b.id,crop_id=next(r.crop_id for r in farm.recipes if r.id==b.recipe_id),harvest_date=str(b.harvest_date),marketable_kg=float(b.expected_marketable_kg),endpoint='fresh_marketable_kg',origin='synthetic') for b in farm.batches],uncertainty='Declared synthetic scenarios, not calibrated confidence intervals')

def scenarios(seed=20260908):
    # Shared shocks across beds preserve room-level correlation. No inferred probabilities.
    return [dict(id='low-yield-high-demand',yield_factor=.85,demand_factor=1.15,weight=1/3),dict(id='central',yield_factor=1,demand_factor=1,weight=1/3),dict(id='high-yield-low-demand',yield_factor=1.1,demand_factor=.9,weight=1/3)]
