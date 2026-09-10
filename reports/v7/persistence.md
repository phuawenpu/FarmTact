# V7 council research persistence review

Date: 9 September 2026 (UTC)

## Result

The isolated council-research persistence checks passed on the real local
PostgreSQL database `farmtact_edition_v7` through its Unix socket. Tests created
opaque temporary tenants and removed only records belonging to those tenants.
The schema and database were not dropped.

Three adversarial PostgreSQL cases passed:

- Two simultaneous applications of the same proposed edit serialized on the
  tenant revision: one advanced the input version and the stale request received
  `409`. Two simultaneous retries with one idempotency key returned the same
  state and left exactly one action row.
- A queued numerical job was marked running to represent interruption, then read
  through a new Store instance. Recovery returned it to queued with the exact
  frozen farm, controls, input hash, and version. Completion after the session
  advanced archived the old result and did not overwrite current inputs, create
  a selectable current result, alter the main farm, or create a planning run.
- PostgreSQL rejected a job whose session belonged to another tenant through the
  composite foreign key. HTTP reads and advisor-conversation creation also
  returned `404` for the other tenant.

The explicit advisor-conversation action froze the current completed research
version, its numerical strategies, controls, and input hash. The selected
simulation hash matched the conversation snapshot hash. Creation used no
provider budget or inference call; sending an advisor message was intentionally
outside this persistence test.

## Verification

```text
.venv/bin/pytest -q tests/council_research/test_postgres.py
3 passed, 2 dependency deprecation warnings in 5.05s

.venv/bin/pytest -q tests/council_research/test_sessions.py tests/council_research/test_postgres.py
10 passed, 2 dependency deprecation warnings in 14.75s
```

The warnings concern the existing FastAPI/Starlette TestClient compatibility
layer and do not affect these persistence assertions. The tests use concurrent
HTTP requests from threads and PostgreSQL transactions; they do not model
multi-region latency or a process killed midway through a database commit.
Actual provider calls: **0**.
