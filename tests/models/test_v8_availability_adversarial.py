from datetime import datetime, timezone

from packages.fixtures import synthetic_demand_benchmark
from packages.models.evaluation import _rolling_predictions, _tune_alpha


def test_late_outcomes_cannot_enter_history_or_seasonal_reference():
    data=synthetic_demand_benchmark('evaluation')
    selected=data.records[0]
    # Retain one series so the assertion is about a specific delayed observation.
    data.records=[r for r in data.records if r.farm_id==selected.farm_id and r.crop_id==selected.crop_id]
    weeks=sorted({r.due_week for r in data.records})
    delayed=weeks[10]
    for r in data.records:
        if r.due_week==delayed:
            r.outcome_available_at=datetime(2030,1,1,tzinfo=timezone.utc)
    before,checks=_rolling_predictions(data,'farm',.35)
    for r in data.records:
        if r.due_week==delayed:r.gross_ordered_kg=9999
    after,changed_checks=_rolling_predictions(data,'farm',.35)
    # Changing a never-available outcome must not change any forecast, including
    # the calendar-matched seasonal prediction thirteen weeks later.
    assert [r['prediction'] for r in before]==[r['prediction'] for r in after]
    assert checks['unavailable_history_weeks_excluded']>0
    assert checks['unavailable_seasonal_fallbacks']>0
    assert checks['leakage_violations']==changed_checks['leakage_violations']==0


def test_training_tuner_reports_excluded_late_dependencies():
    data=synthetic_demand_benchmark('training')
    selected=data.records[0]
    data.records=[r for r in data.records if r.farm_id==selected.farm_id and r.crop_id==selected.crop_id]
    for r in data.records[:3]:r.outcome_available_at=datetime(2030,1,1,tzinfo=timezone.utc)
    result=_tune_alpha(data)
    assert result['unavailable_history_weeks_excluded']>0
    assert result['evaluation_partition_used_for_selection'] is False
