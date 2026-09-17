"""Small deterministic farms used only by the recorded beginner lessons.

These fixtures are synthetic teaching inputs, not agronomic recommendations.
They deliberately remain small enough that every choice can be replayed through
the production planner and simulation engine during a browser journey.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Literal

from packages.contracts import Farm
from packages.fixtures import synthetic_farm


FIXTURE_VERSION = "beginner-teaching-farm-v1"
PLANNING_DAY = date(2026, 1, 5)
MAINTENANCE_BED_ID = "bed-03"
MAINTENANCE_START = date(2026, 1, 18)
MAINTENANCE_END = date(2026, 1, 31)


def beginner_farm(lesson_id: Literal["first_delivery", "two_orders"] = "first_delivery") -> Farm:
    """Return one isolated four-bed lesson snapshot.

    ``first_delivery`` has one recipe, one in-progress batch and one order. The
    confirmed order makes Lean and Resilient materially different while remaining
    recoverable after the dated B3 maintenance window.

    ``two_orders`` adds a second recipe and competing confirmed order without
    changing the four-bed capacity, forming the bounded follow-on challenge.
    """
    # Reuse the project's approved synthetic recipes exactly. The teaching
    # fixture authors capacity and demand, never a new crop-growth claim.
    approved={recipe.crop_id:recipe.model_dump(mode="json") for recipe in synthetic_farm().recipes}
    recipes = [approved["lettuce"]]
    orders = [
        {
            "id": "order-first-delivery",
            "crop_id": "lettuce",
            "booked_at": datetime(2026, 1, 4, tzinfo=timezone.utc),
            "due_date": PLANNING_DAY + timedelta(days=49),
            "quantity_kg": "18" if lesson_id == "two_orders" else "25",
            "price_sgd_per_kg": "8",
        }
    ]
    if lesson_id == "two_orders":
        recipes.append(approved["pak_choi"])
        orders.append(
            {
                "id": "order-second-delivery",
                "crop_id": "pak_choi",
                "booked_at": datetime(2026, 1, 4, tzinfo=timezone.utc),
                "due_date": PLANNING_DAY + timedelta(days=49),
                "quantity_kg": "7",
                "price_sgd_per_kg": "7",
            }
        )
    return Farm.model_validate(
        {
            "name": "Four-bed teaching farm",
            "location": "Synthetic classroom, Singapore",
            "cutoff": datetime(2026, 1, 5, tzinfo=timezone.utc),
            "horizon_days": 56,
            "fixture_seed": 20261401 if lesson_id == "first_delivery" else 20261402,
            "recipes": recipes,
            "beds": [
                {"id": "bed-01", "name": "A1", "area_m2": "3"},
                {"id": "bed-02", "name": "A2", "area_m2": "3"},
                {"id": "bed-03", "name": "B3", "area_m2": "5"},
                {"id": "bed-04", "name": "B4", "area_m2": "5"},
            ],
            "batches": [
                {
                    "id": "existing-lettuce",
                    "bed_id": "bed-01",
                    "recipe_id": "lettuce-demo-v1",
                    "sow_date": PLANNING_DAY - timedelta(days=17),
                    "transplant_date": PLANNING_DAY - timedelta(days=7),
                    "harvest_date": PLANNING_DAY + timedelta(days=18),
                    "expected_marketable_kg": "6.9",
                    "executed": True,
                }
            ],
            "orders": orders,
            "history": [],
            "resources": {
                "nursery_sites": 1000,
                "labour_hours_per_week": "12",
                "cash_sgd": "400" if lesson_id == "two_orders" else "300",
            },
        }
    )


def maintenance_assumptions() -> dict:
    """Return the server-authored B3 reservation consumed by the real planner."""
    return {
        "reservations": [
            {
                "bed_id": MAINTENANCE_BED_ID,
                "start_date": str(MAINTENANCE_START),
                "end_date": str(MAINTENANCE_END),
            }
        ]
    }
