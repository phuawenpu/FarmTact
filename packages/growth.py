"""Canonical schedule state, deliberately not a physiological biomass model."""
from datetime import date, timedelta

VERSION = 'schedule-state-v2'


def crop_state(allocation, recipe, on_date, *, harvested=False, projection=False):
    """Return civil-date stages; executed harvest always requires a recorded event.

    Projected stages assume scheduled tasks execute. Snapshot stages never infer
    a past harvest actually happened. Progress is elapsed schedule time, not mass.
    Beds remain reserved through harvest + sanitation_days, inclusive.
    """
    today = date.fromisoformat(str(on_date))
    sow = date.fromisoformat(str(allocation['sow_date']))
    transplant = date.fromisoformat(str(allocation['transplant_date']))
    harvest = date.fromisoformat(str(allocation['harvest_date']))
    sanitation_days = recipe.sanitation_days if hasattr(recipe, 'sanitation_days') else recipe['sanitation_days']
    end = harvest + timedelta(days=sanitation_days)
    if today < sow:
        stage = 'empty'
    elif harvested or (projection and today > harvest):
        stage = 'harvested' if today == harvest else ('sanitation' if today <= end else 'empty')
    elif today >= harvest:
        stage = 'ready'
    elif today < transplant:
        stage = 'nursery'
    else:
        stage = 'growing'
    progress = max(0, min(1, (today - sow).days / max(1, (harvest - sow).days)))
    return dict(stage=stage, progress=round(progress, 3), progress_basis='elapsed_schedule_fraction',
                growth_model_version=VERSION, physiological_biomass_model=False,
                state_basis='projected_tasks' if projection else ('recorded_synthetic_tasks' if harvested else 'snapshot_schedule'),
                sanitation_end_date=str(end), next_available_date=str(end + timedelta(days=1)))
