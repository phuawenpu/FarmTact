from datetime import datetime,timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from packages.contracts import content_hash
from packages.fixtures import GENERATOR_VERSION,GeneratorSettings,synthetic_farm
from packages.models import ForecastSettings,forecast
from packages.planner import plan


def test_default_generator_is_byte_for_byte_compatible():
    original=synthetic_farm()
    explicit=synthetic_farm(settings=GeneratorSettings())
    assert GENERATOR_VERSION
    assert original.model_dump_json()==explicit.model_dump_json()
    assert content_hash(original)==content_hash(explicit)
    assert [h.ordered_kg for h in original.history[:4]]==[Decimal('27'),Decimal('29'),Decimal('31'),Decimal('33')]


def test_generator_formula_and_cutoff_are_deterministic():
    cutoff=datetime(2026,10,1,3,tzinfo=timezone.utc)
    settings=GeneratorSettings(history_multiplier=.8,history_trend=.2,pattern_amplitude=1.5,orders_multiplier=1.2,price_multiplier=.5)
    farm=synthetic_farm(cutoff=cutoff,settings=settings)
    assert farm.cutoff==cutoff
    for ci in range(4):
        rows=farm.history[ci*12:(ci+1)*12]
        for w,row in enumerate(rows):
            expected=(Decimal(27+ci*2)+Decimal(w%4)*Decimal(2)*Decimal('1.5'))*Decimal('.8')*(Decimal(1)+Decimal('.2')*Decimal(w)/Decimal(11))
            assert row.ordered_kg==expected
    assert farm.orders[0].quantity_kg==Decimal('26.4')
    assert farm.orders[0].price_sgd_per_kg==Decimal('3.0')
    assert content_hash(farm)==content_hash(synthetic_farm(cutoff=cutoff,settings=settings))


def test_generator_boundaries_are_accepted_and_controls_are_independent():
    GeneratorSettings(history_multiplier=.5,history_trend=-.3,pattern_amplitude=0,orders_multiplier=.5,price_multiplier=.5)
    GeneratorSettings(history_multiplier=1.5,history_trend=.3,pattern_amplitude=2,orders_multiplier=1.5,price_multiplier=1.5)
    baseline=synthetic_farm()
    orders_only=synthetic_farm(settings=GeneratorSettings(orders_multiplier=1.1))
    assert orders_only.history==baseline.history
    assert orders_only.orders[0].quantity_kg==baseline.orders[0].quantity_kg*Decimal('1.1')


@pytest.mark.parametrize('field,value',[
    ('history_multiplier',.49),('history_multiplier',1.51),('history_trend',-.31),('history_trend',.31),
    ('pattern_amplitude',-.01),('pattern_amplitude',2.01),('orders_multiplier',.49),
    ('orders_multiplier',1.51),('price_multiplier',.49),('price_multiplier',1.51),
])
def test_generator_settings_reject_out_of_range_values(field,value):
    with pytest.raises(ValidationError):
        GeneratorSettings(**{field:value})


@pytest.mark.parametrize('value',[float('nan'),float('inf'),float('-inf'),.049,.951,'0.35'])
def test_forecast_settings_are_strict_finite_and_bounded(value):
    with pytest.raises(ValidationError):
        ForecastSettings(alpha=value)


def test_forecast_boundaries_and_planner_use_identical_settings():
    farm=synthetic_farm()
    for alpha in (.05,.95):
        direct=forecast(farm,alpha=alpha)
        planned=plan(farm,alpha=alpha,time_limit=0)
        assert planned['forecast']==direct
        assert planned['forecast_settings']=={'alpha':alpha}
        assert planned['input_hash']==content_hash(farm)
        assert planned['numerical_input_hash']==direct['numerical_input_hash']
        assert all(s['forecast_settings']=={'alpha':alpha} for s in planned['strategies'])


def test_alpha_changes_numerical_hash_and_strategy_ids_but_not_farm_hash():
    farm=synthetic_farm()
    low=plan(farm,alpha=.2,time_limit=0)
    high=plan(farm,alpha=.8,time_limit=0)
    assert low['input_hash']==high['input_hash']==content_hash(farm)
    assert low['configuration_hash']!=high['configuration_hash']
    assert low['numerical_input_hash']!=high['numerical_input_hash']
    assert [s['id'] for s in low['strategies']]!=[s['id'] for s in high['strategies']]
    assert low['forecast']['demand']!=high['forecast']['demand']
