"""Deterministic demand and lot-allocation helpers shared by planning and replay.

Quantities at the allocation boundary are integer grams.  Public planner results
convert them to kilograms only after all mass-balance calculations are complete.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal, ROUND_HALF_UP


def _grams(value) -> int:
    return int((Decimal(str(value)) * Decimal(1000)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _as_date(value) -> date:
    return date.fromisoformat(value) if isinstance(value, str) else value


def demand_line_sort_key(line: dict) -> tuple:
    """Service booked commitments before inferred residual demand.

    Existing order contracts have no buyer priority field.  Within the same
    crop/day/kind, known higher-price lines are served first and IDs break ties.
    This is a declared deterministic allocation policy, not an inferred buyer
    preference.
    """
    known_price = line.get("price_sgd_per_kg") is not None
    price = Decimal(str(line["price_sgd_per_kg"])) if known_price else Decimal("0")
    return (
        0 if line.get("demand_kind") == "booked" else 1,
        0 if known_price else 1,
        -price,
        str(line.get("demand_line_id", "")),
    )


def demand_lines(farm, demand: list[dict], scenario: dict | None = None) -> list[dict]:
    """Expand aggregate forecast rows into booked-order and residual lines.

    The existing Farm order schema supports order ID, date, crop, net quantity,
    and explicit price.  Buyer, grade and contractual priority are absent, so no
    such allocation claims are made.  Any aggregate confirmed remainder is kept
    as a traceable forecast line rather than silently discarded.
    """
    demand_factor = Decimal(str((scenario or {}).get("demand_factor", 1)))
    eligible = [order for order in farm.orders if order.booked_at <= farm.cutoff]
    orders_by_key = defaultdict(list)
    for order in eligible:
        orders_by_key[(order.crop_id, str(order.due_date))].append(order)

    result = []
    for row_index, row in enumerate(demand):
        crop_id = row["crop_id"]
        due = str(row["date"])
        confirmed_g = _grams(row.get("confirmed_kg", 0))
        represented_g = 0
        for order in sorted(orders_by_key[(crop_id, due)], key=lambda item: item.id):
            net_g = _grams(order.quantity_kg - order.cancelled_kg)
            if net_g <= 0:
                continue
            represented_g += net_g
            result.append(
                dict(
                    demand_line_id=f"order:{order.id}",
                    order_id=order.id,
                    demand_kind="booked",
                    crop_id=crop_id,
                    date=due,
                    base_quantity_kg=net_g / 1000,
                    requested_kg=net_g / 1000,
                    requested_g=net_g,
                    price_sgd_per_kg=float(order.price_sgd_per_kg),
                    price_status="order_contract_price",
                )
            )

        # Custom/imported forecast rows may not have corresponding Farm orders.
        # Preserve their confirmed mass with an aggregate ID for full accounting.
        remainder_g = max(0, confirmed_g - represented_g)
        if remainder_g:
            status = row.get("price_status") or (
                "forecast_price" if row.get("price_sgd_per_kg") is not None else "unavailable_no_booked_price"
            )
            value = None if status == "unavailable_no_booked_price" else row.get("price_sgd_per_kg")
            result.append(
                dict(
                    demand_line_id=f"forecast-confirmed:{crop_id}:{due}:{row_index}",
                    order_id=None,
                    demand_kind="booked",
                    crop_id=crop_id,
                    date=due,
                    base_quantity_kg=remainder_g / 1000,
                    requested_kg=remainder_g / 1000,
                    requested_g=remainder_g,
                    price_sgd_per_kg=None if value is None else float(value),
                    price_status=status,
                )
            )

        residual_g = _grams(Decimal(str(row.get("residual_kg", 0))) * demand_factor)
        if residual_g:
            status = row.get("price_status") or (
                "booked_price_proxy" if row.get("price_sgd_per_kg") not in (None, 0, 0.0) else "unavailable_no_booked_price"
            )
            value = None if status == "unavailable_no_booked_price" else row.get("price_sgd_per_kg")
            result.append(
                dict(
                    demand_line_id=f"residual:{crop_id}:{due}:{row_index}",
                    order_id=None,
                    demand_kind="residual",
                    crop_id=crop_id,
                    date=due,
                    base_quantity_kg=_grams(row.get("residual_kg", 0)) / 1000,
                    requested_kg=residual_g / 1000,
                    requested_g=residual_g,
                    price_sgd_per_kg=None if value is None else float(value),
                    price_status=status,
                )
            )

    return sorted(result, key=lambda line: (line["date"], line["crop_id"], demand_line_sort_key(line)))


def allocate_lots(lots: list[dict], lines: list[dict], service_date: date | str) -> list[dict]:
    """Allocate mutable integer-gram lots using deterministic FEFO/FIFO order.

    Earliest expiry is primary because opening inventory has explicit expiry.
    Harvest date and lot ID break ties.  For normal same-crop lots with a common
    shelf life this is also FIFO.  Expired lots must be removed before calling.
    """
    today = _as_date(service_date)
    results = []
    for line in sorted(lines, key=demand_line_sort_key):
        remaining_g = int(line["requested_g"])
        allocations = []
        eligible = sorted(
            (
                lot
                for lot in lots
                if lot["crop_id"] == line["crop_id"]
                and _as_date(lot["expires_date"]) >= today
                and int(lot["quantity_g"]) > 0
            ),
            key=lambda lot: (_as_date(lot["expires_date"]), _as_date(lot["harvested_date"]), str(lot["id"])),
        )
        for lot in eligible:
            if remaining_g <= 0:
                break
            take_g = min(remaining_g, int(lot["quantity_g"]))
            lot["quantity_g"] -= take_g
            remaining_g -= take_g
            allocations.append(
                dict(
                    lot_id=lot["id"],
                    quantity_g=take_g,
                    harvested_date=str(lot["harvested_date"]),
                    expires_date=str(lot["expires_date"]),
                )
            )
        delivered_g = int(line["requested_g"]) - remaining_g
        results.append(
            dict(
                **line,
                delivered_g=delivered_g,
                shortfall_g=remaining_g,
                lot_allocations=allocations,
            )
        )
    return results
