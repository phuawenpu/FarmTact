import copy
from datetime import datetime,timedelta,timezone
from decimal import Decimal
import pytest
from pydantic import ValidationError
from packages.contracts import Farm,content_hash
from packages.fixtures import synthetic_farm
from packages.models import forecast

def test_reproducible_fixture_and_manifest():
    a=synthetic_farm();b=synthetic_farm()
    assert content_hash(a)==content_hash(b)
    assert set(r.crop_id for r in a.recipes)=={'caixin','pak_choi','kailan','lettuce'}
    assert all(r.validation_status=='demo_only' for r in a.recipes)

@pytest.mark.parametrize('mutation',[lambda f:f['batches'][0].update(bed_id='other-tenant'),lambda f:f['orders'][0].update(crop_id='spinach'),lambda f:f.update(cutoff='2026-09-08T00:00:00'),lambda f:f['batches'][0].update(transplant_date=f['batches'][0]['harvest_date']),lambda f:f['recipes'][0].update(marketable_kg_per_m2='NaN'),lambda f:f['orders'][0].update(cancelled_kg='9999'),lambda f:f.update(data_mode='live_advisory'),lambda f:f['beds'][0].update(area_m2=0)])
def test_invalid_data_is_not_silently_normalized(mutation):
    f=synthetic_farm().model_dump(mode='json');mutation(f)
    with pytest.raises(ValidationError):Farm.model_validate(f)

def test_future_history_does_not_change_forecast():
    farm=synthetic_farm();first=forecast(farm)
    row=farm.history[0].model_copy(update={'available_at':farm.cutoff+timedelta(days=1),'ordered_kg':Decimal('99999')})
    farm.history.append(row)
    assert forecast(farm)['demand']==first['demand']

def test_bookings_are_not_added_twice():
    farm=synthetic_farm()
    for h in farm.history:h.ordered_kg=Decimal('1')
    for row in forecast(farm)['demand']:
        assert row['expected_kg']==row['confirmed_kg']
        assert row['residual_kg']==0
