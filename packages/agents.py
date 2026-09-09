"""Current seven-person council; historic editions retain their frozen rosters."""

COUNCIL_VERSION = "seven-agent-council-v1"

ADVISORS = {
    "ravi": dict(id="ravi", name="Ravi", role="demand_analyst", title="Demand agent", location="Market stall", expertise="Required crop quantities and delivery dates; booked orders versus forecast demand"),
    "hana": dict(id="hana", name="Hana", role="weather_analyst", title="Weather agent", location="Weather station", expertise="Observed conditions, source freshness and environmental uncertainty; no unsupported yield adjustment"),
    "idris": dict(id="idris", name="Idris", role="market_analyst", title="Market agent", location="Market desk", expertise="Selling prices, commercial opportunities and sourced buyer/grower reactions; reactions are not measured demand"),
    "mei": dict(id="mei", name="Mei", role="production_analyst", title="Production agent", location="Greenhouse", expertise="Crop recipes, biological lead times, growing space and feasible production"),
    "lina": dict(id="lina", name="Lina", role="supply_chain_analyst", title="Supply Chain agent", location="Packing station", expertise="Inventory, expiry, input availability and delivery timing; distinguish modelled constraints from missing logistics data"),
    "ben": dict(id="ben", name="Ben", role="profit_analyst", title="Profit agent", location="Tool shed", expertise="Computed costs, cash, labour and margins under declared price and demand assumptions"),
    "asha": dict(id="asha", name="Asha", role="planning_chair", title="Planner agent", location="Council pavilion", expertise="Reconcile evidence-backed tradeoffs across feasible numerical strategies and explain the selection policy"),
}

ROLES = [advisor["role"] for advisor in ADVISORS.values()]
ROLE_TO_ADVISOR = {advisor["role"]: advisor_id for advisor_id, advisor in ADVISORS.items()}
ROLE_EXPERTISE = {advisor["role"]: advisor["expertise"] for advisor in ADVISORS.values()}
COUNCIL_MAX_REQUESTS = len(ROLES) + 2  # bounded schema repairs, within existing 16-call ceiling


def council_review_issues(claims):
    """Deterministic evidence gate, independent of any advisor persona."""
    issues = []
    actual = [claim.get("role") for claim in claims]
    if actual != ROLES:
        issues.append("The seven required council findings are incomplete or out of order.")
    if any(claim.get("status") != "validated" for claim in claims):
        issues.append("At least one council finding failed evidence validation.")
    if any(claim.get("recommendation") != "proceed_simulation" for claim in claims):
        issues.append("A council finding raises an unresolved acceptance concern.")
    return issues
