"""Authoritative private-data contracts. Dates use Singapore civil dates; event timestamps are aware."""
from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
import hashlib, json
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

CROPS = ('caixin','pak_choi','kailan','bayam','kangkong','lettuce','kale','mustard_greens','malabar_spinach','sweet_potato_leaves','garlic_chives','sawtooth_coriander')
class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False, validate_default=True)
class Recipe(Strict):
    id: str
    crop_id: Literal['caixin','pak_choi','kailan','lettuce']
    system: Literal['sheltered_hydroponic'] = 'sheltered_hydroponic'
    nursery_days: int = Field(ge=0, le=60)
    grow_days: int = Field(ge=1, le=120)
    sanitation_days: int = Field(default=2, ge=0, le=14)
    density_per_m2: int = Field(ge=1, le=100)
    marketable_kg_per_m2: Decimal = Field(gt=0, le=30)
    cost_sgd_per_m2: Decimal = Field(ge=0, le=100)
    sow_labour_hours_per_m2: Decimal = Field(ge=0, le=10)
    harvest_labour_hours_per_kg: Decimal = Field(ge=0, le=10)
    shelf_life_days: int = Field(ge=1, le=14)
    validation_status: Literal['demo_only'] = 'demo_only'
    origin: Literal['synthetic'] = 'synthetic'
    @property
    def cycle_days(self): return self.nursery_days + self.grow_days
class Bed(Strict):
    id: str
    name: str
    area_m2: Decimal = Field(gt=0, le=1000)
    system: Literal['sheltered_hydroponic'] = 'sheltered_hydroponic'
class Batch(Strict):
    id: str
    bed_id: str
    recipe_id: str
    sow_date: date
    transplant_date: date
    harvest_date: date
    expected_marketable_kg: Decimal = Field(ge=0, le=10000)
    executed: Literal[True] = True
    origin: Literal['synthetic'] = 'synthetic'
    @model_validator(mode='after')
    def dates(self):
        if not self.sow_date <= self.transplant_date < self.harvest_date: raise ValueError('invalid batch stage ordering')
        return self
class Order(Strict):
    id: str
    crop_id: Literal['caixin','pak_choi','kailan','lettuce']
    booked_at: datetime
    due_date: date
    quantity_kg: Decimal = Field(ge=0, le=100000)
    price_sgd_per_kg: Decimal = Field(ge=0, le=1000)
    cancelled_kg: Decimal = Field(default=0, ge=0)
    origin: Literal['synthetic'] = 'synthetic'
    @model_validator(mode='after')
    def valid(self):
        if self.booked_at.tzinfo is None: raise ValueError('booked_at must be timezone-aware')
        if self.cancelled_kg > self.quantity_kg: raise ValueError('cancelled exceeds ordered')
        return self
class History(Strict):
    crop_id: Literal['caixin','pak_choi','kailan','lettuce']
    week: date
    available_at: datetime
    ordered_kg: Decimal = Field(ge=0)
    origin: Literal['synthetic'] = 'synthetic'
    @model_validator(mode='after')
    def aware(self):
        if self.available_at.tzinfo is None: raise ValueError('available_at must be aware')
        return self
class Resources(Strict):
    nursery_sites: int = Field(ge=0, le=1000000)
    labour_hours_per_week: Decimal = Field(ge=0, le=100000)
    cash_sgd: Decimal = Field(ge=0, le=10000000)
class InventoryLot(Strict):
    id: str
    crop_id: Literal['caixin','pak_choi','kailan','lettuce']
    quantity_kg: Decimal = Field(ge=0, le=100000)
    harvested_date: date
    expires_date: date
    origin: Literal['synthetic'] = 'synthetic'
    @model_validator(mode='after')
    def dates(self):
        if self.expires_date < self.harvested_date: raise ValueError('lot expiry before harvest')
        return self
class Farm(Strict):
    schema_version: Literal['1.0'] = '1.0'
    id: Literal['demo-farm'] = 'demo-farm'
    name: str = Field(max_length=100)
    location: str = Field(max_length=100)
    timezone: Literal['Asia/Singapore'] = 'Asia/Singapore'
    data_mode: Literal['synthetic_demo'] = 'synthetic_demo'
    cutoff: datetime
    horizon_days: int = Field(default=56, ge=7, le=84)
    version: int = Field(default=1, ge=1)
    recipes: list[Recipe] = Field(min_length=1, max_length=10)
    beds: list[Bed] = Field(min_length=1, max_length=40)
    batches: list[Batch] = Field(max_length=40)
    orders: list[Order] = Field(max_length=1000)
    history: list[History] = Field(max_length=1000)
    inventory: list[InventoryLot] = Field(default_factory=list, max_length=100)
    resources: Resources
    fixture_seed: int = 20260908
    @property
    def planning_date(self):
        from zoneinfo import ZoneInfo
        return self.cutoff.astimezone(ZoneInfo(self.timezone)).date()
    @model_validator(mode='after')
    def integrity(self):
        if self.cutoff.tzinfo is None: raise ValueError('cutoff must be timezone aware')
        for name in ('recipes','beds','batches','orders','inventory'):
            ids=[x.id for x in getattr(self,name)]
            if len(ids)!=len(set(ids)): raise ValueError(f'duplicate {name} IDs')
        recipes={r.id:r for r in self.recipes}; beds={b.id:b for b in self.beds}
        crops={r.crop_id for r in self.recipes}
        if any(o.crop_id not in crops for o in self.orders):raise ValueError('order crop has no approved development recipe')
        occupied=set()
        for b in self.batches:
            if b.bed_id not in beds or b.recipe_id not in recipes: raise ValueError('unknown batch dependency')
            if b.bed_id in occupied: raise ValueError('overlapping existing batches')
            occupied.add(b.bed_id)
            r=recipes[b.recipe_id]
            if (b.transplant_date-b.sow_date).days < r.nursery_days or (b.harvest_date-b.transplant_date).days < r.grow_days: raise ValueError('biological lead time violation')
            if r.system != beds[b.bed_id].system: raise ValueError('incompatible system')
        if any(o.booked_at>self.cutoff for o in self.orders): raise ValueError('order unavailable at cutoff')
        return self

def content_hash(value):
    if isinstance(value,BaseModel): value=value.model_dump(mode='json')
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
