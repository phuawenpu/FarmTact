"""Server-directed, replayable beginner planning lesson.

The journey is metadata on an ordinary guided planning session. All schedules,
inventory transitions and deliveries still come from the local planner and
simulation engine; this module only constrains the order in which a learner may
invoke those existing capabilities.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
import secrets

from fastapi import HTTPException, Request
from sqlalchemy import func, select, update

from packages.beginner_contracts import BeginnerActionRequest, CreateBeginnerJourney
from packages.beginner_fixture import (
    FIXTURE_VERSION,
    MAINTENANCE_BED_ID,
    MAINTENANCE_END,
    MAINTENANCE_START,
    beginner_farm,
    maintenance_assumptions,
)
from packages.contracts import Farm, content_hash
from services.api.planning_sessions import (
    JOBS,
    RECEIPTS,
    SESSIONS,
    activate_strategy,
    get_result,
    get_session,
    queue_initial_calculation,
    queue_recalculation,
    save_session,
)
from services.api.store import now


VERSION = "beginner-journey-v1"


def _journey(session: dict) -> dict:
    value=session.get("beginner_journey")
    if not isinstance(value,dict) or value.get("version")!=VERSION:
        raise HTTPException(404,"Beginner journey not found")
    return value


def _effective_stage(session: dict) -> str:
    stage=_journey(session)["stage"]
    if session.get("status")=="FAILED" and stage in ("CALCULATING","RECALCULATING"):
        return "FAILED"
    if stage=="CALCULATING" and session.get("status")=="COMPLETED" and session.get("result_id"):
        return "CHOOSE_PLAN"
    if stage=="RECALCULATING" and session.get("status")=="COMPLETED" and session.get("result_id"):
        return "CHOOSE_RECOVERY"
    return stage


def _status(session: dict) -> str:
    stage=_effective_stage(session)
    if stage in ("CALCULATING","RECALCULATING"):return stage
    if stage=="FAILED":return "FAILED"
    if stage=="COMPLETE":return "COMPLETE"
    return "ACTIVE"


def _metric_view(strategy: dict | None, total_area: float = 20) -> dict:
    if strategy is None:
        return {"planned_harvest_kg":None,"committed_demand_kg":None,"fulfilled_demand_kg":None,
                "waste_kg":None,"shortfall_kg":None,"land_utilization_pct":None,"cost_sgd":None,"margin_sgd":None}
    metric=(strategy or {}).get("metrics",{})
    planned_beds={row["bed_id"]:float(row.get("area_m2",0)) for row in strategy.get("allocations",[]) if not row.get("executed")}
    return {
        "planned_harvest_kg": float(metric.get("harvest_kg",0)),
        "committed_demand_kg": float(metric.get("booked_requested_kg",0)),
        "fulfilled_demand_kg": float(metric.get("booked_delivered_kg",0)),
        "waste_kg": float(metric.get("waste_kg",0)),
        "shortfall_kg": float(metric.get("booked_shortfall_kg",metric.get("shortfall_kg",0))),
        "land_utilization_pct": round(sum(planned_beds.values())/total_area*100,1) if total_area else 0.0,
        "cost_sgd": float(metric.get("cost_sgd",0)),
        "margin_sgd": float(metric.get("margin_sgd",0)),
    }


def _strategy_signature(strategy: dict, total_area: float) -> tuple:
    metric=_metric_view(strategy,total_area)
    placements=tuple(sorted((row["bed_id"],row["crop_id"],row["sow_date"],row["harvest_date"]) for row in strategy.get("allocations",[]) if not row.get("executed")))
    return tuple(metric.values()),placements


def _choices(session: dict, stage: str | None = None) -> list[dict]:
    stage=stage or _effective_stage(session)
    if stage not in ("CHOOSE_PLAN","CHOOSE_RECOVERY"):
        return []
    result=get_result(session["_store"],session["_tenant"],session.get("result_id"))
    total_area=float(sum(bed.area_m2 for bed in Farm.model_validate(session["farm"]).beds))
    feasible=[row for row in (result or {}).get("strategies",[]) if row.get("status")=="FEASIBLE" and not row.get("violations")]
    ordered=[]
    policies=("Balanced","Resilient","Lean") if _journey(session)["lesson_id"]=="two_orders" else ("Lean","Resilient","Balanced")
    for policy in policies:
        row=next((item for item in feasible if item.get("name")==policy),None)
        if row and _strategy_signature(row,total_area) not in {_strategy_signature(item,total_area) for item in ordered}:
            ordered.append(row)
        if len(ordered)==2:break
    baseline=(result or {}).get("retained_strategy") if stage=="CHOOSE_RECOVERY" else None
    output=[]
    if baseline:
        before=_metric_view(baseline,total_area)
        violations=baseline.get("violations",[])
        output.append({"id":f'retained:{baseline.get("id")}',"strategy_id":baseline.get("id"),
            "title":"Saved plan (conflicts)","tradeoff":"The saved placement is evaluated unchanged under the B3 maintenance constraint.",
            "metrics":before,"deltas":{key:0 for key in before},"eligible":False,
            "disabled_reason":("B3 maintenance conflicts with the saved placement." if violations else "A recalculated alternative is required for this lesson."),
            "result_id":session.get("result_id"),"result_hash":content_hash(result),
            "board_target_ids":sorted({allocation["bed_id"] for allocation in baseline.get("allocations",[]) if not allocation.get("executed")}),
            "allocations":[{key:allocation[key] for key in ("id","bed_id","crop_id","sow_date","transplant_date","harvest_date","expected_kg")}
                           for allocation in baseline.get("allocations",[])],"inference_triggered":False})
    for row in ordered:
        metric=_metric_view(row,total_area)
        delivered=float(metric["fulfilled_demand_kg"] or 0);committed=float(metric["committed_demand_kg"] or 0)
        shortfall=max(0,committed-delivered);space=float(metric["land_utilization_pct"] or 0)
        if shortfall:
            status_label=f"Feasible with {shortfall:g} kg shortfall"
            plain_tradeoff=f"Uses {space:g}% of the growing space and delivers {delivered:g} of {committed:g} kg, leaving a {shortfall:g} kg shortfall."
        else:
            status_label="Covers all confirmed demand"
            plain_tradeoff=f"Uses {space:g}% of the growing space and covers all {committed:g} kg of confirmed demand under the tested conditions."
        deltas={}
        if baseline:
            before=_metric_view(baseline,total_area)
            deltas={key:round(metric[key]-before[key],3) for key in metric if key!="land_utilization_pct"}
            deltas["land_utilization_pct"]=round(metric["land_utilization_pct"]-before["land_utilization_pct"],1)
        output.append({
            "id": row["id"],
            "strategy_id": row["id"],
            "title": f'{row["name"]} plan',
            "tradeoff":plain_tradeoff if stage=="CHOOSE_PLAN" else f"Moves future work around the recorded B3 maintenance window. {plain_tradeoff}",
            "status_label":status_label,
            "metrics": metric,
            "deltas": deltas,
            "eligible": True,
            "disabled_reason": None,
            "result_id": session.get("result_id"),
            "result_hash": content_hash(result),
            "board_target_ids": sorted({allocation["bed_id"] for allocation in row.get("allocations",[]) if not allocation.get("executed")}),
            "allocations": [{key:allocation[key] for key in ("id","bed_id","crop_id","sow_date","transplant_date","harvest_date","expected_kg")}
                            for allocation in row.get("allocations",[])],
            "inference_triggered": False,
        })
    return output


def _action(action_id: str, label: str, kind: str, *, eligible=True, reason=None, option=False) -> dict:
    return {"id":action_id,"label":label,"kind":kind,"eligible":eligible,
            "disabled_reason":reason,"requires_option":option,"inference_triggered":False}


def _next_action(session: dict, stage: str) -> dict | None:
    if stage=="START":return _action("calculate_choices","Calculate two plans","calculate")
    if stage=="CALCULATING":return _action("calculate_choices","Calculating plans","calculate",eligible=False,reason="The local planning job is still running.")
    if stage=="CHOOSE_PLAN":return _action("select_plan","Choose this plan","choose",option=True)
    if stage=="PLAN_SELECTED":return _action("advance","Advance to next checkpoint","advance")
    if stage=="MAINTENANCE_DUE":return _action("record_b3_maintenance","Record B3 maintenance","record")
    if stage=="RECALCULATING":return _action("record_b3_maintenance","Recalculating recovery plans","calculate",eligible=False,reason="The local planning job is still running.")
    if stage=="CHOOSE_RECOVERY":return _action("select_recovery","Choose recovery plan","choose",option=True)
    if stage=="GROWING":return _action("advance","Advance to next crop event","advance")
    if stage=="DELIVERY_DUE":return _action("record_delivery","Review recorded delivery","record")
    if stage=="COMPLETE":
        if _journey(session)["lesson_id"]=="first_delivery":return _action("next_challenge","Try two competing orders","replay")
        return _action("replay","Replay this challenge","replay")
    if stage=="FAILED":return _action("replay","Start a fresh attempt","replay")
    return None


def _cards(session: dict, stage: str, choices: list[dict]) -> list[dict]:
    journey=_journey(session)
    origin=Farm.model_validate(journey["origin_farm"])
    due=max(order.due_date for order in origin.orders)
    requirements=[f'{float(order.quantity_kg-order.cancelled_kg):g} kg of {order.crop_id.replace("_"," ")}'
                  for order in sorted(origin.orders,key=lambda row:row.id)]
    requirement=" and ".join(requirements)
    customer="customer" if len(origin.orders)==1 else "customers"
    verb="needs" if len(origin.orders)==1 else "need"
    provenance={"label":"SYNTHETIC TEACHING SIMULATION","source":FIXTURE_VERSION}
    next_action=_next_action(session,stage)
    if stage=="COMPLETE":
        metrics=_metrics(session["_store"],session["_tenant"],session)
        initial=journey.get("initial_choice") or {};recovery=journey.get("recovery_choice") or {}
        delivered=float(metrics.get("fulfilled_demand_kg") or 0);requested=float(metrics.get("committed_demand_kg") or 0)
        replay=_action("replay","Replay this lesson","replay")
        onward=next_action
        bed_names={bed.id:bed.name for bed in origin.beds}
        initial_beds=", ".join(bed_names.get(id,id) for id in initial.get("board_target_ids",[])) or "the original beds"
        recovery_beds=", ".join(bed_names.get(id,id) for id in recovery.get("board_target_ids",[])) or "the recalculated beds"
        return [{
            "id":"debrief-result","type":"result","title":f"Delivered {delivered:g} of {requested:g} kg",
            "summary":f'The recorded season finished with SGD {float(metrics.get("cost_sgd") or 0):.2f} in cost and {float(metrics.get("waste_kg") or 0):g} kg disposed.',
            "state":"completed","provenance":{"label":"RECORDED SIMULATION RESULT","source":"synthetic-execution-v1"},
            "entity":{"kind":"simulation","id":session.get("world_id")},"actions":[],"inference_triggered":False,
        },{
            "id":"debrief-change","type":"comparison","title":"What your decision changed",
            "summary":f'Your starting plan used {initial_beds}. After B3 maintenance, the calculated recovery moved future work to {recovery_beds}.',
            "state":"completed","provenance":{"label":"STORED PLAN COMPARISON","source":"guided-planning-v1"},
            "entity":{"kind":"planning_result","id":session.get("result_id")},"actions":[replay],"inference_triggered":False,
        },{
            "id":"debrief-next","type":"next_challenge","title":"Balance two customer orders" if journey["lesson_id"]=="first_delivery" else "Replay with a different policy",
            "summary":"Try the isolated follow-on farm with lettuce and pak choi competing for the same four beds." if journey["lesson_id"]=="first_delivery" else "Replay this challenge and choose the other calculated starting policy.",
            "state":"current","provenance":provenance,"entity":{"kind":"lesson","id":"two_orders" if journey["lesson_id"]=="first_delivery" else journey["lesson_id"]},
            "actions":[onward] if onward else [],"inference_triggered":False,
        }]
    cards=[{
        "id":"lesson-objective","type":"objective","title":f"Grow {requirement} for {due.strftime('%-d %b')}",
        "summary":f"Your {customer} {verb} {requirement} by {due.strftime('%-d %B')}. Compare two ways to grow it, then choose your plan.",
        "state":"active" if stage=="START" else "recorded","provenance":provenance,
        "entity":{"kind":"order","id":"order-first-delivery"},
        "actions":[next_action] if next_action and stage in ("START","PLAN_SELECTED","GROWING","DELIVERY_DUE","COMPLETE","FAILED") else [],
        "inference_triggered":False,
    }]
    if stage in ("PLAN_SELECTED","GROWING"):
        scene=_scene(session["_store"],session["_tenant"],session,stage);event=scene["event"]
        cards[0]["actions"]=[]
        cards.insert(0,{"id":f'crop-progress:{scene.get("clock_date") or "ready"}',"type":"crop_progress",
            "title":event["label"],"summary":event.get("summary") or f'The simulated farm is recorded through {event["date"]}.',
            "state":"active","provenance":{"label":"RECORDED SIMULATION CHECKPOINT","source":"synthetic-execution-v1"},
            "entity":{"kind":"simulation","id":session.get("world_id")},"actions":[next_action] if next_action else [],
            "inference_triggered":False})
    if choices:
        cards.append({
            "id":"plan-choice" if stage=="CHOOSE_PLAN" else "recovery-choice","type":"strategy",
            "title":"Choose a starting plan" if stage=="CHOOSE_PLAN" else "Choose the recalculated recovery",
            "summary":"Both options are feasible outputs from the frozen local planner.","state":"active",
            "provenance":{"label":"LOCAL CALCULATION","source":"guided-planning-v1"},
            "entity":{"kind":"planning_result","id":session.get("result_id")},
            "actions":[_next_action(session,stage)],"inference_triggered":False,
        })
    if stage in ("PLAN_SELECTED","MAINTENANCE_DUE","RECALCULATING","CHOOSE_RECOVERY","GROWING","DELIVERY_DUE","COMPLETE"):
        cards.append({
            "id":"b3-maintenance","type":"constraint","title":"B3 maintenance window",
            "summary":f"B3 is unavailable from {MAINTENANCE_START.isoformat()} through {MAINTENANCE_END.isoformat()}.",
            "state":"active" if stage in ("MAINTENANCE_DUE","RECALCULATING","CHOOSE_RECOVERY") else ("recorded" if journey.get("maintenance_recorded") else "upcoming"),
            "provenance":{"label":"RECORDED SIMULATION EVENT" if journey.get("maintenance_recorded") else "SCHEDULED TEACHING EVENT","source":FIXTURE_VERSION},
            "entity":{"kind":"grow_space","id":MAINTENANCE_BED_ID},
            "actions":[_next_action(session,stage)] if stage=="MAINTENANCE_DUE" else [],"inference_triggered":False,
        })
    return cards


def _simulation_events(store, tenant_id: str, world_id: str | None) -> list[dict]:
    if not world_id:return []
    from services.api.simulation import EVENTS
    with store.connection() as connection:
        rows=list(connection.execute(select(EVENTS.c.payload).where(EVENTS.c.tenant_id==tenant_id,EVENTS.c.world_id==world_id).order_by(EVENTS.c.sequence)).scalars())
    names={"world_created":"Simulation started","task_completed":"Farm task completed",
           "demand_serviced":"Customer demand serviced","day_closed":"Simulation day recorded",
           "future_replanned":"Future schedule replaced","maintenance_recorded":"B3 maintenance recorded"}
    output=[]
    for row in rows:
        kind=row["type"]
        if kind=="day_closed":
            summary="Inventory, cash and commitments were advanced from the frozen ledger."
        elif kind=="task_completed":
            summary=f'{row.get("task", "Farm task").replace("_"," ").title()} · {row.get("crop_id","")} · {row.get("bed_id","")}'.strip(" ·")
        elif kind=="demand_serviced":
            summary=f'{float(row.get("delivered_kg",0)):.1f} kg delivered for {row.get("order_id") or "recorded demand"}.'
        elif kind=="maintenance_recorded":
            summary=f'B3 unavailable {row.get("start_date")} to {row.get("end_date")}.'
        else:summary="Recorded by the deterministic local simulation."
        output.append({"id":f'{world_id}:{row["sequence"]}',"sequence":row["sequence"],"event_type":kind,
                       "occurred_on":row["date"],"title":names.get(kind,kind.replace("_"," ").title()),
                       "summary":summary,"source":row.get("engine_version","synthetic-execution-v1"),
                       "revision":row["sequence"]})
    return output


def _timeline(store, tenant_id: str, session: dict) -> list[dict]:
    audit=[]
    for index,row in enumerate(_journey(session).get("audit",[]),1):
        audit.append({"id":f'journey:{session["id"]}:{index}',"sequence":index,"event_type":row["type"],
                      "occurred_on":row.get("civil_date") or row["recorded_at"][:10],"title":row["title"],
                      "summary":row["summary"],"source":VERSION,"revision":row["revision"]})
    return audit+_simulation_events(store,tenant_id,session.get("world_id"))


def _selected_strategy(session: dict) -> dict | None:
    result=get_result(session["_store"],session["_tenant"],session.get("result_id"))
    return next((row for row in (result or {}).get("strategies",[]) if row["id"]==session.get("selected_strategy_id")),None)


def _metrics(store, tenant_id: str, session: dict) -> dict:
    from services.api.simulation import get_world
    farm=Farm.model_validate(session["farm"])
    strategy=_selected_strategy(session)
    view=_metric_view(strategy,float(sum(bed.area_m2 for bed in farm.beds)))
    world=get_world(store,tenant_id,session.get("world_id")) if session.get("world_id") else None
    origin=Farm.model_validate(_journey(session)["origin_farm"])
    view.update({
        "clock_date":world.get("clock_date") if world else None,
        "horizon_end":world.get("end_date") if world else str(farm.planning_date+timedelta(days=farm.horizon_days-1)),
        "committed_demand_kg":float(sum(order.quantity_kg-order.cancelled_kg for order in origin.orders)),
        "fulfilled_demand_kg":float(world["totals"]["delivered_kg"]) if world else 0.0,
        "waste_kg":float(world["totals"]["disposed_kg"]) if world else 0.0,
        "cost_sgd":float(world["cost_sgd"]) if world else view.get("cost_sgd"),
        "cash_balance":float(world["cash_sgd"]) if world else float(farm.resources.cash_sgd),
    })
    return view


def _scene(store, tenant_id: str, session: dict, stage: str) -> dict:
    """Project the exact board scene so clients never infer crop state."""
    from packages.growth import crop_state
    from packages.planner.engine import allocations_existing
    from services.api.simulation import get_world, public_world
    farm=Farm.model_validate(session["farm"])
    recipe_by_id={recipe.id:recipe for recipe in farm.recipes}
    crop_labels={"lettuce":"Lettuce","pak_choi":"Pak choi","caixin":"Caixin","kailan":"Kailan"}
    world=get_world(store,tenant_id,session.get("world_id")) if session.get("world_id") else None
    if world:
        raw_beds=public_world(world)["beds"]
    else:
        day=str(farm.planning_date);allocations=allocations_existing(farm);raw_beds=[]
        for bed in farm.beds:
            states=[(row,crop_state(row,recipe_by_id[row["recipe_id"]],day)) for row in allocations if row["bed_id"]==bed.id]
            active=next(((row,state) for row,state in states if state["stage"]!="empty"),None)
            raw={"id":bed.id,"name":bed.name,"stage":"empty","progress":0}
            if active:
                row,state=active;raw.update(state,crop_id=row["crop_id"],allocation_id=row["id"])
            raw_beds.append(raw)
    maintenance_active=stage in ("MAINTENANCE_DUE","RECALCULATING","CHOOSE_RECOVERY")
    beds=[]
    for row in raw_beds:
        crop_id=row.get("crop_id");crop_stage=row.get("stage","empty")
        is_target=row["id"]==MAINTENANCE_BED_ID
        beds.append({"id":row["id"],"name":row["name"],"crop_label":crop_labels.get(crop_id,crop_id.replace("_"," ").title() if crop_id else None),
                     "crop_stage":crop_stage,"stage":crop_stage,"progress":float(row.get("progress",0)),
                     "accent":"warning" if is_target and maintenance_active else ("crop" if crop_stage!="empty" else "neutral"),
                     "status_label":"Maintenance constraint" if is_target and maintenance_active else crop_stage.replace("_"," ").title(),
                     "allocation_id":row.get("allocation_id")})
    if stage in ("MAINTENANCE_DUE","RECALCULATING","CHOOSE_RECOVERY"):
        event={"tone":"warning","label":"B3 maintenance","date":str(MAINTENANCE_START),"weather":"Simulated farm",
               "summary":f"B3 is unavailable from {MAINTENANCE_START.strftime('%-d %b')} through {MAINTENANCE_END.strftime('%-d %b')}."}
    elif stage in ("DELIVERY_DUE","COMPLETE"):
        delivery=max(order.due_date for order in Farm.model_validate(_journey(session)["origin_farm"]).orders)
        event={"tone":"success","label":"Customer delivery","date":str(delivery),"weather":"Simulated farm",
               "summary":f"The simulated customer delivery was recorded on {delivery.strftime('%-d %b')}."}
    else:
        event={"tone":"neutral","label":"Your teaching farm","date":world.get("clock_date") if world else str(farm.planning_date),"weather":"Simulated farm",
               "summary":"The simulated season is ready for its first bounded advance."}
        if world:
            current=date.fromisoformat(world["clock_date"] or world["start_date"])
            current_label=current.strftime("%-d %b")
            from services.api.simulation import EVENTS
            with store.connection() as connection:
                recorded=list(connection.execute(select(EVENTS.c.payload).where(
                    EVENTS.c.tenant_id==tenant_id,EVENTS.c.world_id==world["id"]
                ).order_by(EVENTS.c.sequence)).scalars())
            today=[row for row in recorded if row.get("date")==str(current)]
            deliveries=[row for row in today if row.get("type")=="demand_serviced"]
            tasks=[row for row in today if row.get("type")=="task_completed" and row.get("task") in ("sow","transplant","harvest")]
            allocations={row["id"]:row for row in world["segment_allocations"]};names={bed.id:bed.name for bed in farm.beds}
            if deliveries:
                delivered=sum(float(row.get("delivered_kg",0)) for row in deliveries)
                event.update(label=f"Delivered {delivered:g} kg to customers",date=str(current),tone="success",
                             summary=f"Recorded customer deliveries on {current_label}.")
            elif tasks:
                labels=[]
                verbs={"sow":"Sowed","transplant":"Transplanted","harvest":"Harvested"}
                for row in tasks:
                    allocation=allocations.get(row.get("allocation_id"),{})
                    cycle="existing" if allocation.get("executed") else ("recovery" if _journey(session).get("maintenance_recorded") else "planned")
                    crop=crop_labels.get(row.get("crop_id"),str(row.get("crop_id","")).replace("_"," ").title())
                    labels.append(f'{verbs[row["task"]]} the {cycle} {crop.lower()} crop in {names.get(row.get("bed_id"),row.get("bed_id"))}')
                label=labels[0] if len(labels)==1 else f"Recorded {len(labels)} crop tasks"
                event.update(label=label,date=str(current),summary=f'{"; ".join(labels)} on {current_label}.')
            elif not world.get("clock_date"):
                event.update(label=f"Ready to start on {current_label}",date=str(current),
                             summary="Your plan is saved. Advance to the next checkpoint when you are ready; simulated time has not advanced yet.")
            else:
                event.update(label=f"Farm advanced to {current_label}",date=str(current),
                             summary=f"No sowing, transplanting, harvest, or delivery was due on {current_label}.")
    return {"result_id":session.get("result_id"),"world_id":session.get("world_id"),"clock_date":world.get("clock_date") if world else None,
            "beds":beds,"event":event,"board_target_ids":[MAINTENANCE_BED_ID] if maintenance_active else [],
            "date_label":world.get("clock_date") if world and world.get("clock_date") else event["date"],
            "weather_label":event["weather"],"event_label":event["label"],"event_tone":event["tone"],
            "projection_source":"synthetic-execution-v1" if world else FIXTURE_VERSION}


def _order_outcomes(store, tenant_id: str, session: dict) -> list[dict]:
    origin=Farm.model_validate(_journey(session)["origin_farm"])
    raw=[]
    if session.get("world_id"):
        from services.api.simulation import EVENTS
        with store.connection() as connection:
            raw=list(connection.execute(select(EVENTS.c.payload).where(
                EVENTS.c.tenant_id==tenant_id,EVENTS.c.world_id==session["world_id"]
            ).order_by(EVENTS.c.sequence)).scalars())
    output=[]
    for order in origin.orders:
        events=[row for row in raw if row.get("type")=="demand_serviced" and row.get("order_id")==order.id]
        requested=float(order.quantity_kg-order.cancelled_kg);delivered=sum(float(row.get("delivered_kg",0)) for row in events)
        output.append({"order_id":order.id,"crop_id":order.crop_id,"requested_kg":requested,
                       "delivered_kg":round(delivered,6),"fulfilled":delivered+1e-6>=requested,
                       "event_recorded":bool(events)})
    return output


def _debrief(store, tenant_id: str, session: dict, metrics: dict, stage: str) -> dict | None:
    if stage!="COMPLETE":return None
    orders=_order_outcomes(store,tenant_id,session)
    requested=sum(row["requested_kg"] for row in orders);delivered=sum(min(row["delivered_kg"],row["requested_kg"]) for row in orders)
    met=bool(orders) and all(row["fulfilled"] and row["event_recorded"] for row in orders)
    return {"outcome":"delivered" if met else "partial_delivery","title":"Teaching season complete",
            "summary":f'{delivered:.1f} of {requested:.1f} kg in confirmed orders was delivered by the recorded simulation.',
            "objective_met":met,"highlights":["You selected a calculated policy.","B3 maintenance was recorded before its affected transplant.","The remaining schedule was recalculated rather than edited by hand."],
            "orders":orders,"replay_available":True}


def _public(store, tenant_id: str, source: dict) -> dict:
    session=deepcopy(source);session["_store"]=store;session["_tenant"]=tenant_id
    journey=_journey(session);stage=_effective_stage(session);choices=_choices(session,stage)
    metrics=_metrics(store,tenant_id,session);next_action=_next_action(session,stage);cards=_cards(session,stage,choices)
    if stage in ("CHOOSE_PLAN","CHOOSE_RECOVERY") and not any(choice["eligible"] for choice in choices):
        next_action=_action("replay","No feasible choice; start a fresh attempt","replay",eligible=True)
    return {
        "id":session["id"],"version":VERSION,"lesson_id":journey["lesson_id"],"attempt":journey["attempt"],
        "name":session["name"],"revision":session["revision"],"status":_status(session),"stage":stage,
        "objective":{"id":"deliver-confirmed-orders","title":"Deliver the confirmed order" if journey["lesson_id"]=="first_delivery" else "Balance two confirmed orders",
                     "summary":cards[0]["summary"],"detail":cards[0]["summary"],"server_derived":True},
        "origin_farm":deepcopy(journey["origin_farm"]),
        "scenario":{"title":"Scheduled B3 maintenance","summary":"A dated maintenance window is introduced before the affected B3 transplant.",
                    "bed_id":MAINTENANCE_BED_ID,"bed_name":"B3","maintenance":{"start_date":str(MAINTENANCE_START),"end_date":str(MAINTENANCE_END)},
                    "provenance_label":"SYNTHETIC TEACHING SIMULATION","data_mode":"synthetic_demo"},
        "planning_session":{"id":session["id"],"status":session["status"],"revision":session["revision"],"result_id":session.get("result_id"),"job":deepcopy(session.get("job"))},
        "cards":cards,"choices":choices,"selected_choice_id":journey.get("selected_choice_id"),
        "result_id":session.get("result_id"),"scene":_scene(store,tenant_id,session,stage),
        "next_action":next_action,"timeline":_timeline(store,tenant_id,session),"metrics":metrics,
        "debrief":_debrief(store,tenant_id,session,metrics,stage),"audit":{"event_count":len(journey.get("audit",[])),"latest_revision":session["revision"]},
        "execution_mode":"simulation","data_mode":"synthetic_demo","real_operations_enabled":False,
    }


def _audit(session: dict, event_type: str, title: str, summary: str, *, civil_date: str | None = None) -> None:
    _journey(session).setdefault("audit",[]).append({"type":event_type,"title":title,"summary":summary,
        "recorded_at":now(),"civil_date":civil_date,"revision":session["revision"]+1,"inference_triggered":False})


def _new_session(store, tenant_id: str, body: CreateBeginnerJourney, *, attempt: int | None = None) -> dict:
    with store.connection() as connection:
        rows=list(connection.execute(select(SESSIONS.c.payload).where(SESSIONS.c.tenant_id==tenant_id)).scalars())
    if len(rows)>=8:raise HTTPException(429,"Eight planning sessions per tenant maximum")
    same=[row for row in rows if row.get("beginner_journey",{}).get("lesson_id")==body.lesson_id]
    attempt=attempt or len(same)+1
    farm=beginner_farm(body.lesson_id)
    session={"id":secrets.token_hex(16),"name":body.name,"version":"guided-planning-v1","revision":0,
             "status":"DRAFT","stage":"beginner","created_at":now(),"updated_at":now(),"farm":farm.model_dump(mode="json"),
             "input_hash":content_hash(farm),"result_id":None,"selected_strategy_id":None,
             "review":{"status":"not_requested","findings":[]},"assumptions":{},"world_id":None,"history":[],"job":None,
             "data_mode":"synthetic_demo","council_policy":"not_invoked","real_operations_enabled":False,
             "workflow_version":VERSION,
             "beginner_journey":{"version":VERSION,"fixture_version":FIXTURE_VERSION,"lesson_id":body.lesson_id,
                 "attempt":attempt,"stage":"START","selected_choice_id":None,"maintenance_recorded":False,
                 "origin_farm":farm.model_dump(mode="json"),"audit":[]}}
    _audit(session,"journey_created","Lesson created",f'Attempt {attempt} uses an isolated four-bed synthetic farm.')
    with store.connection(write=True) as connection:
        connection.execute(SESSIONS.insert().values(id=session["id"],tenant_id=tenant_id,status=session["status"],payload=session))
    return session


def _ready(session: dict, body: BeginnerActionRequest) -> str:
    if session["revision"]!=body.revision:raise HTTPException(409,"Journey revision changed; refresh before continuing")
    stage=_effective_stage(session)
    if stage in ("CALCULATING","RECALCULATING"):raise HTTPException(409,"The local calculation is still running")
    expected={"START":{"calculate_choices"},"CHOOSE_PLAN":{"select_plan"},"PLAN_SELECTED":{"advance"},
              "MAINTENANCE_DUE":{"record_b3_maintenance"},"CHOOSE_RECOVERY":{"select_recovery"},
              "GROWING":{"advance"},"DELIVERY_DUE":{"record_delivery"},
              "COMPLETE":{"replay","next_challenge"},"FAILED":{"replay"}}
    expected.setdefault(stage,set()).add("replay")
    if stage=="COMPLETE" and _journey(session)["lesson_id"]!="first_delivery":expected[stage].discard("next_challenge")
    if body.action_id not in expected.get(stage,set()):raise HTTPException(409,f'Action {body.action_id} is not available at stage {stage}')
    return stage


def _advance(store, tenant_id: str, session: dict, stage: str) -> None:
    from services.api.simulation import WORLDS, advance, get_world
    world=get_world(store,tenant_id,session.get("world_id"))
    if not world:raise HTTPException(409,"The teaching simulation has not started")
    current=date.fromisoformat(world["clock_date"]) if world.get("clock_date") else date.fromisoformat(world["start_date"])-timedelta(days=1)
    if stage=="PLAN_SELECTED":
        target=min(current+timedelta(days=7),MAINTENANCE_START-timedelta(days=1))
    else:
        future=[]
        for allocation in world["segment_allocations"]:
            for field in ("sow_date","transplant_date","harvest_date"):
                day=date.fromisoformat(allocation[field])
                if day>current:future.append(day)
        delivery_days=[order.due_date for order in Farm.model_validate(_journey(session)["origin_farm"]).orders if order.due_date>current]
        future.extend(delivery_days)
        target=min([current+timedelta(days=7),*future])
    days=(target-current).days
    if not 1<=days<=7:raise HTTPException(409,"No bounded simulation checkpoint remains")
    advance(store,tenant_id,world,days)
    with store.connection(write=True) as connection:
        connection.execute(update(WORLDS).where(WORLDS.c.id==world["id"],WORLDS.c.tenant_id==tenant_id).values(payload=world))
    delivery_due=max(order.due_date for order in Farm.model_validate(_journey(session)["origin_farm"]).orders)
    if stage=="PLAN_SELECTED" and target==MAINTENANCE_START-timedelta(days=1):
        _journey(session)["stage"]="MAINTENANCE_DUE"
    elif stage=="GROWING" and target>=delivery_due:
        _journey(session)["stage"]="DELIVERY_DUE"
    _audit(session,"simulation_advanced","Simulation advanced",f'The frozen ledger advanced {days} day(s) through {target}.',civil_date=str(target))
    session["revision"]+=1;save_session(store,tenant_id,session)


def install_routes(app, tenant):
    """Install the isolated beginner journey API."""

    def owned(tenant_id: str, journey_id: str) -> dict:
        store=app.state.store
        session=get_session(store,tenant_id,journey_id)
        if not session or not session.get("beginner_journey"):raise HTTPException(404,"Beginner journey not found")
        return session

    def operation(request: Request, tenant_id: str, body, scope: str):
        store=app.state.store
        raw=request.headers.get("Idempotency-Key","")
        if not raw or len(raw)>128:raise HTTPException(422,"Idempotency-Key required, maximum 128 characters")
        key="beginner:"+raw
        digest=content_hash({"scope":scope,"body":body.model_dump(mode="json")})
        with store.connection() as connection:
            old=connection.execute(select(RECEIPTS).where(RECEIPTS.c.tenant_id==tenant_id,RECEIPTS.c.key==key)).mappings().first()
        if old and old["request_hash"]!=digest:raise HTTPException(409,"Idempotency key reused with changed inputs")
        return key,digest,deepcopy(old["payload"]) if old else None

    def finish(tenant_id: str, key: str, digest: str, session: dict):
        store=app.state.store
        value=_public(store,tenant_id,session)
        with store.connection(write=True) as connection:
            connection.execute(RECEIPTS.insert().values(tenant_id=tenant_id,key=key,request_hash=digest,payload=value))
        return value

    @app.get("/api/v1/beginner-journeys")
    def listing(request: Request):
        tenant_id=tenant(request);store=app.state.store
        with store.connection() as connection:
            rows=list(connection.execute(select(SESSIONS.c.payload).where(SESSIONS.c.tenant_id==tenant_id)).scalars())
        rows=[row for row in rows if row.get("beginner_journey")]
        rows.sort(key=lambda row:row["updated_at"],reverse=True)
        return {"journeys":[_public(store,tenant_id,row) for row in rows],"latest_id":rows[0]["id"] if rows else None,"limit":8}

    @app.post("/api/v1/beginner-journeys",status_code=201)
    def create(body: CreateBeginnerJourney, request: Request):
        tenant_id=tenant(request);store=app.state.store
        with store.transaction(tenant_id):
            key,digest,replay=operation(request,tenant_id,body,"beginner:create")
            if replay is not None:return replay
            return finish(tenant_id,key,digest,_new_session(store,tenant_id,body))

    @app.get("/api/v1/beginner-journeys/{journey_id}")
    def get(journey_id: str, request: Request):
        tenant_id=tenant(request);return _public(app.state.store,tenant_id,owned(tenant_id,journey_id))

    @app.get("/api/v1/beginner-journeys/{journey_id}/replay")
    def replay_journal(journey_id: str, request: Request):
        tenant_id=tenant(request);store=app.state.store;session=owned(tenant_id,journey_id)
        public=_public(store,tenant_id,session)
        return {"journey_id":journey_id,"version":VERSION,"lesson_id":public["lesson_id"],
                "attempt":public["attempt"],"timeline":public["timeline"],"debrief":public["debrief"],
                "read_only":True,"real_operations_enabled":False}

    @app.post("/api/v1/beginner-journeys/{journey_id}/actions")
    def act(journey_id: str, body: BeginnerActionRequest, request: Request):
        tenant_id=tenant(request);store=app.state.store
        with store.transaction(tenant_id):
            key,digest,replay=operation(request,tenant_id,body,"beginner:action:"+journey_id)
            if replay is not None:return replay
            session=owned(tenant_id,journey_id);stage=_ready(session,body);journey=_journey(session)
            if body.action_id=="calculate_choices":
                if body.option_id is not None:raise HTTPException(422,"This action does not accept an option")
                journey["stage"]="CALCULATING";_audit(session,"calculation_queued","Planning calculation queued","The bounded local worker is calculating two feasible policy choices.")
                queue_initial_calculation(store,tenant_id,session)
            elif body.action_id in ("select_plan","select_recovery"):
                choices=_choices(dict(session,_store=store,_tenant=tenant_id),stage)
                selected=next((choice for choice in choices if choice["id"]==body.option_id and choice["eligible"]),None)
                if not selected:raise HTTPException(422,"Choose one of the current server-derived options")
                replacing=body.action_id=="select_recovery"
                activate_strategy(store,tenant_id,session,selected["strategy_id"],replace_future=replacing)
                journey["selected_choice_id"]=selected["strategy_id"]
                snapshot={key:deepcopy(selected[key]) for key in ("strategy_id","result_id","title","metrics","board_target_ids")}
                journey["recovery_choice" if replacing else "initial_choice"]=snapshot
                journey["stage"]="GROWING" if replacing else "PLAN_SELECTED"
                _audit(session,"recovery_selected" if replacing else "plan_selected",
                       "Recovery selected" if replacing else "Starting plan selected",
                       f'{selected["title"]} was bound to its exact calculated execution trace.')
                session["revision"]+=1;save_session(store,tenant_id,session)
            elif body.action_id=="advance":
                if body.option_id is not None:raise HTTPException(422,"This action does not accept an option")
                _advance(store,tenant_id,session,stage)
            elif body.action_id=="record_b3_maintenance":
                if body.option_id is not None:raise HTTPException(422,"This action does not accept an option")
                from services.api.simulation import WORLDS, append_event, get_world
                world=get_world(store,tenant_id,session.get("world_id"))
                if not world or world.get("clock_date")!=str(MAINTENANCE_START-timedelta(days=1)):
                    raise HTTPException(409,"Advance through the day before maintenance first")
                append_event(store,tenant_id,world,"maintenance_recorded",MAINTENANCE_START,
                             bed_id=MAINTENANCE_BED_ID,start_date=str(MAINTENANCE_START),end_date=str(MAINTENANCE_END),inference_triggered=False)
                with store.connection(write=True) as connection:
                    connection.execute(update(WORLDS).where(WORLDS.c.id==world["id"],WORLDS.c.tenant_id==tenant_id).values(payload=world))
                journey.update(stage="RECALCULATING",maintenance_recorded=True)
                _audit(session,"maintenance_recorded","B3 maintenance recorded","The dated B3 constraint was added before its affected transplant.",civil_date=str(MAINTENANCE_START))
                queue_recalculation(store,tenant_id,session,[{"kind":"planning_assumptions","assumptions":maintenance_assumptions()}])
                session["workflow_version"]=VERSION;save_session(store,tenant_id,session)
            elif body.action_id=="record_delivery":
                events=_simulation_events(store,tenant_id,session.get("world_id"))
                if not any(row["event_type"]=="demand_serviced" for row in events):
                    raise HTTPException(409,"No simulated delivery event has been recorded")
                if not all(row["event_recorded"] for row in _order_outcomes(store,tenant_id,session)):
                    raise HTTPException(409,"A confirmed order has no recorded delivery event")
                journey["stage"]="COMPLETE"
                _audit(session,"delivery_reviewed","Delivery reviewed","The debrief is derived from recorded demand-service and inventory events.")
                session["revision"]+=1;save_session(store,tenant_id,session)
            elif body.action_id in ("replay","next_challenge"):
                lesson="two_orders" if body.action_id=="next_challenge" else journey["lesson_id"]
                if body.option_id is not None:raise HTTPException(422,"This action does not accept an option")
                _audit(session,"replay_created","New attempt created",f'A separate {lesson} attempt was created; this journal remains immutable.')
                session["revision"]+=1;save_session(store,tenant_id,session)
                created=_new_session(store,tenant_id,CreateBeginnerJourney(name=session["name"],lesson_id=lesson))
                return finish(tenant_id,key,digest,created)
            return finish(tenant_id,key,digest,session)
