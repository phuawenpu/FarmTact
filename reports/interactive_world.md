# FarmTact interactive farming world

Status: implementation and integration in progress. This report records only checks actually executed; deployment and live conversation acceptance remain pending until updated below.

## Scope and architecture

The existing four-crop numerical planner remains authoritative. Additive tenant-owned scenario, quest and conversation records extend the existing PostgreSQL database. Branch jobs use the existing worker but never write farm versions or planning runs. Original crop/advisor SVG artwork is served from a fixed asset directory; no arbitrary file route is introduced. Application inference remains restricted to the existing DeepSeek gateway, global daily budget and finite per-exchange limits.

Scenario controls target one batch for delay/yield, one simulated crop for demand, the weekly labour allowance across the horizon, and horizon cash. Continued branches apply percentages to the parent snapshot and retain the original baseline for comparison. Demand changes are explicitly synthetic counterfactual orders/history; actual buyer commitments and main-farm input remain unchanged. The date scrubber previews declared schedules only.

## Verification so far

- Existing regression suite: ` .venv/bin/python -m pytest tests -q --ignore=tests/gameplay` — **202 passed**, 104.85s.
- Initial scenario suite: `.venv/bin/python -m pytest tests/gameplay/test_scenarios.py -q` — **16 passed**, 18.06s. More cases added subsequently; final run pending.
- Real PostgreSQL concurrent-create/run and store-recreation persistence: `.venv/bin/python -m pytest tests/gameplay/test_scenario_postgres.py -q` — **1 passed**, 2.10s.
- Generated public view contracts after adding batch/transplant references: `.venv/bin/python scripts/generate_web_contracts.py`; `.venv/bin/python -m pytest tests/contracts/test_view_contracts.py -q` — **3 passed**, 1.75s.
- Fly existing app capability verified using process-authenticated normal CLI; current app healthy. Private release session with completed numerical plan saved outside repository for post-deployment comparison. No credentials printed.
- Official DeepSeek Chat Completions documentation rechecked: https://api-docs.deepseek.com/api/create-chat-completion/ confirms the existing allowlisted model aliases and messages/JSON interface. Local service daily budget has only two requests remaining from earlier work; it is not reset or raised. Existing Fly service has room for the bounded release conversation trial.

## Pending

Frontend integration and browser/screenshot inspection; conversation/security/interrupt/budget tests; original asset visual review; full final automated checks; bounded deployed DeepSeek exchange/council; deployment and saved-state verification.
