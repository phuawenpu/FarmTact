from datetime import date, timedelta
from decimal import Decimal

import pytest

from packages.contracts import Farm, InventoryLot
from packages.fixtures import synthetic_farm
from packages.planner.engine import (
    VERSION,
    _harvest_lot_id,
    _objective_terms,
    _solve,
    candidates,
    normalize_scenario_set,
    plan,
    simulate,
    validate_allocations,
)


def empty_one_bed_farm():
    farm = synthetic_farm()
    farm.batches = []
    farm.inventory = []
    farm.orders = []
    farm.history = []
    farm.beds = farm.beds[:1]
    return farm


def relative_cycle(allocation, planning_date):
    return (
        allocation["bed_id"],
        allocation["crop_id"],
        allocation["recipe_id"],
        (date.fromisoformat(allocation["sow_date"]) - planning_date).days,
        (date.fromisoformat(allocation["transplant_date"]) - planning_date).days,
        (date.fromisoformat(allocation["harvest_date"]) - planning_date).days,
    )


def test_candidate_identity_uses_absolute_cycle_dates_across_replans():
    original = empty_one_bed_farm()
    shifted = original.model_copy(deep=True)
    shifted.cutoff += timedelta(days=14)

    first = candidates(original)
    later = candidates(shifted)
    first_by_relative_cycle = {relative_cycle(row, original.planning_date): row for row in first}
    later_by_relative_cycle = {relative_cycle(row, shifted.planning_date): row for row in later}
    shared_cycles = set(first_by_relative_cycle) & set(later_by_relative_cycle)

    assert VERSION == "daily-bed-cpsat-v3"
    assert candidates(original) == first
    assert shared_cycles
    assert all(
        first_by_relative_cycle[key]["id"] != later_by_relative_cycle[key]["id"]
        for key in shared_cycles
    )
    assert all(len(row["id"]) == 43 for row in first + later)


def test_harvest_lot_identity_avoids_opening_collision_and_keeps_origin():
    farm = empty_one_bed_farm()
    allocation = next(row for row in candidates(farm) if row["crop_id"] == "caixin")
    colliding_id = _harvest_lot_id(allocation, ())
    template = synthetic_farm().inventory[0]
    farm.inventory = [
        template.model_copy(
            update={
                "id": colliding_id,
                "quantity_kg": Decimal("1"),
                "harvested_date": farm.planning_date,
                "expires_date": farm.planning_date + timedelta(days=80),
            }
        )
    ]
    delivered_kg = Decimal(str(allocation["expected_kg"])) / 2
    demand = [
        {
            "crop_id": "caixin",
            "week": 0,
            "date": allocation["harvest_date"],
            "confirmed_kg": 0,
            "residual_kg": delivered_kg,
            "price_sgd_per_kg": 10,
            "price_status": "forecast_price",
        }
    ]

    replay = simulate(
        Farm.model_validate(farm.model_dump(mode="json")),
        [allocation],
        demand,
        {"id": "central", "yield_factor": 1, "demand_factor": 1, "weight": 1},
    )
    harvest_index = (date.fromisoformat(allocation["harvest_date"]) - farm.planning_date).days
    closing_lots = replay["inventory_snapshots"][harvest_index]["closing_lots"]
    generated = replay["harvest_lot_origins"][0]

    assert generated["lot_id"] != colliding_id
    assert generated["source_allocation_id"] == allocation["id"]
    assert len(generated["lot_id"]) == 40
    assert len({lot["id"] for lot in closing_lots}) == len(closing_lots)
    assert [InventoryLot.model_validate(lot) for lot in closing_lots]
    delivered = next(row for row in replay["order_allocations"] if row["delivered_kg"])
    assert delivered["lot_allocations"][0]["lot_id"] == generated["lot_id"]
    assert delivered["lot_allocations"][0]["source_allocation_id"] == allocation["id"]
    assert delivered["lot_allocations"][0]["quantity_kg"] == float(delivered_kg)


def test_identity_changes_preserve_optimizer_replay_objective():
    farm = empty_one_bed_farm()
    candidate = next(row for row in candidates(farm) if row["crop_id"] == "caixin")
    demand = [
        {
            "crop_id": "caixin",
            "week": 4,
            "date": candidate["harvest_date"],
            "confirmed_kg": 0,
            "residual_kg": candidate["expected_kg"],
            "price_sgd_per_kg": 10,
            "price_status": "forecast_price",
        }
    ]
    scenarios = normalize_scenario_set(
        [{"id": "only", "yield_factor": 1, "demand_factor": 1, "weight": 1}]
    )

    chosen, metadata = _solve(farm, [candidate], [], demand, scenarios, "Balanced", 1)
    replay = simulate(farm, chosen, demand, scenarios[0])
    terms = _objective_terms(farm, chosen, replay, "Balanced")

    assert metadata["status"] == "OPTIMAL"
    assert metadata["objective"] / metadata["objective_scale"]["solver_units_per_sgd"] == pytest.approx(
        terms["policy_utility_sgd_equivalent"]
    )


def test_historical_candidate_exclusions_do_not_remove_current_locks():
    farm = empty_one_bed_farm()
    historical = next(row for row in candidates(farm) if row["crop_id"] == "caixin")

    excluded = plan(farm, time_limit=0, excluded_candidate_ids=[historical["id"]])
    assert excluded["excluded_candidate_ids"] == [historical["id"]]
    assert all(
        historical["id"] not in {allocation["id"] for allocation in strategy["allocations"]}
        for strategy in excluded["strategies"]
    )

    historical["executed"] = True
    locked = plan(
        farm,
        time_limit=0,
        locked_allocations=[historical],
        excluded_candidate_ids=[historical["id"]],
    )
    assert all(
        next(allocation for allocation in strategy["allocations"] if allocation["id"] == historical["id"])
        == historical
        for strategy in locked["strategies"]
    )
    with pytest.raises(ValueError, match="collection"):
        plan(farm, time_limit=0, excluded_candidate_ids=historical["id"])
    with pytest.raises(ValueError, match="at most 10000"):
        plan(farm, time_limit=0, excluded_candidate_ids=(str(index) for index in range(10001)))


def test_max_declared_yield_reserves_harvest_labour_and_cash():
    farm = empty_one_bed_farm()
    candidate = next(row for row in candidates(farm) if row["crop_id"] == "caixin")
    demand = [
        {
            "crop_id": "caixin",
            "week": 4,
            "date": candidate["harvest_date"],
            "confirmed_kg": 0,
            "residual_kg": 88,
            "price_sgd_per_kg": 20,
            "price_status": "forecast_price",
        }
    ]
    default = normalize_scenario_set(
        [{"id": "default", "yield_factor": 1.1, "demand_factor": 1, "weight": 1}]
    )
    high = normalize_scenario_set(
        [{"id": "high", "yield_factor": 2, "demand_factor": 1, "weight": 1}]
    )

    labour_limited = farm.model_copy(deep=True)
    labour_limited.resources.labour_hours_per_week = Decimal("4")
    default_choice, _ = _solve(labour_limited, [candidate], [], demand, default, "Balanced", 1)
    high_choice, _ = _solve(labour_limited, [candidate], [], demand, high, "Balanced", 1)
    assert [row["id"] for row in default_choice] == [candidate["id"]]
    assert high_choice == []
    assert "LABOUR_CAPACITY" in {
        row["constraint_code"]
        for row in validate_allocations(labour_limited, [candidate], scenario_set=high)
    }

    cash_limited = farm.model_copy(deep=True)
    cash_limited.resources.labour_hours_per_week = Decimal("100")
    cash_limited.resources.cash_sgd = Decimal("160")
    default_choice, _ = _solve(cash_limited, [candidate], [], demand, default, "Balanced", 1)
    high_choice, _ = _solve(cash_limited, [candidate], [], demand, high, "Balanced", 1)
    assert [row["id"] for row in default_choice] == [candidate["id"]]
    assert high_choice == []
