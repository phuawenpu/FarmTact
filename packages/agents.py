"""Current seven-person council; historic editions retain their frozen rosters."""

COUNCIL_VERSION = "seven-agent-council-v3"
COUNCIL_WORKFLOW_TYPE = "sequential_specialists_then_chair"

ADVISORS = {
    "ravi": dict(id="ravi", name="Demand Planner", role="demand_analyst", title="Demand Planner", location="Market stall", expertise="Required crop quantities and delivery dates; booked orders versus forecast demand"),
    "hana": dict(id="hana", name="Weather & Risk", role="weather_analyst", title="Weather & Risk", location="Weather station", expertise="Observed conditions, source freshness and environmental uncertainty; no unsupported yield adjustment"),
    "idris": dict(id="idris", name="Market Analyst", role="market_analyst", title="Market Analyst", location="Market desk", expertise="Selling prices, commercial opportunities and sourced buyer/grower reactions; reactions are not measured demand"),
    "mei": dict(id="mei", name="Crop Planner", role="production_analyst", title="Crop Planner", location="Greenhouse", expertise="Crop recipes, biological lead times, growing space and feasible production"),
    "lina": dict(id="lina", name="Supply Planner", role="supply_chain_analyst", title="Supply Planner", location="Packing station", expertise="Inventory, expiry, input availability and delivery timing; distinguish modelled constraints from missing logistics data"),
    "ben": dict(id="ben", name="Resource Planner", role="profit_analyst", title="Resource Planner", location="Tool shed", expertise="Computed costs, cash, labour and margins under declared price and demand assumptions"),
    "asha": dict(id="asha", name="Chair", role="planning_chair", title="Chair", location="Council pavilion", expertise="Reconcile evidence-backed tradeoffs across feasible numerical strategies and explain the selection policy"),
}

ROLES = [advisor["role"] for advisor in ADVISORS.values()]
ROLE_TO_ADVISOR = {advisor["role"]: advisor_id for advisor_id, advisor in ADVISORS.items()}
ROLE_EXPERTISE = {advisor["role"]: advisor["expertise"] for advisor in ADVISORS.values()}
COUNCIL_MAX_REQUESTS = len(ROLES) + 2  # bounded schema repairs, within existing 16-call ceiling
COUNCIL_MAX_REPAIRS = 2


def council_review_issues(claims):
    """Deterministic evidence gate, independent of any advisor persona."""
    issues = []
    actual = [claim.get("role") for claim in claims]
    if actual != ROLES:
        issues.append("The seven required council findings are incomplete or out of order.")
    if any(claim.get("status") != "validated" for claim in claims):
        issues.append("At least one council finding failed evidence validation.")
    if any(claim_requests_withholding(claim) for claim in claims):
        issues.append("A council finding raises an unresolved acceptance concern.")
    return issues


def claim_requests_withholding(claim):
    """Optional-context absence is compatible with a validated numerical plan."""

    if claim.get("recommendation") == "proceed_simulation":
        return False
    if (
        claim.get("claim_type") == "abstention"
        and claim.get("role") in {"weather_analyst", "market_analyst"}
        and claim.get("status") == "validated"
    ):
        return False
    return True


def council_statuses(claims):
    """Expose transport, evidence and policy influence as separate dimensions."""

    if not claims:
        return {
            "execution_status": "not_run",
            "evidence_status": "numerical_only",
            "decision_influence": "none",
        }
    rejected = [claim for claim in claims if claim.get("status") != "validated"]
    vetoes = [
        claim
        for claim in claims
        if claim_requests_withholding(claim)
    ]
    unverified = [
        claim
        for claim in claims
        if claim.get("evidence_status")
        in {"qualitative_unverified", "grounded_facts_qualitative_unverified"}
    ]
    return {
        "execution_status": (
            "completed" if len(claims) == len(ROLES) else "partial"
        ),
        "evidence_status": (
            "unsupported"
            if rejected
            else "qualitative_unverified"
            if unverified
            else "reference_grounded"
        ),
        "decision_influence": (
            "withhold_requested"
            if rejected or vetoes
            else "advisory_gate_passed"
        ),
    }
