from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from packages.beginner_fixture import MAINTENANCE_BED_ID, beginner_farm
from packages.beginner_fixture import MAINTENANCE_START
from packages.fixtures import synthetic_farm
from packages.planner import plan
from services.api.app import create_app
from services.api.planning_sessions import execute_job, get_result, get_session
from services.api.simulation import get_world
from services.api.store import Store


@pytest.fixture()
def journey_api(monkeypatch):
    for name in ("DEEPSEEK_API_KEY","MOONSHOT_API_KEY","MINIMAX_API_KEY"):
        monkeypatch.delenv(name,raising=False)
    store=Store("sqlite://")
    with TestClient(create_app(store,start_worker=False)) as client:
        client.get("/api/v1/bootstrap")
        tenant=store.authenticate(client.cookies.get("farmtact_session"))
        yield client,store,tenant


def _key():
    return uuid4().hex


def _create(client, **body):
    response=client.post("/api/v1/beginner-journeys",json=body,headers={"Idempotency-Key":_key()})
    assert response.status_code==201,response.text
    return response.json()


def _act(client, journey, action_id, option_id=None, *, key=None):
    body={"revision":journey["revision"],"action_id":action_id}
    if option_id is not None:body["option_id"]=option_id
    response=client.post(f'/api/v1/beginner-journeys/{journey["id"]}/actions',json=body,
                         headers={"Idempotency-Key":key or _key()})
    assert response.status_code==200,response.text
    return response.json()


def _complete_job(store, tenant, journey):
    execute_job(store,tenant,journey["planning_session"]["job"]["id"])


def test_fixture_reuses_existing_recipes_and_calibrates_distinct_b3_choices():
    approved={recipe.crop_id:recipe.model_dump(mode="json") for recipe in synthetic_farm().recipes}
    farm=beginner_farm("first_delivery")
    assert farm.recipes[0].model_dump(mode="json")==approved["lettuce"]
    assert len(farm.beds)==4 and len(farm.batches)==1 and len(farm.orders)==1
    result=plan(farm,time_limit=2)
    lean=next(row for row in result["strategies"] if row["name"]=="Lean")
    resilient=next(row for row in result["strategies"] if row["name"]=="Resilient")
    assert lean["status"]==resilient["status"]=="FEASIBLE"
    assert lean["metrics"]["shortfall_kg"]==pytest.approx(2)
    assert resilient["metrics"]["shortfall_kg"]==pytest.approx(0)
    assert lean["metrics"]["area_m2"]<resilient["metrics"]["area_m2"]
    for strategy in (lean,resilient):
        targets=[row for row in strategy["allocations"] if not row.get("executed") and row["bed_id"]==MAINTENANCE_BED_ID]
        assert targets and min(row["sow_date"] for row in targets)>=str(MAINTENANCE_START)


@pytest.mark.parametrize("policy_name",["Lean plan","Resilient plan"])
def test_full_first_delivery_uses_real_jobs_events_recovery_and_replay(journey_api, policy_name):
    client,store,tenant=journey_api
    journey=_create(client)
    assert journey["stage"]=="START"
    assert journey["cards"][0]["title"]=="Grow 25 kg of lettuce for 23 Feb"
    assert "customer needs 25 kg of lettuce" in journey["cards"][0]["summary"]
    assert journey["scene"]["beds"][2]["name"]=="B3"
    assert journey["real_operations_enabled"] is False
    assert all(card["inference_triggered"] is False for card in journey["cards"])
    assert journey["metrics"]["planned_harvest_kg"] is None
    assert journey["metrics"]["shortfall_kg"] is None
    assert journey["metrics"]["committed_demand_kg"]==pytest.approx(25)

    idem=_key()
    queued=_act(client,journey,"calculate_choices",key=idem)
    replay=client.post(f'/api/v1/beginner-journeys/{journey["id"]}/actions',
                       json={"revision":journey["revision"],"action_id":"calculate_choices"},
                       headers={"Idempotency-Key":idem})
    assert replay.status_code==200 and replay.json()==queued
    _complete_job(store,tenant,queued)

    journey=client.get(f'/api/v1/beginner-journeys/{journey["id"]}').json()
    assert journey["stage"]=="CHOOSE_PLAN" and len(journey["choices"])==2
    assert {choice["title"] for choice in journey["choices"]}=={"Lean plan","Resilient plan"}
    assert all(MAINTENANCE_BED_ID in choice["board_target_ids"] for choice in journey["choices"])
    assert all(choice["result_id"]==journey["result_id"] for choice in journey["choices"])
    assert all(choice["metrics"]["cost_sgd"]>0 and 0<=choice["metrics"]["land_utilization_pct"]<=100
               for choice in journey["choices"])
    selected=next(choice for choice in journey["choices"] if choice["title"]==policy_name)
    journey=_act(client,journey,"select_plan",selected["id"])

    session=get_session(store,tenant,journey["id"]);world=get_world(store,tenant,session["world_id"])
    assert world["strategy_id"]==selected["strategy_id"]
    chosen=next(row for row in get_result(store,tenant,session["result_id"])["strategies"] if row["id"]==selected["id"])
    assert world["segment_allocations"]==chosen["allocations"]
    assert world["trace"]["metrics"]==chosen["metrics"]

    while journey["stage"]=="PLAN_SELECTED":
        before=journey["metrics"]["clock_date"]
        journey=_act(client,journey,"advance")
        after=journey["metrics"]["clock_date"]
        assert after!=before
    assert journey["stage"]=="MAINTENANCE_DUE"
    assert journey["metrics"]["clock_date"]=="2026-01-17"

    queued=_act(client,journey,"record_b3_maintenance")
    assert queued["stage"]=="RECALCULATING"
    _complete_job(store,tenant,queued)
    journey=client.get(f'/api/v1/beginner-journeys/{journey["id"]}').json()
    assert journey["stage"]=="CHOOSE_RECOVERY"
    assert any(row["event_type"]=="maintenance_recorded" for row in journey["timeline"])
    retained=next(choice for choice in journey["choices"] if not choice["eligible"])
    before_world=get_world(store,tenant,get_session(store,tenant,journey["id"])["world_id"])["state_hash"]
    rejected=client.post(f'/api/v1/beginner-journeys/{journey["id"]}/actions',
                         json={"revision":journey["revision"],"action_id":"select_recovery","option_id":retained["id"]},
                         headers={"Idempotency-Key":_key()})
    assert rejected.status_code==422
    unchanged=client.get(f'/api/v1/beginner-journeys/{journey["id"]}').json()
    assert unchanged["revision"]==journey["revision"]
    assert get_world(store,tenant,get_session(store,tenant,journey["id"])["world_id"])["state_hash"]==before_world
    recovery=next(choice for choice in journey["choices"] if choice["eligible"])
    assert recovery["metrics"]["shortfall_kg"]==pytest.approx(0)
    assert MAINTENANCE_BED_ID not in recovery["board_target_ids"]
    journey=_act(client,journey,"select_recovery",recovery["id"])
    world=get_world(store,tenant,get_session(store,tenant,journey["id"])["world_id"])
    assert world["strategy_id"]==recovery["id"]
    assert all(row["bed_id"]!=MAINTENANCE_BED_ID for row in world["segment_allocations"] if not row.get("executed"))

    advances=0
    while journey["stage"]=="GROWING":
        journey=_act(client,journey,"advance");advances+=1
        assert advances<20
    assert advances>=5 and journey["stage"]=="DELIVERY_DUE"
    assert any(row["event_type"]=="task_completed" for row in journey["timeline"])
    assert any(row["event_type"]=="demand_serviced" for row in journey["timeline"])
    journey=_act(client,journey,"record_delivery")
    assert journey["stage"]=="COMPLETE"
    assert [card["id"] for card in journey["cards"]]==["debrief-result","debrief-change","debrief-next"]
    assert journey["cards"][1]["actions"][0]["id"]=="replay"
    assert journey["cards"][2]["actions"][0]["id"]=="next_challenge"
    assert journey["debrief"]["objective_met"] is True
    assert journey["metrics"]["fulfilled_demand_kg"]==pytest.approx(25)
    assert all(row["fulfilled"] and row["event_recorded"] for row in journey["debrief"]["orders"])

    old_id=journey["id"]
    replayed=_act(client,journey,"replay")
    assert replayed["id"]!=old_id and replayed["attempt"]==2 and replayed["stage"]=="START"
    journal=client.get(f"/api/v1/beginner-journeys/{old_id}/replay").json()
    assert journal["read_only"] is True and journal["debrief"]["objective_met"] is True


def test_revision_option_idempotency_and_tenant_isolation(journey_api):
    client,store,_tenant=journey_api
    journey=_create(client)
    stale=client.post(f'/api/v1/beginner-journeys/{journey["id"]}/actions',
                      json={"revision":99,"action_id":"calculate_choices"},headers={"Idempotency-Key":_key()})
    assert stale.status_code==409
    unexpected=client.post(f'/api/v1/beginner-journeys/{journey["id"]}/actions',
                           json={"revision":journey["revision"],"action_id":"select_plan","option_id":"forged"},
                           headers={"Idempotency-Key":_key()})
    assert unexpected.status_code==409
    key=_key();_act(client,journey,"calculate_choices",key=key)
    changed=client.post(f'/api/v1/beginner-journeys/{journey["id"]}/actions',
                        json={"revision":journey["revision"],"action_id":"advance"},headers={"Idempotency-Key":key})
    assert changed.status_code==409 and "Idempotency" in changed.json()["detail"]

    _other,token=store.new_session();client.cookies.set("farmtact_session",token)
    assert client.get(f'/api/v1/beginner-journeys/{journey["id"]}').status_code==404
    assert client.get(f'/api/v1/beginner-journeys/{journey["id"]}/replay').status_code==404
    assert client.get("/api/v1/beginner-journeys").json()["journeys"]==[]


def test_stale_calculation_receipt_cannot_regress_completed_poll(journey_api):
    client,store,tenant=journey_api
    journey=_create(client);key=_key()
    queued=_act(client,journey,"calculate_choices",key=key)
    _complete_job(store,tenant,queued)
    current=client.get(f'/api/v1/beginner-journeys/{journey["id"]}').json()
    assert current["stage"]=="CHOOSE_PLAN"
    replay=client.post(f'/api/v1/beginner-journeys/{journey["id"]}/actions',
                       json={"revision":journey["revision"],"action_id":"calculate_choices"},
                       headers={"Idempotency-Key":key})
    assert replay.status_code==200 and replay.json()["stage"]=="CALCULATING"
    after=client.get(f'/api/v1/beginner-journeys/{journey["id"]}').json()
    assert after["stage"]=="CHOOSE_PLAN" and after["revision"]==current["revision"]


def test_failed_and_no_feasible_jobs_offer_bounded_fresh_attempt(journey_api, monkeypatch):
    import services.api.planning_sessions as planning_sessions

    client,store,tenant=journey_api
    failed=_create(client,name="Failure path")
    queued=_act(client,failed,"calculate_choices")
    monkeypatch.setattr(planning_sessions,"calculate",lambda *_args,**_kwargs: (_ for _ in ()).throw(RuntimeError("bounded test failure")))
    _complete_job(store,tenant,queued)
    failed=client.get(f'/api/v1/beginner-journeys/{failed["id"]}').json()
    assert failed["stage"]=="FAILED" and failed["next_action"]["id"]=="replay"
    retried=_act(client,failed,"replay")
    assert retried["id"]!=failed["id"] and retried["stage"]=="START"

    def no_feasible(_operation,payload,**_kwargs):
        return {"forecast":{"demand":[]},"strategies":[],"selected_strategy_id":None,
                "input_snapshot":payload["farm"],"calculation_contract":"guided-planning-v12"}
    monkeypatch.setattr(planning_sessions,"calculate",no_feasible)
    empty=_create(client,name="No feasible path")
    queued=_act(client,empty,"calculate_choices");_complete_job(store,tenant,queued)
    empty=client.get(f'/api/v1/beginner-journeys/{empty["id"]}').json()
    assert empty["stage"]=="CHOOSE_PLAN" and empty["choices"]==[]
    assert empty["next_action"]["id"]=="replay" and empty["next_action"]["eligible"] is True
    retried=_act(client,empty,"replay")
    assert retried["id"]!=empty["id"] and retried["stage"]=="START"


def test_legacy_cancel_calculate_and_proposal_cannot_mutate_journey(journey_api):
    client,store,tenant=journey_api
    journey=_create(client);before=get_session(store,tenant,journey["id"])
    calculate=client.post(f'/api/v1/planning-sessions/{journey["id"]}/calculate',json={"revision":journey["revision"]},
                          headers={"Idempotency-Key":_key()})
    cancel=client.post(f'/api/v1/planning-sessions/{journey["id"]}/cancel',json={"revision":journey["revision"]},
                       headers={"Idempotency-Key":_key()})
    proposal=client.post('/api/v1/farm-workflow/proposals',json={"session_id":journey["id"],"base_revision":journey["revision"],
        "changes":[{"kind":"planning_assumptions","assumptions":{"reservations":[]}}],"idempotency_key":_key()})
    assert calculate.status_code==409 and cancel.status_code==409 and proposal.status_code in (409,422)
    after=get_session(store,tenant,journey["id"])
    assert after["revision"]==before["revision"] and after["result_id"] is None and after["job"] is None


def test_two_order_challenge_is_isolated_and_server_derived(journey_api):
    client,store,tenant=journey_api
    journey=_create(client,lesson_id="two_orders",name="Two orders")
    session=get_session(store,tenant,journey["id"])
    farm=beginner_farm("two_orders")
    assert {recipe["crop_id"] for recipe in session["farm"]["recipes"]}=={"lettuce","pak_choi"}
    assert len(farm.orders)==2 and len(session["farm"]["orders"])==2
    assert sum(float(order.quantity_kg) for order in farm.orders)==pytest.approx(25)
    queued=_act(client,journey,"calculate_choices");_complete_job(store,tenant,queued)
    journey=client.get(f'/api/v1/beginner-journeys/{journey["id"]}').json()
    assert journey["objective"]["title"]=="Balance two confirmed orders"
    assert {choice["title"] for choice in journey["choices"]}=={"Balanced plan","Resilient plan"}
    assert all(MAINTENANCE_BED_ID in choice["board_target_ids"] for choice in journey["choices"])
    assert any("pak_choi" in {allocation["crop_id"] for allocation in choice["allocations"]} for choice in journey["choices"])


@pytest.mark.parametrize("policy_name",["Balanced plan","Resilient plan"])
def test_two_order_challenge_has_full_recorded_recovery(journey_api, policy_name):
    client,store,tenant=journey_api
    journey=_create(client,lesson_id="two_orders",name="Two orders")
    queued=_act(client,journey,"calculate_choices");_complete_job(store,tenant,queued)
    journey=client.get(f'/api/v1/beginner-journeys/{journey["id"]}').json()
    selected=next(choice for choice in journey["choices"] if choice["title"]==policy_name)
    journey=_act(client,journey,"select_plan",selected["id"])
    while journey["stage"]=="PLAN_SELECTED":journey=_act(client,journey,"advance")
    queued=_act(client,journey,"record_b3_maintenance");_complete_job(store,tenant,queued)
    journey=client.get(f'/api/v1/beginner-journeys/{journey["id"]}').json()
    full=next(choice for choice in journey["choices"] if choice["eligible"] and choice["metrics"]["shortfall_kg"]==0)
    assert MAINTENANCE_BED_ID not in full["board_target_ids"]
    journey=_act(client,journey,"select_recovery",full["id"])
    while journey["stage"]=="GROWING":journey=_act(client,journey,"advance")
    journey=_act(client,journey,"record_delivery")
    assert journey["stage"]=="COMPLETE" and journey["debrief"]["objective_met"] is True
    assert len(journey["cards"])==3 and journey["next_action"]["id"]=="replay"
    assert journey["cards"][2]["actions"][0]["id"]=="replay"
    assert journey["metrics"]["fulfilled_demand_kg"]==pytest.approx(25)
