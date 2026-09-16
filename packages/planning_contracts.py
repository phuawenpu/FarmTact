"""V11 guided planning inputs; assumptions never masquerade as observations."""
from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import Field, model_validator
from packages.contracts import Strict, Farm

Crop = Literal['caixin', 'pak_choi', 'kailan', 'lettuce']


class DatedCrop(Strict):
    crop_id: Crop
    start_date: date
    end_date: date

    @model_validator(mode='after')
    def ordered(self):
        if self.start_date > self.end_date:
            raise ValueError('Assumption dates must be ordered')
        return self


class FutureDemand(DatedCrop):
    percent: int = Field(default=100, ge=50, le=150, strict=True)


class SeasonalAssumption(DatedCrop):
    system: Literal['sheltered_hydroponic'] = 'sheltered_hydroponic'
    yield_percent: int = Field(default=100, ge=50, le=100, strict=True)
    delay_days: int = Field(default=0, ge=0, le=14, strict=True)
    reason: str = Field(min_length=1, max_length=400)
    provenance: Literal['synthetic_assumption'] = 'synthetic_assumption'


class OrderChange(Strict):
    operation: Literal['add', 'amend', 'cancel']
    order_id: str = Field(min_length=1, max_length=100)
    crop_id: Crop | None = None
    due_date: date | None = None
    quantity_kg: Decimal | None = Field(default=None, ge=0, le=100000)
    price_sgd_per_kg: Decimal | None = Field(default=None, ge=0, le=1000)

    @model_validator(mode='after')
    def fields_for_operation(self):
        values=(self.crop_id,self.due_date,self.quantity_kg,self.price_sgd_per_kg)
        if self.operation=='add' and any(v is None for v in values):
            raise ValueError('New orders require crop, date, quantity and price')
        if self.operation=='amend' and all(v is None for v in values):
            raise ValueError('Amendment requires a changed field')
        if self.operation=='cancel' and any(v is not None for v in values):
            raise ValueError('Cancellation names an order without changing its other fields')
        return self


class TentativeOrder(Strict):
    order_id: str = Field(min_length=1,max_length=100)
    crop_id: Crop
    due_date: date
    quantity_kg: Decimal = Field(ge=0,le=100000)
    price_sgd_per_kg: Decimal | None = Field(default=None,ge=0,le=1000)
    status: Literal['tentative'] = 'tentative'


class BedReservation(Strict):
    bed_id: str = Field(min_length=1,max_length=100)
    start_date: date
    end_date: date

class CapacityChange(Strict):
    nursery_sites: int | None = Field(default=None,ge=0,le=1000000,strict=True)
    labour_hours_per_week: Decimal | None = Field(default=None,ge=0,le=100000)
    cash_sgd: Decimal | None = Field(default=None,ge=0,le=10000000)



class PlanningAssumptions(Strict):
    tentative_orders: list[TentativeOrder] = Field(default_factory=list,max_length=32)
    reservations: list[BedReservation] = Field(default_factory=list,max_length=32)
    capacity: CapacityChange | None = None
    future_demand: list[FutureDemand] = Field(default_factory=list, max_length=16)
    seasonal: list[SeasonalAssumption] = Field(default_factory=list, max_length=16)
    order_changes: list[OrderChange] = Field(default_factory=list, max_length=32)

    @model_validator(mode='after')
    def no_ambiguous_overlap(self):
        for collection in (self.future_demand,self.seasonal):
            for i,left in enumerate(collection):
                for right in collection[i+1:]:
                    if left.crop_id==right.crop_id and left.start_date<=right.end_date and right.start_date<=left.end_date:
                        raise ValueError('Overlapping assumptions for one crop are ambiguous')
        ids=[change.order_id for change in self.order_changes]
        if len(ids)!=len(set(ids)):
            raise ValueError('Only one explicit change per order per input version')
        return self

    def check_farm(self, farm: Farm):
        from datetime import timedelta
        end=farm.planning_date+timedelta(days=farm.horizon_days-1)
        crops={r.crop_id for r in farm.recipes}
        for item in [*self.future_demand,*self.seasonal]:
            if item.crop_id not in crops or item.start_date<farm.planning_date or item.end_date>end:
                raise ValueError('Assumption must target a configured crop inside the remaining horizon')
        from packages.planner.engine import _reservation_windows
        _reservation_windows(farm,[r.model_dump(mode='json') for r in self.reservations])
        for tentative in self.tentative_orders:
            if not farm.planning_date<=tentative.due_date<=end:
                raise ValueError('Tentative order must be within the remaining horizon')
        for change in self.order_changes:
            if change.due_date and not farm.planning_date<=change.due_date<=end:
                raise ValueError('Changed order must be due inside the remaining horizon')
        return self


class CreatePlanningSession(Strict):
    workflow: bool = False
    name: str = Field(default='Farm production mission', min_length=1, max_length=100)


class PlanningRevision(Strict):
    revision: int = Field(ge=0, strict=True)


class PlanningDisruption(PlanningRevision):
    assumptions: PlanningAssumptions


class PlanningAdvance(PlanningRevision):
    days: Literal[1, 7] = 1
